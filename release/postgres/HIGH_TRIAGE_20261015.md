# PostgreSQL 15.19 RHEL9 image: HIGH vulnerability triage (2026-10-15)

**Source of truth:** GitHub Actions run [38772878654, attempt 4](https://github.com/mesiasaerickd/awx-operator/actions/runs/38772878654), evidence artifact `postgres-rhel9-vendor-qualification`: `trivy.json`, `qualification.json`, `image-pinned-digest.txt`.

Image: `registry.redhat.io/rhel9/postgresql-15@sha256:04dc558560697443edac184d16684147eba4d6bb7a6dd646928ad433def33c95`. **Actual PostgreSQL server version: 15.19**, startup/UID26/SQL/volume-restart PASS. **Vulnerability scan: 0 CRITICAL, 26 HIGH, native `redhat 9.8` OS package coverage present.** Production status: **BLOCKED**.

## Findings by RPM family

| Family | HIGH detections | CVEs | RPM versions observed | Trivy fixed version |
|---|---:|---|---|---|
| util-linux (libblkid, libfdisk, libmount, libsmartcols, libuuid, util-linux, util-linux-core) | 14 | CVE-2026-53613, CVE-2026-53615 | 2.37.4-25.el9 | Not supplied |
| python3 + python3-libs | 4 | CVE-2026-19445, CVE-2026-19553 | 3.9.25-7.el9_8.3 | Not supplied; Trivy marks `end_of_life` |
| expat | 2 | CVE-2026-76641, CVE-2026-77214 | 2.5.0-6.el9_8.5 | Not supplied |
| gnutls | 1 | CVE-2026-88647 | 3.8.10-9.el9_8 | Not supplied |
| python3-pip-wheel | 1 | CVE-2026-57585 | 21.3.1-2.el9_8 | Not supplied |
| python3-urllib3 | 2 | CVE-2026-97687, CVE-2026-97689 | 1.26.5-8.el9_8 | Not supplied |
| vim-filesystem, vim-minimal | 2 | CVE-2026-43961 | 2:8.2.2637-26.el9_8.23 | Not supplied |
| **TOTAL** | **26** | **11 distinct CVE identifiers** | | |

These are **26 RPM/CVE detections**, not 26 unique vulnerabilities: e.g., each util-linux CVE appears on seven related RPMs. Trivy reports `FixedVersion` empty for all 26; this does **not** prove that no fix exists in vendor errata, later image tags or backports. Consult official Red Hat security advisories for each CVE, OS release, and image digest, taking applicability/backported fixes into account.

## Approved next mitigation investigations

1. Confirm the latest supported Red Hat PostgreSQL 15 image digest and its signed provenance, not just the floating `latest` tag.
2. Run `microdnf update` or another vendor-supported package update on a **throwaway** RHEL base image with active entitlement, record updated RPM NEVRAs and re-scan RHEL9 OS coverage. Do not write to the existing AWX K3s PVC.
3. If any finding persists, verify Red Hat CVE applicability, fixed-package NEVRA, support status and vendor-provided workaround; document every finding by CVE, package, fixed version, vendor source and residual severity.
4. For required `vim-minimal`, Python dependencies and other OS packages, only remove packages after a tested proof they are not required by the SCL startup scripts, PostgreSQL init, health check, or AWX restore path; avoid brittle forced rpm removals. No replacement with unsigned or cross-distribution RPMs.
5. Re-run exact server version 15.19, UID 26, clean init, SQL, restart persistence, baseline scan coverage and *full AWX* integrated staging.
6. **No production release or waiver without named SecOps approval, vulnerability-level justification, expiration date, image digests, backup/restore test and protected `dev -> prd` PR.**

## Automated gates
- `.github/workflows/postgres-vendor-qualification.yml` downloads and tests the official image, then runs `release/postgres/security_gate.py`; any HIGH/CRITICAL or absent RHEL9 OS coverage fails.
- The existing CentOS Stream + Rocky RPM experimental image remains **rejected** (70 HIGH comparative findings, unsupported native OS scan).
- `release/closure/closure.py` now requires all FOUR image digests (AWX, Operator, EE, PostgreSQL) for staged release manifests.
