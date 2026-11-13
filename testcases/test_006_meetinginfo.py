# -*- coding:utf-8 -*-
import time

import allure
import pytest

from common.base_analyze import analyze_data
from common.test_preconditions import require_minimum_records,pagination_records


ADD_SUCCESS = "\u65b0\u589e\u6210\u529f"
DELETE_SUCCESS = "\u5220\u9664\u6210\u529f"

@pytest.fixture(scope="module")
def meeting_cleanup(meeting_info):
    names = []
    yield names

    seen = set()
    cleanup_names = []
    for name in reversed(names):
        if name in seen:
            continue
        seen.add(name)
        cleanup_names.append(name)
    assert meeting_info.delete_meetings_by_names(cleanup_names, DELETE_SUCCESS) is True, cleanup_names


@pytest.fixture
def managed_meeting(meeting_info, meeting_cleanup):
    stamp = time.time_ns() % 1000000000
    state = {
        "name": f"meeting{stamp}",
        "cancel_name": f"meetingcancel{stamp}",
        "modified_name": f"meetingmod{stamp}",
    }

    meeting_cleanup.append(state["name"])
    assert meeting_info.add_meeting(state["name"], ADD_SUCCESS) is True

    try:
        yield state
    finally:
        meeting_info._dismiss_blocking_layers()
        names=list(dict.fromkeys([state['name'],state['modified_name']]))
        assert meeting_info.delete_meetings_by_names(names,DELETE_SUCCESS) is True, names
        for name in names:
            while name in meeting_cleanup:meeting_cleanup.remove(name)


@pytest.fixture(scope="module")
def authorization_user(meeting_info):
    """Provide a known unassigned user instead of relying on environment data."""
    from pages.ContactList_Page.UserPage import UserManagerPage

    user_page = UserManagerPage(driver=meeting_info.driver)
    username = f"au_{time.time_ns() % 1000000000}"
    created = False
    last_error = None
    for _ in range(2):
        try:
            assert user_page.common_enter_user() is True
            created = user_page.add_user(username, "uipass12", "添加成功")
            if created:
                break
        except Exception as exc:
            last_error = exc
        user_page._hard_reload_user_page()
    assert created is True, f"授权候选用户创建失败：{last_error}"
    # Creating the candidate navigates the shared browser to user management.
    # Re-enter the meeting page before the authorization test uses its object.
    assert meeting_info.common_enter_meeting_info() is True
    try:
        yield username
    finally:
        assert user_page.ensure_user_absent(username) is True, username


def test_enter_meeting_info(meeting_info):
    assert meeting_info.common_enter_meeting_info() is True


def test_add_meeting_success(meeting_info, meeting_cleanup):
    unique_name = f"meeting_add_{time.time_ns() % 1000000000}"
    meeting_cleanup.append(unique_name)
    assert meeting_info.add_meeting(unique_name, ADD_SUCCESS) is True


def test_add_meeting_advanced_settings_and_recording_matrix(meeting_info):
    """新增弹窗：所有高级区块可用，录制方式随模板和自动录制联动。"""
    meeting_info.click_new_add()
    try:
        snapshot = meeting_info.advanced_meeting_settings_snapshot()
        allure.attach(str(snapshot), "新增会议室高级设置快照", allure.attachment_type.TEXT)
        displayed_titles = " ".join(item["title"] for item in snapshot or [])
        assert all(title in displayed_titles for title in meeting_info.advanced_section_titles)
        if "文字转写" in displayed_titles:
            assert "人脸签到" in displayed_titles
        else:
            assert "会议纪要" in displayed_titles
        assert all(item["controls"] > 0 for item in snapshot or [])

        expanded_sections = meeting_info.expand_advanced_meeting_sections()
        allure.attach(str(expanded_sections), "新增会议室高级区块交互快照", allure.attachment_type.TEXT)
        assert all(item["visible_controls"] > 0 for item in expanded_sections)
        expected_labels = {
            "默认视频参数": "默认视频参数编辑器",
            "H.323会议参数": "通话质量",
            "会议室参数": "会议模式",
            "录制设置": "录制模板",
            "指定主服务器": "服务器名称",
        }
        if "文字转写" in displayed_titles:
            expected_labels.update({"文字转写": "开启", "人脸签到": "开启"})
        else:
            expected_labels["会议纪要"] = "开启"
        for section, label in expected_labels.items():
            assert label in meeting_info.advanced_section_text(section)

        assert meeting_info.choose_recording_template("标准") is True
        assert meeting_info.visible_recording_mode_options() == meeting_info.create_basic_recording_modes
        assert meeting_info.choose_recording_template("自定义") is True
        assert meeting_info.set_auto_recording(False) is True
        assert meeting_info.visible_recording_mode_options() == meeting_info.create_basic_recording_modes
        assert meeting_info.set_auto_recording(True) is True
        assert meeting_info.visible_recording_mode_options() == meeting_info.create_auto_recording_modes
    finally:
        meeting_info.click_cancel_button()


