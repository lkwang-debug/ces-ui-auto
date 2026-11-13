# -*- coding: utf-8 -*-
import time
import pytest
from testcases.feature_assertions import assert_page_feature

pytestmark = pytest.mark.requires_capability("developer_sdk")


def test_developer_page_structure(feature_catalog):
    page = assert_page_feature(feature_catalog, "开发者中心", "开发者", False)
    assert any(word in page["text"] for word in ("开发者", "API", "SDK", "密钥", "凭据"))


def test_admin_developer_crud_and_client_id(developer_page):
    # Keep the value within older-page application-name limits while retaining
    # the uiauto_ prefix required for safe cleanup.
    name = f"uiauto_d_{time.time_ns() % 100000000}"
    modified = f"{name}_m"
    try:
        assert developer_page.create_temporary(name) is True, developer_page.last_action_error
        assert developer_page.query_client_id(name) is not None, developer_page.last_client_id_evidence
        assert developer_page.modify(name, modified) is True, developer_page.last_action_error
        assert developer_page.disable_and_delete(modified) is True
    finally:
        developer_page.disable_and_delete(name)
        developer_page.disable_and_delete(modified)


@pytest.mark.requires_capability("developer_ces")
@pytest.mark.parametrize(
    "channel,label",
    [("developer_ces", "CES")],
    ids=["CES应用"],
)
def test_admin_sdk_and_ces_full_lifecycle(developer_page, channel, label):
    if channel == "developer_ces" and not developer_page.use_channel(channel):
        pytest.skip("当前版本不支持CES开发者")
    assert developer_page.use_channel(channel) is True
    suffix = str(time.time_ns())[-8:]
    name = f"uiauto_{label.lower()}_{suffix}"
    modified = name + "_m"
    try:
        assert developer_page.create_temporary(name) is True, developer_page.last_action_error
        assert developer_page.query_client_id(name) is not None, developer_page.last_client_id_evidence
        assert developer_page.modify(name, modified) is True, developer_page.last_action_error
        assert developer_page.change_status(modified, "停用") is True
        assert developer_page.change_status(modified, "启用") is True
        assert developer_page.delete(modified) is True
    finally:
        developer_page.delete(name)
        developer_page.delete(modified)
