// SPDX-License-Identifier: GPL-2.0-or-later
// ratchetport: user settings changed at run time from the in-game menu (ratchet_overlay.h) and kept
// in ratchet.ini (RATCHET_CONFIG overrides the path). Environment variables override the file at
// start. Readers load the atomics every frame; writers are the menu and Load().

#pragma once


#include "ratchet_resolution.h"
#include <atomic>
#include <cstdint>

namespace RatchetSettings {

enum Upscaler : int { UpscalerOff = 0, UpscalerFsr3 = 1, UpscalerFsr4 = 2, UpscalerFsr411 = 3,
                      UpscalerTaa = 4, UpscalerDlss = 5, UpscalerCount };
/// FSR 4 v07 or FSR 4.1.1: the same inputs, settings and placement in the frame.
inline bool IsFsr4(int upscaler) {
    return upscaler == UpscalerFsr4 || upscaler == UpscalerFsr411;
}
enum Preset : int { NativeAA = 0, Quality, Balanced, Performance, UltraPerformance, PresetCount };
enum DebugView : int { DebugNone = 0, DebugReactive = 1, DebugMotion = 2, DebugViewCount };

/// Live output resolutions: the upscaler's output and the UI host targets.
inline constexpr int OutputWidths[] = {960, 1280, 1600, 1920, 2560, 3840};
inline constexpr int OutputHeights[] = {540, 720, 900, 1080, 1440, 2160};
inline constexpr int OutputCount = 6;
inline constexpr int OutputDefault = 1; ///< 1280x720, conservative host output

struct Values {
    std::atomic<int> upscaler{UpscalerOff};
    std::atomic<int> preset{NativeAA};
    std::atomic<bool> sharpen{true};
    std::atomic<float> sharpness{0.3f};
    std::atomic<bool> jitter{true};
    std::atomic<bool> reactive{false};
    std::atomic<bool> object_motion{true};
    std::atomic<float> reactive_scale{1.0f};
    std::atomic<float> reactive_threshold{0.2f};
    std::atomic<float> reactive_max{0.9f};
    std::atomic<int> debug_view{DebugNone};
    std::atomic<bool> show_fps{false};
    /// Performance overlay (ratchet_perf_stats.h): items shown, font size and background opacity
    /// in percent, corner (0 top left, 1 top right, 2 bottom left, 3 bottom right), layout
    /// (0 one line, 1 one item per line). menu_tab: the menu's last tab.
    std::atomic<unsigned> overlay_items{7};
    std::atomic<int> overlay_scale{100}, overlay_corner{1}, overlay_opacity{50}, overlay_layout{0};
    std::atomic<int> menu_tab{0};
    // Graphics (ratchet_graphics.h). Live: applied on the next frame.
    std::atomic<int> display_mode{0};
    std::atomic<bool> vsync{true};
    std::atomic<int> fps_limit{30};
    std::atomic<bool> async_shaders{true};
    std::atomic<bool> fsr1{false};
    std::atomic<bool> rcas{true};
    std::atomic<int> rcas_strength{75};
    /// Set by the presenter: sharpening ran on the last frame (it needs FSR 1 when the game's
    /// image is smaller than the window).
    std::atomic<bool> rcas_applied{false};
    /// Set by the presenter: the game's image and the window it is shown in, in pixels.
    std::atomic<int> image_width{0}, image_height{0}, window_width{0}, window_height{0};
    std::atomic<int> frames_queued{1};
    /// Controller vibration strength in percent; 0 turns it off (runtime_pad.c). Live.
    std::atomic<int> vibration{100};
    /// Keep the mouse in the game window while the game has it (window.cpp). Live.
    std::atomic<bool> mouse_lock{true};
    /// Mouse target: 0 off, 1 left, 2 right. Activation: 0 always, 1 while L2 is held. Live.
    std::atomic<int> mouse_stick{1};
    std::atomic<int> mouse_activation{0};
    std::atomic<int> mouse_invert_y{0};
    /// Mouse style: 0 relative, 1 absolute.
    std::atomic<int> mouse_aim_style{0};
    /// Mouse sensitivity in percent, 10 to 200: lower needs more mouse for the same stick. Live.
    std::atomic<int> mouse_aim_sensitivity{100};
    // Startup: run.py turns them into patches and environment variables; "Apply and restart".
    std::atomic<int> render_resolution{0};
    std::atomic<int> engine_fps{60}; // Legacy preference; never activates a patch.
    std::atomic<int> game_fps{30}; // Requested startup mode; retained when saving the overlay.
    std::atomic<bool> motion_blur_off{false}; // Requested startup effects, retained on fallback.
    std::atomic<int> shadow_resolution{0}; // 0 original, or 1024 / 512 / 256 pixel cap.
    std::atomic<int> internal_resolution{0}; // Requested startup mode; independent of host output.
    int applied_internal_resolution = 0; // Prepared startup mode, not a measurement.
    // Last matching MRT/depth draw and its viewport; zero means not observed.
    std::atomic<std::uint64_t> observed_scene_size{0}, observed_scene_viewport{0};
    bool applied_motion_blur_off = false;
    int applied_shadow_resolution = 0;
    // Synchronous readbacks are the Ratchet baseline: deferred reads stalled scene entry.
    std::atomic<bool> deferred_readback{false};
    std::atomic<bool> stale_readback{true};
    /// RatchetGraphics::Anisotropies; the samplers read startup_anisotropy.
    std::atomic<int> anisotropy{0};
    int startup_anisotropy = 0;
    /// Set before an "Apply and restart"; cleared once the new launch shows the game. run.py
    /// restores the previous startup options when a launch never cleared it.
    std::atomic<bool> restart_unconfirmed{false};
    int startup_render_resolution = 0;
    /// Nominal target from the verified startup transaction, not measured FPS.
    /// Original is 30; 60 is experimental and requires restart.
    std::atomic<int> applied_engine_fps{30};
    /// Legacy ABI storage; never written through by Ratchet timing.
    std::atomic<float*> engine_fps_global{nullptr};
    std::atomic<int32_t*> engine_fps_int_global{nullptr};
    bool startup_deferred_readback = false, startup_stale_readback = true;
    // FSR 4 checks (menu): the provider's auto exposure, the jitter sign it is given.
    std::atomic<bool> fsr4_auto_exposure{true};
    std::atomic<bool> fsr4_invert_jitter{false};
    std::atomic<int> active_render_width{1920}, active_render_height{1080};
    std::atomic<int> output_res{OutputDefault}; ///< index into OutputWidths
    /// Live resolution and preset changes (run.sh): 0 off by default (startup patch, fastest
    /// on the Steam Deck and older GPUs), -1 auto (strong discrete GPUs), 1 on. On restart.
    std::atomic<int> live_resolution{0};
    /// Why FSR 4 cannot run (assets, device features), or null. Set by the renderer.
    std::atomic<const char*> fsr4_problem{nullptr};
    std::atomic<bool> fsr4_supported{false}, fsr411_supported{false};
    /// DLSS (ratchet_dlss.dll, NVIDIA RTX) is ready, or why not (null before the device exists).
    std::atomic<bool> dlss_supported{false};
    std::atomic<const char*> dlss_problem{nullptr};

