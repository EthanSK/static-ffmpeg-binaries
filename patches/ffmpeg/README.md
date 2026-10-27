# Carried FFmpeg patch

`seek-stream.patch` is the complete proposed upstream change, including its
documentation and nine FATE regressions. It is under upstream review and is
not endorsed or merged by FFmpeg. The modified FFmpeg sources retain FFmpeg's
licenses.

`versions.txt` is the canonical record of the exact upstream revision, patch
SHA256, reviewed resulting source tree, public review commit, issue and PR.
The build verifies all three identities before configuring FFmpeg. It fails
on dirty, incompatible, already integrated or unexpectedly modified sources;
there is no fuzzy application or automatic reconciliation.

When upstream merges an equivalent change, remove or reconcile this carried
patch explicitly, update its identity and version suffix, and repeat the
control/candidate qualification. Do not silently skip a patch that stops
applying. A source update is a new candidate, not a reason to overwrite a
previous candidate tag.
