# static-ffmpeg-binaries

Static binaries of FFmpeg, for multiple OS &amp; CPU combinations, built from
source in a GitHub Actions workflow.

To download binaries, visit the [releases page][releases].


# License

The GitHub Actions workflows and other scripts in this repo are covered by the
Apache license.
Please see the [workflow source][workflow], [version script source][version-script],
and [the Apache license][apache]
for license details.

The resulting FFmpeg binaries are built using GPL libraries, and are therefore
published under the GPL license.
Please see the [releases page][releases] for binaries, and see [FFmpeg's GPL
license][gpl] for license details.


# How are they built?

FFmpeg and its key dependencies are all built from source and linked statically.
Candidate builds record SHA256, source identity, configuration and platform
linkage in per-platform provenance files. Versioned releases include SHA256SUMS
and retain MD5 for compatibility. Checksums identify the downloaded bytes; they
are not signatures or a promise of bit-identical rebuilds on moving runner images.
You can read the details in the [workflow source][workflow].

Minimal third-party GitHub Actions have been used in this workflow, to protect
against supply-chain attacks.  The following actions are used:

 - mxschmitt/action-tmate: Used only on failure to debug failed builds, and
   only if debug is configured at the repo level.


# Seek-stream candidates

The current branch pins an exact tested upstream FFmpeg revision and carries a
small proposed `-seek_stream` patch. `versions.txt` records the patch digest,
reviewed source tree, and upstream issue/PR links. It is under upstream review.
See [BUILD-NOTES.md](BUILD-NOTES.md) for qualification, limitations and rollback.

Tags such as `git-2026-10-27-86444dd-seek-stream-rc1` build both supported native
platforms and publish a prerelease with `--latest=false`. Never reuse a candidate
tag. Qualification builds include separately named `control-unpatched-*`
binaries from the same upstream pin, toolchain, dependencies and configure path.
The candidate adds only an identifying `--extra-version` configure argument.

Do not merge this branch to main or replace the moving `latest` release before
application qualification. When enabled, the monthly scheduled workflow rebuilds main into
`latest`; this candidate does not modify that schedule or installed binaries.

# Triggering a build

Update the version numbers as needed in the [version file][version-file], then
create a tag on the new commit.  Full builds will be triggered, and binaries
will be attached to a release on the new tag.


# Tag names

Tag names should follow the form of `$FFMPEG_VERSION-$WORKFLOW_RELEASE_NUMBER`.
For example, the first time we release a build based on FFmpeg n4.4, the tag
should be "n4.4-1".  If we need to update the dependencies, or change the
configuration, or make any other changes to the workflow that don't change the
FFmpeg version, the next release would be "n4.4-2".  When FFmpeg n4.5 is
released upstream, we could update to that and then tag "n4.5-1".


# Local builds

You can do these steps on your actual device, or on a virtual device or
container to avoid polluting your system.

1. Set up a build environment (packages, tools, etc) similar to what is done in
   the [workflow source][workflow] for your OS.
2. If you are using Linux or macOS, run `export SUDO=sudo`.
3. If you are using Linux, run `export RUNNER_OS=Linux`.
4. If you are using macOS, run `export RUNNER_OS=macOS`.
5. If you are using Windows, run `export RUNNER_OS=Windows`.
6. Set a temp path for `GITHUB_ENV`, for example `export GITHUB_ENV=/tmp/github.env`.
7. Create a build folder.  For example, `mkdir -p build.noindex`.  It does not need to
   be in the git working directory.
8. Change into that build directory.
9. Create a symlink to the repo root called `repo-src` to emulate the structure
   used by the workflow.  For example, if `build.noindex` is inside the repo, use
   `ln -s ../ repo-src`.
10. Run the build scripts in [`build-scripts`][] in numerical order.


# Docker builds

You can run the above steps automatically in an Ubuntu Docker container with:

```sh
docker build -t static-ffmpeg-binaries /path/to/static-ffmpeg-binaries
docker run -v /path/to/static-ffmpeg-binaries:/src static-ffmpeg-binaries /src/build.sh
```


[releases]: https://github.com/EthanSK/static-ffmpeg-binaries/releases
[workflow]: .github/workflows/release.yaml
[version-script]: get-version.sh
[version-file]: versions.txt
[apache]: LICENSE
[gpl]: https://github.com/FFmpeg/FFmpeg/blob/master/COPYING.GPLv3
