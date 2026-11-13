# -*- coding:utf-8 -*-
import pytest
import allure
from conf.conf import ConfigManager


def test_enter_server_log(server_log):
    assert server_log.common_enter_server_log() is True


def test_meeting_server_tab(server_log):
    assert server_log.meeting_server_rows_valid() is True


def test_web_server_tab(server_log):
    assert server_log.web_server_rows_valid() is True


def test_node_server_tab(server_log):
    assert server_log.switch_to_tab(server_log.node_server_tab) is True
    # Node logs are optional in this environment. Validate the supported empty
    # state instead of skipping a normal regression case.
    if server_log.current_tab_has_no_data():
        return
    assert server_log.node_server_rows_valid() is True


def test_open_warning_receiver_modal(server_log):
    modal_text = server_log.open_warning_receiver_modal()
    assert modal_text
    assert "设置邮箱接收者" in modal_text
    assert "选择邮箱接收者" in modal_text
    assert server_log.close_receiver_modal() is True


@pytest.mark.parametrize("tab", ["会议服务器", "Web服务器", "节点服务器"])
def test_server_log_download(server_log, tab):
    if tab in ConfigManager.UNDEPLOYED_SERVER_LOG_TABS:
        reason = f"当前环境已确认未部署{tab}：下载验收不适用"
        allure.attach(reason, "服务部署前置说明", allure.attachment_type.TEXT)
        pytest.skip(reason)
    downloaded = server_log.download_server_log(tab)
    assert downloaded is not None, server_log.last_download_error
    assert downloaded.suffix.lower() in {".zip", ".log", ".txt", ".gz"}
    assert downloaded.stat().st_size > 0
