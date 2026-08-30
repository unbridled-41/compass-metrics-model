import unittest

from compass_metrics_v2.developer_metrics_v2 import (
    _get_core_contributor_set_from_maps,
    _tier_counts_from_contribution_map,
)


class TierCountsFromContributionMapTest(unittest.TestCase):
    """core/regular/visitor 分层应基于"累计贡献占比前 50%/80%"划分，
    且与晋升/留存使用的 _get_core_contributor_set_from_maps 口径一致。"""

    def test_single_contributor_is_core(self):
        # 仓库唯一的贡献者就是核心贡献者，不应被划分为 visitor
        self.assertEqual(_tier_counts_from_contribution_map({"alice": 100}), (1, 0, 0))

    def test_dominant_contributor_is_core(self):
        # 头部贡献者覆盖 60% 贡献量，属于 core；第二位处于 50%-80% 区间，属于 regular
        self.assertEqual(_tier_counts_from_contribution_map({"a": 60, "b": 40}), (1, 1, 0))

    def test_majority_contributor_is_core(self):
        # 覆盖 51% 贡献量的贡献者是 core，而不是 regular
        self.assertEqual(_tier_counts_from_contribution_map({"a": 51, "b": 49}), (1, 1, 0))

    def test_uniform_contributors(self):
        # 10 个均等贡献者：前 5 位覆盖 50% 为 core，接下来 3 位覆盖到 80% 为 regular
        contributions = {f"c{i}": 10 for i in range(10)}
        self.assertEqual(_tier_counts_from_contribution_map(contributions), (5, 3, 2))

    def test_empty_map(self):
        self.assertEqual(_tier_counts_from_contribution_map({}), (0, 0, 0))

    def test_zero_total_contributions(self):
        # 全部贡献量为 0 时无法划分层级，全部算作 visitor
        self.assertEqual(_tier_counts_from_contribution_map({"a": 0, "b": 0}), (0, 0, 2))

    def test_core_set_consistency_with_tier_counts(self):
        # 分层函数与核心集合函数对 core 的界定必须一致
        for contributions in ({"a": 100}, {"a": 60, "b": 40}, {"a": 51, "b": 49}, {"a": 30, "b": 30, "c": 40}):
            core_count, _, _ = _tier_counts_from_contribution_map(contributions)
            core_set = _get_core_contributor_set_from_maps(contributions, {}, dimension="code", core_ratio=0.5)
            self.assertEqual(
                core_count,
                len(core_set),
                f"core count mismatch for {contributions}: tier={core_count}, set={sorted(core_set)}",
            )


if __name__ == "__main__":
    unittest.main()
