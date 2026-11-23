# portaudio-windows-builds

Automatically built [PortAudio](https://github.com/PortAudio/portaudio) DLLs for Windows,
with and without ASIO support.

This is an unofficial project, not affiliated with or endorsed by the PortAudio project or
Steinberg Media Technologies GmbH.

All files are built with GitHub Actions from public sources at recorded commits, which
can be [verified](#verifying-a-download).

## Downloads

The DLLs are available on the [Releases](../../releases) page, as individual files:

| File | Host APIs |
|---|---|
| `portaudio-<version>-win-<arch>.dll` | MME, DirectSound, WASAPI, WDM-KS |
| `portaudio-<version>-win-<arch>-asio.dll` | the same, plus ASIO |

- `<version>` is a PortAudio release (e.g. `v19.7.0`) or a state of its master branch, by
  commit date and hash (e.g. `master-20261120-e813847`).
- `<arch>` is `x64`, `x86` or `arm64`, and has to match the application that loads the DLL.

The DLLs don't require the Visual C++ redistributable.

## ASIO

The `-asio` DLLs load every installed ASIO driver when PortAudio initializes, even if ASIO
is never used. This can cause slow startup, disrupted audio and other problems, as
described in [PortAudio #696](https://github.com/PortAudio/portaudio/issues/696) and
[python-sounddevice #496](https://github.com/spatialaudio/python-sounddevice/issues/496).
The DLLs without `-asio` contain no ASIO code.

## Licenses

| What | License |
|---|---|
| The code in this repository (scripts, workflow) | [MIT](LICENSE) |
| DLLs without ASIO | [PortAudio's license](https://github.com/PortAudio/portaudio/blob/master/LICENSE.txt) |
| `-asio` DLLs | [GPLv3](https://www.gnu.org/licenses/gpl-3.0.html) |

**PortAudio** is developed by Ross Bencina, Phil Burk and contributors. See
[portaudio.com](https://www.portaudio.com/license.html) and the
[PortAudio repository](https://github.com/PortAudio/portaudio).

The **ASIO SDK** is by Steinberg Media Technologies GmbH. The `-asio` DLLs use it under
its GPLv3 option. See the [SDK repository](https://github.com/audiosdk/asio) and
[Steinberg's developer site](https://www.steinberg.net/en/company/developers.html).

ASIO is a trademark and software of Steinberg Media Technologies GmbH.

Users of these files are responsible for complying with the terms of the respective
licenses.

Each release includes the license texts, and its `NOTICE.md` links to the exact source
code of PortAudio, the ASIO SDK and the build scripts. The "Source code" archives that
GitHub adds to each release contain only this repository's code.

The ASIO SDK source is taken from [a fork](https://github.com/zEdS15B3GCwq/asio) of
[audiosdk/asio](https://github.com/audiosdk/asio). When the fork was created (2026-11-21),
it was identical to that repository, and differed from the ASIO SDK
[obtainable from Steinberg's website](https://www.steinberg.net/asiosdk) only in line
endings.

## Releases

A daily check looks for a new PortAudio release and for new commits on master, and
releases only what is new: a release build, a master build, or both. The release marked
"Latest" is the newest one with a PortAudio release build, so newer master builds may be
listed above it. `NOTICE.md` in each release records the commits and toolchain.

`Pa_GetVersionText()` returns `V19.7.0-devel` for both kinds of build. The revision after
it identifies the commit.

## Verifying a download

Each file has a signed
[attestation](https://docs.github.com/en/actions/concepts/security/artifact-attestations)
that links it to the workflow run and commit that produced it. It can be checked with the
[GitHub CLI](https://cli.github.com/):

```
gh attestation verify <file> --repo zEdS15B3GCwq/portaudio-windows-builds
```

Alternatively, the output of `Get-FileHash <file>` can be compared with `SHA256SUMS` from
the release. Either way, this shows where a file came from, and is not an audit of the code
in it.
