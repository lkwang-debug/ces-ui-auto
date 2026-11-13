# -*- coding: utf-8 -*-
from testcases.feature_assertions import assert_page_feature


def test_meeting_statistics_structure(feature_catalog):
    page = assert_page_feature(feature_catalog, "会议管理", "会议统计")
    assert page["inputs"] or page["headers"]


def test_statistics_metrics_periods_and_export(meeting_statistics):
    assert meeting_statistics.open_statistics()
    for metric in meeting_statistics.metrics:
        assert meeting_statistics.select_metric(metric) is True
    for period in meeting_statistics.periods:
        assert meeting_statistics.select_period(period) is True
    # Custom range uses the first two visible date inputs and must be exportable.
    assert meeting_statistics.select_custom_month_range() is True, meeting_statistics.last_custom_range_error
    assert meeting_statistics.submit_and_wait() is True
    exported = meeting_statistics.download(("导出",), {".xlsx", ".xls", ".csv"})
    assert exported is not None and exported.stat().st_size > 0
