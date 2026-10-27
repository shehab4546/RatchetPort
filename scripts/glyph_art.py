# SPDX-License-Identifier: GPL-2.0-or-later
"""Shared vector geometry for GFX and rasterized game prompts."""
import math
import struct
from glyph_font import GLYPHS

INK=(231,233,232,255)
RIM=(111,116,119,255)
BODY=(34,33,35,255)
COLORS={'A':(132,193,134,255),'B':(223,113,111,255),
        'X':(129,167,212,255),'Y':(222,196,117,255)}


def rounded(x,y,w,h,r):
    return [(cx+r*math.cos(a+i*math.pi/12),cy+r*math.sin(a+i*math.pi/12))
            for cx,cy,a in ((x+w-r,y+r,-math.pi/2),(x+w-r,y+h-r,0),
                           (x+r,y+h-r,math.pi/2),(x+r,y+r,math.pi)) for i in range(7)]


def text(value,box=(12,24,76,50),color=INK):
    value=value.upper()
    if not value or any(c not in GLYPHS for c in value):value='?'
    x,y,w,h=box
    width=sum(GLYPHS[c][0] for c in value)
    scale=min(w/max(width,1),h/1493)
    cursor=x+(w-width*scale)/2
    baseline=y+(h+1493*scale)/2
    out=[]
    for c in value:
        advance,paths=GLYPHS[c]
        out.append((color,[[(cursor+px*scale,baseline-py*scale) for px,py in path] for path in paths]))
        cursor+=advance*scale
    return out


def line(points,width=3,color=INK):
    out=[]
    for (x,y),(X,Y) in zip(points,points[1:]):
        length=math.hypot(X-x,Y-y)
        if not length:continue
        dx,dy=-(Y-y)*width/2/length,(X-x)*width/2/length
        out.append((color,[[(x+dx,y+dy),(X+dx,Y+dy),(X-dx,Y-dy),(x-dx,y-dy)]]))
    return out


def transform(geometry,sx=1,sy=1,dx=0,dy=0):
    return [(c,[[(x*sx+dx,y*sy+dy) for x,y in p] for p in paths]) for c,paths in geometry]


def arrow(direction,box=(25,25,50,50)):
    p=[(0,-1),(.7,-.25),(.25,-.25),(.25,1),(-.25,1),(-.25,-.25),(-.7,-.25)]
    a={'up':0,'right':math.pi/2,'down':math.pi,'left':-math.pi/2}[direction]
    x,y,w,h=box
    return [(INK,[[(x+w/2+(u*math.cos(a)-v*math.sin(a))*w/2,
                     y+h/2+(u*math.sin(a)+v*math.cos(a))*h/2) for u,v in p]])]


def art(spec,background=True):
    kind,value=spec
    out=[]
    if background:
        r=43 if kind=='pad' and value in COLORS else 11
        out=[(RIM,[rounded(4,6,92,88,r)]),(BODY,[rounded(6,7,88,84,max(2,r-2))])]
    if kind in ('key','pad'):
        if value=='SPACE':out+=line([(24,47),(24,59),(76,59),(76,47)],4)
        elif value=='ENTER':
            out+=line([(74,34),(74,53),(28,53),(39,42)],4)+line([(28,53),(39,64)],4)
        elif value=='DPAD':
            for direction,box in [('up',(38,15,24,24)),('down',(38,61,24,24)),
                                  ('left',(15,38,24,24)),('right',(61,38,24,24))]:out+=arrow(direction,box)
        else:out+=text(value,(11,24,78,50),COLORS.get(value,INK) if kind=='pad' else INK)
    elif kind=='arrow':out+=arrow(value)
    elif kind=='stick':
        out += [(INK,[rounded(25,25,50,50,25)]),(BODY,[rounded(28,28,44,44,22)])]
        out += text(value,(31,36,38,27))
        for direction,box in [('up',(42,9,16,16)),('down',(42,75,16,16)),
                              ('left',(9,42,16,16)),('right',(75,42,16,16))]:out+=arrow(direction,box)
    elif kind=='cluster':
        for child,(x,y) in zip(value,((2,58),(66,58),(34,8),(34,58))):
            out+=transform(art(child),.32,.4,x,y)
    elif kind=='chord':
        out+=transform(art(value[0]),.44,.66,1,17)+transform(art(value[1]),.44,.66,55,17)
        out+=text('+',(44,38,12,22))
    elif kind=='mouse':
        out += [(INK,[rounded(33,18,34,65,14)]),(BODY,[rounded(36,21,28,59,11)])]
        out += line([(50,20),(50,45),(35,45)],2)+line([(50,45),(65,45)],2)
        if value in ('Mouse Left','Mouse Right'):
            out += [(INK,[rounded(37 if value=='Mouse Left' else 52,24,11,17,3)])]
        elif value=='Mouse Middle':out += [(INK,[rounded(46,27,8,16,3)])]
        elif value in ('Mouse Back','Mouse Forward'):
            out += [(INK,[rounded(24,57 if value=='Mouse Back' else 40,6,14,2)])]
        elif value.startswith('Wheel '):
            out += arrow(value.split()[-1].lower(),(40,47,20,28))+[(INK,[rounded(47,26,6,14,2)])]
        else:
            direction=value.split()[-1].lower()
            for dr,x in [('left',9),('right',73)]:
                if direction in (dr,'all'):out+=arrow(dr,(x,37,18,25))
            for dr,y in [('up',1),('down',83)]:
                if direction in (dr,'all'):out+=arrow(dr,(42,y,16,16))
    else:raise ValueError('Unknown prompt design')
    return out


