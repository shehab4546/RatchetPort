# Review of the supplied game research

Reviewed `Ratchet_Game_Research.rar` for the 30/60 frame timing preview.
Archive SHA-256: `ec5c599d3ca989c47b577d1e5f8e9c18627eacf419ffbbfe542f63ccfab18390`.
It contains 14 Markdown reports and three JSON files, including 37 findings and
the 18-task plan. The build plan text matches the previously supplied plan.
The linked `evidence/` and `tools/` directories are absent from this archive;
the reports themselves explicitly describe static analysis, not gameplay tests.

## Fingerprint and signature validation

The report's BASE fingerprint matches the owner's supplied CUSA01047 USA 01.00
SELF. All 12 BASE code signatures were independently scanned across executable
ELF segments and reproduce the report's match counts and stated locations.
[Numeric results](evidence/ratchet-research-signature-checks.json) record the scan.
Eight signatures are unique. Q02/Q03/Q04/Q05 have 4/4/24/2 matches respectively
and must not be used as standalone patch locators.

The timing findings T01–T05 and exposure finding R08 describe UPDATE109, whose
SELF fingerprint differs. Its executable is not part of this archive. Neither
its addresses nor its signatures are imported into the 01.00 patch profile.
RP-04 uses the independently recovered BASE sites documented in
[the frame timing implementation](RP04_FRAME_TIMING.md).

| Research requirement | BASE implementation or remaining acceptance |
| --- | --- |
| T01/T05: full interval write after settings parsing | Store full float 1.0 at `0x17b7664`; preserve neighboring setup instructions |
| T02: pacing and alternate interval | Keep the wait path and alternate throttle; distinguish host cap from guest pacing |
| T03/T04: clock initialization and elapsed-time floor | Paired change at `0x171e7a1`; retain elapsed TSC, upper bound, smoothing, pause, time scale and 1/60 floor |
| R08: review frame-time-dependent blur | BASE consumer checked separately below; visual temporal-history acceptance remains pending |
| RP-04: 30/60 real-time correctness | Isolated clock experiment passed; owner gameplay, physics, audio, cutscenes and frame-delivery measurements remain pending |
| 90/120/unlocked | Not enabled; the retained floor alone prevents treating an increased display rate as correct higher-rate simulation |

## BASE exposure consumer differs from UPDATE109

Inspection of the actual BASE instructions at `0x176c31d`–`0x176c396`
confirms a time-dependent blur-strength consumer. It reads the time-state object
at `0x49f7b38`, takes its double delta at +0x08, and reads the material/render
parameter +0x200a4 at `0x176c349`. For a positive strength and a finite positive
delta, its scale is 1 when delta is below float 1/30, otherwise (float 1/30)/delta.
The constants at `0x2ee6194` and `0x2ee6190` are float 1/30 and 1.0 respectively.
The result is stored at render context +0x290 at `0x176c38d`.

This is not UPDATE109's interval-dependent expression or context +0x2a4 layout.
The existing BASE normalization is left intact: lowering a normal delta from
about 33.37 ms to 16.68 ms does not make this scale grow beyond 1. This arithmetic
review does not prove blur appearance, motion vectors, TAA/history, or every
caller correct at 60; those require the same-scene visual tests. No blur-disabling
or temporal shader patch is added by RP-04.

The remaining graphics, streaming, language and input findings remain research
inputs for their separate tasks. This review does not mark those tasks complete.
Original archives, game binaries and private machine paths are not redistributed.
