# SPDX-License-Identifier: GPL-2.0-or-later
"""CUSA01047 BC7 prompts: 8x8-block Morton tiles, unchanged descriptors.

BC7 reference: https://learn.microsoft.com/en-us/windows/win32/direct3d11/bc7-format
"""
import struct
from glyph_archive import unpack_built,pack_built
from glyph_art import art,raster

TEXTURE_LOGICAL={0:'dpad_all',1:'down',2:'left',3:'right',4:'up',5:'l1',6:'l2',7:'r1',8:'r2',
                 9:'l3',10:'stick_left',11:'r3',12:'stick_right',14:'options',15:'cross',
                 16:'square',17:'triangle',18:'circle',20:'touchpad_left'}
WEIGHTS=(0,4,9,13,17,21,26,30,34,38,43,47,51,55,60,64)


def morton(x,y):return sum(((x>>i)&1)<<(2*i)|((y>>i)&1)<<(2*i+1) for i in range(3))


def encode_block(pixels):
    if max(p[3] for p in pixels)-min(p[3] for p in pixels)>16:return encode_alpha_block(pixels)
    def distance(a,b):return sum((a[i]-b[i])**2 for i in range(4))
    a=pixels[0];b=max(pixels,key=lambda p:distance(a,p));a=max(pixels,key=lambda p:distance(b,p))
    def quantize(color):
        choices=[]
        for bit in (0,1):
            q=tuple(max(0,min(127,round((v-bit)/2)))*2+bit for v in color)
            choices.append((distance(color,q),q,bit))
        return min(choices)[1:]
    a,pa=quantize(a);b,pb=quantize(b)
    palette=[tuple(((64-w)*a[c]+w*b[c]+32)>>6 for c in range(4)) for w in WEIGHTS]
    indices=[min(range(16),key=lambda i:distance(p,palette[i])) for p in pixels]
    if indices[0]>=8:a,b=b,a;pa,pb=pb,pa;indices=[15-i for i in indices]
    bits=64;pos=7
    for c in range(4):
        for endpoint in (a,b):bits|=(endpoint[c]>>1)<<pos;pos+=7
    bits|=pa<<pos;pos+=1;bits|=pb<<pos;pos+=1
    for i,index in enumerate(indices):bits|=index<<pos;pos+=3 if i==0 else 4
    if pos!=128:raise ValueError('Invalid BC7 block length')
    return bits.to_bytes(16,'little')


def encode_alpha_block(pixels):
    """Mode 5 keeps edge opacity independent of the body and rim colors."""
    visible=[p[:3] for p in pixels if p[3]>16] or [(0,0,0)]
    def distance(a,b):return sum((x-y)**2 for x,y in zip(a,b))
    a=visible[0];b=max(visible,key=lambda p:distance(a,p));a=max(visible,key=lambda p:distance(b,p))
    a=tuple(round(v*127/255) for v in a);b=tuple(round(v*127/255) for v in b)
    A=tuple((v<<1)|(v>>6) for v in a);B=tuple((v<<1)|(v>>6) for v in b)
    palette=[tuple(((64-w)*A[c]+w*B[c]+32)>>6 for c in range(3)) for w in (0,21,43,64)]
    indices=[min(range(4),key=lambda i:distance(p[:3],palette[i])) if p[3]>16 else 0 for p in pixels]
    if indices[0]>=2:a,b=b,a;indices=[3-i for i in indices]
    lo=min(p[3] for p in pixels);hi=max(p[3] for p in pixels)
    alpha=[((64-w)*lo+w*hi+32)>>6 for w in (0,21,43,64)]
    ai=[min(range(4),key=lambda i:abs(p[3]-alpha[i])) for p in pixels]
    if ai[0]>=2:lo,hi=hi,lo;ai=[3-i for i in ai]
    bits=32;pos=8
    for c in range(3):
        for endpoint in (a,b):bits|=endpoint[c]<<pos;pos+=7
    bits|=lo<<pos;pos+=8;bits|=hi<<pos;pos+=8
    for values in (indices,ai):
        for i,index in enumerate(values):bits|=index<<pos;pos+=1 if i==0 else 2
    if pos!=128:raise ValueError('Invalid BC7 alpha block')
    return bits.to_bytes(16,'little')


def encode(image,stream_size):
    width,height=image.size
    if width!=64 or height not in (24,40,64):raise ValueError('Unsupported prompt dimensions')
    blocks_y=((height+31)//32)*8
    if 16*blocks_y*16!=stream_size:raise ValueError('Texture padding mismatch')
    pixels=image.load();out=bytearray(stream_size);cache={}
    for by in range(blocks_y):
        for bx in range(16):
            block=tuple(pixels[bx*4+x,by*4+y] if by*4+y<height else (0,0,0,0)
                        for y in range(4) for x in range(4))
            if block not in cache:cache[block]=encode_block(block)
            index=((by//8)*2+bx//8)*64+morton(bx%8,by%8)
            out[index*16:(index+1)*16]=cache[block]
    return bytes(out)


def inspect(raw):
    data=unpack_built(raw)
    if (len(data)<84 or data[:4]!=b'1TAD' or struct.unpack_from('<II',data,8)!=(84,1)
            or struct.unpack_from('<III',data,16)!=(0x4ede3593,48,36)):
        raise ValueError('Unsupported prompt texture header')
    stream,unused,width,height,pitch,stored_height,depth,mips,fmt,tile=struct.unpack_from('<II8H',data,48)
    if (stream!=len(data)-84 or unused or width!=64 or pitch!=64 or stored_height!=height
            or height not in (24,40,64) or (depth,mips,fmt,tile)!=(1,16,98,13)):
        raise ValueError('Unsupported prompt texture descriptor')
    return data,width,height


def decode(raw):
    """Independent Pillow BC7 decoder for verification and previews."""
    from PIL import Image
    data,width,height=inspect(raw);blocks_y=((height+31)//32)*8;linear=bytearray(len(data)-84)
    for y in range(blocks_y):
        for x in range(16):
            index=((y//8)*2+x//8)*64+morton(x%8,y%8)
            linear[(y*16+x)*16:(y*16+x+1)*16]=data[84+index*16:84+(index+1)*16]
    return Image.frombytes('RGBA',(64,blocks_y*4),bytes(linear),'bcn',(7,'BC7')).crop((0,0,width,height))


def patch(raw,logical,resolver):
    data,width,height=inspect(raw)
    pixels=raster(art(resolver.resolve(logical)),width,height)
    stream=encode(pixels,len(data)-84)
    result=pack_built(raw[:36],data[:84]+stream)
    if unpack_built(result)!=data[:84]+stream:raise ValueError('Texture round trip failed')
    return result
