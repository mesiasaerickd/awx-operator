# AWX/Operator/EE downloadable Linux test images

The GitHub Action "AWX offline staging image archives" builds three images in
separate runners. Open the run's Artifacts to download the AWX, Operator and EE
archives. Each GitHub ZIP contains a .tar.zst, .sha256 checksum, Trivy JSON and
manifest.json. These are for NON-PRODUCTION isolated testing only.

Image tags:
- localhost/awx:git-d0f3cd1c7563
- localhost/operator:git-3bb442b02ce9
- localhost/ee:git-b89f11424bf5

Unzip each artifact into a separate folder. On a Linux Docker server, verify
and import each archive (substitute component name awx/operator/ee):

    sha256sum -c awx.sha256
    zstd -dc awx.tar.zst | docker load

For Podman, pipe instead to podman load.

To load images into a disposable Kubernetes Kind cluster:

    kind create cluster --name awx-staging
    kind load docker-image localhost/awx:git-d0f3cd1c7563 --name awx-staging
    kind load docker-image localhost/operator:git-3bb442b02ce9 --name awx-staging
    kind load docker-image localhost/ee:git-b89f11424bf5 --name awx-staging

Use the staging manifests and acceptance requirements in release/closure.
Local Kind image loading is separate from the release image-lock mechanism,
which requires a registry digest. Do not invent a digest or claim that
Molecule alone verifies full AWX+Operator+EE Kubernetes integration.

Security: these images still contain up to 13 open HIGH detections from Trivy
(Operator 9, EE 4). The workflow blocks CVE regressions, not open risks.
No production readiness is claimed. The artifacts expire in 14 days and
large archives might fail due to GitHub Actions storage limits.
