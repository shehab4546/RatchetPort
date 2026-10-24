# 30/60 frame timing preview

Implementation status: **opt-in experimental 60 target; gameplay acceptance pending**.
Original/30 remains the default. This is not sustained-60, 120 FPS, a tearing fix,
a cutscene-stutter fix, or proof that all physics/rendering systems tolerate 60.

## Actual changes

The launcher Home and Performance pages expose `Game frame rate`: 30 FPS /
Original and 60 FPS (experimental). Set it before launching; changing it requires
closing and restarting the game. `game_fps=60` in ratchet.ini selects a reviewed
two-write transaction for the exact SELF/ELF hashes in `ratchet_patches.PROFILE`.
Legacy `engine_fps=60/120/240` and saved XML names do not activate it. Selecting
Original removes a stale 60 group and produces an empty packet on the next launch.

Hash/signature/original-byte/link/ISA rejection keeps the host ceiling at 30 and
prints a skip reason. If native validation fails after preparation, the loader
aborts before entering the game; it never runs half the pair. A valid receipt
means that the bytes were applied, not that gameplay passed validation.

The host cap follows the prepared target (30/60); an explicit RATCHET_FPS_LIMIT
can lower it but cannot exceed it. The display vblank stays at 60 Hz. Host caps,
guest pacing, and guest elapsed time are separate. Inherited live FPS global
writes and cycling are disabled. The in-game menu reports the nominal target
and retains the requested setting when saving other preferences.

## Instruction evidence

Addresses are ELF virtual / pre-link image offsets, never physical SELF offsets.
Both sites have unique 32-byte source signatures and belong to one atomic group.
Both signature windows were also checked against all 559,629 source relocation
slots: neither overlaps one. Linking and ISA guards are rechecked at every launch.

| Site | Before | After |
| --- | --- | --- |
| `0x17b7664` (10 bytes) | Load render settings +0x24 into xmm0, copy to frame state +0x1c | Store float 1.0 directly at frame state +0x1c, three NOPs |
| `0x171e7a1` (4 bytes) | Raise derived clock floor to the caller minimum with vmaxsd | Four NOPs: retain period × interval |

The interval replacement occurs in renderer setup after parsing, rather than
changing only a constructor default that configuration could overwrite. The next
instruction reloads xmm0 with the alternate interval; no later use needs the
removed load. The +0x20 alternate interval and +0x24 throttle flag are unchanged.
The normal base period is float 0x3c88ac0c, about 0.01668360084 seconds; target
labels 30/60 therefore do not promise exact 30.000/60.000 Hz guest pacing.

Renderer initialization at 0x18710c7 precedes the clock init call at 0x18713e1.
That call is the only direct call found to 0x171e710. It takes its caller minimum
from settings 0x4ee66f8 +0x0c; the experimental mode intentionally replaces that
minimum with the selected pacing period. The independent 1/60 lower safety bound
at 0x2ee24b0, caller upper delta bound, elapsed-TSC conversion, history smoothing,
time scale and pause branches remain unchanged. The tick function at 0xe6c760
still clamps elapsed delta and accumulates it. Game-time update 0x171e9d0 and
pause suppression around 0x183df13 are unchanged. The alternate wait throttle
continues to use max(normal interval, alternate interval).

This review narrows the change to clock/pacing. It does not prove every later
writer or gameplay consumer has been exercised. That is why it remains opt-in.
The retained 1/60 safety floor is also a reason not to expose 120 FPS here.

The supplied research archive was cross-checked against this BASE executable,
including its different blur normalization: see
[research review and signature validation](RP04_RESEARCH_REVIEW.md).

## Reproducible isolated experiment

`tools/verify_frame_clock.py` reads the owner's exact supplied SELF, validates
both fingerprints and replacement signatures, maps its loadable image privately,
and calls only the settings-copy fragment, clock initialization and clock tick.
It substitutes a deterministic nanosecond TSC in that private image. The source
file is read-only; no proprietary bytes are committed or exported. Requires
Linux x86-64 with AVX, using the System V ABI:

```bash
python tools/verify_frame_clock.py --game-dir /path/to/own/dump --output /new/path/clock.json
```

[Recorded numeric results](evidence/ratchet-cusa01047-0100-clock.json): 16 cases
cover original/patched code, settings intervals 2 and 3, caller minimum 0 and
1/30, smoothing off/on, recurring frame drops, pause and half speed. Largest
accumulated clock deviation was 0.041255% across these synthetic sequences.
Leaving the old caller minimum while running the shorter interval produced a
1.99797 speed ratio, demonstrating why both writes must apply together.
These are execution results for isolated clock instructions, not Windows gameplay
or a benchmark of frame delivery, audio, physics, movies, loading or GPU behavior.

Automated tests additionally cover routing, unknown/stale selections, strict
30/60 normalization, rejected-patch host fallback, paired-write rejection,
settings save/restart/rollback, and disabling live inherited timing writes.

## Owner gameplay acceptance still required

1. Use the same save and scene at Original/30 and experimental60. Keep output
   size, VSync and other rendering options fixed; close and restart each time.
2. Save `user/last_run.log` and `out/patch_status.json` separately for each run.
   For 60 expect two prepared writes and a current loader receipt. Record real
   FPS/frame times with an external capture; repeated display flips alone are
   not proof of new frames.
3. Compare movement, falling, firing/cooldowns, projectiles, animation and
   particles over 60 real seconds. Proposed acceptance: <=1% timing difference
   outside pause/loading. Check audio synchronization and at least one cutscene.
4. Include slow frames, pause/resume, menus, save/load and a 30-minute session.
   Return to Original and restart; verify an empty patch transaction and baseline
   behavior. Any speed/audio/scene regression blocks stable acceptance.

No additional game upload is needed to build this experiment. Actual-game logs
and a matching 30/60 recording are needed to complete RP-04 gameplay acceptance.
