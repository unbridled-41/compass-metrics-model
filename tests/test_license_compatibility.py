import itertools
import unittest
from unittest.mock import patch

from compass_metrics.license import (
    check_license_compatibility,
    license_commercial_allowed,
    license_is_weak,
)
from compass_metrics.constants.license_constants import LICENSE_COMPATIBILITY


class CheckLicenseCompatibilityTest(unittest.TestCase):
    """许可证兼容性判定不应依赖许可证列表的顺序。

    get_license_msg 返回的 license_list 来自 set（list(all_licenses)），
    其顺序受字符串哈希随机化影响，同一仓库在不同进程中的判定结果可能翻转。"""

    def test_one_way_compatible_pair_is_compatible_in_both_orders(self):
        # mit 兼容矩阵声明 mit -> gpl-2.0 单向兼容
        self.assertEqual(check_license_compatibility(["mit", "gpl-2.0"])["status"],
                         check_license_compatibility(["gpl-2.0", "mit"])["status"])

    def test_incompatible_pair_is_incompatible_in_both_orders(self):
        self.assertEqual(check_license_compatibility(["gpl-2.0", "apache-2.0"])["status"], "incompatible")
        self.assertEqual(check_license_compatibility(["apache-2.0", "gpl-2.0"])["status"], "incompatible")

    def test_unknown_license_reported(self):
        self.assertEqual(check_license_compatibility(["not-a-real-license"])["status"], "unknown")

    def test_empty_license_list_is_compatible(self):
        self.assertEqual(check_license_compatibility([])["status"], "compatible")


class EmptyLicenseListSemanticsTest(unittest.TestCase):
    """仓库没有许可证数据时，不应因 all() 的空真值而被判为
    全部是弱许可证 / 允许商业化。"""

    EMPTY_MSG = {"license_list": [], "osi_license_list": [], "non_osi_licenses": []}

    def test_no_license_data_is_not_reported_as_weak(self):
        with patch("compass_metrics.license.get_license_msg", return_value=dict(self.EMPTY_MSG)):
            self.assertEqual(license_is_weak(None, None, None, None)["license_is_weak"], 0)

    def test_no_license_data_is_not_reported_as_commercial_allowed(self):
        with patch("compass_metrics.license.get_license_msg", return_value=dict(self.EMPTY_MSG)):
            self.assertEqual(license_commercial_allowed(None, None, None, None)["license_commercial_allowed"], 0)

    def test_weak_license_still_detected(self):
        msg = {"license_list": ["MIT"], "osi_license_list": ["MIT"], "non_osi_licenses": []}
        with patch("compass_metrics.license.get_license_msg", return_value=msg):
            self.assertEqual(license_is_weak(None, None, None, None)["license_is_weak"], 1)


if __name__ == "__main__":
    unittest.main()


class ExhaustiveOrderIndependenceTest(unittest.TestCase):
    """穷举兼容矩阵中全部许可证对：判定必须与输入顺序无关。
    这是对本修复所针对缺陷（顺序依赖导致跨进程结果翻转）的直接性质约束。"""

    def test_every_matrix_pair_is_order_independent(self):
        licenses = sorted(LICENSE_COMPATIBILITY.keys())
        checked = 0
        for a, b in itertools.combinations(licenses, 2):
            with self.subTest(pair=(a, b)):
                self.assertEqual(
                    check_license_compatibility([a, b])["status"],
                    check_license_compatibility([b, a])["status"])
                checked += 1
        self.assertEqual(checked, len(licenses) * (len(licenses) - 1) // 2)
