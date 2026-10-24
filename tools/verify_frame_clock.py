# SPDX-License-Identifier: GPL-2.0-or-later
"""Execute only fingerprinted clock routines with a synthetic TSC (Linux x86-64 AVX).

No game entry point, renderer, audio or gameplay runs. No game bytes are exported.
This is an isolated native-instruction experiment, not gameplay acceptance.
"""
from pathlib import Path
import sys,struct,mmap,ctypes,json,argparse,platform
if sys.platform != 'linux' or platform.machine() != 'x86_64':
    raise SystemExit('Requires Linux x86-64 using the System V ABI')
if ' avx ' not in Path('/proc/cpuinfo').read_text():
    raise SystemExit('Requires AVX CPU support')
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--game-dir',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
if args.output.exists() or args.output.resolve().is_relative_to(args.game_dir.resolve()):
    parser.error('Use a new output file outside the original game folder')
sys.path.insert(0,str(Path(__file__).resolve().parents[1] / 'scripts'))
from ratchet_binary_audit import Binary
from ratchet_patches import PROFILE,digest,compile_groups
from frame_timing import FPS60_GROUP
b=Binary((args.game_dir / 'eboot.bin').read_bytes())
assert digest(b.source).hex()==PROFILE['source_sha256']
assert digest(b.elf).hex()==PROFILE['elf_sha256']
size=max(p['vaddr']+p['memsz'] for p in b.segments)
m=mmap.mmap(-1,size,prot=mmap.PROT_READ|mmap.PROT_WRITE|mmap.PROT_EXEC)
for p in b.segments:m[p['vaddr']:p['vaddr']+p['filesz']]=b.elf[p['offset']:p['offset']+p['filesz']]
writes,prepared,skipped=compile_groups(b,m[:],[(p['vaddr'],p['memsz'],p['flags']) for p in b.segments],[],[FPS60_GROUP])
assert prepared==[FPS60_GROUP] and not skipped
base=ctypes.addressof(ctypes.c_char.from_buffer(m)); ticks=ctypes.c_uint64(0)
# Redirect only ReadTsc in this isolated clock experiment, never in the patch.
m[0x2c88198:0x2c88198+14]=b'\x48\xb8'+struct.pack('<Q',ctypes.addressof(ticks))+b'\x48\x8b\x00\xc3'
init=ctypes.CFUNCTYPE(None,ctypes.c_void_p,ctypes.c_int,ctypes.c_double,ctypes.c_double)(base+0x171e710)
tick=ctypes.CFUNCTYPE(None,ctypes.c_void_p,ctypes.c_double)(base+0xe6c760)
clock=ctypes.create_string_buffer(0x80); settings=ctypes.create_string_buffer(0x80)
frame=base+0x4a49a60
period=struct.unpack('<f',bytes.fromhex('0cac883c'))[0]
# Run the actual settings copy and alternate interval initialization as a small callable.
copy=mmap.mmap(-1,4096,prot=7);copybase=ctypes.addressof(ctypes.c_char.from_buffer(copy))
copyfn=ctypes.CFUNCTYPE(None,ctypes.c_void_p,ctypes.c_void_p)(copybase)
results=[]
for patched in (False,True):
 for address,before,after in writes:m[address:address+len(before)]=after if patched else before
 copy[:25]=m[0x17b7664:0x17b767c]+b'\xc3'
 for smooth in (0,1):
  for interval in (2.,3.):
   for minimum in (0.,1/30):
    ctypes.memset(clock,0,0x80);struct.pack_into('<d',clock,8,1e9)
    struct.pack_into('<ff',settings,0x24,interval,7.)
    copyfn(frame,ctypes.addressof(settings));struct.pack_into('<f',m,0x4a49a78,period)
    assert struct.unpack_from('<f',m,0x4a49a80)[0]==7
    ticks.value=0;init(ctypes.addressof(clock),smooth,minimum,.25)
    floor,upper=struct.unpack_from('<dd',clock,0x40)
    target=period if patched else max(period*interval,minimum)
    assert abs(floor-target)<1e-7 and upper==.25
    elapsed=0.
    # 60 seconds of deterministic TSC, with recurring frame drops.
    for n in range(3600 if patched else 1800):
     dt=(period if patched else period*interval)*(2 if n%100==99 else 1)
     elapsed+=dt;ticks.value=round(elapsed*1e9);tick(ctypes.addressof(clock),1.)
    game=struct.unpack_from('<d',clock,0x30)[0]
    assert abs(game/elapsed-1)<.01,(patched,smooth,interval,minimum,game,elapsed)
    # Time scale zero is pause; half speed remains half speed.
    ticks.value+=round(period*4*1e9);tick(ctypes.addressof(clock),0.)
    assert struct.unpack_from('<d',clock,0x38)[0]==0.
    struct.pack_into('<d',clock,0x50,.5)
    for n in range(8):ticks.value+=round(period*4*1e9);tick(ctypes.addressof(clock),1.)
    assert abs(struct.unpack_from('<d',clock,0x38)[0]-period*2)<1e-7
    results.append(dict(patched=patched,smoothing=smooth,settings_interval=interval,caller_minimum=minimum,floor=floor,wall_seconds=elapsed,game_seconds=game,ratio=game/elapsed))
# Regression demonstration: changing only render interval leaves caller's 1/30 floor.
address,before,after=writes[0] # sorted: clock site first
assert address==0x171e7a1
m[address:address+len(before)]=before
ticks.value=0;ctypes.memset(clock,0,0x80);struct.pack_into('<d',clock,8,1e9)
init(ctypes.addressof(clock),0,1/30,.25)
for n in range(3600):ticks.value=round((n+1)*period*1e9);tick(ctypes.addressof(clock),1.)
regression=struct.unpack_from('<d',clock,0x30)[0]/(3600*period)
assert regression>1.9
out={'source_sha256':PROFILE['source_sha256'],'verified_writes':len(writes),'clock_only_experiment':True,'gameplay_tested':False,'cases':results,'interval_only_speed_ratio':regression}
args.output.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'cases':len(results),'max_drift_percent':max(abs(r['ratio']-1)*100 for r in results),'interval_only_speed_ratio':regression,'source_sha256':PROFILE['source_sha256']}))