class Writer:
    def __init__(self):self.data=bytearray();self.value=0;self.count=0
    def bits(self,value,count):
        if count<0 or value<0 or value>=1<<count:raise ValueError('SWF bit value out of bounds')
        for i in range(count-1,-1,-1):
            self.value=self.value*2+((value>>i)&1);self.count+=1
            if self.count==8:self.data.append(self.value);self.count=self.value=0
    def signed(self,value,count):self.bits(value&((1<<count)-1),count)
    def finish(self):
        if self.count:self.bits(0,8-self.count)
        return bytes(self.data)


def nbits(values):return max(1,max(abs(v).bit_length()+1 for v in values))


def rect(bounds):
    w=Writer();n=nbits(bounds)
    if n>31:raise ValueError('SWF bounds overflow')
    w.bits(n,5)
    for v in bounds:w.signed(v,n)
    return w.finish()


def shape(cid,bounds,geometry):
    """DefineShape3 payload with source ID and source bounds."""
    x,X,y,Y=bounds
    layers=[(color,paths) for color,paths in geometry if paths]
    if not layers:raise ValueError('Empty prompt geometry')
    fs=b'\1\0'+bytes(layers[0][0])+b'\0'
    w=Writer();w.bits(1,4);w.bits(0,4)
    for layer,(color,paths) in enumerate(layers):
        if layer:
            # A new style group is a new painter layer. Reusing a fill index
            # would merge overlapping contours and turn mouse bodies into holes.
            w.bits(0,1);w.bits(16,5);w.finish()
            w.data.extend(b'\1\0'+bytes(color)+b'\0')
            w.bits(1,4);w.bits(0,4)
        for path in paths:
            points=[(round(x+px*(X-x)/100),round(y+py*(Y-y)/100)) for px,py in path]
            if len(points)<3:continue
            start=points[0];n=nbits(start)
            w.bits(0,1);w.bits(5,5);w.bits(n,5)
            for v in start:w.signed(v,n)
            w.bits(1,1);previous=start
            for point in points[1:]+[start]:
                dx,dy=point[0]-previous[0],point[1]-previous[1];previous=point
                if not dx and not dy:continue
                n=max(2,nbits((dx,dy)))
                if n>17:raise ValueError('SWF edge overflow')
                w.bits(3,2);w.bits(n-2,4);w.bits(1,1);w.signed(dx,n);w.signed(dy,n)
    w.bits(0,6)
    return struct.pack('<H',cid)+rect(bounds)+fs+w.finish()


def raster(geometry,width=64,height=64):
    from PIL import Image,ImageDraw,ImageChops
    size=(width*4,height*4);out=Image.new('RGBA',size)
    for color,paths in geometry:
        mask=Image.new('1',size)
        for path in paths:
            layer=Image.new('1',size)
            ImageDraw.Draw(layer).polygon([(x*size[0]/100,y*size[1]/100) for x,y in path],fill=1)
            mask=ImageChops.logical_xor(mask,layer)
        out.paste(color,(0,0,*size),mask)
    return out.resize((width,height),Image.Resampling.LANCZOS)
