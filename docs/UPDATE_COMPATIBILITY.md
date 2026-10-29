# Game update compatibility

The development build adds an **experimental CUSA01047 USA 1.09 profile**. The
published V2.0 release still targets USA 1.00. This change does not establish
playable 1.09 gameplay or add European/DLC support.

## Installation selection

In **Game and saves**, keep the complete USA 1.00 installation in **Game folder**
and select the separately extracted USA 1.09 files in **Update folder (optional)**.
Leave the update field empty to run the installed version. A complete, already
combined 1.09 installation can also be selected directly; an update-only folder
cannot replace the base game.

The launcher saves the selection and reports the effective `APP_VER`. The runner
combines base, update, then optional mods in temporary views. The original folders
are not modified. Applying settings and restarting reconstructs the view from the
original paths; normal exit and preparation failures remove it.

The update needs its original `eboot.bin`, `sce_sys/param.sfo`, valid
`sce_sys/playgo-chunk.dat`, `sce_module/libc.prx`, `sce_module/libSceFios2.prx`,
`asset_archive/toc` and `asset_archive/p000035` through `p000048`. Base archives
remain necessary. Voice checks prefer an updated archive when one exists and
otherwise inspect the base archive. Missing voice data is reported separately.

For command-line starts, `RATCHET_GAME_DIR` identifies the base installation and
`RATCHET_PATCH_DIR` identifies the optional update. Keep the data/output directory
outside both folders.

## Independent patch profiles

| Feature | USA 1.00 | USA 1.09 development profile |
| --- | --- | --- |
| Executable preparation and native module linking | Existing path | Verified on the supplied update files |
| Separate text and voice | Existing experimental patches | Independently guarded 1.09 lookup replacement |
| 60 FPS clock patch | Existing experimental patch | Original 30 FPS ceiling |
| Native resolution | 720p–4K experimental overrides | Independently guarded 720p, 900p, 1080p, 1440p and 4K overrides |
| Shadow-map cap | 256/512/1024 px experimental caps | Independently guarded 256/512/1024 px caps |
| Motion blur override | Existing experimental patch | Original game settings |
| Mapping-aware button artwork | Existing verified assets | Installed artwork |
| Host renderer options and keyboard/controller mapping | Available | Available; gameplay validation pending |
| EU builds and add-ons | Unreviewed | Unreviewed |

Saved settings are retained when changing versions. An unsupported 1.09 request
is logged as skipped and never falls back to a 1.00 address. Selecting 1.00 again
restores access to its existing patches and prompt assets. Host window/output
resolution remains separate from the game's native rendering resolution.

`TITLE_ID` and `APP_VER` select a profile; `VERSION` is not used as the game update
number. Exact SELF and reconstructed ELF hashes, unique signatures, original
bytes, mapped ranges, and relocation/ISA exclusions still guard patch writes.
Every launch resets the patch packet and invalidates the previous loader receipt.
The 1.09 preflight also verifies the executable and TOC fingerprints, checks
required patch archives, and rejects mismatched titles, unknown versions and
incomplete update folders. It does not verify every byte of every game archive.

## 1.09 evidence

- Title: `CUSA01047`; `APP_VER=01.09`; `VERSION=01.00`; update category `gp`.
- SELF SHA-256: `d0bbf7a28ff633bf8f80379c00bd12209611cfcafcaaa39598263f34c366113b`.
- Reconstructed ELF SHA-256: `4deebb465b6635b351a301b64841062d3986122a99cc4ffc4f92c1b9aea53bb5`.
- TOC SHA-256: `5fdfb07df834d6be96435a39dcb92b03fdcff128bc518de9cce31f8bb1aad654`.
- Entry: `0x1f70fa0`; prepared image: 80,017,808 bytes; PlayGo: 72 chunks.
- Module linking: 168 native bindings; 494 imports left for the host runtime;
  2,154 FS-to-GS rewrites. These counts are not a complete host-import acceptance test.
- Language conversion table: `0x29a2ab0`; USA mask: `0x242042`.
- Resource lookup: `0x17dd2b0`, 98 bytes. It reads 48-byte language rows,
  six resource classes, 64-bit sorted hashes and 12-byte resource records.
  The replacement redirects only the `localization_all` hash and preserves the
  selected system/voice language for every other resource.

