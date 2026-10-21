"""Generate original RatchetPort SVG, PNG and multi-size Windows icons (Pillow).

Run without arguments to regenerate all icons. An optional ICO PNG pair retains
the old single-icon command line. No fonts or game artwork are needed.
"""
import sys
from pathlib import Path
from xml.sax.saxutils import quoteattr
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
SIZES = (16, 24, 32, 48, 64, 128, 256)
VARIANTS = {'ratchetport': None, 'ratchet-play': 'play',
            'ratchet-probe': 'runtime', 'ratchet-gpu-capabilities': 'gpu'}
NAVY, CYAN, GOLD, WHITE = '#101E35', '#38D9EA', '#FFBF52', '#F1FAFF'


def shapes(variant):
    """Shared vector geometry for SVG export and raster generation."""
    items = []
    def polygon(points, fill):
        items.append(('polygon', {'points': points, 'fill': fill}))
    # Cut corners and an interrupted portal rim remain legible at small sizes.
    polygon('58,12 198,12 244,58 244,198 198,244 58,244 12,198 12,58', NAVY)
    polygon('64,27 192,27 229,64 229,192 192,229 64,229 27,192 27,64', CYAN)
    polygon('69,40 187,40 216,69 216,187 187,216 69,216 40,187 40,69', NAVY)
    polygon('170,20 198,20 236,58 236,86 221,86 221,65 191,35 170,35', GOLD)
    polygon('72,64 141,64 177,88 177,126 151,146 188,191 151,191 '
            '119,151 101,151 101,191 72,191', WHITE)
    polygon('101,90 133,90 148,100 148,115 133,125 101,125', NAVY)
    if variant:
        polygon('177,160 225,160 248,183 248,226 226,248 177,248 155,226 155,183', NAVY)
        polygon('181,170 221,170 238,187 238,222 222,238 181,238 165,222 165,187', GOLD)
        if variant == 'play':
            polygon('190,184 190,225 222,205', NAVY)
        elif variant == 'runtime':
            polygon('187,189 216,189 216,218 187,218', NAVY)
            for offset in (191, 208):
                polygon(f'{offset},182 {offset+5},182 {offset+5},225 {offset},225', NAVY)
                polygon(f'180,{offset} 223,{offset} 223,{offset+5} 180,{offset+5}', NAVY)
            polygon('196,198 207,198 207,209 196,209', GOLD)
        else:
            for x, y in ((181, 210), (196, 198), (211, 185)):
                polygon(f'{x},{y} {x+9},{y} {x+9},225 {x},225', NAVY)
    return items


def render(variant, size):
    scale = size * 4 / 256
    canvas = Image.new('RGBA', (size * 4, size * 4))
    draw = ImageDraw.Draw(canvas)
    for _, attrs in shapes(variant):
        points = [tuple(float(n) * scale for n in pair.split(','))
                  for pair in attrs['points'].split()]
        draw.polygon(points, fill=attrs['fill'])
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def write_icon(variant, ico, png):
    frames = [render(variant, size) for size in SIZES]
    frames[-1].save(ico, sizes=[(s, s) for s in SIZES], append_images=frames[:-1])
    frames[-1].save(png)


def main():
    if len(sys.argv) == 3:
        write_icon(None, *sys.argv[1:])
        return
    if len(sys.argv) != 1:
        raise SystemExit('Usage: make_icon.py [output.ico output.png]')
    vector_dir = ROOT / 'packaging/icon'
    vector_dir.mkdir(exist_ok=True)
    for name, variant in VARIANTS.items():
        elements = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">',
                    f'<title>{name}</title>']
        for tag, attrs in shapes(variant):
            attributes = ' '.join(f'{key}={quoteattr(value)}' for key, value in attrs.items())
            elements.append(f'<{tag} {attributes}/>')
        (vector_dir / f'{name}.svg').write_text('\n'.join([*elements, '</svg>', '']), encoding='utf-8')
        write_icon(variant, ROOT / f'launcher/{name}.ico', ROOT / f'launcher/{name}.png')
        print(f'Generated {name}: SVG, PNG and ICO ({len(SIZES)} sizes)')


if __name__ == '__main__':
    main()
