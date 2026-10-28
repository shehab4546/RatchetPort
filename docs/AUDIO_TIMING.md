# Audio timing and the October 25 diagnostic run

The supplied Intel UHD 730 run used English text and voice, without the language-split patch. The sampled English archive passed, WASAPI opened two 512-frame audio ports, and AJM reported 393,753 decoded ATRAC9 frames. There was no recorded decoder failure. Graphics usage reached 5433 MiB against a roughly 5250 MiB driver budget; the log also contained 840 partially mapped-region warnings. These are signs of graphics/memory pressure, not proof of a specific audio-latency cause.

The old log did not enable per-port audio timing statistics. Buffer totals over a session do not establish starvation, backlog, lip-sync offset or device latency. Gameplay verification remains required.

The output path now records statistics every five seconds by default: maximum submission gap, minimum queued bytes, empty-queue observations, maximum queued input duration and backlog resets. `RATCHET_AUDIO_STATS=0` disables periodic statistics. [SDL_GetAudioStreamQueued](https://wiki.libsdl.org/SDL3/SDL_GetAudioStreamQueued) reports queued input bytes, not end-to-end device latency; each port keeps a fixed input format so its queue duration can be calculated.

After a scheduling stall exceeding one buffer period, the pacing clock is rebased instead of issuing up to eight buffers in a catch-up burst. If queued input exceeds 250 ms, the stream is cleared, its cadence controller reset, and current PCM resumes. This recovery deliberately drops stale sound and may produce a brief discontinuity. It does not time-stretch audio or repair slow rendering, missing assets or cinematic synchronization. PCM conversion, Wwise/AJM decoding and Bink selection are unchanged.

Tests cover stereo downmix and backlog thresholds across input formats. The Windows build executes this native test along with the mouse mapping tests. Actual audible latency on WASAPI must be checked in-game.
