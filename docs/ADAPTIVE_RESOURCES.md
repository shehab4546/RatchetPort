# Adaptive resources and controls

V1.7 keeps the selected internal resolution, including 4K, while adapting image-cache cleanup to the graphics driver's current memory budget. It targets cleanup overhead and cache churn; it does not promise a particular frame rate or resolve every GPU synchronization stall.

## Memory pressure

- Collection starts at 78% of the reported budget and remains active until usage falls below 71%. Pressure and critical thresholds are 85% and 95%.
- Each sweep visits at most 256 candidates, evicts at most 4/12/24 images according to pressure, and allows at most one synchronous image writeback. A cooperative 2 ms deadline stops further work; a single blocking GPU operation can exceed it.
- A persistent LRU cursor advances through eligible images instead of restarting behind the same blocked entries. The cursor is repaired when images are touched, freed or their slots reused.
- Images requiring unsupported tiled writeback remain protected. Blocked candidates wait 120 submission ticks before retrying; using the image resets that delay. Minimum ages remain 16/80/160 submission ticks by pressure tier, with no startup eviction before that age. These ticks are not display frames.
- Existing synchronous readback and deferred Vulkan destruction preserve guest data and in-flight resource lifetime. This does not implement tiled readback or enable deferred readbacks.
- Logical guest bytes are tracked separately from heap usage. Diagnostics report both without claiming that guest bytes evicted equal physical memory reclaimed. Without driver budget reporting, conservative cache-accounting thresholds are used.

Adaptive collection is enabled by default. The earlier experimental `RATCHET_GC01` and fixed `RATCHET_GC_BUDGET_MB` overrides are superseded by this policy. Resolution, shadows and frame-rate targets remain explicit settings.

## Keyboard and mouse

Controls exposes all eight stick directions alongside the existing button assignments. Select a field and press the desired key or mouse button; resetting keyboard and mouse restores both the assignments and mouse settings.

Mouse movement defaults to the **left stick**, with **Always** activation. The launcher and in-game Controls menu offer **Left stick / Right stick / Off**, **Always / Hold L2**, relative or absolute movement, sensitivity, and vertical inversion. WASD still maps to the left stick and arrows to the right unless reassigned. When mouse movement actively drives a stick, it takes priority over that stick's keyboard/controller value; idle relative movement releases it. Overlay capture and focus loss clear the mouse state.

`ratchet.ini` stores `mouse_stick` (0 off, 1 left, 2 right), `mouse_activation` (0 always, 1 L2), `mouse_invert_y` (0 normal, 1 inverted), `mouse_aim_style` and `mouse_aim_sensitivity`. Keyboard stick assignments are saved in `settings.json` and sent through `RATCHET_STICK_KEYS`; button assignments retain their existing format.

## Game language

Game and saves now includes a persistent **Game language** selector independent of the launcher language. Existing system-language IDs are retained, including Latin American Spanish (20) and Brazilian Portuguese (17). Changes apply after restarting the game.

The inspected CUSA01047 v1.00 NA selector accepts English, French, Portuguese (Portugal/Brazil), and Latin American Spanish. Only these five languages are offered. Previously saved unsupported IDs remain visible as unavailable and launch with an explicit English fallback. System ID 22 also resolves to the same French content. Selection does not install missing language assets or bypass those rules. The earlier language-list comments referred to a different game's content and have been removed.

Text and voice currently follow the game's own language pairing. The executable has two language outputs, but an independent audio-bank selection path has not been verified. No independent voice selector is advertised as functional. References: issues #14 and #5; [USA language verification](USA_LANGUAGES.md).

## Validation

The native policy test covers hysteresis, large budgets, bounded progress, age boundaries, cursor deletion/touch/reuse and deletion from a callback. Graphics settings tests cover mouse-setting save/reload. Pad mapping tests cover remapping, opposite-key neutralization, left/right/off mouse routing, activation, inversion and focus reset. Launcher tests cover language persistence, UI-language independence and stick-key serialization. Windows CI runs the native input tests and real Tk save/rebuild regression tests.

Gameplay validation should compare the same scene and settings on the same device. Use `Adaptive texture GC` logs alongside frame-time measurements; counts from runs of different lengths do not establish an FPS gain. Check text and voice after a full restart, test both mouse stick targets, and verify that physical controller movement resumes when the mouse is idle or disabled.
