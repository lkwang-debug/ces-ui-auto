# -*- coding: utf-8 -*-
from datetime import datetime

import allure

from common.runtime_artifacts import require_external_data, trigger_terminal_log
from conf.conf import ConfigManager
from testcases.feature_assertions import assert_page_feature


def test_terminal_log_structure(feature_catalog):
    page = assert_page_feature(feature_catalog, "日志管理", "终端日志")
    expected = {"员工帐号", "用户ID", "设备ID", "日志类型", "操作"}
    assert expected.issubset(set(page["headers"]))


def test_configured_terminal_log(terminal_log):
    username = require_external_data(
        ConfigManager.TERMINAL_LOG_USERNAME, "UIAUTO_TERMINAL_LOG_USERNAME"
    )
    device_id = require_external_data(
        ConfigManager.TERMINAL_LOG_DEVICE_ID, "UIAUTO_TERMINAL_LOG_DEVICE_ID"
    )
    log_type = require_external_data(
        ConfigManager.TERMINAL_LOG_TYPE, "UIAUTO_TERMINAL_LOG_TYPE"
    )
    started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    result = trigger_terminal_log()
    if result is not None:
        allure.attach(result.stdout or "", "trigger_stdout", allure.attachment_type.TEXT)
        allure.attach(result.stderr or "", "trigger_stderr", allure.attachment_type.TEXT)
        assert result.returncode == 0
        allure.attach(started, "trigger_started_at", allure.attachment_type.TEXT)
    else:
        allure.attach(
            "No trigger command configured; validating pre-existing fixed data.",
            "terminal_log_data_mode",
            allure.attachment_type.TEXT,
        )
    assert terminal_log.validate_configured_log(username, device_id, log_type)


def test_terminal_log_download_and_check(terminal_log):
    assert terminal_log.open_logs()
    downloaded = terminal_log.download(("下载",), {".xlsx", ".xls", ".csv", ".zip", ".log", ".txt"})
    assert downloaded is not None and downloaded.stat().st_size > 0
    assert terminal_log.open_check() is True
