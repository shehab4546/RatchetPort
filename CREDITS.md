# Credits and licensing

RatchetPort builds directly on **FelipePrado0/SpartanPort**: https://github.com/FelipePrado0/SpartanPort . The original loader, runtime, launcher, packaging work and contributions remain credited to their original authors in Git history. Renaming identifiers and local-change comments does not transfer authorship.

Additional ancestry includes **deadinside28/bloodborne_pc** (original native runtime) and **Supermedo / Mohammed Albarghouthi's Windows port** (https://github.com/Supermedo/bloodborne_pc), and renderer work from **cuesta4's eltutz branch** (https://github.com/cuesta4/shadPS4/tree/eltutz). **WilkPrintes** designed and built the original SpartanPort website. Their contributions remain credited in the project's history.

The GPU renderer, shader recompiler and supporting emulation code derive from **shadPS4**: https://github.com/shadps4-emu/shadPS4 . See `gpu/VENDOR.txt` for the vendored revision and backports. References to KrachDev/shadPS4_GOW3 in diagnostic comments identify the source of research, not active game hooks.

Dependencies include FSR-Vulkan/FidelityFX and AMD's upstream work; Vulkan-Headers, Vulkan-Loader, SPIRV-Headers, SPIRV-Tools, glslang and SPIRV-Cross from Khronos and contributors; Dear ImGui; SDL; FFmpeg; Boost; fmt; xxHash; robin-map; magic_enum; miniz; Xbyak; Sirit; Vulkan Memory Allocator; Zydis/Zycore; LibAtrac9; Python, Tcl/Tk, Pillow, iced-x86 and PyInstaller. Cinzel Black is by its original font authors under the bundled SIL Open Font License (`launcher/OFL-Cinzel.txt`). The optional DLSS bridge preserves IFreemz and SpartanPort contributors' MIT license in `gpu/dlss_bridge/LICENSE.txt`.

See each dependency's source and license for its complete author list and terms. The Windows package includes dependency notices under `licenses/` and the font license beside the font. No proprietary PS4 module, game file or game artwork is redistributed. Optional proprietary DLSS binaries are not bundled.

The project's GPL-2.0 license is in `LICENSE`. Existing per-file SPDX statements, copyright notices and upstream license files continue to apply. For any public binary release, publish its corresponding source commit and the referenced submodule revisions and patches together with the release.
