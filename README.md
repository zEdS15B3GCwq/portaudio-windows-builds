# portaudio-windows-builds

Automatically built [PortAudio](https://github.com/PortAudio/portaudio) DLLs for Windows,
with and without ASIO support.

This is an unofficial project, not affiliated with or endorsed by the PortAudio project or
Steinberg Media Technologies GmbH.

All files are built with GitHub Actions from public sources at recorded commits, and you
can [verify that](#verifying-a-download).

## Downloads

The DLLs are on the [Releases](../../releases) page, as individual files:

| File | Host APIs |
|---|---|
| `portaudio-<version>-win-<arch>.dll` | MME, DirectSound, WASAPI, WDM-KS |
| `portaudio-<version>-win-<arch>-asio.dll` | the same, plus ASIO |

- `<version>` is a PortAudio release (e.g. `v19.7.0`) or a state of its master branch, by
  commit date and hash (e.g. `master-20261120-e813847`).
- `<arch>` is `x64`, `x86` or `arm64`. It must match the application that loads the DLL.

The DLLs don't need the Visual C++ redistributable.

To link at compile time, get the headers and import libraries from
`portaudio-<version>-win-dev.zip`, and rename the DLL to the name of the library
(e.g. `portaudio.lib` needs `portaudio.dll`).

## Before you use a DLL with ASIO

**Use an `-asio` DLL only if you need ASIO.** When PortAudio initializes, it loads and
queries *every* installed ASIO driver, even if your application never uses ASIO. These
drivers are third-party code of varying quality, which has consequences:

- **Security risk**: the drivers' code runs inside your process, with its privileges.
- **Slow initialization**: each driver adds to the startup time, some of them seconds.
- **Disrupted audio**: some drivers seize the device when loaded, which can interrupt the
  audio of other applications.
- **Crashes**: a faulty driver can take down your application.

[python-sounddevice issue #496](https://github.com/spatialaudio/python-sounddevice/issues/496)
describes the problems this caused in practice: with ASIO included in the bundled DLL,
merely importing the package interrupted other audio and delayed startup, so ASIO is no
longer enabled there by default. The underlying cause is discussed in
[PortAudio issue #696](https://github.com/PortAudio/portaudio/issues/696).

The DLLs without `-asio` don't have these problems, as they contain no ASIO code.

## Licenses

| What | License |
|---|---|
| The code in this repository (scripts, workflow) | [MIT](LICENSE) |
| DLLs without ASIO | PortAudio's [MIT license](https://github.com/PortAudio/portaudio/blob/master/LICENSE.txt) |
| `-asio` DLLs | [GPLv3](https://www.gnu.org/licenses/gpl-3.0.html) |

**PortAudio** is by Ross Bencina, Phil Burk and contributors, under the MIT license. See
[portaudio.com](https://www.portaudio.com/license.html) and its
[repository](https://github.com/PortAudio/portaudio).

**Steinberg Audio Stream I/O API (ASIO)** is by Steinberg Media Technologies GmbH, who
offer the SDK under either a proprietary license or GPLv3. The DLLs here use the GPLv3
option. See the [SDK repository](https://github.com/audiosdk/asio) and
[Steinberg's developer site](https://www.steinberg.net/en/company/developers.html).

ASIO is a trademark and software of Steinberg Media Technologies GmbH.

**Your responsibilities**: if you redistribute a DLL, you have to comply with its license.
For the `-asio` DLLs that is GPLv3, which can also affect the licensing of software that
you distribute with them. If GPLv3 doesn't suit you, use a DLL without ASIO, or obtain a
license from Steinberg and build your own. Refer to the documentation linked above.

Each release includes the license texts and the sources of PortAudio, the ASIO SDK and
the build scripts.

## Releases

A daily check looks for a new PortAudio release and for new commits on master, and
releases only what is new: a release build, a master build, or both. The release marked
"Latest" is the newest with a PortAudio release build, so look through the list for newer
master builds. `NOTICE.md` in each release records the commits and toolchain.

`Pa_GetVersionText()` says `V19.7.0-devel` for both kinds of build, as that's what the
PortAudio sources contain. The revision after it identifies the commit.

## Verifying a download

Each file has a signed
[attestation](https://docs.github.com/en/actions/concepts/security/artifact-attestations)
that links it to the workflow run and commit that produced it. To check it with the
[GitHub CLI](https://cli.github.com/):

```
gh attestation verify <file> --repo zEdS15B3GCwq/portaudio-windows-builds
```

Alternatively, compare `Get-FileHash <file>` with `SHA256SUMS` from the release. Either
way, this shows where a file came from, and isn't an audit of the code in it.

## How it's built

[`build.yml`](.github/workflows/build.yml) fetches
[PortAudio](https://github.com/PortAudio/portaudio) and a pinned commit of the ASIO SDK
([fork](https://github.com/zEdS15B3GCwq/asio) of
[audiosdk/asio](https://github.com/audiosdk/asio)), builds with CMake and MSVC in Release
mode with a static runtime, then checks and test-loads each DLL. The tests don't need
audio hardware.

- **Testing a change**: push to a branch other than `main`. The would-be release is
  uploaded as the run's `release` artifact, and nothing is published.
- **Releasing now**: run the workflow manually on `main`. `force` rebuilds and releases
  both sources even if they were released before.
- **Updating the SDK**: change `ASIO_REF` in the workflow and run it with `force`.
- **If releases stop**: GitHub disables schedules after 60 days without repository
  activity. Re-enable the workflow on the Actions tab.