@pytest.mark.parametrize(
    "recording_mode, requires_authorized_user",
    [
        ("完整录制", False),
        ("仅录共享者", False),
        ("仅录主持人", False),
        ("仅录音频", False),
        ("指定用户合流录制", True),
        ("指定用户分流录制", True),
    ],
    ids=("完整录制", "仅录共享者", "仅录主持人", "仅录音频", "指定用户合流录制", "指定用户分流录制"),
)
def test_modify_meeting_advanced_recording_modes_and_persistence(
    meeting_info, meeting_cleanup, recording_mode, requires_authorized_user, request
):
    """每种录制方式使用独立会议室，验证保存和重新打开后的配置。"""
    allure.dynamic.parameter("录制方式", recording_mode)
    meeting_name = f"meeting_recording_{time.time_ns() % 1000000000}"
    meeting_cleanup.append(meeting_name)
    assert meeting_info.add_meeting(meeting_name, ADD_SUCCESS) is True
    recording_user = None
    if requires_authorized_user:
        # The environment's first account can have an empty nickname. Use a
        # registered test account with a known display name and persisted room
        # authorization, rather than assuming its panel text equals its login.
        recording_user = request.getfixturevalue('authorization_user')
        assert meeting_info.authorize_user_for_recording(meeting_name, recording_user) is True
        allure.dynamic.parameter("指定录制用户", recording_user)
    try:
        assert meeting_info.open_meeting_for_modify(meeting_name) is True
        expanded_sections = meeting_info.expand_advanced_meeting_sections()
        assert all(item["visible_controls"] > 0 for item in expanded_sections)
        assert meeting_info.choose_recording_template("自定义") is True
        assert meeting_info.set_auto_recording(True) is True
        assert meeting_info.visible_recording_mode_options() == meeting_info.modify_auto_recording_modes

        if requires_authorized_user:
            assert meeting_info.open_designated_recording_user_dialog(recording_mode) is True
            assert meeting_info.select_designated_recording_user(recording_user) is True
            allure.attach(
                f"{recording_mode}: {recording_user}",
                "指定录制用户选择结果",
                allure.attachment_type.TEXT,
            )
        else:
            assert meeting_info.choose_recording_mode(recording_mode) is True
        assert meeting_info.recording_option_is_selected(recording_mode) is True
        meeting_info.click_save_button()
        assert meeting_info.wait_meeting_saved(timeout=30) is True

        assert meeting_info.open_meeting_for_modify(meeting_name) is True
        assert meeting_info.choose_recording_template("自定义") is True
        assert meeting_info.auto_recording_enabled() is True
        assert meeting_info.recording_option_is_selected(recording_mode) is True
    finally:
        assert meeting_info._dismiss_blocking_layers() is True


def test_add_meeting_failed_when_name_empty(meeting_info):
    meeting_info.click_new_add()
    meeting_info.click_save_button()
    assert "\u4e0d\u80fd\u4e3a\u7a7a" in meeting_info.get_wrong_meeting_name_msg()
    assert meeting_info.click_cancel_button() is True


@pytest.mark.requires_profile("legacy")
def test_admin_password_meeting_password_is_null(meeting_info):
    unique_name = f"meetingpwdempty{time.time_ns() % 1000000000}"
    try:
        assert meeting_info.enable_admin_password_and_select_meeting_password() is True
        meeting_info.send_meeting_name(unique_name)
        meeting_info.click_save_button()
        assert (
            "\u542f\u7528\u7ba1\u7406\u5458\u5bc6\u7801\u540e\u7ba1\u7406\u5458\u5bc6\u7801\u4e0d\u80fd\u4e3a\u7a7a"
            in meeting_info.get_admin_password_msg()
        )
        assert (
            "\u542f\u7528\u4f1a\u8bae\u5ba4\u5bc6\u7801\u65f6\uff0c\u4f1a\u8bae\u5ba4\u767b\u5f55\u5bc6\u7801\u4e0d\u80fd\u4e3a\u7a7a"
            in meeting_info.get_meeting_password_msg()
        )
    finally:
        meeting_info.click_cancel_button()


@pytest.mark.parametrize("params", analyze_data("add_meeting_password_unusual_data.json"))
@pytest.mark.requires_profile("legacy")
def test_send_admin_password_meeting_password_unusually(meeting_info, params):
    unique_name = f"meetingpwdinvalid{time.time_ns() % 1000000000}"
    try:
        assert meeting_info.enable_admin_password_and_select_meeting_password() is True
        meeting_info.send_meeting_name(unique_name)
        assert meeting_info.send_admin_password_and_meeting_password(
            params["admin_password"], params["meeting_password"]
        ) is True
        meeting_info.click_save_button()
        assert params["admin_password_msg"] in meeting_info.get_admin_password_msg()
        assert params["meeting_password_msg"] in meeting_info.get_meeting_password_msg()
    finally:
        meeting_info.click_cancel_button()


