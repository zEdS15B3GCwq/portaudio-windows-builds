# SPDX-License-Identifier: MIT
"""Names and constants shared by the build scripts."""

# Our architecture name -> the name CMake's Visual Studio generator uses.
ARCHES = {"x86": "Win32", "x64": "x64", "arm64": "ARM64"}

# Variant -> whether ASIO is compiled in.
VARIANTS = {"asio": True, "no-asio": False}


def short_sha(sha: str) -> str:
    return sha[:7]


def file_suffix(variant: str) -> str:
    return "-asio" if VARIANTS[variant] else ""


def dll_name(label: str, arch: str, variant: str) -> str:
    return f"portaudio-{label}-win-{arch}{file_suffix(variant)}.dll"


def build_artifact_name(label: str, arch: str, variant: str) -> str:
    # Must match the artifact name in .github/workflows/build.yml
    return f"build-{label}-{arch}-{variant}"


def dev_zip_name(label: str) -> str:
    # resolve.py also uses this asset as the "already released" marker for a source.
    return f"portaudio-{label}-win-dev.zip"
