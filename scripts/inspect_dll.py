# SPDX-License-Identifier: MIT
"""Static checks on a built DLL. Doesn't execute it, so works for every architecture."""

import argparse
import sys
from pathlib import Path

import pefile
from common import ARCHES, VARIANTS, short_sha

MACHINES = {0x14C: "x86", 0x8664: "x64", 0xAA64: "arm64"}

# Importing any of these means that the C runtime is linked dynamically (/MD, not /MT).
DYNAMIC_CRT = ("vcruntime", "msvcp", "msvcr", "ucrtbase", "api-ms-win-crt-")

# The names that host APIs report are only in the binary if they were compiled in. Unlike
# asking PortAudio at runtime, this doesn't depend on the audio system of the machine.
HOST_API_MARKERS = {
    "MME": b"MME\0",
    "DirectSound": b"Windows DirectSound",
    "WASAPI": b"Windows WASAPI",
    "WDM-KS": b"Windows WDM-KS",
}


def check(path: Path, arch: str, variant: str, sha: str) -> list[str]:
    """Return a list of problems, which is empty if the DLL is as intended."""
    data = path.read_bytes()
    pe = pefile.PE(data=data)
    actual_arch = MACHINES.get(pe.FILE_HEADER.Machine, hex(pe.FILE_HEADER.Machine))
    imports = sorted(e.dll.decode().lower() for e in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []))
    export_table = getattr(pe, "DIRECTORY_ENTRY_EXPORT", None)
    exports = {s.name.decode() for s in export_table.symbols if s.name} if export_table else set()
    asio_exports = sorted(e for e in exports if e.startswith("PaAsio_"))

    print(f"== {path.name}")
    print(f"   arch    : {actual_arch}")
    print(f"   imports : {', '.join(imports)}")
    print(f"   exports : {len(exports)}, of which ASIO: {', '.join(asio_exports) or '-'}")

    problems = []
    if actual_arch != arch:
        problems.append(f"architecture is {actual_arch}, expected {arch}")
    if crt := [name for name in imports if name.startswith(DYNAMIC_CRT)]:
        problems.append(f"C runtime is linked dynamically: {crt}")
    if "Pa_Initialize" not in exports:
        problems.append("Pa_Initialize is not exported")
    if VARIANTS[variant] and not asio_exports:
        problems.append("ASIO is missing from the asio variant")
    if not VARIANTS[variant] and asio_exports:
        problems.append("ASIO is present in the no-asio variant")
    for name, marker in HOST_API_MARKERS.items():
        if marker not in data:
            problems.append(f"{name} is missing")
    if f"revision {short_sha(sha)}".encode() not in data:
        problems.append("the source revision is missing from the version text")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dll", type=Path)
    parser.add_argument("--arch", choices=ARCHES, required=True)
    parser.add_argument("--variant", choices=VARIANTS, required=True)
    parser.add_argument("--sha", required=True)
    args = parser.parse_args()

    if problems := check(args.dll, args.arch, args.variant, args.sha):
        sys.exit("\n".join(f"FAIL: {problem}" for problem in problems))
    print("   OK")


if __name__ == "__main__":
    main()
