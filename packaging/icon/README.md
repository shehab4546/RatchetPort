# RatchetPort application icons

Original geometric artwork for this project, distributed under the repository's
GPL-2.0 license. These icons contain no game artwork, fonts or third-party logos.

The cyan portal and white R identify RatchetPort. Gold badges distinguish direct
play (triangle), the runtime (chip), and GPU capabilities (bars).

Regenerate the SVG sources and the checked-in PNG/ICO assets with:

```sh
python packaging/windows/make_icon.py
```

Requires Pillow. The generator uses the same geometry for SVG and raster output.
ICO files contain 16, 24, 32, 48, 64, 128 and 256 pixel frames, individually
supersampled. Checked-in assets allow native builds without Python or Pillow.

Windows resource files embed the corresponding icon into each native product.
PyInstaller embeds `launcher/ratchetport.ico` into the launcher. The package also
includes the launcher's ICO/PNG and runtime PNG for window icons and shortcuts.
The Linux package uses the main PNG, including as the runtime fallback.
