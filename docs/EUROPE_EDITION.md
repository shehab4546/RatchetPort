# European edition (CUSA01073 v1.00)

RatchetPort was reviewed on **CUSA01047 USA v1.00**. This change adds the European
edition **CUSA01073 v1.00** without altering anything for USA: the USA linked image,
patch groups, languages and launcher behaviour are the same as before (all 597
original Python tests pass unchanged, plus `tests/test_editions.py`).

The European build is a later compile of the same game (`PUBTOOLINFO c_date=20180213`,
SDK 4.0, PS4 Pro aware), so the same code sits at other addresses, is sometimes
compiled differently, and links against a newer libc. As with USA, players must dump
their own copy; no game bytes are included.

## Where things live

| File | Role |
| --- | --- |
| `scripts/editions.py` | Single source of per-edition facts: TITLE_ID, SHA-256 fingerprints, languages and voice archives, aliases, text/voice split, compat set. |
| `scripts/edition_compat.py` | Link-time compatibility for non-USA editions (explicit stub lists, SSE4a emulation, red-zone frames). `compat_for()` returns `None` for USA and unknown dumps. |
| `scripts/ratchet_patches.py` | `PROFILES`: the USA `PROFILE` unchanged plus `PROFILE_EUROPE`; `prepare()` picks the profile by TITLE_ID. |
| `scripts/frame_timing.py` | `FPS60_WRITES_EUROPE`, the European RP-04 pair. |
| `scripts/ratchet_game.py`, `voice_archive.py`, `language_split.py` | Accept both editions; languages normalised per edition (USA results unchanged). |
| `scripts/link_libc.py`, `link_modules.py` | Newer-SDK symbol names; edition stubs bound only when no native export exists. |
| `run.py` | Passes the edition to the language code; pins the game to performance cores on hybrid CPUs (`RATCHET_ALL_CORES=1` opts out). |
| `launcher/` | Detects the edition of the chosen folder; language lists per edition; texts for both. |

## Fingerprints

| | source SHA-256 | ELF SHA-256 |
| --- | --- | --- |
| CUSA01047 | `fdf72d68…76697d` | `dc1a8862…f05cf` |
| CUSA01073 | `0aeafa5fb7f511b2e0dfb1feef37dff60ce66cb322c6db9a63ee4ba8942f7362` | `a12d10e22b3ddbb869ad6e0995661de283fc1db143c435c4d5c665cde55d3fad` |

## Verified patch groups (Europe)

Located so far: **Ratchet 60 FPS (experimental)** and **Ratchet Motion Blur Off
(experimental)**. Shadow caps, internal resolution and the text/voice split are skipped
with "feature has no reviewed RP-03 replacement group" until located.

**Motion blur Off, `0x1735604` (4 bytes).** Same per-render state builder as USA
`0x17cb0b6`: `lea rdx,[RenderSettingsUser]` (`0x4bfccd0`; USA `0x4ee6cb8`),
`cmp byte [rdx+1],0` (MotionBlurEnable), `sete dl; or dl,r15b; test dl,1; je`, then
`mov dword [r13+200A4h],0` and `cmp ecx,0FFFFFFh` as in USA. The compare becomes
`cmp edx,edx; nop; nop` (USA uses `cmp esi,esi`): disabled flags, no register changed.
In cinematics the native blur showed block-shaped smears and ghosting on animated
characters on this port; Off removes them (velocity, TAA and DOF are untouched).

The two RP-04 sites were found by behaviour, not by USA bytes (which do not occur):

1. **Interval copy, `0x1722f64` (34 bytes).** Same function as USA `0x17b7664`: settings
   `+0x24` → frame state `+0x1c`, `+0x28` → `+0x20`, then `byte [+0x24] = 1`,
   `dword [+0x2c] = 0` (the signature continues with that store, as in USA). The newer
   compiler copies with integer moves, so `mov dword [r14+1Ch], 1.0` (8 bytes) fits only by
   reordering the block; every other instruction and effect is kept:

   ```
   before                          after
   mov eax,[rsi+24h]               imul r15,r12,148h
   imul r15,r12,148h               mov dword [r14+1Ch],3F800000h
   mov [r14+1Ch],eax               mov eax,[rsi+28h]
   mov eax,[rsi+28h]               mov [r14+20h],eax
   mov esi,8                       mov byte [r14+24h],1
   mov rdi,r15                     mov rdi,r15
   mov [r14+20h],eax               push 8 ; pop rsi
   mov byte [r14+24h],1            nop
   ```

   Checks: no branch targets inside the block; the enclosing function makes 11 calls and
   has no `[rsp-X]` access (no red zone), so `push/pop` is safe; flags after the block are
   those of `imul` in both versions.
