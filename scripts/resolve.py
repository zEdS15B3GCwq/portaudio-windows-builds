# SPDX-License-Identifier: MIT
"""Decide which PortAudio sources need building.

There are two candidates: the latest PortAudio release and the head of master. On main,
a candidate is built only if none of our releases contains it yet (or if forced). On
other branches both are always built, and nothing is published.

Our own GitHub releases are the only state, so there is no state file to maintain.
"""

import datetime as dt
import json
import os
import re
import urllib.parse
import urllib.request

from common import marker_name, short_sha

API = "https://api.github.com"
UPSTREAM = "PortAudio/portaudio"

# Upstream names end up in file names, artifact names and commands, so restrict them.
SAFE_TAG = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,49}")
FULL_SHA = re.compile(r"[0-9a-f]{40}")


def get_json(path: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "portaudio-build-script",
    }
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{API}{path}", headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def get_all_pages(path: str) -> list:
    items, page = [], 1
    PER_PAGE = 100
    while True:
        batch = get_json(f"{path}?per_page={PER_PAGE}&page={page}")
        items += batch
        if len(batch) < PER_PAGE:
            return items
        page += 1


def get_commit(ref: str) -> dict:
    commit = get_json(f"/repos/{UPSTREAM}/commits/{urllib.parse.quote(ref, safe='')}")
    if not FULL_SHA.fullmatch(commit["sha"]):
        raise ValueError(f"unexpected commit id for {ref}: {commit['sha']!r}")
    return commit


def find_candidates() -> list[dict]:
    tag = get_json(f"/repos/{UPSTREAM}/releases/latest")["tag_name"]
    if not SAFE_TAG.fullmatch(tag):
        raise ValueError(f"unexpected PortAudio release tag: {tag!r}")
    release_sha = get_commit(f"refs/tags/{tag}")["sha"]

    master = get_commit("master")
    # The commit date, not today's, so that a commit always gets the same label.
    committed = dt.datetime.fromisoformat(master["commit"]["committer"]["date"])
    date = committed.astimezone(dt.UTC).strftime("%Y%m%d")

    return [
        {"kind": "release", "label": tag, "sha": release_sha},
        {
            "kind": "master",
            "label": f"master-{date}-{short_sha(master['sha'])}",
            "sha": master["sha"],
        },
    ]


def select_new(candidates: list[dict], releases: list[dict]) -> list[dict]:
    published = {
        asset["name"]
        for release in releases
        if not release["draft"]
        for asset in release["assets"]
    }
    return [c for c in candidates if marker_name(c["label"]) not in published]


def next_tag(today: str, existing: set[str]) -> str:
    """Return 2026-11-22, or 2026-11-22.2, .3, ... if that tag is taken."""
    tag, number = today, 1
    while tag in existing:
        number += 1
        tag = f"{today}.{number}"
    return tag


def main() -> None:
    repo = os.environ["GITHUB_REPOSITORY"]
    publish = os.environ["GITHUB_REF"] == "refs/heads/main"
    build_all = not publish or os.environ.get("FORCE") == "true"

    candidates = find_candidates()
    if build_all:
        sources = candidates
    else:
        sources = select_new(candidates, get_all_pages(f"/repos/{repo}/releases"))

    today = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")
    refs = get_json(f"/repos/{repo}/git/matching-refs/tags/{today}")
    tag = next_tag(today, {ref["ref"].removeprefix("refs/tags/") for ref in refs})

    outputs = {
        "sources": json.dumps(sources, separators=(",", ":")),
        "any": str(bool(sources)).lower(),
        "publish": str(publish and bool(sources)).lower(),
        # A master-only release must not replace the last one with a stable build as "Latest".
        "latest": str(any(s["kind"] == "release" for s in sources)).lower(),
        "tag": tag,
    }
    with open(os.environ["GITHUB_OUTPUT"], "a") as file:
        for key, value in outputs.items():
            file.write(f"{key}={value}\n")
            print(f"{key}={value}")


if __name__ == "__main__":
    main()
