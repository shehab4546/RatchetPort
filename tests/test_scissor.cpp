// The intersection of guest clipping rectangles can be empty. It must never
// become a huge unsigned Vulkan extent when right/bottom precede left/top.
#include <algorithm>
#include <cassert>
#include <cstdio>
#include "video_core/amdgpu/regs_primitive.h"

int main() {
    AmdGpu::Scissor scissor{};
    scissor.top_left_x = 6025;
    scissor.bottom_right_x = 5131;
    scissor.top_left_y = 316;
    scissor.bottom_right_y = 0;
    if (scissor.GetWidth() != 0 || scissor.GetHeight() != 0) {
        std::fprintf(stderr, "FAIL: empty intersection became %u x %u\n",
                     scissor.GetWidth(), scissor.GetHeight());
        return 1;
    }
    scissor.top_left_x = 10;
    scissor.bottom_right_x = 1920;
    scissor.top_left_y = 20;
    scissor.bottom_right_y = 1080;
    assert(scissor.GetWidth() == 1910 && scissor.GetHeight() == 1060);
    scissor.top_left_x = -100;
    scissor.bottom_right_x = 200;
    scissor.top_left_y = -40;
    scissor.bottom_right_y = -1;
    assert(scissor.GetWidth() == 200 && scissor.GetHeight() == 0);
    std::puts("PASS: empty, ordinary, and negative guest scissor bounds");
}
