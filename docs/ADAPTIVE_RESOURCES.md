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

Mouse movement defaults to the **right stick**. In the same keyboard mapping table, click a stick direction and move the mouse left, right, up or down to bind it. Movement capture ignores the first 12 pixels of click jitter and selects the dominant direction. Keyboard keys and mouse buttons can still be assigned in these fields. Saved explicit key assignments survive; resetting keyboard controls restores mouse movement on the right stick.

`settings.json` stores these bindings with the other keyboard inputs, and `RATCHET_STICK_KEYS` passes `Mouse Move Left/Right/Up/Down` to the runtime. There are no relative/absolute, stick-target, activation or per-direction setup panels. Earlier mouse-mode INI fields are retained for file compatibility but do not control this path. The game captures the pointer automatically; menus, pause and lost focus release it.

Keyboard diagonals combine both axes inside a circular stick range. Mouse speed applies dead-zone compensation to the whole movement vector, preserving its angle rather than boosting each axis separately. A 40 ms report hold bridges closely spaced pad reads, then releases to physical controller/keyboard input. There is no accumulated center offset. Overlay capture and focus loss discard pending movement. This is still stick emulation, with the game's maximum camera-turn speed; it is not a native camera-angle patch or guaranteed one-to-one mouse aiming.

## Graphics presets

Graphics owns resolution, effects, display and frame-pacing settings. Low, Medium, High, Very High and Ultra set internal/output resolution, shadow cap, anisotropy and motion blur together. A manual mismatch displays Custom. Presets preserve input, language, frame-rate, HDR and driver-safety preferences. No new texture-quality or geometry control is implied. Save and restart to apply patched rendering settings.

## Game language

Game and saves includes persistent **Text / Subtitles** and **Voice** selectors independent of the launcher language. Existing system-language IDs are retained, including Latin American Spanish (20) and Brazilian Portuguese (17). Changes apply after restarting the game.

The inspected CUSA01047 v1.00 NA selector accepts English, French, Portuguese (Portugal/Brazil), and Latin American Spanish. Only these five languages are offered. Previously saved unsupported IDs remain visible as unavailable and launch with an explicit English fallback. System ID 22 also resolves to the same French content. Selection does not install missing language assets or bypass those rules. The earlier language-list comments referred to a different game's content and have been removed.

The experimental text-resource override allows independent voice selection on the verified executable. Archive sampling warns about missing or repeated-block voice data without blocking play. See [USA language verification](USA_LANGUAGES.md) for the selection path and playback limits.

## Validation

The native policy test covers hysteresis, large budgets, bounded progress, age boundaries, cursor deletion/touch/reuse and deletion from a callback. Graphics settings tests cover mouse-setting save/reload. Pad mapping tests cover remapping, opposite-key neutralization, mouse-direction bindings, small continuous movements, report gaps, release and focus reset. Launcher tests cover language persistence, UI-language independence and stick-key serialization. Windows CI runs the native input tests and real Tk save/rebuild regression tests.

Gameplay validation should compare the same scene and settings on the same device. Use `Adaptive texture GC` logs alongside frame-time measurements; counts from runs of different lengths do not establish an FPS gain. Check text and voice after a full restart, test both mouse stick targets, and verify that physical controller movement resumes when the mouse is idle or disabled.
