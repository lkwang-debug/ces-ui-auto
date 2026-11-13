# -*- coding:utf-8 -*-
import pytest
from common.test_preconditions import require_minimum_records
import time
from conf.conf import ConfigManager
from datetime import datetime,timedelta


# Verified sentinel for the 4.39.7 username filter. It stays within the
# input limit and contains no characters treated as a fuzzy-query wildcard.
MISSING_LOG_USER = "missing_x_987654321"

def test_enter_operation_log(log):
    assert log.common_enter_operation_log() is True


def test_change_operation_log_page_size(log):
    require_minimum_records(
        log,
        minimum_total=11,
        module_name="操作日志",
        scenario_name="分页相关测试",
    )
    try:
        assert log.jump_to_result_page(1) is True
        assert log.set_result_page_size(10) is True
        assert "10" in (log.get_current_page_size_text() or "")
    finally:
        log.set_result_page_size(15)
        log.jump_to_result_page(1)


def test_jump_operation_log_page(log):
    require_minimum_records(
        log,
        minimum_total=11,
        module_name="操作日志",
        scenario_name="分页相关测试",
    )
    try:
        assert log.jump_to_result_page(1) is True
        assert log.set_result_page_size(10) is True
        first_page_summary = log.get_pagination_summary_text()
        assert log.jump_to_result_page(2) is True
        assert log.get_current_page_text() == "2"
        second_page_summary = log.get_pagination_summary_text()
        assert second_page_summary
        assert second_page_summary != first_page_summary
        assert log.jump_to_result_page(1) is True
        assert log.get_current_page_text() == "1"
    finally:
        log.set_result_page_size(15)
        log.jump_to_result_page(1)


def test_search_operation_log_by_username(log):
    username = ConfigManager.USERNAME
    rows = log.search_by_username(username)
    assert rows
    # The page also retains server-generated system rows whose username is
    # rendered as '-'.  Those are not user-operation records; every actual
    # user row must still match the requested username.
    user_rows = [row for row in rows if row["username"] not in {"", "-"}]
    assert any(row["username"] == username for row in user_rows)
    assert all(row["username"] == username for row in user_rows)
    assert any(row["result"] == "成功" for row in rows)
    log.reset_search()


def test_search_operation_log_no_result(log):
    assert log.search_username_failed(MISSING_LOG_USER) is True
    log.reset_search()


def test_search_operation_log_by_date_range_and_clear(log):
    today=datetime.now()
    start=(today-timedelta(days=1)).strftime('%Y-%m-%d')
    end=(today+timedelta(days=1)).strftime('%Y-%m-%d')
    assert log.search_by_date_and_username(start, end, ConfigManager.USERNAME) is True
    rows=log.get_visible_rows()
    assert rows
    assert all(start <= row['operation_time'][:10] <= end for row in rows)
    lower=datetime.fromisoformat(log.last_filter_values['开始时间'])
    upper=datetime.fromisoformat(log.last_filter_values['结束时间'])
    assert all(lower <= datetime.fromisoformat(row['operation_time']) <= upper for row in rows)
    future_start=(today+timedelta(days=7)).strftime('%Y-%m-%d')
    future_end=(today+timedelta(days=8)).strftime('%Y-%m-%d')
    assert log.search_by_date_and_username(future_start,future_end,ConfigManager.USERNAME) is True
    assert log.get_visible_rows() == [] and log.has_no_data()
    assert log.reset_search() is True
    assert log.search_by_username(ConfigManager.USERNAME)
    assert log.reset_search() is True
