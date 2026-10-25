/* C interface of the GPU library (gpu/): shadPS4's Liverpool/Vulkan video core,
 * GnmDriver, VideoOut and kernel event queues, adapted to the native loader. */
#ifndef SPARTANGPU_H
#define SPARTANGPU_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    const char *title;          /* window title */
    const char *serial;         /* CUSA id, names the pipeline cache */
    const char *user_dir;       /* pipeline cache/logs directory */
    uint32_t sdk_version;       /* from the eboot's procparam */
    uint32_t psf_attributes;    /* param.sfo ATTRIBUTE */
    int32_t width, height;      /* initial window size */
} RatchetGpuConfig;
/* Registers kernel event queues (needed with or without graphics). */
void ratchetgpu_register_kernel(void);
/* Creates window, Vulkan device, presenter and GPU command processor. */
int ratchetgpu_init(const RatchetGpuConfig *config);
/* Function for an imported NID ("NID#lib#mod"), or 0 when the GPU library does not provide it. */
uintptr_t ratchetgpu_resolve(const char *scoped_nid);
/* Called first by the loader's SIGSEGV handler: 1 when a GPU page-tracking fault was handled. */
int ratchetgpu_handle_fault(void *ucontext, void *address);
/* RATCHET_WRITE_LOG=1: prints the logged GPU-side writes to guest memory near the fault. */
void ratchetgpu_dump_guest_writes(void *ucontext);
/* Keyboard text entry through the game window (IME dialog). begin returns 0 when
 * no window exists; poll returns 0 typing, 1 confirmed, 2 cancelled (UTF-8 text). */
int ratchetgpu_text_input_begin(const char *initial_utf8, const char *prompt_utf8);
int ratchetgpu_text_input_poll(char *out_utf8, uint64_t size);
/* A list for the player to choose from, drawn over the game (save list). images: a PNG path per
 * item drawn beside it (NULL array or entry: none). begin: 0 when no window exists.
 * poll: -1 while open, -2 cancelled, else the chosen index. */
int ratchetgpu_choice_begin(const char *title, const char *const *items, const char *const *images, int count, int focus);
int ratchetgpu_choice_poll(void);
/* 1 while the in-game settings menu is open: the game's pad input is held neutral. */
int ratchetgpu_overlay_captures_input(void);
/* Controller vibration strength set in the menu, 0 (off) to 100 (the game's own). */
int ratchetgpu_vibration_percent(void);
/* R3 + L1 + R1 (pad) or F9: the next engine frame rate (60, 100, 120, 144, 180, 240), applied live. */
void ratchetgpu_engine_fps_cycle(void);
/* The video decoder handed the game a picture: a cutscene is on screen (the presenter draws
 * black bars outside its 16:9 picture when the render resolution is not 16:9). */
void ratchetgpu_movie_picture(void);
/* Mouse movement in px that counts as one step of a stick prompt, set in the menu. */
/* The pause key (touchpad right) was pressed: it lets go of the mouse lock, or takes it back. */
void ratchetgpu_mouse_pause_key(void);
/* Mouse target: 0 off, 1 left, 2 right; activation: 0 always, 1 hold L2. */
int ratchetgpu_mouse_stick(void);
int ratchetgpu_mouse_activation(void);
int ratchetgpu_mouse_invert_y(void);
/* Style: 0 relative, 1 absolute. */
int ratchetgpu_mouse_aim_style(void);
/* Mouse sensitivity in percent (10 to 200), set in the menu. */
int ratchetgpu_mouse_aim_sensitivity(void);
/* Number of symbols registered by the vendored libraries (diagnostics). */
unsigned ratchetgpu_symbol_count(void);
/* Yields of threads waiting for guest memory copies (CPU report, #209). */
unsigned long long ratchetgpu_copy_yields(void);
#ifdef __cplusplus
}
#endif
#endif
