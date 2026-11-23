# SPDX-License-Identifier: MIT
"""Assemble what a release publishes: binaries, licenses, list of sources, checksums.

The DLLs are separate files, and the licenses that apply to them are released next to them.
Third-party sources are linked, not copied. GitHub adds the archive of this repository.
Runs without write permissions. The release job only uploads what this produces.
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from common import ARCHES, VARIANTS, build_artifact_name, dll_name
from inspect_dll import check
from notices import asio_license, notice, release_notes

# GPLv3 has to be passed on with the binaries. Ubuntu, which this runs on, ships the text.
GPL_TEXT = Path("/usr/share/common-licenses/GPL-3")


class Repo:
    """A single commit of a git repository, read without checking it out."""

    def __init__(self, directory: Path, commit: str):
        self.directory, self.commit = directory, commit

    @classmethod
    def fetch(cls, url: str, commit: str, directory: Path) -> "Repo":
        subprocess.run(["git", "init", "--quiet", str(directory)], check=True)
        repo = cls(directory, commit)
        repo.git("fetch", "--quiet", "--depth=1", url, commit)
        return repo

    def git(self, *args: str) -> bytes:
        return subprocess.run(
            ["git", "-c", "core.autocrlf=false", "-C", str(self.directory), *args],
            check=True,
            stdout=subprocess.PIPE,
        ).stdout

    def read(self, path: str) -> bytes:
        return self.git("show", f"{self.commit}:{path}")

    def text(self, path: str) -> str:
        return self.read(path).decode("utf-8", errors="replace").replace("\r\n", "\n")


def read_gpl(path: Path) -> bytes:
    text = path.read_bytes() if path.is_file() else b""
    if b"GNU GENERAL PUBLIC LICENSE" not in text or b"Version 3, 29 June 2007" not in text:
        sys.exit(f"{path} doesn't contain the GPLv3 text, which the release needs")
    return text


def collect_builds(source: dict, artifacts: Path, assets: Path) -> list[dict]:
    """Check and copy all DLLs of a source. Return their build details."""
    label, sha = source["label"], source["sha"]
    builds = []
    for arch in ARCHES:
        for variant in VARIANTS:
            directory = artifacts / build_artifact_name(label, arch, variant)
            name = dll_name(label, arch, variant)
            # Check again here, as this is the copy that gets published.
            if problems := check(directory / name, arch, variant, sha):
                sys.exit(f"{name}: {'; '.join(problems)}")
            (assets / name).write_bytes((directory / name).read_bytes())

            builds.append(json.loads((directory / "build-info.json").read_text(encoding="utf-8")))
    return builds


def write_checksums(assets: Path) -> None:
    lines = [
        f"{hashlib.sha256(file.read_bytes()).hexdigest()}  {file.name}\n"
        for file in sorted(assets.iterdir())
    ]
    (assets / "SHA256SUMS").write_bytes("".join(lines).encode())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--gpl-text", type=Path, default=GPL_TEXT)
    parser.add_argument("--portaudio-url", default="https://github.com/PortAudio/portaudio.git")
    args = parser.parse_args()

    sources = json.loads(os.environ["SOURCES"])
    sdk_repo, sdk_sha = os.environ["ASIO_REPO"], os.environ["ASIO_REF"]
    sdk_url = os.environ.get("ASIO_URL", f"https://github.com/{sdk_repo}.git")
    repo_name, builder_sha = os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_SHA"]
    gpl = read_gpl(args.gpl_text)

    assets = args.out / "assets"
    assets.mkdir(parents=True)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as work_dir:
        work = Path(work_dir)
        sdk = Repo.fetch(sdk_url, sdk_sha, work / "sdk")
        portaudio = {
            s["label"]: Repo.fetch(args.portaudio_url, s["sha"], work / f"pa-{number}")
            for number, s in enumerate(sources)
        }

        (assets / "LICENSE-GPL-3.0.txt").write_bytes(gpl)
        (assets / "LICENSE-ASIO-SDK.txt").write_bytes(asio_license(sdk).encode())
        # Normally the release and master have the same text. If not, include both.
        texts = dict.fromkeys(repo.read("LICENSE.txt") for repo in portaudio.values())
        (assets / "LICENSE-PortAudio.txt").write_bytes(b"\n\n".join(texts))

        all_builds = []
        for source in sources:
            all_builds += collect_builds(source, args.artifacts, assets)

    date = dt.datetime.now(dt.timezone.utc).date().isoformat()
    text = notice(sources, all_builds, sdk_repo, sdk_sha, repo_name, builder_sha, date)
    (assets / "NOTICE.md").write_bytes(text.encode())

    write_checksums(assets)
    notes = release_notes(sources, sdk_repo, sdk_sha, repo_name, builder_sha)
    (args.out / "RELEASE_NOTES.md").write_bytes(notes.encode())

    for file in sorted(assets.iterdir()):
        print(f"{file.stat().st_size:>10}  {file.name}")


if __name__ == "__main__":
    main()
