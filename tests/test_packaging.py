import os
import unittest

from setuptools import find_namespace_packages

# 与 setup.py 中保持一致的发现范围
INCLUDE = ["compass_common*", "compass_contributor*", "compass_metrics*", "compass_model*", "compass_prediction*"]
SKIP_DIRS = {"__pycache__", "build", ".git", ".venv", "node_modules"}


def source_packages():
    """收集仓库中所有包含 .py 文件的 compass_* 目录（不含数据目录）。"""
    found = set()
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.endswith(".egg-info")]
        rel = os.path.relpath(root, ".")
        if rel == ".":
            continue
        if not rel.split(os.sep)[0].split("-")[0].startswith("compass_"):
            continue
        if any(f.endswith(".py") for f in files):
            found.add(rel.replace(os.sep, "."))
    return found


class PackagingTest(unittest.TestCase):
    """pip install 后的发行包必须包含全部源码包。

    find_packages() 只识别带 __init__.py 的目录，仓库内大量 PEP 420
    命名空间包（compass_metrics_v2、compass_model_v2 的全部子包、
    compass_metrics/constants、compass_model 的子包等）会被整包遗漏，
    导致 pip install 后 import compass_metrics_v2 直接失败。"""

    def test_discovery_covers_every_source_package(self):
        packages = set(find_namespace_packages(include=INCLUDE))
        missing = source_packages() - packages
        self.assertEqual(missing, set(), f"未被打包的源码包: {sorted(missing)}")

    def test_setup_uses_namespace_package_discovery(self):
        with open("setup.py", encoding="utf-8") as f:
            setup_src = f.read()
        self.assertIn("find_namespace_packages", setup_src)
        self.assertNotIn("packages=find_packages()", setup_src)


if __name__ == "__main__":
    unittest.main()
