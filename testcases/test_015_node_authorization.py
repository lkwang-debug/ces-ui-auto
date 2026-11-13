# -*- coding: utf-8 -*-
import re

from testcases.feature_assertions import assert_page_feature


def test_node_authorization_fields(feature_catalog):
    page = assert_page_feature(feature_catalog, "系统信息", "节点授权信息", False)
    assert "到期时间" in page["body_text"]
    assert re.search(r"\d{4}-\d{2}-\d{2}", page["body_text"])
