import struct
import sys
import tempfile
import unittest
from unittest import mock
import zlib
from pathlib import Path
from paths import ROOT
sys.path.insert(0,str(ROOT/'scripts'))
import game_glyphs
from glyph_archive import Toc,digest,pack_built,unpack_built
from glyph_mapping import Resolver,apply,KEY_DEFAULTS
from glyph_art import art,shape,rect,raster,BODY,INK
from glyph_gfx import tag,movie,patch,translated_place,tags,Bits
from glyph_texture import encode_block,encode,morton


def fixture_toc(payload=b'original'):
    sections=[(0xede8ada9,struct.pack('<II',0,1)),(0x506d7b8a,struct.pack('<Q',123)),
              (0x6d921d7b,b''),(0x65bcf461,struct.pack('<III',1,len(payload),0)),
              (0xdcd720b5,struct.pack('<II',0,5)),
              (0x398abff0,struct.pack('<II16s',0,10000,b'g00s000'))]
    data=bytearray(88)
    for i,(section,raw) in enumerate(sections):
        struct.pack_into('<III',data,16+12*i,section,len(data),len(raw));data.extend(raw)
    struct.pack_into('<IIII',data,0,0x44415431,0x04fb948f,len(data),6)
    return bytes.fromhex('af12af77')+struct.pack('<I',len(data))+zlib.compress(data)


def gfx_fixture():
    entries=[]
    for cid in range(1,5):
        entries.append(tag(32,shape(cid,(-680,680,-680,680),art(('pad','A')))))
        entries.append(tag(39,struct.pack('<HH',10+cid,1)+translated_place(cid,1,0,0)+tag(1)+tag(0)))
    timeline=[]
    for cid,label in enumerate(('button_a','button_b','button_x','button_y'),1):
        timeline.extend((tag(43,label.encode()+b'\0'),translated_place(10+cid,1,0,0),tag(1)))
    entries.append(tag(39,struct.pack('<HH',20,4)+b''.join(timeline)+tag(0)))
    entries.extend((tag(82,b'opaque action bytecode'),tag(1),tag(0)))
    result=bytearray(b'GFX\x15'+b'\0'*4+rect((0,2000,0,2000))+struct.pack('<HH',24<<8,1)+b''.join(entries))
    struct.pack_into('<I',result,4,len(result))
    return bytes(result)


def decoded_geometry(raw):
    """Independent solid-fill shape reader for the painter-order regression."""
    b=Bits(raw,2);bounds=b.rect();colors=[];paths={};points=[];fill=0;offset=0
    def styles():
        for _ in range(b.u(8)):
            if b.u(8)!=0:raise ValueError('not solid')
            colors.append(tuple(b.u(8) for _ in range(4)))
        if b.u(8):raise ValueError('unexpected line styles')
    def flush():
        if points:paths.setdefault(fill,[]).append(points.copy())
    styles();nf=b.u(4);nl=b.u(4);x=y=0
    while True:
        if b.u(1):
            if b.u(1)!=1:raise ValueError('unexpected curve')
            n=b.u(4)+2
            if b.u(1):x+=b.s(n);y+=b.s(n)
            elif b.u(1):y+=b.s(n)
            else:x+=b.s(n)
            points.append((x,y))
        else:
            flags=b.u(5)
            if not flags:flush();break
            if flags&1:flush();points=[];n=b.u(5);x=b.s(n);y=b.s(n);points.append((x,y))
            if flags&10:raise ValueError('unexpected fill side or line')
            if flags&4:fill=b.u(nf)+offset
            if flags&16:
                flush();points=[];b.align();offset=len(colors);styles();nf=b.u(4);nl=b.u(4)
    x,X,y,Y=bounds
    return [(colors[i-1],[[(100*(a-x)/(X-x),100*(v-y)/(Y-y)) for a,v in p] for p in contours])
            for i,contours in paths.items() if i]


