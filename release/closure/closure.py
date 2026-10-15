#!/usr/bin/env python3
"""Four-stage AWX release closure: no automatic production actions."""
import argparse
import datetime
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

PARTS = ("awx", "operator", "ee")
# All images required for Kubernetes release and runtime digest verification.
IMAGE_PARTS = PARTS + ("postgres",)

def load(path):
    return json.loads(pathlib.Path(path).read_text())

def write(path, obj):
    pathlib.Path(path).write_text(json.dumps(obj, indent=2) + "\n")

def audit(paths, review=None):
    found = []
    for name in PARTS:
        data = load(paths[name])
        if not isinstance(data.get("Results"), list) or "SchemaVersion" not in data:
            raise ValueError("Invalid Trivy report: " + name)
        for result in data["Results"]:
            for vuln in result.get("Vulnerabilities") or []:
                if vuln.get("Severity") in ("CRITICAL", "HIGH"):
                    found.append({"component": name, "severity": vuln["Severity"],
                                  "id": vuln.get("VulnerabilityID"), "package": vuln.get("PkgName"),
                                  "version": vuln.get("InstalledVersion")})
    risk = load(review) if review else {}
    allowed = {(x.get("component"), x.get("id"), x.get("package"))
               for x in risk.get("accepted_findings", [])}
    blockers = []
    if any(x["severity"] == "CRITICAL" for x in found):
        blockers.append("CRITICAL findings cannot be waived")
    missing = [x for x in found if x["severity"] == "HIGH" and
               (x["component"], x["id"], x["package"]) not in allowed]
    if missing:
        blockers.append(str(len(missing)) + " HIGH findings require individual acceptance")
    if any(risk.get("os_coverage_review", {}).get(x) != "approved" for x in PARTS):
        blockers.append("OS vulnerability scan coverage not approved for all images")
    if not risk.get("approver") or not risk.get("ticket"):
        blockers.append("Named security approver and change ticket required")
    try:
        if datetime.date.fromisoformat(risk.get("expires", "")) < datetime.date.today():
            blockers.append("Security approval expired")
    except ValueError:
        blockers.append("Security approval expiry missing")
    counts = {c: {s: sum(v["component"] == c and v["severity"] == s for v in found)
                  for s in ("CRITICAL", "HIGH")} for c in PARTS}
    return {"status": "BLOCKED" if blockers else ("RISK_ACCEPTED" if found else "CLEAR"),
            "counts": counts, "findings": found, "blockers": blockers}

def check_lock(lock):
    if lock.get("namespace") != "awx-staging":
        raise ValueError("Only awx-staging is supported")
    if not re.fullmatch("[a-z][a-z0-9-]{0,35}", lock.get("awx_name", "")):
        raise ValueError("Invalid AWX name")
    for part in IMAGE_PARTS:
        item = lock.get(part, {})
        if not item.get("repository") or item.get("tag") in ("", "latest", "dev", "devel", None):
            raise ValueError(part + ": immutable image tag required")
        if not re.fullmatch("sha256:[a-f0-9]{64}", item.get("digest", "")):
            raise ValueError(part + ": verified digest required")
        if any(c in item["repository"] + item["tag"] for c in (" ", "\n", "@")):
            raise ValueError("Invalid image reference")

def render(lock_path, output):
    lock = load(lock_path)
    check_lock(lock)
    out = pathlib.Path(output)
    out.mkdir(parents=True, exist_ok=True)
    def image(part):
        x = lock[part]
        return x["repository"] + ":" + x["tag"]
    resource = {"apiVersion": "awx.ansible.com/v1beta1", "kind": "AWX",
                "metadata": {"name": lock["awx_name"], "namespace": "awx-staging"},
                "spec": {"service_type": "ClusterIP", "image": lock["awx"]["repository"],
                         "image_version": lock["awx"]["tag"],
                         "control_plane_ee_image": image("ee"),
                         "ee_images": [{"name": "Closure EE", "image": image("ee")}],
                         "postgres_image": lock["postgres"]["repository"],
                         "postgres_image_version": lock["postgres"]["tag"]}}
    write(out / "awx-cr.json", resource)
    (out / "kustomization.yaml").write_text(
        "apiVersion: kustomize.config.k8s.io/v1beta1\nkind: Kustomization\n"
        "namespace: awx-staging\nresources:\n  - ../../../config/default\n"
        "images:\n  - name: quay.io/ansible/awx-operator\n"
        "    newName: " + lock["operator"]["repository"] + "\n"
        "    newTag: " + lock["operator"]["tag"] + "\n")
    write(out / "images.lock.json", lock)
    (out / "ROLLBACK.md").write_text(
        "# Manual rollback and database recovery\n\n"
        "Record the original operator overlay, AWX CR, PostgreSQL backup and image digests.\n"
        "Pause job launches. Restore the previous operator image/overlay and AWX CR "
        "under explicit change approval. Verify API, jobs, permissions and data.\n"
        "If database schema/data changed, Kubernetes rollout undo is insufficient: "
        "follow the previously tested AWXBackup/AWXRestore recovery procedure.\n"
        "No production automation is included.\n")

def cmd(args):
    result = subprocess.run(args, text=True, capture_output=True, check=True)
    return result.stdout.strip()