    /// Startup settings for the explicit RATCHET_RENDER_RES compatibility patch only.
    int startup_preset = NativeAA;
    int startup_upscaler = UpscalerFsr3;
    bool startup_object_motion = true;
    int startup_output_res = OutputDefault;
    int startup_live_resolution = 0;
};

Values& Get();

/// Reads the file, then the environment overrides. Called once at start.
void Load();
/// Checks the loaded choice before the first frame; unsupported FSR 4 uses FSR 3.1.
void ConfigureUpscalerSupport(bool fsr4, bool fsr411);
/// After device creation: DLSS availability; a DLSS setting falls back to FSR 3.1 without it.
void ConfigureDlssSupport(bool available, const char* problem);
/// Startup-patched scene dimensions cannot change until run.sh prepares a new image.
bool FixedRenderSession();
int RenderPreset();
bool ResolutionNeedsRestart();
/// A startup graphics option differs from the one this launch started with.
bool GraphicsNeedRestart();
/// Nominal startup target; not measured gameplay throughput.
int EngineFpsNow();
/// Compatibility no-op: Ratchet does not rewrite live FPS globals.
void SyncEngineFps();
/// Returns zero: Ratchet requires restart to change the guest timing.
int CycleEngineFps();
/// Writes the file (menu changes).
void Save();

/// Render resolution divisor of a preset (1.0 native, 1.5 quality, ...).
float PresetScale(int preset);
const char* PresetName(int preset);
const char* UpscalerName(int upscaler);

} // namespace RatchetSettings
