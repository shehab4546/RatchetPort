# SPDX-License-Identifier: GPL-2.0-or-later
"""Bounded GFX adapters preserving unrelated tags, timelines and ActionScript."""
import struct
from glyph_art import art,shape,Writer,nbits

SHAPES=(2,22,32,83)
LABELS=dict(button_a='cross',button_b='circle',button_x='square',button_y='triangle',
            trigger_left='l2',trigger_right='r2',bumper_left='l1',bumper_right='r1',
            stick_left='stick_left',stick_right='stick_right',
            button_left_stick='l3',button_right_stick='r3')
DEDICATED={
    'ui/export/hud/pois.gfx':{14:'triangle',4:'square',16:'l2',21:'r1',24:'l1',29:'r2'},
    'ui/export/hud/quickselect.gfx':{32:'l1',34:'l2',37:'r1',39:'r2'},
    'ui/export/popup/bataliaturretui.gfx':{11:'l2',13:'square',15:'l1'},
    'ui/export/hud/progressbar.gfx':{33:'l1',35:'l2'},
    'ui/export/pause/cardsmenu.gfx':{403:'l1',405:'l2',407:'r1',409:'r2'},
    'ui/export/pause/weaponsmenu.gfx':{78:'l2',80:'l1',85:'r2',87:'r1'},
}


