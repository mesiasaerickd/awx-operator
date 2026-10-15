#!/usr/bin/env python3
"""Fail-closed Trivy security qualifier for a vendor-supported PostgreSQL image."""
import argparse
import json
from pathlib import Path

def assess(report, required_os_type="redhat"):
    blockers=[]
    counts={"CRITICAL":0,"HIGH":0}
    targets=report.get("Results")
    if not isinstance(report.get("SchemaVersion"),int) or not isinstance(targets,list):
        return {"status":"BLOCKED","counts":counts,"blockers":["Missing or malformed Trivy results"]}
    os_found=False
    ids=[]
    for target in targets:
        if target.get("Class") == "os-pkgs" and target.get("Type") == required_os_type:
            os_found=True
        for item in target.get("Vulnerabilities") or []:
            sev=item.get("Severity")
            if sev in counts:
                counts[sev]+=1
                ids.append({"severity":sev,"id":item.get("VulnerabilityID"),"package":item.get("PkgName"),
                            "installed":item.get("InstalledVersion"),"fixed":item.get("FixedVersion")})
    if not os_found:
        blockers.append("OS vulnerability coverage missing: expected "+required_os_type)
    if counts["CRITICAL"]:
        blockers.append(str(counts["CRITICAL"])+" CRITICAL vulnerability detections")
    if counts["HIGH"]:
        blockers.append(str(counts["HIGH"])+" HIGH vulnerability detections")
    return {"status":"PASS" if not blockers else "BLOCKED","counts":counts,
            "os_advisory_coverage":os_found,"findings":ids,"blockers":blockers}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--report",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--os-type",default="redhat")
    a=ap.parse_args()
    try:
        data=json.loads(Path(a.report).read_text())
        result=assess(data,a.os_type)
    except (OSError,ValueError,TypeError) as error:
        result={"status":"BLOCKED","counts":{"CRITICAL":0,"HIGH":0},
                "blockers":["Invalid or inaccessible Trivy JSON: "+str(error)]}
    Path(a.output).parent.mkdir(parents=True,exist_ok=True)
    Path(a.output).write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"counts":result["counts"],"blockers":result["blockers"]},indent=2))
    return 0 if result["status"]=="PASS" else 2

if __name__=="__main__":
    raise SystemExit(main())
