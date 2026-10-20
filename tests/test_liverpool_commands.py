"""Exercise the production ProcessCommands body with deterministic arrival timing.

The harness supplies queue/rasterizer stand-ins, not a second implementation of
ProcessCommands. Arrival immediately after an empty atomic load models a valid
producer interleaving; callbacks must never run before the draw-pipe drain.
"""
from pathlib import Path
import argparse
import os
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

HARNESS = r'''
#include <functional>
#include <mutex>
#include <queue>
#include <cstdio>
#include <stdexcept>
#include <vector>
namespace Common { template<class T> using UniqueFunction = std::function<T()>; }
namespace Vulkan {
struct DrawPipe { enum { ReasonCommands }; };
struct Rasterizer {
    bool drained = false;
    unsigned drains = 0;
    void DrainDrawPipe(unsigned) { drained = true; ++drains; }
};
}
namespace AmdGpu {
struct Counter {
    unsigned value = 0;
    std::function<void()> after_first_load;
    operator unsigned() {
        const unsigned observed = value;
        if (after_first_load) {
            auto arrival = std::move(after_first_load);
            after_first_load = {};
            arrival();
        }
        return observed;
    }
    Counter& operator--() { --value; return *this; }
};
struct Liverpool {
    Vulkan::Rasterizer* rasterizer;
    Counter num_commands;
    std::mutex submit_mutex;
    std::queue<Common::UniqueFunction<void>> command_queue;
    void ProcessCommands();
    void Push(std::function<void()> callback) {
        std::scoped_lock lock{submit_mutex};
        command_queue.push(std::move(callback));
        ++num_commands.value;
    }
};
__PRODUCTION_BODY__
}
int main() {
    using AmdGpu::Liverpool;
    Vulkan::Rasterizer raster;
    Liverpool gpu{&raster};
    std::vector<unsigned> calls;
    const auto callback = [&](unsigned index) {
        if (!raster.drained)
            throw std::runtime_error("callback executed while stage B could still own the scheduler");
        calls.push_back(index);
    };
    try {
        // Queue was already nonempty on entry.
        gpu.Push([&] { callback(1); });
        gpu.ProcessCommands();
        if (calls != std::vector<unsigned>{1}) return 2;
        // Queue becomes nonempty immediately after the first empty load.
        raster.drained = false;
        gpu.num_commands.after_first_load = [&] { gpu.Push([&] { callback(2); }); };
        gpu.ProcessCommands();
        gpu.ProcessCommands();
        if (calls != std::vector<unsigned>{1, 2}) return 3;
        // Another producer arrives while a callback is being executed.
        raster.drained = false;
        gpu.Push([&] {
            callback(3);
            gpu.Push([&] { callback(4); });
        });
        gpu.ProcessCommands();
        if (calls != std::vector<unsigned>{1, 2, 3, 4}) return 4;
        // No renderer: preserve the early-initialization command path.
        Liverpool startup{nullptr};
        bool ran = false;
        startup.Push([&] { ran = true; });
        startup.ProcessCommands();
        if (!ran) return 5;
    } catch (const std::exception& error) {
        std::fprintf(stderr, "FAIL: %s\n", error.what());
        return 1;
    }
    std::puts("PASS: pending, late-arrival, callback-arrival, and startup commands");
    return 0;
}
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path,
                        default=ROOT/'gpu/shadps4/video_core/amdgpu/liverpool.cpp')
    args = parser.parse_args()
    source = args.source.read_text(encoding='utf-8')
    start = source.index('void Liverpool::ProcessCommands() {')
    cursor = source.index('{', start)+1
    depth = 1
    while depth:
        depth += (source[cursor] == '{') - (source[cursor] == '}')
        cursor += 1
    body = source[start:cursor]
    compiler = shutil.which('clang++') or r'C:\msys64\clang64\bin\clang++.exe'
    env = dict(os.environ)
    env['PATH'] = str(Path(compiler).parent)+os.pathsep+env.get('PATH', '')
    with tempfile.TemporaryDirectory(prefix='ratchet-command-race-') as temporary:
        folder = Path(temporary)
        cpp = folder/'test.cpp'
        exe = folder/('test.exe' if os.name == 'nt' else 'test')
        cpp.write_text(HARNESS.replace('__PRODUCTION_BODY__', body), encoding='utf-8')
        subprocess.run([compiler, '-std=c++23', '-O2', '-Wall', '-Wextra',
                        '-Wno-missing-field-initializers', str(cpp), '-o', str(exe)],
                       env=env, check=True)
        return subprocess.run([str(exe)], env=env).returncode


if __name__ == '__main__':
    raise SystemExit(main())
