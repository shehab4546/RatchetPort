# In-game button icons

Controls includes an **In-game button icons** selector:

- **Original / PlayStation** uses the installed artwork without mounting a prompt override.
- **Xbox** shows physical button labels from the saved gamepad mapping. Analog triggers remain LT/RT.
- **Keyboard & mouse** follows saved button and stick-direction bindings. Letters, digits, F1–F24, arrows, numpad and common special keys have labels. Space and Enter use symbols; mouse buttons, wheel directions and movement have distinct drawings. Unsupported labels show `?`; unbound inputs show a dash.
- **Auto** checks the first connected controller at launch. Xbox labels select Xbox; no controller selects keyboard/mouse. PlayStation and unidentified layouts use installed artwork. Auto does not track the last device used during play.

Save and restart to apply. Every input device remains available in every icon
mode. The selector does not change camera movement, button behavior or dead zones.

## Coverage

The CUSA01047 USA 01.00 profile checks 46 GFX files, 21 button textures and iconmap.
It changes 17 GFX files and the 19 textures referenced by input entries in
`iconmap.config`. The two other textures and copyright symbols are preserved.

Adapters cover HUD messages/objectives/progress, POI interaction and wrench
prompts, QuickSelect shoulders and mapped D-pad labels, loading, lobby, overlay,
pause shell, cards, weapons, Galactic Map, race screens, Trespasser, Batalia turret
and both weapon vendors. Race-screen sticks receive separate definitions.
Baked stick-click text is suppressed; named POI TextField instances are retained
with their old labels cleared. ActionScript bytecode is preserved.

The texture path covers iconmap-backed prompts, including the cinematic UI route.
Static inspection does not establish which prompt each scene displays at runtime.
Gameplay, cinematic coverage and animation quality remain pending validation.

## Files and recovery

Installed archives are only read. A small prompt archive, replacement TOC,
original TOC snapshot and hash receipt are generated under `out/glyphs`.
Four exact-file mounts expose the replacement pair through `/app0` and `/hostapp`.
Other files keep their existing mounts. Original mode omits those mounts and
returns to the installed bytes without rewriting any archive.

The cache depends on the effective mappings, style, generator version and source
identities. Cached files are verified before reuse. Unknown or changed assets,
invalid bounds and incomplete coverage stop prompt preparation with a diagnostic.
Selecting Original permits the installed artwork to load. This option cannot
undo unrelated modifications made to a dump before installation.

The texture reference was corrected against the restored PlayStation assets
collected on 2026-10-27. The initial reference mistakenly included 12 textures
from an earlier Xbox icon modification, causing restored installations to fail
identity checks. The 46 GFX files, iconmap and TOC matched between collections.
Unknown content is still rejected; mismatch diagnostics now identify the asset
path and expected/actual SHA-256. Corrected source hashes select a new cache entry
automatically. No manual cache removal or game archive modification is required.

## Validation

Automated checks cover mapping aliases, invalid entries, unbound sources,
independent stick directions, variable-size GFX tags, preserved bytecode, TOC
relocation, archive bounds, LZ4 lengths, BC7 decoding and Original mode.
Private local asset checks also validate all 68 source identities, generate
default/remapped keyboard and Xbox overlays, verify cache reuse, decode modified
textures and render modified GFX prompt shapes. No game payload is committed.

Gameplay checks still needed: menus, NPC interaction, map zoom, weapon selection,
vendors, stick-click prompts, a skippable cinematic, changed bindings and switching
back to Original. These asset checks are not gameplay verification.
