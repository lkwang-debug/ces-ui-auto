# -*- coding: utf-8 -*-
import allure
import pytest

from testcases.feature_assertions import assert_page_feature
from pages.Meeting_Page.MeetingRecordsPage import has_record_detail_content


def test_meeting_records_structure(feature_catalog):
    page = assert_page_feature(feature_catalog, "会议管理", "会议记录")
    assert "会议室ID" in page["text"] and "会议时长" in page["text"]


def test_meeting_records_no_result(feature_catalog):
    assert feature_catalog.open_feature("会议管理", "会议记录")
    if feature_catalog.fill_first_search("AUTO_MISSING_MEETING_RECORD_987654321"):
        assert "AUTO_MISSING_MEETING_RECORD_987654321" not in feature_catalog.snapshot_main()["text"]


def test_meeting_records_sort_filters_clear_and_export(meeting_records):
    page = meeting_records.open_records()
    assert page
    assert meeting_records.sort_by_duration() is True
    cells = meeting_records.driver.execute_script("return [...document.querySelectorAll('main table tbody tr:first-child td')].map(x => (x.innerText || '').trim())")
    if len(cells) >= 2:
        assert meeting_records.search_by_room(cells[1], cells[0]) is True
        assert cells[0] in meeting_records._main_text() and cells[1] in meeting_records._main_text()
    assert meeting_records.clear_search() is True
    exported = meeting_records.download(("导出",), {".xlsx", ".xls", ".csv"})
    assert exported is not None and exported.stat().st_size > 0


@pytest.mark.requires_profile("4.39.8")
@pytest.mark.parametrize(
    "action_title",
    ("参会人详情", "投票结果", "签到结果", "录制与纪要"),
    ids=("参会人详情", "投票结果", "签到结果", "录制与纪要"),
)
def test_meeting_record_authorized_detail_entries(meeting_records, action_title):
    available = meeting_records.available_record_action_titles()
    allure.attach(str(available), "会议记录实际可用入口", allure.attachment_type.TEXT)
    assert action_title in available, f"固定会议记录缺少入口：{action_title}"
    evidence = meeting_records.open_record_action(action_title)
    allure.attach(str(evidence), f"{action_title}查看结果", allure.attachment_type.TEXT)
    assert evidence and evidence["title"] == action_title
    if action_title == "参会人详情":
        legacy_table = {"用户昵称", "用户名", "参会情况", "登录IP"}.issubset(
            evidence["headers"]
        )
        modern_file_list = "全部下载" in evidence["text"] and len(
            evidence["text"].replace("参会人详情", "").replace("全部下载", "").strip()
        ) > 0
        assert legacy_table or modern_file_list
    elif action_title == "投票结果":
        assert "操作" in evidence["headers"] or "暂无数据" in evidence["text"]
    elif action_title == "签到结果":
        assert all(text in evidence["text"] for text in ("签到总人数", "导出详情"))
    else:
        assert has_record_detail_content(evidence), "录制与纪要详情既无纪要内容也无实际录制文件"
