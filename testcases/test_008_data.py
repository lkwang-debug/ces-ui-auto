# -*- coding:utf-8 -*-
import pytest

import allure

from conf.conf import ConfigManager


EXPECTED_HEADERS = ["文件名称", "备份日期", "自动备份", "恢复", "下载", "操作"]


def test_enter_data(data):
    assert data.common_enter_data() is True


def test_data_table_headers(data):
    headers = data.get_table_headers()
    assert headers == EXPECTED_HEADERS


def test_data_empty_state(data):
    assert data.get_date_input_placeholder() == "备份日期"
    if data.has_no_data():
        return
    assert data.get_visible_row_count() > 0


def test_open_add_backup_dialog_and_cancel(data):
    dialog_text = data.open_add_backup_dialog()
    assert "数据备份" in dialog_text
    assert "是否添加一个数据备份" in dialog_text
    assert data.cancel_active_dialog() is True


def test_open_upload_backup_dialog(data):
    dialog_text = data.open_upload_dialog()
    assert "上传备份文件" in dialog_text
    assert "选择文件" in dialog_text
    assert data.get_upload_accept_extensions() == ".sql,.dmp"
    assert data.close_active_dialog() is True


def test_backup_download_and_upload(data):
    with allure.step("下载一份现有备份文件"):
        source = data.download_existing_backup()
    if source is None:
        message = "数据管理页面没有可下载的 .sql 或 .dmp 备份文件"
        if ConfigManager.ACCEPTANCE_MODE:
            pytest.fail(message)
        pytest.skip(message)

    downloaded = source["path"]
    uploaded = None
    try:
        with allure.step("校验下载备份文件"):
            assert downloaded.exists()
            assert downloaded.suffix.lower() in {".sql", ".dmp"}
            assert downloaded.stat().st_size > 0
            allure.attach.file(
                str(downloaded),
                name="下载的备份文件",
                attachment_type=allure.attachment_type.TEXT,
                extension=downloaded.suffix.lstrip("."),
            )

        with allure.step("生成唯一文件名的上传副本"):
            uploaded = data.make_unique_upload_copy(downloaded)
            assert uploaded.exists() and uploaded.stat().st_size == downloaded.stat().st_size

        with allure.step("上传下载备份的副本并验证新增记录"):
            upload_result = data.upload_backup_file(uploaded)
            assert isinstance(upload_result, dict)
            allure.attach(
                f"本地文件：{uploaded.name}\n服务端文件：{upload_result['file_name']}",
                "上传备份文件信息",
                allure.attachment_type.TEXT,
            )
    finally:
        try:
            if uploaded is not None:
                with allure.step("删除本次上传产生的备份记录"):
                    if "upload_result" not in locals():
                        pytest.fail("上传未返回服务端文件名，无法安全清理备份记录")
                    assert data.delete_backup_by_name(upload_result["file_name"]) is True
        finally:
            data.restore_default_download_dir()