class MappingTest(unittest.TestCase):
    def test_defaults_and_logical_interaction(self):
        r=Resolver('keyboard',{})
        self.assertEqual(r.resolve('cross'),('key','SPACE'))
        self.assertEqual(r.resolve('triangle'),('key','Q'))
        self.assertEqual(r.resolve('l3'),('key','Z'))
        self.assertEqual(r.resolve('stick_right'),('mouse','Mouse Move All'))

    def test_last_valid_alias_and_none(self):
        keys=apply(KEY_DEFAULTS,'cross=F24,cross=not-a-key,touchpad=Mouse Back,l3=None,circle=Left Ctrl')
        self.assertEqual(keys['cross'],'F24')
        self.assertEqual(keys['touchpad_left'],'Mouse Back')
        self.assertEqual(keys['l3'],'none')
        self.assertEqual(keys['circle'],'Left Ctrl')

    def test_key_families_and_mouse(self):
        r=Resolver('keyboard',{})
        for key in ('A','9','F1','F24','PageUp','Keypad 0','Keypad Enter','Left','Comma','Equals','Right Shift'):
            self.assertNotEqual(r.key(key),('key','?'),key)
        self.assertEqual(r.key('Unrecognized'),('key','?'))
        for key in ('Mouse Left','Mouse Right','Mouse Middle','Mouse Back','Mouse Forward','Wheel Up','Wheel Down','Mouse Move Left'):
            self.assertEqual(r.key(key),('mouse',key))
        self.assertEqual(apply(KEY_DEFAULTS,'cross=Keypad Equals')['cross'],'Space')

    def test_sticks_follow_individual_mapping(self):
        r=Resolver('keyboard',{'RATCHET_STICK_KEYS':'lx_neg=F1,ry_pos=Wheel Down'})
        self.assertEqual(r.resolve('stick_left')[1][0],('key','F1'))
        self.assertEqual(r.resolve('stick_right')[1][3],('mouse','Wheel Down'))

    def test_xbox_mapping_and_fixed_triggers(self):
        r=Resolver('xbox',{'RATCHET_PAD_MAP':'cross=y,l1=b,l2=a'})
        self.assertEqual(r.resolve('cross'),('pad','Y'))
        self.assertEqual(r.resolve('l1'),('pad','B'))
        self.assertEqual(r.resolve('l2'),('pad','LT'))

    def test_secondary_only_prompt_follows_alternate(self):
        r=Resolver('keyboard',{'RATCHET_KEY_MAP':'cross=None','RATCHET_KEY_MAP_ALT':'cross=F24'})
        self.assertEqual(r.resolve('cross'),('key','F24'))
        r=Resolver('keyboard',{'RATCHET_KEY_MAP_ALT':'cross=F24'})
        self.assertEqual(r.resolve('cross'),('key','SPACE'))

    def test_auto_fallback(self):
        self.assertEqual(game_glyphs.auto_style('Gamepad: none\n'),'keyboard')
        self.assertEqual(game_glyphs.auto_style('Gamepad: type=xboxone south=a east=b west=x north=y name=Test'),'xbox')
        for value in ('','Gamepad: type=ps5 south=cross','Gamepad: type=switchpro south=b east=a west=y north=x '):
            self.assertEqual(game_glyphs.auto_style(value),'off')

    def test_touchpad_hint_matches_actual_chord_and_keyboard_binding(self):
        self.assertEqual(Resolver('xbox',{}).resolve('touchpad_left'),
                         ('chord',(('pad','LB'),('pad','VIEW'))))
        remap=Resolver('xbox',{'RATCHET_PAD_MAP':'l1=b,touchpad_right=start'})
        self.assertEqual(remap.resolve('touchpad_left'),
                         ('chord',(('pad','B'),('pad','MENU'))))
        self.assertEqual(Resolver('keyboard',{'RATCHET_KEY_MAP':'touchpad_left=F2'}).
                         resolve('touchpad_left'),('key','F2'))


