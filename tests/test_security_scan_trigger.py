import unittest
from unittest.mock import patch

from compass_metrics import security


class TriggerScanForMissingDataTest(unittest.TestCase):
    """仓库缺少安全扫描数据时应触发 opencheck 扫描，且 project_url
    必须是单个仓库地址（f"{repo}.git"），而不是把 repo_list 整个列表
    f-string 成 "['org/a', 'org/b'].git" 这样的非法 URL。"""

    def test_scan_triggered_per_repo_with_valid_project_url(self):
        post_calls = []

        def fake_post(request_path, payload, token=None):
            post_calls.append((request_path, payload))
            if request_path == "auth":
                return {"status": True, "body": {"access_token": "tok"}}
            return {"status": True, "body": {}}

        with patch("compass_metrics.license.get_all_index_data", return_value=[]), \
                patch("compass_metrics.security.get_all_index_data", return_value=[]), \
                patch("compass_metrics.security.base_post_request", side_effect=fake_post):
            result = security.get_security_msg(
                client=None, contributors_index="opencheck-idx", version="v1",
                repo_list=["org/repo-a", "org/repo-b"], page_size=1)

        self.assertEqual(result, [])  # 无数据时返回空，由触发扫描兜底
        scan_calls = [payload for path, payload in post_calls if path == "opencheck"]
        self.assertEqual(
            sorted(payload["project_url"] for payload in scan_calls),
            ["org/repo-a.git", "org/repo-b.git"],
        )


if __name__ == "__main__":
    unittest.main()
