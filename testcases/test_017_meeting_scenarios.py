# -*- coding: utf-8 -*-
from testcases.feature_assertions import assert_page_feature


def test_meeting_scenario_structure(feature_catalog):
    page = assert_page_feature(feature_catalog, "会议管理", "会议场景管理")
    assert all(word in page["text"] for word in ("会控", "培训", "讨论", "设置默认场景"))
    assert any("保存" in button.replace(" ", "") for button in page["buttons"])


def test_enterprise_templates_and_default_restore(meeting_scenarios):
    assert meeting_scenarios.open_scenarios()
    assert meeting_scenarios.enterprise_templates_visible() is True
    assert meeting_scenarios.set_default_and_restore() is True, meeting_scenarios.last_default_error