class ArchiveTest(unittest.TestCase):
    def test_overlay_round_trip_and_original(self):
        original=fixture_toc();toc=Toc(original);snapshot=bytes(toc.data)
        encoded,payload=toc.overlay({123:b'larger replacement payload'})
        name,offset,size,*_=Toc(encoded).locate(123)
        self.assertEqual(name,'rpglyph')
        self.assertEqual(payload[offset:offset+size],b'larger replacement payload')
        self.assertEqual(bytes(toc.data),snapshot)
        self.assertEqual(Toc(original).locate(123)[:3],('g00s000',5,8))
        self.assertEqual(game_glyphs.prepare('missing','missing','off',{})[0],[])

    def test_segment_identity_bounds_and_no_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'g00s000';p.write_bytes(b'12345original')
            before=p.read_bytes();toc=Toc(fixture_toc())
            self.assertEqual(toc.read(tmp,123,digest(b'original')),b'original')
            with self.assertRaises(ValueError):toc.read(tmp,123,'0'*64)
            self.assertEqual(p.read_bytes(),before)
            p.write_bytes(b'short')
            with self.assertRaises(ValueError):toc.read(tmp,123,digest(b'original'))

    def test_corrupt_toc_and_second_overlay_rejected(self):
        for raw in (b'',b'bad header',fixture_toc()[:-20]):
            with self.assertRaises((ValueError,zlib.error)):Toc(raw)
        changed,_=Toc(fixture_toc()).overlay({123:b'new'})
        with self.assertRaises(ValueError):Toc(changed).overlay({123:b'again'})

    def test_identity_failure_names_asset_and_never_mounts_old_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);game=root/'game';folder=game/'asset_archive'
            folder.mkdir(parents=True)
            toc=fixture_toc();source=b'12345original'
            (folder/'toc').write_bytes(toc);(folder/'g00s000').write_bytes(source)
            cache=root/'cache';cache.mkdir();stale=cache/'old-overlay';stale.write_bytes(b'stale')
            name='ui/textures/buttons/ps4/key_11.texture'
            wrong=digest(b'previously modified')
            with mock.patch.object(game_glyphs,'ASSETS',{name:(123,wrong)}), \
                    mock.patch.object(game_glyphs,'mounts') as mounts:
                with self.assertRaises(ValueError) as caught:
                    game_glyphs.prepare(game,cache,'keyboard',{})
            message=str(caught.exception)
            for detail in (name,'g00s000 at 5','asset=000000000000007b',
                           'expected_sha256='+wrong,'actual_sha256='+digest(b'original')):
                self.assertIn(detail,message)
            mounts.assert_not_called()
            self.assertEqual(list(cache.iterdir()),[stale])
            self.assertEqual((folder/'toc').read_bytes(),toc)
            self.assertEqual((folder/'g00s000').read_bytes(),source)
            self.assertEqual(game_glyphs.prepare(game,cache,'off',{})[0],[])

    def test_lz4_exact_lengths(self):
        for count in (1,14,15,16,270,4180):
            data=bytes(i%251 for i in range(count));header=bytearray(36);struct.pack_into('<II',header,4,count,0)
            raw=pack_built(bytes(header),data)
            self.assertEqual(unpack_built(raw),data)
            with self.assertRaises(ValueError):unpack_built(raw+b'garbage')
            with self.assertRaises(ValueError):unpack_built(raw[:-1])

    def test_exact_mount_paths(self):
        args=game_glyphs.mounts(Path(tempfile.gettempdir())/'glyphs')
        self.assertEqual(args[::2],['--mount']*4)
        self.assertEqual([a.split('=')[0] for a in args[1::2]],
            ['/app0/asset_archive/toc','/app0/asset_archive/rpglyph',
             '/hostapp/asset_archive/toc','/hostapp/asset_archive/rpglyph'])