@pytest.mark.requires_profile("legacy")
def test_send_admin_password_meeting_password_normally(meeting_info, meeting_cleanup):
    unique_name = f"meetingpwdok{time.time_ns() % 1000000000}"
    meeting_cleanup.append(unique_name)
    assert meeting_info.add_meeting_with_passwords(
        unique_name, "123456", "123456", ADD_SUCCESS
    ) is True


def test_find_meeting(meeting_info, managed_meeting):
    assert meeting_info.search_meeting(managed_meeting["name"]) is True


def test_find_missing_meeting(meeting_info):
    assert meeting_info.search_meeting(f"missing_meeting_{time.time_ns()}") is False


def test_cancel_add_meeting(meeting_info,meeting_cleanup):
    name=f'uicM_{time.time_ns()%1000000000}'
    meeting_cleanup.append(name)
    meeting_info.click_new_add()
    meeting_info.send_meeting_name(name)
    assert meeting_info.click_cancel_button() is True
    assert meeting_info.search_meeting(name) is False, '取消新增后仍产生了会议室'
    meeting_cleanup.remove(name)


@pytest.fixture
def meeting_pagination_data(meeting_info):
    with pagination_records(meeting_info,meeting_info.common_enter_meeting_info,
        lambda value:meeting_info.add_meeting(value,ADD_SUCCESS),
        lambda value:meeting_info.delete_meetings_by_names([value],DELETE_SUCCESS),'UIM'):
        yield


def test_change_meeting_page_size(meeting_info,meeting_pagination_data):
    require_minimum_records(
        meeting_info,
        minimum_total=11,
        module_name="会议管理",
        scenario_name="分页相关测试",
    )
    try:
        assert meeting_info.jump_to_result_page(1) is True
        assert meeting_info.set_result_page_size(10) is True
        assert "10" in (meeting_info.get_current_page_size_text() or "")
    finally:
        meeting_info.set_result_page_size(15)
        meeting_info.jump_to_result_page(1)


def test_jump_meeting_page(meeting_info,meeting_pagination_data):
    require_minimum_records(
        meeting_info,
        minimum_total=11,
        module_name="会议管理",
        scenario_name="分页相关测试",
    )
    try:
        assert meeting_info.jump_to_result_page(1) is True
        assert meeting_info.set_result_page_size(10) is True
        first_page_summary = meeting_info.get_pagination_summary_text()
        assert meeting_info.jump_to_result_page(2) is True
        assert meeting_info.get_current_page_text() == "2"
        second_page_summary = meeting_info.get_pagination_summary_text()
        assert second_page_summary
        assert second_page_summary != first_page_summary
        assert meeting_info.jump_to_result_page(1) is True
        assert meeting_info.get_current_page_text() == "1"
    finally:
        meeting_info.set_result_page_size(15)
        meeting_info.jump_to_result_page(1)


def test_authorize_first_available_user(meeting_info, managed_meeting, authorization_user):
    assert meeting_info.authorize_user_with_role(managed_meeting['name'], authorization_user, role='管理员', result='操作成功') is True
    authorized_username = meeting_info.sort_first_authorized_user(managed_meeting['name'], '1')
    assert authorized_username == authorization_user


def test_sort_first_authorized_user(meeting_info, managed_meeting, authorization_user):
    assert meeting_info.authorize_user_with_role(managed_meeting['name'], authorization_user, role='管理员', result='操作成功') is True
    sorted_username = meeting_info.sort_first_authorized_user(
        managed_meeting["name"], "1"
    )
    assert sorted_username is not None


def test_cancel_modify_meeting(meeting_info, managed_meeting):
    assert meeting_info.cancel_modify_meeting(
        managed_meeting["name"], managed_meeting["cancel_name"]
    ) is True


def test_modify_meeting(meeting_info, managed_meeting, meeting_cleanup):
    old_name = managed_meeting["name"]
    meeting_cleanup.append(managed_meeting['modified_name'])
    assert meeting_info.modify_meeting(
        old_name, managed_meeting["modified_name"]
    ) is True
    managed_meeting["name"] = managed_meeting["modified_name"]
    if old_name in meeting_cleanup:
        meeting_cleanup.remove(old_name)
    meeting_cleanup.append(managed_meeting["name"])


def test_delete_meeting(meeting_info, managed_meeting, meeting_cleanup):
    assert meeting_info.delete_meeting(managed_meeting["name"], DELETE_SUCCESS) is True
    if managed_meeting["name"] in meeting_cleanup:
        meeting_cleanup.remove(managed_meeting["name"])
