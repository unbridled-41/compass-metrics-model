import unittest
from unittest.mock import MagicMock

from compass_common.opensearch_utils import free_scroll, get_items


class FreeScrollTest(unittest.TestCase):
    """clear_scroll 失败时应记录 debug 日志后返回，
    而不是因日志语句自身的 "{}" .scroll_id 属性错误抛 AttributeError。"""

    def test_clear_scroll_failure_is_logged_not_raised(self):
        client = MagicMock()
        client.clear_scroll.side_effect = RuntimeError("boom")
        free_scroll(client, "scroll-abc")  # 修复前：AttributeError

    def test_clear_scroll_success_noop(self):
        client = MagicMock()
        free_scroll(client, "scroll-abc")
        client.clear_scroll.assert_called_once_with(scroll_id="scroll-abc")


class GetItemsTest(unittest.TestCase):
    """search 抛出非 ES 传输类异常时不应在 except 分支里访问 e.info
    导致二次异常（AttributeError）掩盖原始错误。"""

    def test_non_transport_exception_returns_none_without_masking(self):
        client = MagicMock()
        client.search.side_effect = KeyError("bad body")
        self.assertIsNone(get_items(client, "idx", {"query": {}}, 10))

    def test_es_error_without_too_many_scrolls_returns_none(self):
        class FakeTransportError(Exception):
            info = {"status": 400, "error": {"root_cause": [{"reason": "other failure"}]}}

        client = MagicMock()
        client.search.side_effect = FakeTransportError("x")
        self.assertIsNone(get_items(client, "idx", {"query": {}}, 10))


if __name__ == "__main__":
    unittest.main()
