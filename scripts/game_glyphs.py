# SPDX-License-Identifier: GPL-2.0-or-later
"""Immutable visual prompt overlay built only from verified installed assets."""
import json
import re
import shutil
import tempfile
from pathlib import Path
from glyph_archive import Toc,digest,ARCHIVE_NAME,LIMIT
from glyph_profile import ASSETS
from glyph_mapping import Resolver
from glyph_gfx import patch as patch_gfx
from glyph_texture import patch as patch_texture,TEXTURE_LOGICAL

VERSION=4


def auto_style(output):
    if 'Gamepad: none' in output:return 'keyboard'
    if re.search(r'^Gamepad: type=\S+ south=a east=b west=x north=y ',output,re.M):return 'xbox'
    return 'off'  # Unknown layouts and failed detection keep installed artwork.


def mounts(folder):
    result=[]
    for root in ('/app0','/hostapp'):
        for name in ('toc',ARCHIVE_NAME):
            path=str((folder/name).resolve())
            if len(path.encode('utf-8'))>=512:raise ValueError('Prompt cache path exceeds mount limit')
            result.extend(('--mount',f'{root}/asset_archive/{name}={path}'))
    return result


def prepare(game,cache,style,env):
    if style in ('off','playstation'):
        return [],{'style':'off','status':'Installed artwork; original archives unchanged'}
    resolver=Resolver(style,env)
    folder=Path(game)/'asset_archive';cache=Path(cache).resolve()
    if cache.is_relative_to(Path(game).resolve()):raise ValueError('Prompt cache must be outside game folder')
    toc_path=folder/'toc'
    if not 8<=toc_path.stat().st_size<=LIMIT:raise ValueError('Invalid prompt TOC size')
    original_toc=toc_path.read_bytes();toc=Toc(original_toc)
    originals={}
    for name,(aid,sha) in ASSETS.items():
        try:
            originals[name]=toc.read(folder,aid,sha)
        except (OSError,ValueError) as error:
            raise ValueError(f'{name}: {error}') from error
    fingerprint={'version':VERSION,'toc':digest(original_toc),'style':style,
                 'keys':resolver.keys,'sticks':resolver.sticks,'pad':resolver.pad,
                 'assets':{name:digest(raw) for name,raw in originals.items()}}
    key=digest(json.dumps(fingerprint,sort_keys=True).encode());target=cache/key
    if target.exists():
        if target.is_symlink() or target.resolve().parent!=cache:raise ValueError('Unsafe prompt cache directory')
        receipt_path=target/'receipt.json'
        if receipt_path.is_symlink() or receipt_path.stat().st_size>1<<20:raise ValueError('Unsafe prompt receipt')
        receipt=json.loads(receipt_path.read_text())
        if receipt.get('fingerprint')!=fingerprint:raise ValueError('Prompt cache receipt mismatch; remove this entry')
        for name in ('toc',ARCHIVE_NAME,'original.toc'):
            path=target/name
            if path.is_symlink() or path.stat().st_size>LIMIT or digest(path.read_bytes())!=receipt['files'][name]:
                raise ValueError('Prompt cache integrity mismatch; remove this entry')
        return mounts(target),{'style':style,'status':'Verified cache','coverage':receipt['coverage']}
    replacements={};coverage={}
    for name,raw in originals.items():
        if name.endswith('.gfx'):
            changed,report=patch_gfx(raw,name,resolver)
            if report['shapes']:replacements[ASSETS[name][0]]=changed;coverage[name]=report
        elif name.endswith('.texture'):
            number=int(name.rsplit('key_',1)[1].split('.')[0])
            if number in TEXTURE_LOGICAL:
                replacements[ASSETS[name][0]]=patch_texture(raw,TEXTURE_LOGICAL[number],resolver)
                coverage[name]={'logical':TEXTURE_LOGICAL[number]}
    if len(coverage)!=36:raise ValueError(f'Incomplete prompt coverage: {len(coverage)} assets')
    encoded,payload=toc.overlay(replacements)
    cache.mkdir(parents=True,exist_ok=True)
    temporary=Path(tempfile.mkdtemp(prefix='.building-',dir=cache))
    try:
        outputs={'toc':encoded,ARCHIVE_NAME:payload,'original.toc':original_toc}
        for name,raw in outputs.items():(temporary/name).write_bytes(raw)
        receipt={'fingerprint':fingerprint,'coverage':coverage,'files':{name:digest(raw) for name,raw in outputs.items()}}
        (temporary/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        temporary.rename(target)
    finally:
        if temporary.exists():shutil.rmtree(temporary)
    return mounts(target),{'style':style,'status':'Prepared 36 prompt assets','coverage':coverage}
