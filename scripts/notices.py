# SPDX-License-Identifier: MIT
"""The notices that the licenses require with the binaries, and the release notes."""

from common import ARCHES, VARIANTS, dll_name, short_sha

TRADEMARK = "ASIO is a trademark and software of Steinberg Media Technologies GmbH."

ASIO_ISSUES = (
    "[PortAudio #696](https://github.com/PortAudio/portaudio/issues/696) and "
    "[python-sounddevice #496](https://github.com/spatialaudio/python-sounddevice/issues/496)"
)

# About the fork's origin, so it stays true when the pinned commit changes.
SDK_ORIGINS = (
    "  - [audiosdk/asio](https://github.com/audiosdk/asio), which it was forked from",
    "  - the ASIO SDK [obtainable from Steinberg's website](https://www.steinberg.net/asiosdk)",
    "  - When the fork was created (2026-11-21, at commit 496a076), it was identical to",
    "    audiosdk/asio, and differed from Steinberg's download only in line endings. Both",
    "    may have changed since.",
)


def asio_license(sdk) -> str:
    """The SDK's LICENSE.txt, plus the license that is embedded in its host/ sources.

    The latter is BSD-style and has to be reproduced with binaries. All compiled host/
    files have the same one, so it's taken from one of them.
    """
    header = []
    for line in sdk.text("host/asiodrivers.cpp").splitlines():
        if line.strip() and not line.strip().startswith("//"):
            break
        header.append(line.rstrip())
    embedded = "\n".join(header).strip()
    if "Redistribution and use" not in embedded:
        raise ValueError("the license in the SDK's host/ sources has changed, review it")

    return (
        f"{sdk.text('LICENSE.txt').rstrip()}\n\n"
        "The SDK's host/ sources have the following license:\n\n"
        f"{embedded}\n"
    )


def source_list(
    sources: list[dict], sdk_repo: str, sdk_sha: str, repo: str, builder_sha: str
) -> list[str]:
    """Where to get the source of the binaries, as GPLv3 section 6(d) requires."""

    def link(name: str, sha: str) -> str:
        return f"[{name}@{short_sha(sha)}](https://github.com/{name}/tree/{sha})"

    return [
        *(f"- PortAudio {s['label']}: {link('PortAudio/portaudio', s['sha'])}" for s in sources),
        f"- ASIO SDK (only in `-asio` DLLs): {link(sdk_repo, sdk_sha)}",
        *SDK_ORIGINS,
        f"- Build scripts: {link(repo, builder_sha)}, also attached to the release as",
        '  "Source code" (zip and tar.gz), which contains only the code of this project',
    ]


def notice(
    sources: list[dict],
    builds: list[dict],
    sdk_repo: str,
    sdk_sha: str,
    repo: str,
    builder_sha: str,
    date: str,
) -> str:
    lines = [
        "# Notice",
        "",
        "- DLLs without `-asio` in the name are PortAudio, see LICENSE-PortAudio.txt.",
        "- `*-asio.dll` files combine PortAudio with the Steinberg ASIO SDK, which is used",
        "  under its GPLv3 option. These files are licensed under GPLv3, see",
        "  LICENSE-GPL-3.0.txt, LICENSE-PortAudio.txt and LICENSE-ASIO-SDK.txt.",
        "- There is no warranty.",
        "",
        TRADEMARK,
        "",
        "## Sources",
        "",
        f"Built on {date} from the source code at these locations:",
        "",
        *source_list(sources, sdk_repo, sdk_sha, repo, builder_sha),
    ]
    if any(source["kind"] == "master" for source in sources):
        lines += [
            "",
            "In master builds, PortAudio's CMake script compiles a modified copy of the SDK's",
            "host/pc/asiolist.cpp, with `delete lpdrv` replaced by `delete[] lpdrv`.",
        ]

    toolchains = sorted(
        {
            f"- MSVC {b['msvc']}, Windows SDK {b['windows_sdk']}, "
            f"CMake {b['cmake']}, image {b['runner_image']}"
            for b in builds
        }
    )
    return "\n".join([*lines, "", "## Toolchain", "", *toolchains, ""])


def release_notes(
    sources: list[dict], sdk_repo: str, sdk_sha: str, repo: str, builder_sha: str
) -> str:
    lines = ["Unofficial PortAudio DLLs for Windows, built with GitHub Actions.", ""]
    for source in sources:
        label, sha = source["label"], source["sha"]
        lines += [
            f"### PortAudio {label}",
            "",
            f"Commit [`{short_sha(sha)}`](https://github.com/PortAudio/portaudio/commit/{sha})",
            "",
            "| Architecture | With ASIO support | Without ASIO |",
            "|---|---|---|",
        ]
        for arch in ARCHES:
            names = " | ".join(f"`{dll_name(label, arch, variant)}`" for variant in VARIANTS)
            lines.append(f"| {arch} | {names} |")
        lines.append("")

    readme = f"https://github.com/{repo}/blob/{builder_sha}/README.md"
    lines += [
        "All DLLs support MME, DirectSound, WASAPI and WDM-KS.",
        "",
        "The `-asio` DLLs load every installed ASIO driver when PortAudio initializes, which",
        f"can cause slow startup, disrupted audio and other problems. See {ASIO_ISSUES}.",
        "",
        "### Licenses",
        "",
        "- `-asio` DLLs: **GPLv3**, as they contain code of the Steinberg ASIO SDK",
        "- Other DLLs: PortAudio's license",
        "",
        "The license texts are attached to this release. Users are responsible for complying",
        "with the terms of these licenses.",
        f"See the [README]({readme}#licenses) for details.",
        "",
        "### Sources",
        "",
        *source_list(sources, sdk_repo, sdk_sha, repo, builder_sha),
        "",
        "### Verification",
        "",
        "```",
        f"gh attestation verify <file> --repo {repo}",
        "```",
        "",
        "SHA-256 checksums are in `SHA256SUMS`.",
        "",
        TRADEMARK,
        "",
    ]
    return "\n".join(lines)