def staging(lock_path):
    lock = load(lock_path)
    check_lock(lock)
    context = os.environ.get("KUBE_CONTEXT", "")
    if not context or not ("staging" in context or "test" in context) or any(
            x in context for x in ("prod", "prd", "production")):
        raise ValueError("Explicit non-production Kubernetes context required")
    required = ("AWX_URL", "AWX_TOKEN", "AWX_TEST_TEMPLATE_ID", "AWX_DENIED_TOKEN",
                "AWX_DENIED_TEMPLATE_ID", "AWX_BACKUP_NAME", "AWX_RESTORE_NAME")
    for key in required:
        if not os.environ.get(key):
            raise ValueError("Missing staging-only credential or proof: " + key)
    ns = "awx-staging"
    base = ["kubectl", "--context", context, "-n", ns]
    cmd(base + ["get", "awx", lock["awx_name"]])
    for deploy in ("awx-operator-controller-manager",
                   lock["awx_name"] + "-web", lock["awx_name"] + "-task"):
        cmd(base + ["rollout", "status", "deployment/" + deploy, "--timeout=600s"])
    # Verify image identifiers in live runtime, not only intended manifest tags.
    pod_data = json.loads(cmd(base + ["get", "pods", "-o", "json"]))
    expected = {k: lock[k]["digest"] for k in IMAGE_PARTS}
    observed = set()
    for pod in pod_data.get("items", []):
        for item in pod.get("status", {}).get("containerStatuses", []):
            imgid = item.get("imageID", "")
            for part, digest in expected.items():
                if digest in imgid:
                    observed.add(part)
    if observed != set(IMAGE_PARTS):
        raise ValueError("Kubernetes has not verified all four locked image digests: " +
                         str(sorted(observed)))
    deny = cmd(base + ["auth", "can-i", "create", "secrets", "--as",
                       "system:serviceaccount:awx-staging:default"])
    if deny.strip() != "no":
        raise ValueError("Default service account has excessive RBAC")
    for kind, env in (("awxbackup", "AWX_BACKUP_NAME"), ("awxrestore", "AWX_RESTORE_NAME")):
        item = json.loads(cmd(base + ["get", kind, os.environ[env], "-o", "json"]))
        status = item.get("status", {})
        passed = str(status.get("status", "")).lower() in ("successful", "completed", "complete")
        passed |= any(c.get("status") == "True" and c.get("type", "").lower()
                      in ("successful", "ready", "complete") for c in status.get("conditions", []))
        if not passed:
            raise ValueError("Missing proven staging " + kind + " successful completion")
    url = os.environ["AWX_URL"].rstrip("/")
    def api(path, token, body=None):
        headers = {"Authorization": "Bearer " + token, "Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url + path, data=body, headers=headers,
                                         method="POST" if body is not None else "GET")
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    token = os.environ["AWX_TOKEN"]
    api("/api/v2/ping/", token)
    try:
        api("/api/v2/job_templates/" + os.environ["AWX_DENIED_TEMPLATE_ID"] + "/",
            os.environ["AWX_DENIED_TOKEN"])
    except urllib.error.HTTPError as error:
        if error.code not in (403, 404):
            raise
    else:
        raise ValueError("AWX RBAC failure: restricted user could access denied template")
    launched = api("/api/v2/job_templates/" + os.environ["AWX_TEST_TEMPLATE_ID"] +
                   "/launch/", token, b"{}")
    job = launched.get("id")
    if not isinstance(job, int):
        raise ValueError("AWX job launch did not return ID")
    for _ in range(60):
        state = api("/api/v2/jobs/" + str(job) + "/", token).get("status")
        if state == "successful":
            print("Staging accepted, AWX job", job)
            return
        if state in ("failed", "error", "canceled"):
            raise ValueError("Staging AWX job failed: " + state)
        time.sleep(5)
    raise ValueError("Staging AWX job exceeded 300 seconds")

def provenance(file):
    base = load(file)
    results = []
    for name in PARTS:
        item = base[name]
        url = ("https://api.github.com/repos/" + item["repository"] +
               "/actions/runs/" + str(item["run_id"]))
        req = urllib.request.Request(url, headers={"User-Agent": "awx-release-closure",
                                                  "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=20) as response:
            data = json.load(response)
        results.append({"component": name, "run": item["run_id"], "success":
                        data.get("conclusion") == "success" and
                        data.get("head_sha") == item["sha"]})
    return results

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="action", required=True)
    a = sub.add_parser("audit")
    for part in PARTS:
        a.add_argument("--" + part, required=True)
    a.add_argument("--review")
    a.add_argument("--output", default="closure-audit.json")
    r = sub.add_parser("render")
    r.add_argument("--lock", required=True)
    r.add_argument("--output", default="release/closure/generated")
    s = sub.add_parser("staging")
    s.add_argument("--lock", required=True)
    e = sub.add_parser("evidence")
    e.add_argument("--baseline", required=True)
    e.add_argument("--output", default="closure-ci-evidence.json")
    b = sub.add_parser("baseline")
    b.add_argument("--baseline", required=True)
    args = p.parse_args()
    try:
        if args.action == "audit":
            result = audit({name: getattr(args, name) for name in PARTS}, args.review)
            write(args.output, result)
            print(json.dumps({"status": result["status"], "counts": result["counts"],
                              "blockers": result["blockers"]}, indent=2))
            return 2 if result["status"] == "BLOCKED" else 0
        if args.action == "render":
            render(args.lock, args.output)
            print("Manifest and rollback preparation rendered")
        if args.action == "staging":
            staging(args.lock)
        if args.action == "evidence":
            result = provenance(args.baseline)
            write(args.output, result)
            print(json.dumps(result, indent=2))
            return 0 if all(x["success"] for x in result) else 2
        if args.action == "baseline":
            base = load(args.baseline)
            print(json.dumps({"status": "PRODUCTION_BLOCKED",
                              "trivy": {c: base[c]["last_trivy"] for c in PARTS},
                              "reason": "Open HIGH, PostgreSQL qualification, OS coverage and Kubernetes acceptance"},
                             indent=2))
        return 0
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError,
            urllib.error.URLError) as exc:
        print("Closure blocked:", str(exc), file=sys.stderr)
        return 2

if __name__ == "__main__":
    sys.exit(main())
