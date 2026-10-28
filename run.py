#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Prepares the game image and starts ratchet-probe (Windows and Linux; run.sh wraps it on Linux).

Environment variables (RATCHET_GAME_DIR, RATCHET_DATA_DIR, RATCHET_PATCHES, RATCHET_MODS_*,
RATCHET_USER_DIR, ...). Extra arguments go to ratchet-probe.
The in-game "Apply and restart" runs this script again through RATCHET_RESTART_COMMAND;
`--after PID` waits for the previous game process to end first (its GPU device and memory).
"""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time

WINDOWS = sys.platform == 'win32'
EXE_SUFFIX = '.exe' if WINDOWS else ''
if WINDOWS:
    import ctypes

PORT = Path(__file__).resolve().parent


def fail(message):
    print(message, file=sys.stderr)
    sys.exit(1)


def wait_for(pid):
    if not WINDOWS:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            except PermissionError:
                pass
            time.sleep(0.1)
        return
    kernel32 = ctypes.windll.kernel32
    SYNCHRONIZE = 0x00100000
    handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
    if handle:
        kernel32.WaitForSingleObject(handle, 30000)
        kernel32.CloseHandle(handle)


def no_console():
    """Started without a console (the launcher): console programs must not open their own."""
    if not WINDOWS:
        return 0
    return 0 if ctypes.windll.kernel32.GetConsoleWindow() else subprocess.CREATE_NO_WINDOW


def parse_cpu_features(output):
    """Instruction sets `ratchet-probe --cpu-features` reports missing ([] when complete)."""
    for line in output.splitlines():
        if line.startswith('CPU: missing '):
            return [name.strip() for name in line[len('CPU: missing '):].split(',') if name.strip()]
    return []


def isa_rewrite_wanted(missing, env):
    """RATCHET_ISA_REWRITE=1 forces the ISA rewrite table, 0 disables it; otherwise the CPU decides."""
    policy = env.get('RATCHET_ISA_REWRITE')
    if policy in ('0', '1'):
        return policy == '1'
    return bool(missing)


def run_script(name, *args, capture=False, check=True):
    # Inside the packaged launcher executable (PyInstaller) the executable runs scripts itself.
    script = ['--script'] if getattr(sys, 'frozen', False) else []
    command = [sys.executable, *script, str(PORT / 'scripts' / name), *map(str, args)]
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    if capture:
        result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True,
                                encoding='utf-8', env=env, creationflags=no_console())
        if not check:
            return result.returncode, result.stdout
        if result.returncode:
            sys.exit(result.returncode)
        return result.stdout
    # stdin given: the output handles are passed explicitly (a windowed launcher child would
    # get none otherwise).
    result = subprocess.run(command, stdin=subprocess.DEVNULL, env=env, creationflags=no_console())
    if result.returncode:
        sys.exit(result.returncode)
    return None


def launch_prefix(env):
    """Linux integrations chosen in the launcher: MangoHud is its Vulkan layer (an environment
    variable), GameMode a command that starts the game."""
    if WINDOWS:
        return []
    if env.get('RATCHET_MANGOHUD') == '1':
        env.setdefault('MANGOHUD', '1')
    if env.get('RATCHET_GAMEMODE') == '1':
        if gamemode := shutil.which('gamemoderun'):
            return [gamemode]
        print('GameMode: gamemoderun not found, starting without it', flush=True)
    return []


def find_executable(name):
    """bin/ (packaged), else out/ (built with build.sh)."""
    for candidate in (PORT / 'bin' / name, PORT / 'out' / name):
        if candidate.is_file():
            return candidate
    return None


def main():
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == '--after':
        wait_for(int(args[1]))
        args = args[2:]
    # As run.sh: relative paths (RATCHET_GAME_DIR, RATCHET_DATA_DIR, fsr4_shaders/) are from the port.
    os.chdir(PORT)
    env = os.environ
    sys.path.insert(0, str(PORT / 'scripts'))
    from session_diagnostics import header
    from release_info import VERSION
    print(header(VERSION), end='', flush=True)
    from control_bindings import validate_environment
    try:
        validate_environment(env)
    except ValueError as error:
        fail(str(error))
    data = Path(env.get('RATCHET_DATA_DIR', PORT))
    out = data / 'out'
    env.setdefault('RATCHET_CONFIG', str(data / 'ratchet.ini'))
    # Values this script derived on the previous start ("Apply and restart" inherits them) are
    # derived again from the new options.
    for key in env.pop('RATCHET_DERIVED', '').split(','):
        env.pop(key, None)
    derived = []
    import graphics_options
    try:
        import discord_presence
    except Exception:
        discord_presence = None
    import mods
    import ratchet_patches
    import frame_timing
    import motion_blur
    import shadow_resolution
    import internal_resolution
    import language_split
    import voice_archive
    game = Path(env.get('RATCHET_GAME_DIR', PORT.parent / 'CUSA01047'))
    if out.resolve().is_relative_to(game.resolve()):
        fail('Data output must be outside the original game directory.')
    ratchet_patches.reset(out)
    extra_resolutions = []
    graphics, reverted = graphics_options.prepare(env['RATCHET_CONFIG'], out / 'graphics_state.json', extra_resolutions)
    if reverted:
        print('Graphics: the last restart never reached the game; previous options restored', flush=True)
    env.update(graphics_options.environment(graphics))
    if not env.get('RATCHET_FSR411_DIR') and not (PORT / 'fsr4_411').is_dir() and (data / 'fsr4_411').is_dir():
        env['RATCHET_FSR411_DIR'] = str(data / 'fsr4_411')

    probe = Path(env['RATCHET_PROBE']) if env.get('RATCHET_PROBE') else find_executable('ratchet-probe' + EXE_SUFFIX)
    if not probe or not probe.is_file():
        fail(f'ratchet-probe{EXE_SUFFIX} not found: build it with build.sh or use a packaged build.')
    # Development builds run from the MSYS2 tree: its CLANG64 DLLs (SDL3, FFmpeg, ...).
    if WINDOWS and not (probe.parent / 'SDL3.dll').is_file():
        clang64 = Path(env.get('MSYS2_ROOT', r'C:\msys64')) / 'clang64' / 'bin'
        if clang64.is_dir():
            env['PATH'] = f'{clang64}{os.pathsep}{env.get("PATH", "")}'
    # Instruction sets this CPU lacks (MOVBE, BMI1, LZCNT): the ISA rewrite covers them; exit 20
    # is a set nothing covers.
    features = subprocess.run([str(probe), '--cpu-features'], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              text=True, creationflags=no_console())
    if features.returncode == 20:
        print(features.stdout, end='', flush=True)
        sys.exit(20)
    missing = parse_cpu_features(features.stdout)

    game = Path(env.get('RATCHET_GAME_DIR', PORT.parent / 'CUSA01047'))
    if not (game / 'eboot.bin').is_file():
        fail(f'No eboot.bin in {game} (set RATCHET_GAME_DIR).')
    from ratchet_game import validate_game
    try:
        validate_game(game)
    except (OSError, ValueError) as error:
        fail(str(error))
    if env.get('RATCHET_PATCH_DIR'):
        fail('Separate game updates are not supported: use CUSA01047 USA v1.00.')
    original_game = game.resolve()
    game = Path(run_script('mods.py', game, '--out', out,
                           '--mods-dir', env.get('RATCHET_MODS_DIR', data / 'mods'),
                           '--config', env.get('RATCHET_MODS_CONFIG', data / 'mods.json'),
                           '--enabled', env.get('RATCHET_MODS_ENABLED', '1'), capture=True).strip())
    mod_view = game if game.resolve() != original_game else None
    try:
        run_script('prepare.py', game, '--out', out)
        run_script('link_libc.py', game, '--out', out)
        run_script('link_modules.py', game, '--out', out)
        # A failed rewrite prints its reason and the game starts without the table.
        isa_args = []
        if isa_rewrite_wanted(missing, env):
            code, output = run_script('isa_rewrite.py', out / 'boot-linked.bin', '--out', out,
                                      capture=True, check=False)
            print(output, end='', flush=True)
            if code == 0:
                isa_args = ['--isa-rewrite', str(out / 'isa-rewrite.bin')]
        run_script('content_profile.py', game, '--out', out, '--sku', env.get('RATCHET_CONTENT_SKU', 'full'))

        requested = [n.strip() for n in env.get('RATCHET_PATCHES', '').split(';') if n.strip()]
        requested = frame_timing.requested_groups(graphics['game_fps'], requested)
        requested = motion_blur.requested_groups(graphics['motion_blur'], requested)
        requested = shadow_resolution.requested_groups(graphics['shadow_resolution'], requested)
        requested = internal_resolution.requested_groups(graphics['internal_resolution'], requested)
        text_language = env.get('RATCHET_TEXT_LANGUAGE', env.get('RATCHET_LANGUAGE', '1'))
        voice_language = env.get('RATCHET_VOICE_LANGUAGE', text_language)
        requested = language_split.requested_groups(text_language, voice_language, requested)
        patch_report = ratchet_patches.prepare(game, out, requested, isa_args[1] if isa_args else None)
        languages = language_split.launch_environment(text_language, voice_language, patch_report)
        env.update(languages)
        print(f"Languages: text={text_language}, requested voice={voice_language}, "
              f"launch voice={languages['RATCHET_LANGUAGE']}, split={languages['RATCHET_LANGUAGE_SPLIT']}; "
              "loader confirmation required", flush=True)
        text_locale = voice_archive.LANGUAGES[language_split.normalize(text_language)][1]
        voice_id = languages['RATCHET_LANGUAGE']
        report = voice_archive.inspect(original_game, voice_id)
        print(f"[Language]\nText language: {text_locale}\nVoice language: {report['locale']}", flush=True)
        print(voice_archive.describe(report), flush=True)
        if report['integrity'] in ('FAILED', 'WARNING'):
            print('WARNING: ' + voice_archive.warning(report), flush=True)
        timing = frame_timing.launch_environment(patch_report, env.get('RATCHET_FPS_LIMIT'))
        env.update(timing)
        derived.extend(timing)
        effects = {**motion_blur.launch_environment(patch_report),
                   **shadow_resolution.launch_environment(patch_report),
                   **internal_resolution.launch_environment(patch_report, env.get('RATCHET_DMEM_MB'))}
        env.update(effects)
        derived.extend(effects)
        print(f"Graphics effects: requested blur={graphics['motion_blur']}, "
              f"shadow cap={graphics['shadow_resolution']}; prepared "
              f"blur={effects['RATCHET_MOTION_BLUR']}, "
              f"shadow cap={effects['RATCHET_SHADOW_RESOLUTION']}; loader confirmation required", flush=True)
        print(f"Internal resolution: requested {graphics['internal_resolution']}, "
              f"prepared {effects['RATCHET_INTERNAL_RESOLUTION']}; loader confirmation required; "
              "output/window unchanged", flush=True)
        if heap_mb := internal_resolution.GPU_HEAP_MB.get(effects['RATCHET_INTERNAL_RESOLUTION']):
            print(f"Internal resolution memory: prepared XMemGpu={heap_mb} MiB, "
                  f"direct pool={effects['RATCHET_RESOLUTION_DMEM_MB']} MiB; loader confirmation required; "
                  "experimental high-resolution headroom", flush=True)
        print(f"Frame timing: requested {graphics['game_fps']}, launch ceiling "
              f"{timing['RATCHET_ENGINE_FPS']} FPS; loader confirmation required", flush=True)
        icon_file = PORT / 'launcher' / 'ratchet-probe.png'
        if not icon_file.is_file():
            icon_file = PORT / 'launcher' / 'ratchetport.png'
        try:
            from PIL import Image
            with Image.open(icon_file) as icon:
                icon.convert('RGBA').resize((64, 64)).save(out / 'window_icon.bmp')
            env.setdefault('RATCHET_WINDOW_ICON', str(out / 'window_icon.bmp'))
        except (ImportError, OSError):
            pass
        env.setdefault('RATCHET_UPSCALER', 'none')
        env.setdefault('RATCHET_READBACK_LINEAR', '1')
        env.setdefault('RATCHET_ZERO_CLEAR', '0')
        env.setdefault('RATCHET_VSYNC', '1')
        env.setdefault('RATCHET_OUTPUT_RES', '1280x720')
        env['RATCHET_DERIVED'] = ','.join(derived)
        mount_args = []
        import game_glyphs
        glyph_style = env.get('RATCHET_GLYPH_STYLE', 'off')
        if glyph_style == 'auto':
            try:
                detected = subprocess.run([str(probe), '--gamepad'], stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=15,
                    creationflags=no_console())
                glyph_style = game_glyphs.auto_style(detected.stdout) if detected.returncode == 0 else 'off'
            except (OSError, subprocess.SubprocessError):
                glyph_style = 'off'
        try:
            mount_args, glyph_report = game_glyphs.prepare(game, out / 'glyphs', glyph_style, env)
        except (OSError, ValueError, KeyError) as error:
            fail(f'Button icons could not be prepared: {error}. Select Original to use installed artwork.')
        print(f"Button icons: {glyph_report['style']} — {glyph_report['status']}; input mapping unchanged", flush=True)
        # Windows commits the direct pool and flexible span in full at startup.
        import guest_memory
        pool_mb = effects.get('RATCHET_RESOLUTION_DMEM_MB', env.get('RATCHET_DMEM_MB'))
        if warning := guest_memory.memory_warning(pool_mb, guest_memory.physical_memory_mb(),
                                                  env.get('RATCHET_STREAM_MEMORY', 'cached')):
            print(warning, flush=True)

        # The in-game restart starts this script again once this process is gone.
        # GPU caches (shaders, pipelines) beside the saves; read before main(), so set here.
        user_dir = Path(env.get('RATCHET_USER_DIR', data / 'user')).resolve()
        user_dir.mkdir(parents=True, exist_ok=True)
        env.setdefault('RATCHET_GPU_USER_DIR', str(user_dir))
        from save_backup import backup
        try:
            if made := backup(user_dir):
                print(f'Saves backed up to {made}', flush=True)
        except OSError as error:
            print(f'Save backup failed, starting anyway: {error}', flush=True)
        this = ['--run'] if getattr(sys, 'frozen', False) else [str(Path(__file__).resolve())]
        # Windows: the probe starts the new launch and ends, so it waits for this process. Linux:
        # the probe replaces itself with the new launch while this process still waits for it.
        after = ['--after', str(os.getpid())] if WINDOWS else []
        restart = [sys.executable, *this, *after, *args]
        env['RATCHET_RESTART_COMMAND'] = subprocess.list2cmdline(restart) if WINDOWS else shlex.join(restart)
        command = [*launch_prefix(env), str(probe), str(out / 'boot-linked.bin'), '--content-profile', str(out / 'content.bin'),
                   '--patches', str(out / 'patches.bin'), '--patch-receipt', str(out / 'patch_receipt.bin'),
                   '--app0', str(game),
                   '--user', str(user_dir),
                   '--timeout', env.get('RATCHET_TIMEOUT', '0'), *isa_args, *mount_args, *args]
        # No stdin: an inherited pipe (shells such as Git Bash) cost the game its console output.
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, creationflags=no_console())
        presence = None
        try:
            try:
                presence = discord_presence.Presence(pid=process.pid) if discord_presence else None
            except (OSError, RuntimeError):
                print('Discord presence unavailable; the game will continue', flush=True)
            returncode = process.wait()
            ratchet_patches.finish(out, returncode)
            return returncode
        finally:
            if presence:
                presence.close()
    finally:
        if mod_view:
            shutil.rmtree(mod_view, ignore_errors=True)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
