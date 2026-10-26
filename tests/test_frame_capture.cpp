// SPDX-License-Identifier: GPL-2.0-or-later
// The frame analyzer's buffer dump (vk_frame_capture.cpp). A binding whose bytes the host cannot
// read (data null: a constant-ring copy of the flattened user data carries guest address 0,
// issue #174) is skipped instead of read through the null pointer. No game or Vulkan device.
#include <array>
#include <cstdio>
#include <cassert>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <sstream>

#include "video_core/renderer_vulkan/vk_frame_capture.h"
#include "video_core/texture_cache/image_info.h"

int main() {
    // A buffer with host bytes is dumped as before.
    std::array<float, 16> words{};
    Vulkan::FrameCapture::Buffer(0x1234, 0, 0x1000, words.data(), sizeof(words));
    // Flattened user data in the constant ring: host copy only, guest address 0, and here
    // nothing readable at all. Must not dereference `data`.
    Vulkan::FrameCapture::Buffer(0x1234, 1, 0, nullptr, 64);
    const auto directory = std::filesystem::temp_directory_path() /
        ("ratchet-capture-test-" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
#ifdef _WIN32
    _putenv_s("RATCHET_CAPTURE_DIR", directory.string().c_str());
#else
    setenv("RATCHET_CAPTURE_DIR", directory.string().c_str(), 1);
#endif
    VideoCore::ImageInfo target{};
    target.guest_address = 0x1000;
    target.size = {3840, 2160, 1};
    target.pitch = 4096;
    target.guest_samples = 4;
    target.guest_size = 4096u * 2160 * 4 * 4;
    const VideoCore::ImageInfo* colors[]{&target};
    Vulkan::FrameCapture::AddDisplayBuffer(target.guest_address);
    Vulkan::FrameCapture::Request();
    Vulkan::FrameCapture::OnFlip(target.guest_address);
    Vulkan::FrameCapture::BeginPass(colors, 1, nullptr, "test");
    assert(Vulkan::FrameCapture::IsRecording());
    // No second display boundary: the bounded recorder still writes and stops.
    for (unsigned i = 0; i < 512; ++i) {
        target.guest_address += 0x1000;
        Vulkan::FrameCapture::BeginPass(colors, 1, nullptr, "test");
        Vulkan::FrameCapture::Poll();
        if (!Vulkan::FrameCapture::Active()) break;
    }
    assert(!Vulkan::FrameCapture::Active());
    // A later manual request still completes normally after the bounded capture.
    target.guest_address = 0x1000;
    Vulkan::FrameCapture::Request(false);
    Vulkan::FrameCapture::OnFlip(target.guest_address);
    Vulkan::FrameCapture::BeginPass(colors, 1, nullptr, "normal");
    assert(Vulkan::FrameCapture::IsRecording());
    Vulkan::FrameCapture::Buffer(0x9999, 0, 0x7000, words.data(), sizeof(words));
    target.guest_address = 0x2000;
    Vulkan::FrameCapture::BeginPass(colors, 1, nullptr, "normal");
    Vulkan::FrameCapture::Draw(1, 2, 3, 1);
    target.guest_address = 0x1000;
    Vulkan::FrameCapture::BeginPass(colors, 1, nullptr, "normal");
    assert(!Vulkan::FrameCapture::Active());
    unsigned files = 0;
    unsigned truncated = 0, normal = 0;
    for (const auto& file : std::filesystem::directory_iterator(directory)) {
        ++files;
        std::ifstream in(file.path());
        std::stringstream text;
        text << in.rdbuf();
        truncated += text.str().find("capture_truncated=1") != std::string::npos;
        normal += text.str().find("capture_truncated=0") != std::string::npos;
        assert(text.str().find("guest_samples=4 pitch=4096") != std::string::npos);
        assert(text.str().find("buffer stage 0000000000009999") == std::string::npos);
    }
    assert(files == 2 && truncated == 1 && normal == 1);
    Vulkan::FrameCapture::Request(false);
    Vulkan::FrameCapture::OnFlip(0x1000);
    for (unsigned i = 0; i < 8; ++i) {
        Vulkan::FrameCapture::OnFlip(0x1000);
        Vulkan::FrameCapture::Poll();
    }
    assert(!Vulkan::FrameCapture::Active());
    assert(Vulkan::FrameCapture::LastResult().find("no display-pass boundary") != std::string::npos);
    std::filesystem::remove_all(directory);
    std::puts("frame-capture-test ok");
    return 0;
}
