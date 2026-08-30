# 参与开发（Contributing Guide）

本文面向第一次接触 `compass-metrics-model` 的开发者，覆盖环境搭建、测试、核心概念，以及"新增一个指标 / 新增一个模型"的完整流程。部署与使用方法的更多背景参见 [README](README.md) 与 issue #117。

## 1. 开发环境搭建

```bash
git clone https://github.com/<your-fork>/compass-metrics-model.git
cd compass-metrics-model

python -m venv .venv && source .venv/bin/activate    # 建议 Python 3.8+
pip install -r requirements.txt                       # 运行依赖

# 测试所需（不在 requirements.txt 中的部分）
pip install pytest
```

说明：

- `requirements.txt` 中的 pin 较旧（pandas 1.1.5 / numpy 1.18.3），在 Python 3.10+ 上无法构建；本仓库的单元测试不依赖这些旧版本，直接 `pip install pandas pendulum python-dateutil PyYAML "elasticsearch==6.3.1" opensearch-py "setuptools<81" pytest` 即可在 3.12 上运行全部测试。
- 旧版入口 `run.py`（`compass_metrics_model/`）额外依赖 grimoirelab 组件（`grimoirelab-toolkit`、`grimoire-elk`、`perceval`），未声明在 requirements.txt 中；现行入口 `run_test.py`（v1 模型）与 v2 模型不需要它们。
- 所有需要 Elasticsearch/OpenSearch 的操作都通过 `compass_common/opensearch_utils.get_client(url)` 拿客户端，单元测试中一律以 mock 替代，**本地跑测试不需要任何数据库**。

## 2. 运行测试

```bash
python -m pytest tests/ -v
```

测试文件按主题组织，例如：

| 文件 | 覆盖内容 |
| --- | --- |
| `test_scoring_pipeline.py` | decay 公式、criticality_score 加权平均语义、NEGATICE_METRICS 符号翻转 |
| `test_metrics_config_validation.py` | 模型构造时的 metric 配置快速失败校验 |
| `test_metrics_model_dispatch.py` | year / version / period 三条 enrich 管线的互斥分发 |
| `test_packaging.py` | wheel 打包必须覆盖全部源码包 |
| `test_developer_metrics_v2_tiers.py` | 开发者 core/regular/visitor 分层 |

写新的测试时：metric 函数的第一个参数是 ES client，用 `unittest.mock.MagicMock()` 构造一个带 `search()` 返回固定聚合结果的 stub 即可，参考 `test_pr_comment_count_period.py` 中的 `RecordingClient`。

## 3. 项目结构导览

| 目录 | 内容 |
| --- | --- |
| `compass_common/` | 基础工具：ES 客户端、日期处理、评分算法（`algorithm_utils.py`）、uuid |
| `compass_metrics/` | v1 指标实现（git/issue/pr/contributor/repo/opencheck/license/security 等，均为 `(client, index, date, repo_list)` 签名的函数）+ `resources/thresholds.yaml` |
| `compass_metrics_v2/` | 按周期（月/季/年）计算的 v2 指标（`*_by_period`） |
| `compass_model/` | v1 模型层：`base_metrics_model.py`（指标分发、评分、ES 写出）+ 各模型类 |
| `compass_model_v2/` | v2 模型层：`base_metrics_model_v2.py` + community_health / developer_journey / supply_chain_security 下的模型类 |
| `compass_metrics_model/` | 旧版实现（仅 `run.py` 使用，维护中的历史代码） |
| `compass_contributor/` | 贡献者/组织/机器人信息入库 |
| `run_test.py` | v1 模型的现行入口；`run_scheduler_task.py` | 月度 gitdm 组织映射刷新 |

数据流：预先富集好的 ES 索引（git / issue / pr / contributors_enriched / repo / release）→ `BaseMetricsModel.metrics_model_metrics()` 按**首个 metric 名**选择富集管线 → 周期内逐日期调用各指标函数 → `get_metrics_score()` 打分（criticality_score / aggregate_score，含 decay）→ 批量写 `out_index`。

三条富集管线按首个 metric 名互斥分发（详见 `metrics_model_metrics`）：

- 名称含 `_year` → 按年（`metrics_model_enrich_year`）
- 名称含 `license` / `security` / `activity_quarterly_` → 按版本一次性（`metrics_model_enrich_version`）
- 名称含 `doc_` / `vul_`，或等于 `org_contribution` → 按版本一次性
- 其余 → 按周期循环（`metrics_model_enrich`）

评分语义由 `tests/test_scoring_pipeline.py` 钉住：分数是各指标 log-ratio 的加权平均，负向指标（`NEGATICE_METRICS`）权重取负，`-1` 约定为"数据未知拿一半分"，decay 按 0.0027/天向阈值/0 收敛。

## 4. 新增一个指标

以新增 `my_new_metric`（周期型）为例：

1. **实现指标函数**：在 `compass_metrics/`（静态）或 `compass_metrics_v2/`（周期型，签名多一个 `period` 参数）中添加函数，入参 `(client, index, date, repo_list[, period])`，返回 `{"my_new_metric": value}`（复杂指标可附带 `*_detail` / `*_avg` / `*_mid` 键）；
2. **注册到 switch**：在 `compass_model/base_metrics_model.py` 与/或 `compass_model/base_metrics_model_v2.py` 的 `_metrics_switch()` 中登记 `lambda`；
3. **补充默认阈值**：在 `compass_metrics/resources/thresholds.yaml` 对应分组下添加 `metric / repo_threshold / multiple_threshold` 三项——否则 `threshold: None` 的配置会在构造模型时报错提醒；
4. **接入模型**：在目标模型的 `metrics_weights_thresholds` 中加入 `{"my_new_metric": {"weight": W, "threshold": None}}`；v2 模型还需确认权重常量定义；
5. **加测试**：用 stub client 固定查询结果，断言指标输出；未知指标名现在会在构造模型时快速失败（`test_metrics_config_validation.py`）。

## 5. 新增一个模型

继承 `BaseMetricsModel`（v1）或 `compass_model_v2` 对应基类，只需提供：

```python
class MyMetricsModel(BaseMetricsModel):
    def __init__(self, ...):
        model_name = 'My Model'
        metrics_weights_thresholds = {
            "contributor_count": {"weight": W1, "threshold": None},
            "commit_frequency": {"weight": W2, "threshold": None},
        }
        super().__init__(..., model_name, metrics_weights_thresholds, ...)
```

- `threshold: None` 表示使用 thresholds.yaml 的默认值；显式给出则覆盖；
- 名字在 `NEGATICE_METRICS` 中的指标权重自动取负（越小越好）；
- 注意首个 metric 名决定走哪条富集管线（见第 3 节），并相应传入 `custom_fields`（period 型模型传 `{"period": "month"}`，version 型模型的调用方需提供 `version_number`）。

## 6. 本地打包验证

```bash
python -m build --wheel --outdir dist/
python -m zipfile -l dist/*.whl | head
```

仓库内大量目录是 PEP 420 命名空间包（无 `__init__.py`），`tests/test_packaging.py` 会断言打包发现结果覆盖全部源码包——改动 `setup.py` 或新增顶层目录后请跑一遍。

## 7. 提交规范

- 本仓库启用了 **DCO** 检查：提交必须带签名 `git commit -s`（Signed-off-by 的邮箱需与提交者一致）；
- PR 请说明：缺陷/特性的稳定复现或使用方式、根因、修复方案、测试。
