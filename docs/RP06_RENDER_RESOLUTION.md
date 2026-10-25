# Internal rendering resolution — Resolution Preview

The launcher now offers **Original, 720p, 900p, 1080p, 1440p and 4K** for
CUSA01047 USA 01.00. This changes the native scene-buffer dimensions. Output
resolution continues to control host presentation independently. All explicit
internal modes are experimental and require a game restart.

| Internal setting | Scene dimensions | Half-size targets | Quarter-size targets |
| --- | --- | --- | --- |
| Original | Game-controlled | Game-controlled | Game-controlled |
| 720p | 1280 × 720 | 640 × 360 | 320 × 180 |
| 900p | 1600 × 900 | 800 × 450 | 400 × 225 |
| 1080p | 1920 × 1080 | 960 × 540 | 480 × 270 |
| 1440p | 2560 × 1440 | 1280 × 720 | 640 × 360 |
| 4K | 3840 × 2160 | 1920 × 1080 | 960 × 540 |

These are native allocation **requests verified in isolation**, not captured GPU
frames. 4K contains four times as many scene pixels as 1080p; this does not predict
frame rate or total memory use. No minimum VRAM capacity or 4K stability result has
been established. Original removes the override rather than forcing 1080p.

## Implementation evidence

The exact source and ELF fingerprints are listed in
[evidence/ratchet-cusa01047-0100-resolution.json](evidence/ratchet-cusa01047-0100-resolution.json).
No UPDATE 01.09 addresses, Neo flags or VideoOut resolution patches are imported.

- BASE selector `0x178b4a0` returns a success flag in AL and writes width through
  RSI and height through RDX. Its only direct caller is `0x183e06f`. A 26-byte,
  whole-instruction replacement sets the selected dimensions and returns true.
  Each mode has a unique-source signature, original-byte check and exact binary
  fingerprint guard. Conflicting resolution groups are rejected together.
- The caller aligns dimensions to four pixels, compares them with the current
  shared buffers, synchronizes and calls `ResizeSharedBuffers` at `0x177e330`
  through `0x183e1a5`. All five offered sizes are 16:9 and already four-aligned.
- Resize updates width/height at manager offsets `0x263c`/`0x2640`, releases the
  old shared resources and calls `0x177ccc0` to recreate them. Repeating the same
  dimensions skips recreation. A scene reset can restore the game's defaults;
  the frame selector remains overridden until the next process starts.
- Native creation passes the selected dimensions to depth, linear depth,
  forward, G-buffer, resolved, post-effect and GI targets. Half-, quarter- and
  eighth-size derivatives are computed by the original code. Auxiliary cubic
  output retains the display width; it is not incorrectly counted as a full
  scene-resolution target.
- The caller separately updates the display rectangle via `0x17b7d10`. On the
  successful-selector path its flag is zero and the original display dimensions
  remain in use. Host window/output and final presented image need not equal
  the scene dimensions.

The isolated x86-64 experiment executes the actual selector and native
resize/creation control flow. GPU/resource dependencies are stubbed to record
allocation requests and populate the resource dimensions consumed by later
requests. It checks 50 selector cases, 160 target requests across five modes,
release/recreate versus unchanged-size behavior, and Original restoration.
It does **not** allocate real GPU surfaces or execute shaders. The separate
profile check covers all 96 combinations with frame-rate, blur and shadow
settings and the dump's relocation slots.

No heap-size patch is included. The native buffer builder's allocation tracking
is retained. Successful request arithmetic does not prove that guest heaps or
host VRAM can satisfy all requests in a real scene.

## Settings and runtime verification

`internal_resolution` is independent of `output_res` and the inherited
`render_resolution` option. Missing or invalid values become Original. Saved
patch names cannot override this explicit setting. Only a prepared reviewed
group supplies `RATCHET_INTERNAL_RESOLUTION`; rejected preparation reports
Original. The native loader must accept the patch transaction before guest entry.
Original starts from a fresh unmodified image. Saving from the overlay preserves
the requested internal setting, including when preparation falls back.

The in-game Graphics information panel separates:

- **Internal resolution (startup):** the prepared launch mode, not a measurement.
- **Scene candidate / depth:** the last draw with at least five active, equally
  sized color targets and matching depth, observed independently of upscaling.
- **Scene candidate viewport:** that draw's viewport dimensions.
- **Presented game image** and **Window:** the final image and host window.

Candidate identification is a heuristic. Menus may produce no candidate; the
panel then says **Not observed yet**. A previous sample stays labeled as the last
matching draw. Logs record at most 16 distinct size/viewport combinations; they
never substitute the selected resolution for a missing observation. A matching
sample does not identify or validate temporal history.

## Gameplay acceptance still pending

On the same save and camera position, compare Original against 720p, 900p,
1080p, 1440p and 4K, restarting between choices. Keep output fixed first to isolate
scene detail, then compare with 4K output on a suitable display. Record the
startup mode, observed target/viewport dimensions, screenshots and frame times.

Check gameplay, scene transitions, cutscenes, HUD/text placement, transparency,
depth of field, blur and any temporal reconstruction/history behavior. Look for
cropping, black edges, ghosting, stale frames, device loss and allocation errors.
Repeat scene changes and restore Original to check recovery. If 4K fails, return
to Original or a lower internal setting and restart; keep the failing run log.

The supplied BASE build's temporal-history dimensions have not been independently
measured. History, viewport observations, visual correctness, memory headroom and
sustained performance remain gameplay acceptance gates. This preview makes the
controls available for testing; it does not close those gates.