[Isolated lookup results](evidence/ratchet-cusa01047-0109-lookup.json) cover 12,834
cases across the original function and five text overrides, including empty
buckets, unsigned hashes, hits, misses and every resource class. The test uses
synthetic tables and the actual guarded instructions, without starting the game.
Reproduce it on Linux x86-64 with `tools/verify_update_lookup.py` and a locally
prepared `boot-linked.bin`; neither executable nor asset payloads are distributed.

## Resolution and shadow validation

The 1.09 selector at `0x16fa460` has its own guarded replacement. The native
resize coordinator at `0x16f02d0` receives the selected width and height; changing
internal resolution requires a restart. **Original** restores the native policy.
The shadow manager at `0x17c0e40` clamps its configured maximum to 256, 512 or
1024 px before allocation, retaining smaller requests, 32 px tile alignment,
metadata and the existing 8192×4096 atlas. This cap does not shrink the atlas.

For 1440p and 4K, the native GPU heap is set to **1549 MiB** and **1933 MiB**.
Unlike 1.00, 1.09 adds 128 MiB after its configuration lookup; the replacement
accounts for that addition so the final reservation stays below the runtime's
2 GiB heap slot. Native alignment/reservation remain intact. The direct-memory
pool floors remain 5440/5824 MiB, with larger valid explicit values preserved.
These capacities are experimental headroom, not measured level requirements.
Allocation failures also reach the existing printf diagnostic instead of the
retail no-op logger. Gameplay and GPU rendering still need validation.

[Isolated graphics results](evidence/ratchet-cusa01047-0109-graphics.json) cover:

- 144 resolution/shadow/text combinations against the actual executable and
  linked relocation guards; conflicting selections reject both groups. The
  production 4K + 256 px + text transaction also passes ISA/TCB exclusions.
- 63 native selector cases, including original behavior and restoration.
- Five resize-coordinator modes, with duplicate dimensions avoiding recreation.
- 120 shadow-constructor cases, including smaller maxima and allocation failure;
  55 native tile allocations preserve dimensions, coordinates and metadata.
- 16 native heap initializations across both page sizes, fixed high-resolution
  capacities and original configuration lookup; failure logging preserves NULL.

Reproduce with `tools/verify_update_graphics.py --game-dir <update> --linked
<boot-linked.bin> --output <new-report.json>` on Linux x86-64. OS/GPU dependencies
are intercepted; the tests do not render the world or establish frame rates.

The host resolves the update's PS4 Pro and PS5 queries to the existing base-PS4
hardware model. Save initialization/mount and POSIX file aliases use the existing
implementations. NID/ABI references are the upstream shadPS4
[process](https://github.com/shadps4-emu/shadPS4/blob/0614ce324be092791b758d79f93d9f1ca5b10a81/src/core/libraries/kernel/process.cpp),
[file system](https://github.com/shadps4-emu/shadPS4/blob/0614ce324be092791b758d79f93d9f1ca5b10a81/src/core/libraries/kernel/file_system.cpp)
and [save data](https://github.com/shadps4-emu/shadPS4/blob/0614ce324be092791b758d79f93d9f1ca5b10a81/src/core/libraries/save_data/savedata.cpp)
registrations. The native `update-imports-test` checks exact-library resolution,
console query results, data-import rejection and the file aliases.

The update's native libc also calls `sceLibcHeapGetTraceInfo` through
`NWtTN10cJzE#libSceLibcInternalExt` during startup. The host preserves the caller's
size/flags, disables segment tracing, and returns process-lifetime writable
storage for the allocation mask and 64-entry state table. This is a 32-byte
exchange structure, independently checked against the actual 1.09 caller at
`libc.prx+0x5bd68` and the upstream
[memory registration/contract](https://github.com/shadps4-emu/shadPS4/blob/0614ce324be092791b758d79f93d9f1ca5b10a81/src/core/libraries/libc_internal/libc_internal_memory.cpp).
The native import test checks offsets, boundaries, pointer persistence, retained
contents and exact-library resolution. An isolated execution of the actual libc
query/consumer block through `+0x5be29` also passed; it does not exercise the rest
of initialization or gameplay.

Before promoting this profile, test initial boot, gameplay, save/load, 720p–4K
rendering, all shadow caps, Original restoration, the voice
archive checks, text/voice separation, and returning to 1.00 with the previous
graphics/icon settings. Keep issues #12 and #16 open until game testing confirms
the update path. European base/update executables and matching metadata/assets,
and add-on metadata/assets, still require separate profiles and validation.
