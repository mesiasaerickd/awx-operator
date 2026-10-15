import json
import pathlib
import sys
import tempfile
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import closure

class Gates(unittest.TestCase):
    def report(self, root, part, level=None):
        p=pathlib.Path(root)/(part+".json")
        vulns=[] if level is None else [{
            "VulnerabilityID":"CVE-TEST", "PkgName":"example",
            "Severity":level, "InstalledVersion":"1.0"}]
        p.write_text(json.dumps({"SchemaVersion":2,
                                 "Results":[{"Vulnerabilities":vulns}]}))
        return str(p)
    def test_high_requires_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths={x:self.report(tmp,x,"HIGH" if x=="ee" else None)
                   for x in closure.PARTS}
            self.assertEqual(closure.audit(paths)["status"],"BLOCKED")
    def test_critical_cannot_be_waived(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths={x:self.report(tmp,x,"CRITICAL" if x=="awx" else None)
                   for x in closure.PARTS}
            review=pathlib.Path(tmp)/"review.json"
            review.write_text(json.dumps({"approver":"SecOps","ticket":"SEC-123",
                "expires":"2099-01-01","os_coverage_review":{
                x:"approved" for x in closure.PARTS}}))
            self.assertEqual(closure.audit(paths,review)["status"],"BLOCKED")
    def test_coverage_required_for_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths={x:self.report(tmp,x) for x in closure.PARTS}
            self.assertEqual(closure.audit(paths)["status"],"BLOCKED")
    def test_no_floating_images(self):
        lock={"namespace":"awx-staging","awx_name":"awx-closure"}
        for x in closure.PARTS:
            lock[x]={"repository":"registry.test/"+x,"tag":"latest",
                     "digest":"sha256:"+"a"*64}
        with self.assertRaises(ValueError): closure.check_lock(lock)
    def test_render_valid_lock(self):
        lock={"namespace":"awx-staging","awx_name":"awx-closure"}
        for x in closure.PARTS:
            lock[x]={"repository":"registry.test/"+x,"tag":"git-abcdef",
                     "digest":"sha256:"+"a"*64}
        with tempfile.TemporaryDirectory() as tmp:
            inp=pathlib.Path(tmp)/"lock.json"
            inp.write_text(json.dumps(lock))
            closure.render(inp, pathlib.Path(tmp)/"generated")
            result=json.loads((pathlib.Path(tmp)/"generated"/"awx-cr.json").read_text())
            self.assertEqual(result["spec"]["image_version"],"git-abcdef")
            self.assertTrue((pathlib.Path(tmp)/"generated"/"ROLLBACK.md").exists())

if __name__=="__main__":
    unittest.main()