class GfxTest(unittest.TestCase):
    def test_standalone_poi_sticks_and_map_hint_follow_mapping(self):
        # Minimal independent movies with the same dedicated character IDs.
        for path,ids in [('ui/export/hud/pois.gfx',(4,8,14,16,19,21,24,27,29)),
                         ('ui/export/hud/messages.gfx',(111,))]:
            bounds=(-544,544,-462,637)
            entries=[tag(32,shape(cid,bounds,art(('pad','R')))) for cid in ids]
            if path.endswith('pois.gfx'):
                for root,tid in ((18,17),(23,22),(26,25),(31,30)):
                    entries.extend((tag(37,struct.pack('<H',tid)+b'opaque text'),
                                    tag(39,struct.pack('<HH',root,1)+
                                        translated_place(tid,1,0,0)+tag(1)+tag(0))))
            entries.extend((tag(82,b'unchanged actions'),tag(1),tag(0)))
            raw=bytearray(b'GFX\x15'+b'\0'*4+rect((0,2000,0,2000))+
                          struct.pack('<HH',24<<8,1)+b''.join(entries))
            struct.pack_into('<I',raw,4,len(raw))
            for style,env in [('keyboard',{}),('keyboard',{'RATCHET_STICK_KEYS':
                    'rx_neg=Left,rx_pos=Right,ry_neg=Up,ry_pos=Down',
                    'RATCHET_KEY_MAP':'touchpad_left=F2'}),('xbox',{})]:
                resolver=Resolver(style,env);changed,report=patch(bytes(raw),path,resolver)
                _,actual,defs=movie(changed)
                for cid,logical in ((8,'cross'),(19,'stick_left'),(27,'stick_right')) if len(ids)>1 else ((111,'touchpad_left'),):
                    self.assertEqual(defs[cid],(32,shape(cid,bounds,art(resolver.resolve(logical)))))
                    self.assertEqual(report['logical_shapes'][str(cid)],logical)
                self.assertIn((82,b'unchanged actions'),actual)

    def test_overlapping_mouse_fills_preserve_painter_order(self):
        raw=shape(1,(0,2000,0,2000),art(('mouse','Mouse Left')))
        image=raster(decoded_geometry(raw),100,100)
        self.assertLess(max(abs(a-b) for a,b in zip(image.getpixel((50,65)),BODY)),5)
        self.assertLess(max(abs(a-b) for a,b in zip(image.getpixel((41,32)),INK)),5)

    def test_variable_size_preserves_bytecode_and_timeline(self):
        original=gfx_fixture();data,report=patch(original,'fixture',Resolver('keyboard',{'RATCHET_KEY_MAP':'cross=Mouse Left'}))
        other,_=patch(original,'fixture',Resolver('keyboard',{'RATCHET_KEY_MAP':'cross=F24'}))
        self.assertNotEqual(data,original);self.assertNotEqual(data,other)
        self.assertEqual(struct.unpack_from('<I',data,4)[0],len(data))
        self.assertEqual(report['shapes'],4)
        self.assertIn((82,b'opaque action bytecode'),movie(data)[1])
        self.assertEqual(movie(data)[2][20],movie(original)[2][20])

    def test_truncated_and_ambiguous_gfx(self):
        raw=gfx_fixture()
        with self.assertRaises(ValueError):movie(raw[:-1])
        with self.assertRaises(ValueError):list(tags(tag(32,b'abc')[:-1]))
        with self.assertRaises(ValueError):patch(raw.replace(b'button_y',b'button_z'),'fixture',Resolver('keyboard',{}))


class TextureTest(unittest.TestCase):
    def test_bc7_with_independent_decoder(self):
        from PIL import Image
        cases=[[(231,233,232,255)]*16,[(0,0,0,0)]*16,
               [(220,220,220,255) if i<8 else (34,34,34,255) for i in range(16)],
               [(110,110,110,i*17) for i in range(16)]]
        for pixels in cases:
            im=Image.frombytes('RGBA',(4,4),encode_block(pixels),'bcn',(7,'BC7'))
            result=[im.getpixel((x,y)) for y in range(4) for x in range(4)]
            self.assertLessEqual(max(abs(a[3]-b[3]) for a,b in zip(pixels,result)),43)
            self.assertLess(sum(abs(a[c]-b[c]) for a,b in zip(pixels,result) for c in range(4))/64,12)

    def test_swizzle_and_padding_bounds(self):
        from PIL import Image
        self.assertEqual({morton(x,y) for y in range(8) for x in range(8)},set(range(64)))
        for height,length in ((24,2048),(40,4096),(64,4096)):
            self.assertEqual(len(encode(Image.new('RGBA',(64,height),(30,30,30,255)),length)),length)
        with self.assertRaises(ValueError):encode(Image.new('RGBA',(64,64)),16)


if __name__=='__main__':unittest.main()
