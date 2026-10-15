import unittest
from security_gate import assess

class SecurityGateTest(unittest.TestCase):
    def test_reject_no_os_coverage_even_when_zero_findings(self):
        self.assertEqual("BLOCKED",assess({"SchemaVersion":2,"Results":[]})["status"])
    def test_reject_critical_and_high(self):
        report={"SchemaVersion":2,"Results":[{"Class":"os-pkgs","Type":"redhat",
            "Vulnerabilities":[{"Severity":"HIGH","VulnerabilityID":"TEST-1","PkgName":"libc"}]}]}
        self.assertEqual(1,assess(report)["counts"]["HIGH"])
        self.assertEqual("BLOCKED",assess(report)["status"])
    def test_reject_wrong_distro(self):
        self.assertEqual("BLOCKED",assess({"SchemaVersion":2,"Results":[{"Class":"os-pkgs","Type":"rocky","Vulnerabilities":[]}]})["status"])
    def test_pass_supported_scan_with_no_findings(self):
        report={"SchemaVersion":2,"Results":[{"Class":"os-pkgs","Type":"redhat","Vulnerabilities":[]}]}
        self.assertEqual("PASS",assess(report)["status"])
    def test_reject_invalid_json_shape(self):
        self.assertEqual("BLOCKED",assess({"SchemaVersion":2,"Results":None})["status"])

if __name__=="__main__":
    unittest.main()
