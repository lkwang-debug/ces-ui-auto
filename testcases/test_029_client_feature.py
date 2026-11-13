# -*- coding: utf-8 -*-
import allure
import pytest


pytestmark = pytest.mark.requires_capability("client_feature")
TARGET_FEATURE = "即时会议"


def test_client_feature_page_structure(client_feature):
    page = client_feature.open_features()
    assert page is not None
    for expected in (
        "客户端功能管理", "功能名称", "注册用户默认权限开关", "指定用户范围", "匿名参会用户",
    ):
        assert expected in page["text"]
    for feature in ("即时会议", "预约会议", "全量通讯录", "通讯录呼叫", "云录制", "本地录制", "文字转写", "语音字幕"):
        assert feature in page["text"]


def test_client_feature_default_permission_restore(client_feature):
    assert client_feature.verify_switch_persistence_and_restore(TARGET_FEATURE, 0) is True
    restored = client_feature.snapshot(TARGET_FEATURE)
    assert restored is not None


def test_client_feature_anonymous_permission_restore(client_feature):
    target = client_feature.feature_with_anonymous_switch()
    assert target, "当前页面没有任何匿名用户权限开关"
    assert client_feature.verify_switch_persistence_and_restore(target, 1) is True


def test_client_feature_user_scope_dialog(client_feature):
    result = client_feature.open_user_scope_and_cancel(TARGET_FEATURE)
    allure.attach(
        str(client_feature.last_scope_debug),
        "指定用户范围弹窗诊断",
        allure.attachment_type.TEXT,
    )
    assert result is True, client_feature.last_scope_debug
