# Motion blur and shadow-map controls

V1.5 Visual Controls Preview adds restart-only controls to Home and Graphics.
The default is **Original** for both effects. This implementation targets only
CUSA01047 USA 01.00 with the SELF and ELF fingerprints in
`scripts/ratchet_patches.py`. Visual acceptance is still pending.

| Setting | Choices | Effect |
| --- | --- | --- |
| Motion blur | On / Original; Off (experimental) | Original follows the native game policy; Off takes its general blur-strength disable path |
| Shadow-map resolution | Original; 1024, 512, 256 px maximum (experimental) | Caps each map allocated by the reviewed shadow manager; smaller requested maps stay smaller |

Close the game, choose settings, save and start again. There is no live guest
memory edit. Select Original and restart to remove either patch independently.
The settings also participate in the existing unconfirmed-restart rollback.
The in-game Graphics information rows show this launch's prepared mode; native
transaction failure aborts before the game runs. The launch log records requested
and prepared values; `out/patch_status.json` plus the matching loader receipt
establishes application, not image quality or performance.

## Native motion-blur path

The BASE RenderSettingsUser object is at ELF virtual address `0x4ee6cb8`.
MotionBlurEnable is byte `+1`. A constructor default alone would be overwritten
by settings parsing, so the patch acts at the final consumer instead.

In the per-render state builder (`0x17c92c0`), `0x17cb0b6` compares that byte with
zero. The following `sete`, OR with the independent disable flag, and conditional
store clear strength at state `+0x200a4`. A four-byte replacement changes the
comparison to `cmp esi,esi; nop; nop`, producing the same flags as a disabled
native setting without modifying registers. The original branch and clear stay
intact, as do the following distinct effect fields. The function returns this
state at `0x17cb1cf` without another strength write in its remaining instructions.

The caller's consumer at `0x176c340..0x176c396` reads that strength, applies its
native delta-time scaling, and stores the result at render context `+0x290`.
Zero remains zero at 30/60 FPS and on slower frames. The blur pass at `0x17c77c0`
reads `+0x290`; its debug/frame conditions can still enter the pass at zero.
Consequently Off is a native strength disable, not a claim that every blur-family
GPU draw disappears. The patch does not replace velocity generation, camera or
object transforms, previous-frame data, TAA or DOF code. Their visual correctness
still requires in-game comparison. Separate camera/object blur switches are not
exposed.

## Native shadow path

Renderer settings default the maximum map size to **1792** (`0x178851d`), then
pass the loaded value to the shadow manager constructor at `0x17887da`.
The manager is at `0x4ba6260`; its constructor is `0x186a760`.

A 36-byte replacement at `0x186a771` clamps the incoming signed maximum in ESI
to the selected cap. It retains the original count copy, stack-local maximum,
manager pointer and three zeroed pointer fields. Compact register-zero stores
make room for the clamp without moving code. RAX/flags are not live across this
span: the following `0xe7fbb0` call replaces them. The constructor later stores
the capped maximum at manager `+0`, and the unchanged map count at `+4`.
Lower configured maxima remain lower. The original path is unchanged when the
option is Original.

The size selector at `0x186a990` uses the same maximum. Every reviewed allocation
through `0x186a910` clamps the requested size, substitutes the maximum for
nonpositive requests, and rounds up to 32 pixels. All offered caps are multiples
of 32. The allocator passes the resulting width and height to the packer and
stores the same size in returned tile metadata at `+4`; coordinates and ID are
preserved. Reviewed callers include `0x176c1a3`, `0x184fe58`, `0x1865ba1` and
`0x1865c38`.

The **8192 × 4096 atlas**, its format, allocation and packing implementation stay
unchanged. This reduces individual map detail; it does not reduce the fixed atlas
allocation or promise a VRAM/FPS improvement. Separate sun/cascaded-shadow paths
have not been established as covered. Original can therefore differ by scene,
and a selected cap is not a fixed resolution for all shadows.

## Automated evidence

[Recorded checks](evidence/ratchet-cusa01047-0100-effects.json) identify the exact
source hashes and preserve only results, not game images. On that source:

- All 16 frame-rate/blur/shadow combinations pass unique-signature, original-byte,
  segment and 559,629 relocation-slot checks. Corrupted originals, reserved
  sites and conflicting shadow caps are rejected.
- 32 isolated native blur-gate cases preserve all surrounding state bytes and
  follow the native disabled policy; 20 actual consumer cases verify zero and
  positive strength scaling across 120/60/30/20/10 Hz frame intervals.
- 312 isolated native shadow allocation cases cover all three caps and Original,
  smaller/larger configured maxima, default-size requests and alignment edges.
  Packer dimensions agree with returned metadata, coordinates and ID. Allocation
  dependencies are stubbed; this does not run GPU rendering or the complete game.
- Python tests exercise save/restart/rollback, stale-group removal, independent
  combinations, fallback and the actual launch orchestration with a stubbed game
  process. Native settings tests preserve requested settings when prepared mode
  falls back; native transaction tests check atomic application and receipts.

Windows build, launcher and packaged smoke-test status belongs to the linked CI
run. This document does not assert that a pending run passed.

## Gameplay acceptance

1. Use the same save, scene, output resolution and camera position. Start at
   Original/30, blur Original, shadows Original; retain a screenshot and log.
2. Change only blur to Off and restart. Compare camera sweeps and moving objects.
   Check edges, HUD, DOF, cutscenes and temporal ghosting. Repeat at experimental
   60 FPS after the baseline comparison.
3. Restore blur Original. Compare each shadow cap after restart, including a
   nearby light, moving character, long camera pan and a second scene. Check
   missing shadows, rectangular borders, flicker and incorrect sampling.
4. Combine blur Off with each cap at 30/60. Finally restore both to Original and
   verify the baseline appearance returns after restart.
5. Retain each `user/last_run.log`, `out/patch_status.json`, GPU/driver, settings
   and screenshots. Confirmed patch bytes do not substitute for these checks.

No 120 FPS mode, internal-resolution patch, tearing fix, cutscene-stutter fix or
sustained-performance claim is added by this change.
