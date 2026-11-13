# -*- coding: utf-8 -*-
import pytest

from testcases.feature_assertions import assert_page_feature


def test_online_meeting_empty_or_list(feature_catalog):
    page = assert_page_feature(feature_catalog, "会议管理", "在线会议室", False)
    assert any(value in page["text"] for value in ("暂无", "无数据", "会议", "会议室"))


@pytest.mark.destructive
def test_end_online_meeting_requires_explicit_opt_in():
    pytest.skip("A dedicated online meeting fixture is required")
