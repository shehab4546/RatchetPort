/* RATCHET_PAD_MAP / RATCHET_KEY_MAP parsing (src/runtime_pad.c). */
#define _GNU_SOURCE
#include <assert.h>
#include "../src/runtime_pad.c"

int ratchetgpu_overlay_captures_input(void) { return 0; }
int ratchetgpu_vibration_percent(void) { return 100; }
static int pause_keys;
void ratchetgpu_mouse_pause_key(void) { ++pause_keys; }
static int aim_style;
int ratchetgpu_mouse_aim_style(void) { return aim_style; }
static int aim_sensitivity=100;
static int mouse_stick=2, mouse_activation=1, mouse_invert_y=0;
static int mouse_directions[4]={5,6,7,8};
int ratchetgpu_mouse_direction(int direction) { return mouse_directions[direction]; }
int ratchetgpu_mouse_stick(void) { return mouse_stick; }
int ratchetgpu_mouse_activation(void) { return mouse_activation; }
int ratchetgpu_mouse_invert_y(void) { return mouse_invert_y; }
int ratchetgpu_mouse_aim_sensitivity(void) { return aim_sensitivity; }
void ratchetgpu_engine_fps_cycle(void) {}
uintptr_t runtime_lookup(const RuntimeExport *table, size_t count, const char *name) {
    (void)table; (void)count; (void)name;
    return 0;
}

/* PS4 buttons a host source presses in `map`. */
static uint32_t pressed_by(const ButtonMap *map, int source) {
    uint32_t ps=0;
    for (size_t i=0;i<map->count;++i) if (map->entries[i].source==source) ps|=map->entries[i].ps;
    return ps;
}