2. **Caller minimum, `0x16991f4` (4 bytes).** Same clock initialisation as USA
   `0x171e7a1`: interval `+1c`, throttle `+24`, alternate `+20`, period `+18`, then
   `vmaxsd xmm0,xmm0,xmm1` (caller minimum) and `vmaxsd` against the 1/60 constant, which
   is retained. Replaced by four NOPs.

Both 40-byte signatures match exactly once. In game the loader reports
`Patches: 2 verified writes applied in memory`.

Without this group the European build runs at about 14 FPS with the 30 FPS setting on the
test machine; with it, at the 60 FPS target. Why the 30 FPS pacing halves on this build is
not yet understood.

## Link-time compatibility (Europe only)

1. **Newer libc.** `__start__Ztext`/`__stop__Ztext` are plain-named, unreferenced symbols;
   they are given no NID identity.
2. **Missing HLE functions.** 102 imports have no implementation in ratchet-probe (84
   `libSceNpToolkit`, error dialogs, live streaming, video recording, three `libScePosix`,
   `sceKernelIsNeoMode` and two others in `libkernel`, one `libSceDiscMap`). They are listed
   explicitly in `EUROPE_ZERO_STUBS` and return 0. `sceLibcHeapGetTraceInfo` has a dedicated
   stub (fills `HeapInfoInfo` like shadPS4). A stub is bound only when no native or libc
   export resolves the import.
3. **Saves (newer SDK names).** ratchet-probe implements `sceSaveDataInitialize3` and
   `sceSaveDataMount2` by name (`src/runtime_savedata.c`), but its NID table
   (`src/import_names.inc`) only lists the older SDK's NIDs, so the European imports never
   reached them. `Initialize3` (`TywrFKCoLGY`) is linked under `sceSaveDataInitialize`'s NID
   (`ZkZhskCPXFw`): the runtime uses the same function for both (`EUROPE_IMPORT_ALIASES`).
   `Mount2` (`0z45PIH+SNI`) takes a different struct, so a guest bridge copies `Mount2`
   (user, dir, blocks, mode) into a `Mount1` with no title and no fingerprint (exactly what
   `save_mount2` does) and calls `sceSaveDataMount` through a relocated pointer slot. In game:
   `save data 'rcps4' mounted at /savedata0 (created)`, then `(existing)`, with
   `rcps4.save` and `rcps4_userprefs.save` written under `savedata/1/CUSA01073/`.
   Adding the two NIDs to `import_names.inc` would make the alias and bridge unnecessary.
4. **SSE4a.** Five `insertq xmmN,xmmM,30h,0` (AMD Jaguar only; `#UD` on Intel) jump to
   trampolines that emulate them with `movq/pinsrq`, preserving rax/rcx/rdx, flags and the
   red zone. The scan is cached in `out/sse4a-sites.json`.
5. **Red zone.** The leaf job at `0x178d500` keeps four locals at `[rsp-8…-20h]` while it
   writes buffers watched by the page manager. On Windows the access-violation dispatch
   runs on the guest stack and overwrites them, crashing intermittently on entering the
   post-difficulty cinematic (`lock xadd [rcx]` with `rcx=0`, or `lock add [rax+54h]` with
   `rax=0`). The function gets a real 32-byte frame (prologue/epilogue trampolines,
   displacements rebased). USA issue #42 (`write access to 0x54`) has the same signature
   and may be the USA counterpart; it is not changed here without a USA dump to verify.

## Known limitations

- Xbox/keyboard button icons use the USA prompt profile; they prepared and ran on the
  European dump in testing but are not reviewed for it.
- Cinematics show object/texture pop-in at 30 and 60 FPS (also reported on USA); try
  Readbacks = Precise.
- Tested on Windows 11, i9-13900HX, RTX 4080 Laptop. Gameplay acceptance is pending, as
  for USA.
