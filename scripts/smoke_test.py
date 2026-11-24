# SPDX-License-Identifier: MIT
"""Load a DLL and initialize PortAudio, without assuming any audio hardware.

Needs a Python of the same architecture as the DLL. No stream is opened. Whether all host
APIs were compiled in is checked by inspect_dll.py, as it can't depend on the machine.
What's checked here, based on the initializers in v19.7.0 and master:

- MME, DirectSound and ASIO register even with no devices or drivers, so are required.
  Their device counts are irrelevant.
- WASAPI and WDM-KS don't register if their system components are unavailable, so they
  are optional.
- WASAPI makes Pa_Initialize fail with paInternalError if it can't enumerate endpoints,
  e.g. with no audio service. That is only a warning.
"""

import argparse
import ctypes
import sys
import sysconfig
from pathlib import Path

from common import VARIANTS, short_sha

# Values from portaudio.h
HOST_APIS = {1: "DirectSound", 2: "MME", 3: "ASIO", 11: "WDM-KS", 13: "WASAPI"}
PA_INTERNAL_ERROR = -9986
PA_FLOAT32 = 1


class HostApiInfo(ctypes.Structure):
    _fields_ = [
        ("structVersion", ctypes.c_int),
        ("type", ctypes.c_int),
        ("name", ctypes.c_char_p),
        ("deviceCount", ctypes.c_int),
        ("defaultInputDevice", ctypes.c_int),
        ("defaultOutputDevice", ctypes.c_int),
    ]


def load(path: Path):
    pa = ctypes.CDLL(str(path.resolve()))
    pa.Pa_GetVersionText.restype = ctypes.c_char_p
    pa.Pa_GetErrorText.restype = ctypes.c_char_p
    pa.Pa_GetSampleSize.argtypes = [ctypes.c_ulong]
    pa.Pa_GetHostApiInfo.restype = ctypes.POINTER(HostApiInfo)
    return pa


def check(pa, variant: str, sha: str) -> tuple[list[str], list[str]]:
    """Return problems, and warnings about what this machine didn't allow to test."""
    problems, warnings = [], []
    version = pa.Pa_GetVersionText().decode()
    print(f"   version: {version}")
    if short_sha(sha) not in version:
        problems.append(f"version text doesn't contain {short_sha(sha)}")
    if pa.Pa_GetSampleSize(PA_FLOAT32) != 4:
        problems.append("Pa_GetSampleSize(paFloat32) didn't return 4")

    if error := pa.Pa_Initialize():
        message = f"Pa_Initialize returned {error} ({pa.Pa_GetErrorText(error).decode()})"
        if error == PA_INTERNAL_ERROR:
            warnings.append(f"{message}, so host API registration wasn't tested")
        else:
            problems.append(message)
        return problems, warnings

    try:
        found = set()
        for index in range(pa.Pa_GetHostApiCount()):
            info = pa.Pa_GetHostApiInfo(index).contents
            name = HOST_APIS.get(info.type, f"type {info.type}")
            found.add(name)
            print(f"   [{index}] {name:<12} devices={info.deviceCount}")
    finally:
        pa.Pa_Terminate()

    required, optional = {"MME", "DirectSound"}, {"WASAPI", "WDM-KS"}
    if VARIANTS[variant]:
        required.add("ASIO")
    if missing := required - found:
        problems.append(f"missing host APIs: {', '.join(sorted(missing))}")
    if unexpected := found - required - optional:
        problems.append(f"unexpected host APIs: {', '.join(sorted(unexpected))}")
    if unavailable := optional - found:
        warnings.append(f"not available on this machine: {', '.join(sorted(unavailable))}")
    return problems, warnings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dll", type=Path)
    parser.add_argument("--variant", choices=VARIANTS, required=True)
    parser.add_argument("--sha", required=True)
    args = parser.parse_args()

    # Flush, so that the log names the DLL even if loading it crashes the process.
    print(f"== {args.dll.name}", flush=True)
    print(f"   python : {sys.version.split()[0]} {sysconfig.get_platform()}", flush=True)
    problems, warnings = check(load(args.dll), args.variant, args.sha)
    for warning in warnings:
        print(f"::warning::{args.dll.name}: {warning}")
    if problems:
        sys.exit("\n".join(f"FAIL: {problem}" for problem in problems))
    print("   OK")


if __name__ == "__main__":
    main()