int main(void) {
    { /* Holds survive repeated samples and release only when both sources release. */
        bool held[SDL_SCANCODE_COUNT]={0}, no_wheel[2]={0};
        PadData frame={0};
        ButtonMap saved_primary=key_map;
        apply_button_map(&key_map,"r2=Mouse Left",true);
        apply_button_map(&key_alt_map,"r2=F",true);
        for (int i=0;i<120;++i) {
            memset(&frame,0,sizeof(frame));
            merge_keyboard_buttons(&frame,held,SDL_BUTTON_LMASK,no_wheel);
            assert((frame.buttons & BTN_R2) && frame.r2==255);
        }
        held[SDL_SCANCODE_F]=true;
        memset(&frame,0,sizeof(frame));
        merge_keyboard_buttons(&frame,held,0,no_wheel);
        assert((frame.buttons & BTN_R2) && frame.r2==255);
        held[SDL_SCANCODE_F]=false;
        memset(&frame,0,sizeof(frame));
        merge_keyboard_buttons(&frame,held,0,no_wheel);
        assert(!(frame.buttons & BTN_R2) && frame.r2==0);
        frame.buttons=BTN_R2; frame.r2=87;
        merge_keyboard_buttons(&frame,held,0,no_wheel);
        assert(frame.r2==87); /* Keyboard idle: preserve physical analog pressure. */
        key_map=saved_primary; memset(&key_alt_map,0,sizeof(key_alt_map));
    }

    ButtonMap keys=key_map;
    assert(apply_button_map(&keys,NULL,true)==0 && apply_button_map(&keys,"",true)==0);
    assert(keys.count==key_map.count);

    /* Swap: Q presses Cross, Space presses Triangle; Space no longer presses Cross. */
    assert(apply_button_map(&keys," cross = Q , triangle=Space",true)==2);
    assert(pressed_by(&keys,SDL_SCANCODE_Q)==BTN_CROSS);
    assert(pressed_by(&keys,SDL_SCANCODE_SPACE)==BTN_TRIANGLE);
    assert(pressed_by(&keys,SDL_SCANCODE_E)==BTN_SQUARE);

    /* Names with spaces, any case; the last entry for a button wins. */
    ButtonMap again=key_map;
    assert(apply_button_map(&again,"CIRCLE=left shift,circle=Left Ctrl",true)==2);
    assert(pressed_by(&again,SDL_SCANCODE_LCTRL)==BTN_CIRCLE);
    assert(pressed_by(&again,SDL_SCANCODE_LSHIFT)==0);

    /* Bad entries are skipped and leave the defaults alone. */
    ButtonMap bad=key_map;
    assert(apply_button_map(&bad,"bogus=Q,cross=NotAKey,circle,=Q,square=,,",true)==0);
    assert(bad.count==key_map.count && pressed_by(&bad,SDL_SCANCODE_SPACE)==BTN_CROSS);

    /* Gamepad: Xbox layout swap; 'touchpad' is the left click, Back stays the right click and
     * the real touchpad click keeps its fingers. */
    ButtonMap pad=pad_map;
    assert(apply_button_map(&pad,"cross=b,circle=a,touchpad=misc1",false)==3);
    assert(pressed_by(&pad,SDL_GAMEPAD_BUTTON_EAST)==BTN_CROSS);
    assert(pressed_by(&pad,SDL_GAMEPAD_BUTTON_SOUTH)==BTN_CIRCLE);
    assert(pressed_by(&pad,SDL_GAMEPAD_BUTTON_MISC1)==CLICK_LEFT);
    assert(pressed_by(&pad,SDL_GAMEPAD_BUTTON_BACK)==CLICK_RIGHT);
    assert(pressed_by(&pad,SDL_GAMEPAD_BUTTON_TOUCHPAD)==BTN_TOUCHPAD);
    assert(apply_button_map(&pad,"touchpad_right=guide,touchpad_left=paddle1",false)==2);
    assert(pressed_by(&pad,SDL_GAMEPAD_BUTTON_BACK)==0 && pressed_by(&pad,SDL_GAMEPAD_BUTTON_GUIDE)==CLICK_RIGHT);
    assert(pressed_by(&pad,SDL_GAMEPAD_BUTTON_MISC1)==0 && pressed_by(&pad,SDL_GAMEPAD_BUTTON_RIGHT_PADDLE1)==CLICK_LEFT);
    assert(apply_button_map(&pad,"cross=Space",false)==0); /* a key name is no gamepad button */
    /* Keyboard: each side has a key of its own. */
    assert(pressed_by(&key_map,SDL_SCANCODE_TAB)==CLICK_LEFT && pressed_by(&key_map,SDL_SCANCODE_BACKSPACE)==CLICK_RIGHT);
    ButtonMap sides=key_map;
    assert(apply_button_map(&sides,"touchpad_right=Delete",true)==1);
    assert(pressed_by(&sides,SDL_SCANCODE_BACKSPACE)==0 && pressed_by(&sides,SDL_SCANCODE_DELETE)==CLICK_RIGHT);
    /* Comma and Equals stand for the two separator keys; Escape is an ordinary key. */
    ButtonMap marks=key_map;
    assert(apply_button_map(&marks,"cross=Comma,circle=equals,square=Escape",true)==3);
    assert(pressed_by(&marks,SDL_SCANCODE_COMMA)==BTN_CROSS && pressed_by(&marks,SDL_SCANCODE_EQUALS)==BTN_CIRCLE);
    assert(pressed_by(&marks,SDL_SCANCODE_ESCAPE)==BTN_SQUARE);

    /* Mouse names on the keyboard map (any case); they take the button from its default key. */
    ButtonMap mouse=key_map;
    assert(apply_button_map(&mouse,"square=Mouse Left,triangle=mouse right,circle=Mouse Middle,"
                                   "l1=Wheel Up,r1=wheel down,l2=Mouse Back,r2=Mouse Forward",true)==7);
    assert(pressed_by(&mouse,MOUSE_LEFT)==BTN_SQUARE && pressed_by(&mouse,SDL_SCANCODE_E)==0);
    assert(pressed_by(&mouse,MOUSE_RIGHT)==BTN_TRIANGLE && pressed_by(&mouse,MOUSE_MIDDLE)==BTN_CIRCLE);
    assert(pressed_by(&mouse,WHEEL_UP)==BTN_L1 && pressed_by(&mouse,WHEEL_DOWN)==BTN_R1);
    assert(pressed_by(&mouse,MOUSE_BACK)==BTN_L2 && pressed_by(&mouse,MOUSE_FORWARD)==BTN_R2);
    assert(apply_button_map(&pad_map,"cross=Mouse Left",false)==0); /* the gamepad map has no mouse */

    /* Sources: mouse masks, wheel pulses, and keys only inside the scancode range. */
    bool held[SDL_SCANCODE_COUNT]={0};
    held[SDL_SCANCODE_E]=true;
    const bool no_wheel[2]={false,false}, up[2]={true,false};
    assert(source_down(SDL_SCANCODE_E,held,0,no_wheel) && !source_down(SDL_SCANCODE_Q,held,0,no_wheel));
    assert(source_down(MOUSE_LEFT,held,SDL_BUTTON_LMASK,no_wheel));
    assert(!source_down(MOUSE_RIGHT,held,SDL_BUTTON_LMASK,no_wheel));
    assert(source_down(MOUSE_BACK,held,SDL_BUTTON_X1MASK,no_wheel));
    assert(source_down(MOUSE_FORWARD,held,SDL_BUTTON_X2MASK,no_wheel));
    assert(source_down(WHEEL_UP,held,0,up) && !source_down(WHEEL_DOWN,held,0,up));

    /* Two notches up: press, gap, press, then idle; the other direction stays up. */
    SDL_SetAtomicInt(&wheel_ticks[0],2);
    const uint64_t t0=1000;
    assert(wheel_held(0,t0) && wheel_held(0,t0+WHEEL_PRESS_US-1));
    assert(!wheel_held(0,t0+WHEEL_PRESS_US));
    const uint64_t t1=t0+WHEEL_PRESS_US+WHEEL_GAP_US;
    assert(wheel_held(0,t1) && !wheel_held(0,t1+WHEEL_PRESS_US));
    assert(!wheel_held(0,t1+WHEEL_PRESS_US+WHEEL_GAP_US));
    assert(!wheel_held(1,t1));
    /* Notches beyond the limit are dropped, and the menu drops the rest. */
    SDL_Event spin={0};
    spin.type=SDL_EVENT_MOUSE_WHEEL; spin.wheel.integer_y=-10;
    mouse_watch(NULL,&spin);
    assert(SDL_GetAtomicInt(&wheel_ticks[1])==WHEEL_MAX_PENDING);
    drop_wheel();
    assert(SDL_GetAtomicInt(&wheel_ticks[1])==0 && !wheel_held(1,t1));
    /* The pause key tells the window once per press; L1 + touchpad right (photo mode) does not. */
    PadData menu={0};
    menu.buttons=CLICK_RIGHT; note_pause_key(&menu); note_pause_key(&menu);
    assert(pause_keys==1);
    menu.buttons=0; note_pause_key(&menu);
    menu.buttons=CLICK_RIGHT|BTN_L1; note_pause_key(&menu);
    assert(pause_keys==1);
    menu.buttons=0; note_pause_key(&menu);
    menu.buttons=CLICK_RIGHT; note_pause_key(&menu);
    assert(pause_keys==2);

    /* All four diagonals keep both axes, with a circular rather than square range. */
    for (int horizontal=-1;horizontal<=1;horizontal+=2) for (int vertical=-1;vertical<=1;vertical+=2) {
        uint8_t x=128,y=128;
        keyboard_stick(&x,&y,horizontal<0,horizontal>0,vertical<0,vertical>0);
        assert(((int)x-128)*horizontal>0 && ((int)y-128)*vertical>0);
        assert(abs(abs((int)x-128)-abs((int)y-128))<=1);
        assert(hypotf((float)x-128,(float)y-128)<=128);
    }
    uint8_t kx=128,ky=128;
    keyboard_stick(&kx,&ky,false,true,true,false);
    keyboard_stick(&kx,&ky,true,true,true,false);
    assert(kx==128 && ky==0); // horizontal opposites cancel; forward remains

    /* Small continuous movements clear the game dead zone; no L2 or offset mode. */
    SDL_Event glide={0}; glide.type=SDL_EVENT_MOUSE_MOTION;
    PadData item={0}; item.timestamp=50000000;
    for (int frame=0;frame<20;++frame) {
        item.left_x=item.left_y=item.right_x=item.right_y=128;
        item.timestamp+=16667; glide.motion.xrel=1; glide.motion.yrel=-1;
        mouse_watch(NULL,&glide); apply_mouse_aim(&item);
        assert(item.right_x>128 && item.right_y<128 && item.left_x==128);
    }
    /* Shallow mouse angles are preserved instead of lifting both axes separately. */
    item.timestamp+=16667; glide.motion.xrel=40; glide.motion.yrel=-10;
    mouse_watch(NULL,&glide); apply_mouse_aim(&item);
    assert(item.right_x>128 && item.right_y<128);
    assert(abs(((int)item.right_x-128)-4*(128-(int)item.right_y))<=3);
    assert(hypotf((float)item.right_x-128,(float)item.right_y-128)<=128);
    const uint8_t tilt=item.right_x;
    item.right_x=item.right_y=128; item.timestamp+=1000; apply_mouse_aim(&item);
    assert(item.right_x==tilt); // multiple reads between reports preserve movement
    item.right_x=151; item.right_y=128; item.timestamp+=AIM_HOLD_US;
    apply_mouse_aim(&item); assert(item.right_x==151 && item.right_y==128); // physical pad resumes
    assert(apply_stick_keys("rx_neg=Mouse Move Right,rx_pos=Mouse Move Left,ry_neg=None,ry_pos=Down")==4);
    item.right_x=item.right_y=128; item.timestamp+=16667;
    glide.motion.xrel=10; glide.motion.yrel=-10;
    mouse_watch(NULL,&glide); apply_mouse_aim(&item);
    assert(item.right_x<128 && item.right_y==128); // map controls direction; None disables it
    SDL_Event lost={0}; lost.type=SDL_EVENT_WINDOW_FOCUS_LOST;
    mouse_watch(NULL,&lost); item.right_x=128; apply_mouse_aim(&item);
    assert(!aim.moved && item.right_x==128 && !SDL_GetAtomicInt(&mouse_motion[0]));
    uint8_t opposite=17; key_axis(&opposite,true,true); assert(opposite==128);
    assert(apply_stick_keys("lx_neg=J,lx_pos=L,ly_neg=None,rx_pos=Mouse Right,bad=A,ry_pos=NotAKey")==4);
    assert(stick_keys[0]==SDL_SCANCODE_J && stick_keys[1]==SDL_SCANCODE_L);
    assert(stick_keys[2]==0 && stick_keys[5]==MOUSE_RIGHT && stick_keys[7]==SDL_SCANCODE_DOWN);
    puts("PASS: pad and key maps");
}
