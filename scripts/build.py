# SPDX-License-Identifier: MIT
"""Build one PortAudio DLL (one source, architecture and variant) with CMake and MSVC.

Expected layout, which both v19.7.0 and master find without any path options:

    <dir>/portaudio/   PortAudio sources
    <dir>/asiosdk/     ASIO SDK sources (asio variant only)

Output:

    <out>/portaudio-<label>-win-<arch>[-asio].dll
    <out>/dev/         import library, under its original name
    <out>/build-info.json
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from common import ARCHES, VARIANTS, dll_name, short_sha


def run(command: list[str], env: dict) -> str:
    """Run a command, echo its output into the log and return it."""
    print("+", subprocess.list2cmdline(command), flush=True)
    lines = []
    with subprocess.Popen(
        command,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    ) as process:
        for line in process.stdout:
            print(line, end="", flush=True)
            lines.append(line)
    if process.returncode:
        sys.exit(f"command failed with exit code {process.returncode}")
    return "".join(lines)


def build_environment(sha: str) -> dict:
    define = f"/DPA_GIT_REVISION={short_sha(sha)}"
    return {
        **os.environ,
        # v19.7.0 doesn't configure with CMake 4 without this. Harmless for master.
        "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
        # Both are needed: CMake's Visual Studio generator takes the project's definitions
        # from the C++ flags if the target has C++ files (ASIO), else from the C flags.
        "CFLAGS": define,
        "CXXFLAGS": define,
        # Omit timestamps, so that the same inputs give the same DLL.
        "LDFLAGS": "/Brepro",
    }


def configure_command(source: Path, build: Path, arch: str, with_asio: bool) -> list[str]:
    return [
        "cmake",
        "-S", str(source),
        "-B", str(build),
        "-A", ARCHES[arch],
        f"-DPA_USE_ASIO={'ON' if with_asio else 'OFF'}",
        "-DPA_USE_DS=ON",
        "-DPA_USE_WMME=ON",
        "-DPA_USE_WASAPI=ON",
        "-DPA_USE_WDMKS=ON",
        "-DPA_DLL_LINK_WITH_STATIC_RUNTIME=ON",
    ]


def only_match(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if len(matches) != 1:
        sys.exit(f"expected one {pattern} in {directory}, found {[m.name for m in matches]}")
    return matches[0]


def find_in_log(pattern: str, log: str) -> str:
    match = re.search(pattern, log)
    return match.group(1) if match else "unknown"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--arch", choices=ARCHES, required=True)
    parser.add_argument("--variant", choices=VARIANTS, required=True)
    parser.add_argument("--build", type=Path, default=Path("build"))
    parser.add_argument("--out", type=Path, default=Path("out"))
    args = parser.parse_args()

    source, build, out = args.source.resolve(), args.build.resolve(), args.out.resolve()
    with_asio = VARIANTS[args.variant]
    sdk = source.parent / "asiosdk"
    if with_asio and not (sdk / "common" / "asio.h").is_file():
        sys.exit(f"the asio variant needs the ASIO SDK in {sdk}")
    if not with_asio and sdk.exists():
        sys.exit(f"the no-asio variant must be built without the ASIO SDK present, found {sdk}")
    if build.exists() or out.exists():
        sys.exit("build and output directories must not exist yet")

    env = build_environment(args.sha)
    log = run(configure_command(source, build, args.arch, with_asio), env)
    # If master doesn't find the SDK, it silently downloads another one from steinberg.net.
    if "Downloading ASIO SDK" in log:
        sys.exit("CMake downloaded an ASIO SDK instead of using the pinned one")
    run(["cmake", "--build", str(build), "--config", "Release", "--target", "portaudio"], env)

    release = build / "Release"
    # The names vary: portaudio_x86.dll and portaudio_x64.dll (also for ARM64) in v19.7.0,
    # portaudio.dll in master.
    dll = only_match(release, "portaudio*.dll")
    lib = only_match(release, f"{dll.stem}.lib")

    (out / "dev").mkdir(parents=True)
    shutil.copy2(dll, out / dll_name(args.label, args.arch, args.variant))
    # Keep the library's name: it's also the DLL name that the library refers to.
    shutil.copy2(lib, out / "dev" / lib.name)

    cmake_version = run(["cmake", "--version"], env).splitlines()[0].split()[-1]
    info = {
        "cmake": cmake_version,
        "msvc": find_in_log(r"C compiler identification is MSVC ([\d.]+)", log),
        "windows_sdk": find_in_log(r"Selecting Windows SDK version ([\d.]+)", log),
        "runner_image": " ".join(
            os.environ.get(name, "") for name in ("ImageOS", "ImageVersion")
        ).strip() or "local",
    }
    (out / "build-info.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
