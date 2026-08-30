import unittest

from compass_metrics_v2.supply_chain_security_metrics_v2 import _calc_ecology_test_coverage


class EcologyTestCoverageTest(unittest.TestCase):
    """SonarQube 组件测量接口返回的 value 是字符串（如 "65.0"），
    解析不应因小数字符串而静默失败。"""

    def test_sonar_string_values_are_parsed(self):
        result = _calc_ecology_test_coverage({
            "component": {
                "measures": [
                    {"metric": "duplicated_lines_density", "value": "3.4"},
                    {"metric": "coverage", "value": "65.0"},
                ]
            }
        })
        # 重复率 3% -> 8 分；覆盖率 65% -> 6 分；总分 (8+6)/2 = 7
        self.assertEqual(result["ecology_test_coverage"], 7.0)
        detail = __import__("json").loads(result["ecology_test_coverage_detail"])
        self.assertEqual(detail["duplication_ratio"], 3)
        self.assertEqual(detail["coverage_ratio"], 65)

    def test_integer_string_values_are_parsed(self):
        result = _calc_ecology_test_coverage({
            "component": {
                "measures": [
                    {"metric": "duplicated_lines_density", "value": "0"},
                    {"metric": "coverage", "value": "80"},
                ]
            }
        })
        # 重复率 0% -> 10 分；覆盖率 80% -> 10 分
        self.assertEqual(result["ecology_test_coverage"], 10.0)

    def test_numeric_values_still_work(self):
        result = _calc_ecology_test_coverage({
            "component": {
                "measures": [
                    {"metric": "duplicated_lines_density", "value": 10},
                    {"metric": "coverage", "value": 50},
                ]
            }
        })
        # 重复率 10% -> 4 分；覆盖率 50% -> 6 分
        self.assertEqual(result["ecology_test_coverage"], 5.0)

    def test_missing_measures_fall_back_to_zero(self):
        result = _calc_ecology_test_coverage({"component": {"measures": []}})
        self.assertEqual(result["ecology_test_coverage"], 0.0)


if __name__ == "__main__":
    unittest.main()
