# -*- coding: utf-8 -*-
from testcases.feature_assertions import assert_page_feature


def test_meeting_log_structure(feature_catalog):
    page = assert_page_feature(feature_catalog, "日志管理", "会议日志")
    assert page["inputs"] or page["headers"]


def test_meeting_log_export_available(feature_catalog):
    page = feature_catalog.open_feature("日志管理", "会议日志")
    assert page
    assert any("导出" in button for button in page["buttons"])


def test_meeting_log_export_download(feature_catalog):
    exported = feature_catalog.download_from_feature(
        "日志管理", "会议日志", ["导出"], {".xlsx", ".xls", ".csv"}
    )
    assert exported is not None
    assert exported.suffix.lower() in {".xlsx", ".xls", ".csv"}
    assert exported.stat().st_size > 0


def test_meeting_log_filters_clear_and_filtered_exports(meeting_log):
    assert meeting_log.open_logs()
    cells = meeting_log.driver.execute_script("return [...document.querySelectorAll('main table tbody tr:first-child td')].map(x => (x.innerText || '').trim())")
    assert len(cells) >= 4
    # Fill the visible time, user, room-ID and room-name controls with values
    # taken from a real row; this avoids asserting against arbitrary history.
    # Table order is serial, room ID, room name, username.  The filter order
    # is start, end, username, selected room-keyword.
    assert meeting_log.fill_first_inputs(["2026-01-01", "2026-12-31", cells[3], cells[1]]) is True
    assert meeting_log.submit_and_wait() is True
    first = meeting_log.download(("导出",), {".xlsx", ".xls", ".csv"})
    assert first is not None and first.stat().st_size > 0
    assert meeting_log.clear_search() is True