class Bits:
    def __init__(self,data,pos=0):self.data=data;self.pos=pos*8
    def u(self,n):
        if n<0 or self.pos+n>len(self.data)*8:raise ValueError('Truncated GFX bits')
        v=0
        for _ in range(n):v=(v<<1)|((self.data[self.pos//8]>>(7-self.pos%8))&1);self.pos+=1
        return v
    def s(self,n):
        v=self.u(n);return v-(1<<n) if n and v&(1<<(n-1)) else v
    def align(self):self.pos=(self.pos+7)//8*8
    def rect(self):
        n=self.u(5);r=tuple(self.s(n) for _ in range(4));self.align();return r
    def matrix(self):
        a=d=1;b=c=0
        if self.u(1):n=self.u(5);a=self.s(n)/65536;d=self.s(n)/65536
        if self.u(1):n=self.u(5);b=self.s(n)/65536;c=self.s(n)/65536
        n=self.u(5);x=self.s(n);y=self.s(n);self.align();return a,b,c,d,x,y


def tags(data,start=0):
    pos=start
    for _ in range(200000):
        if pos+2>len(data):raise ValueError('Missing GFX End tag')
        header,=struct.unpack_from('<H',data,pos);pos+=2
        code,size=header>>6,header&63
        if size==63:
            if pos+4>len(data):raise ValueError('Truncated GFX tag size')
            size,=struct.unpack_from('<I',data,pos);pos+=4
        if pos+size>len(data):raise ValueError('GFX tag exceeds stream')
        yield code,data[pos:pos+size];pos+=size
        if code==0:
            if pos!=len(data):raise ValueError('Trailing GFX bytes')
            return
    raise ValueError('Too many GFX tags')


def tag(code,data=b''):
    return (struct.pack('<H',code<<6|len(data)) if len(data)<63 else
            struct.pack('<HI',code<<6|63,len(data)))+data


def placement(code,data):
    if code not in (26,70):return None
    if not data:raise ValueError('Empty placement')
    flags=data[0];pos=1 if code==26 else 2
    if code==70 and data[1]&8:raise ValueError('Unsupported class-based placement')
    depth,=struct.unpack_from('<H',data,pos);pos+=2;cid=None
    if flags&2:cid,=struct.unpack_from('<H',data,pos);pos+=2
    return depth,cid,pos


def movie(data):
    if len(data)<12 or data[:3]!=b'GFX' or struct.unpack_from('<I',data,4)[0]!=len(data):
        raise ValueError('Invalid uncompressed GFX header')
    bits=Bits(data,8);bits.rect();start=bits.pos//8+4
    entries=list(tags(data,start));definitions={}
    for code,payload in entries:
        if code in SHAPES+(39,37):
            cid,=struct.unpack_from('<H',payload)
            if cid in definitions:raise ValueError('Duplicate GFX character')
            definitions[cid]=(code,payload)
    return start,entries,definitions


def label_states(payload):
    live={};label=None
    for code,data in tags(payload,4):
        p=placement(code,data)
        if p:
            depth,cid,_=p
            if cid is not None:live[depth]=cid
        elif code==28:
            depth,=struct.unpack('<H',data);live.pop(depth,None)
        elif code==43:label=data.split(b'\0')[0].decode('ascii')
        elif code==1 and label is not None:
            yield label,tuple(live.values());label=None


def leaves(cid,definitions,trail=()):
    if cid in trail or len(trail)>20:raise ValueError('Recursive prompt sprite')
    if cid not in definitions:return set(),set()
    code,data=definitions[cid]
    if code in SHAPES:return {cid},set()
    if code==37:return set(),{cid}
    shapes=set();texts=set()
    if code==39:
        for c,b in tags(data,4):
            p=placement(c,b)
            if p and p[1] is not None:
                s,t=leaves(p[1],definitions,(*trail,cid));shapes|=s;texts|=t
    return shapes,texts


def translated_place(cid,depth,x,y):
    w=Writer();w.bits(0,2);n=nbits((x,y));w.bits(n,5);w.signed(x,n);w.signed(y,n)
    return tag(26,bytes([6])+struct.pack('<HH',depth,cid)+w.finish())


def patch(data,path,resolver):
    start,entries,definitions=movie(data)
    targets={};suppress=set();labels_seen=set();replacements={};added=[]
    next_id=max(definitions,default=0)+1

    def assign(cid,logical):
        if cid not in definitions or definitions[cid][0] not in SHAPES:
            raise ValueError(f'Missing dedicated prompt {path}:{cid}')
        if cid in targets and targets[cid]!=logical:raise ValueError('Conflicting logical prompt')
        targets[cid]=logical

    for cid,(code,payload) in list(definitions.items()):
        if code!=39:continue
        states=dict(label_states(payload))
        if 'button_a' not in states:continue
        if not all(label in states for label in ('button_a','button_b','button_x','button_y')):
            raise ValueError('Incomplete generic prompt timeline')
        for label,logical in LABELS.items():
            if label not in states:continue
            roots=states[label];shapes=set();texts=set()
            for root in roots:
                s,t=leaves(root,definitions);shapes|=s;texts|=t
            if len(shapes)!=1:raise ValueError(f'Ambiguous prompt frame {path}:{label}')
            shape_id=next(iter(shapes))
            if shape_id in targets and targets[shape_id]!=logical:
                # RaceScreens shares one background between L and R sticks.
                if len(roots)!=1:raise ValueError('Ambiguous shared prompt')
                root=roots[0];rc,rb=replacements.get(root,definitions[root]);rebuilt=[];changed=False
                if rc!=39 or next_id>65535:raise ValueError('Cannot clone shared prompt')
                for c,b in tags(rb,4):
                    p=placement(c,b)
                    if p and p[1]==shape_id:
                        b=bytearray(b);struct.pack_into('<H',b,p[2]-2,next_id);b=bytes(b);changed=True
                    rebuilt.append(tag(c,b))
                if not changed:raise ValueError('Shared prompt is not directly placed')
                replacements[root]=(rc,rb[:4]+b''.join(rebuilt))
                sc,sb=definitions[shape_id];definitions[next_id]=(sc,struct.pack('<H',next_id)+sb[2:])
                added.append(next_id);shape_id=next_id;next_id+=1
            assign(shape_id,logical);labels_seen.add(label)
            for root in roots:suppress.update((root,t) for t in texts)
    for cid,logical in DEDICATED.get(path,{}).items():assign(cid,logical)
    if path=='ui/export/hud/pois.gfx':suppress.update(((18,17),(23,22),(26,25),(31,30)))
    for cid,logical in targets.items():
        _,payload=definitions[cid];bounds=Bits(payload,2).rect()
        replacements[cid]=(32,shape(cid,bounds,art(resolver.resolve(logical))))
    for root,text_id in suppress:
        code,payload=replacements.get(root,definitions[root])
        if code!=39:raise ValueError('Unsupported stick text placement')
        rebuilt=[];removed=False
        for c,b in tags(payload,4):
            p=placement(c,b)
            if p and p[1]==text_id:
                if b[0]&32:
                    # Keep POI's named TextField for AS3; clear its baked label.
                    tc,tb=definitions[text_id];html=tb.find(b'<p ')
                    if tc!=37 or html<0 or not tb.endswith(b'</p>\0'):
                        raise ValueError('Unsupported named prompt text')
                    replacements[text_id]=(tc,tb[:html]+b'\0');rebuilt.append(tag(c,b))
                removed=True;continue
            rebuilt.append(tag(c,b))
        if not removed:raise ValueError('Prompt text was not directly placed')
        replacements[root]=(code,payload[:4]+b''.join(rebuilt))
    added=[tag(*replacements.pop(cid)) for cid in added]
    if path=='ui/export/hud/quickselect.gfx' and resolver.style=='keyboard':
        # Upright labels between rotated backgrounds and weapon-icon layers.
        cid=next_id;code,payload=definitions[81];new=[]
        for i,(logical,x,y) in enumerate((('up',0,-1035),('down',0,1037),
                                         ('right',1036,0),('left',-1036,0))):
            added.append(tag(32,shape(cid+i,(-450,450,-300,300),art(resolver.resolve(logical),False))))
            new.append(translated_place(cid+i,2+i*2,x,y))
        rebuilt=[];inserted=False
        for c,b in tags(payload,4):
            if c==1 and not inserted:rebuilt.extend(new);inserted=True
            rebuilt.append(tag(c,b))
        if not inserted:raise ValueError('QuickSelect has no display frame')
        replacements[81]=(code,payload[:4]+b''.join(rebuilt))
    out=[]
    for code,payload in entries:
        if code==39 and added:out.extend(added);added=[]
        if code in SHAPES+(39,37):
            cid,=struct.unpack_from('<H',payload);code,payload=replacements.get(cid,(code,payload))
        out.append(tag(code,payload))
    result=bytearray(data[:start]+b''.join(out));struct.pack_into('<I',result,4,len(result));movie(result)
    return bytes(result),{'shapes':len(targets),'text_layers':len(suppress),'labels':sorted(labels_seen),
                         'logical_shapes':{str(cid):logical for cid,logical in targets.items()}}
