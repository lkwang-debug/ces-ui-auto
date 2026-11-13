# -*- coding:utf-8 -*-
import json
import sys
import time

import allure
import pytest

from common.base_analyze import analyze_data
from common.test_preconditions import require_minimum_records,pagination_records
from conf.conf import ConfigManager


ADD_SUCCESS = "\u6dfb\u52a0\u6210\u529f"
DELETE_SUCCESS = "\u5220\u9664\u6210\u529f"
DUPLICATE_KEYWORDS = ("重复", "已存在")
PHONE_COMPATIBILITY_CASES = analyze_data("user_phone_compatibility_data.json")
SPECIAL_NICKNAME = "米拉丁江·艾合买提江"


def _build_phone_number(params):
    fixed_phone = params.get("fixed_phone")
    if fixed_phone:
        return str(fixed_phone)
    unique_tail = time.time_ns() % 10000
    return f"{params['prefix']}1587{unique_tail:04d}"


def _masked_phone(phone_number):
    value = str(phone_number)
    return f"{value[:3]}****{value[-4:]}"


def _attach_phone_evidence(params, phone_number, profile, action):
    evidence = {
        "操作": action,
        "场景": params["scenario"],
        "号段分类": params["category"],
        "号段": params["prefix"],
        "手机号": _masked_phone(phone_number),
        "持久化昵称": profile.get("nickname") if profile else None,
        "持久化手机号": _masked_phone(profile.get("phone_number", ""))
        if profile
        else None,
        "字段错误": profile.get("errors") if profile else None,
    }
    allure.attach(
        json.dumps(evidence, ensure_ascii=False, indent=2),
        f"{action}持久化证据",
        allure.attachment_type.JSON,
    )


def _assert_profile(
    profile, phone_number, nickname=None, require_middle_dot=False
):
    assert profile is not None, "刷新后无法重新打开用户修改弹窗"
    assert profile["phone_number"] == str(phone_number)
    if nickname is not None:
        assert profile["nickname"] == nickname
    if require_middle_dot:
        assert "·" in profile["nickname"]
    assert not any(
        profile["errors"].get(label)
        for label in ("用户昵称", "昵称", "手机号码", "手机号")
    )


def _cleanup_compatibility_user(user, user_cleanup, username, phone_number):
    business_error = sys.exc_info()[1]
    cleanup_error = ""
    try:
        cleaned = user.ensure_user_absent(username)
    except Exception as exc:
        cleaned = False
        cleanup_error = type(exc).__name__
    if cleaned:
        while username in user_cleanup:
            user_cleanup.remove(username)
    allure.attach(
        json.dumps(
            {
                "用户名": username,
                "手机号": _masked_phone(phone_number),
                "清理成功": cleaned,
                "清理异常类型": cleanup_error,
                "已有业务失败": business_error is not None,
            },
            ensure_ascii=False,
            indent=2,
        ),
        "测试用户清理结果",
        allure.attachment_type.JSON,
    )
    if not cleaned and business_error is not None:
        # Keep the original business assertion as the primary failure. The
        # account stays registered; module teardown retries and enforces cleanup.
        return
    assert cleaned is True, f"临时用户清理失败: {username} {cleanup_error}"


def assert_duplicate_blocked(result):
    message = result.get("message", "")
    message_source = result.get("message_source", "")
    assert result.get("blocked") is True
    assert isinstance(result.get('before_count'),int) and result['before_count'] > 0
    assert result.get('after_count') == result['before_count']
    if message:
        assert any(keyword in message for keyword in DUPLICATE_KEYWORDS), (
            f"重复新增用户提示不符合预期: {message!r}, "
            f"提示来源: {message_source!r}"
        )


@pytest.fixture(scope="module")
def user_cleanup(user):
    usernames = []
    yield usernames

    seen = set()
    cleanup_usernames = []
    for username in reversed(usernames):
        if username in seen:
            continue
        seen.add(username)
        cleanup_usernames.append(username)
    failures = []
    for username in cleanup_usernames:
        try:
            if not user.ensure_user_absent(username):
                failures.append(username)
        except Exception as exc:
            failures.append(f"{username}: {type(exc).__name__}")
    allure.attach(json.dumps(failures, ensure_ascii=False), "未清理用户清单", allure.attachment_type.JSON)
    assert not failures, f"模块清理失败: {failures}"


@pytest.fixture
def managed_user(user, user_cleanup):
    stamp = time.time_ns() % 1000000000
    state = {
        # 4.39.7 limits user names more strictly than 4.39.8. Keep all
        # mutable fixture values below the shared limit while retaining a
        # per-run unique suffix.
        "username": f"uc_{stamp}",
        "cancel_nickname": f"cn_{stamp}",
        "modified_nickname": f"mn_{stamp}",
        "password": "uipass12",
    }

    with allure.step("用户管理模块前置：进入页面"):
        assert user.common_enter_user() is True
    with allure.step("用户管理模块前置：创建独立基准用户"):
        user_cleanup.append(state["username"])
        assert user.add_user(state["username"], state["password"], ADD_SUCCESS) is True

    try:
        yield state
    finally:
        assert user.ensure_user_absent(state['username']) is True, state['username']
        while state['username'] in user_cleanup:user_cleanup.remove(state['username'])


@pytest.fixture(scope="module")
def user_import_template(user):
    template = user.download_user_import_template()
    assert template is not None
    assert template.stat().st_size > 0
    return template


def test_enter_user(user):
    assert user.common_enter_user() is True


@pytest.mark.parametrize("params", analyze_data("add_user_success_data.json"))
def test_add_user_success(user, user_cleanup, params):
    stamp = time.time_ns() % 1000000000
    unique_name = f"{params['user_name']}_{stamp}"
    user_cleanup.append(unique_name)
    assert user.add_user(unique_name, params["user_password"], params["msg"]) is True


@pytest.mark.parametrize(
    "params", PHONE_COMPATIBILITY_CASES, ids=lambda item: item["scenario"]
)
def test_add_user_phone_segment_compatibility(user, user_cleanup, params):
    username = f"upa_{params['prefix']}_{time.time_ns() % 1000000000}"
    phone_number = _build_phone_number(params)
    user_cleanup.append(username)
    allure.dynamic.parameter("号段分类", params["category"])
    allure.dynamic.parameter("测试手机号", _masked_phone(phone_number))
    try:
        assert user.add_user(
            username, "uipass12", ADD_SUCCESS, phone_number=phone_number
        ) is True
        profile = user.read_user_profile(
            username, refresh=True, expected_phone=phone_number
        )
        _attach_phone_evidence(params, phone_number, profile, "新增用户")
        _assert_profile(profile, phone_number)
    finally:
        _cleanup_compatibility_user(
            user, user_cleanup, username, phone_number
        )




def test_add_duplicate_user_failed(user, user_cleanup):
    stamp = time.time_ns() % 1000000000
    duplicate_name = f"user_dup_{stamp}"
    password = "uipass12"
    user_cleanup.append(duplicate_name)
    assert user.add_user(duplicate_name, password, ADD_SUCCESS) is True
    result = user.add_duplicate_user_expect_failed(duplicate_name, password)
    assert_duplicate_blocked(result)

@pytest.mark.parametrize("params", analyze_data("add_user_failed_data.json"))
def test_add_user_failed(user, params):
    user.click_add_button()
    try:
        # Vue reuses the add-form component between parameterized cases. Write
        # a distinct valid baseline first so empty/same-value targets always
        # produce a real input transition and their own validation event.
        user.send_user_name("uiauto_validation_baseline")
        user.send_password("Baseline123!")
        user.send_user_name(params["user_name"])
        user.send_password(params["user_password"])
        user.send_phone_number(params["phone_number"])
        errors = user.wait_until(
            lambda: (
                current
                if params["name_msg"] in current.get(
                    "用户姓名", current.get("用户名", "")
                )
                and params["password_msg"] in current.get("密码", "")
                else False
            )
            if (current := user.visible_add_user_validation_errors())
            else False,
            timeout=3,
            poll_frequency=0.1,
        )
        assert errors is not False
        assert params["name_msg"] in errors.get("用户姓名", errors.get("用户名", ""))
        assert params["password_msg"] in errors.get("密码", "")
    finally:
        user.click_cancel_button()


@pytest.fixture
def user_pagination_data(user):
    with pagination_records(user,user.common_enter_user,
        lambda value:user.add_user(value,'uipass12',ADD_SUCCESS),user.ensure_user_absent,'UIU'):
        yield


def test_change_user_page_size(user,user_pagination_data):
    require_minimum_records(
        user,
        minimum_total=11,
        module_name="\u7528\u6237\u7ba1\u7406",
        scenario_name="\u5206\u9875\u76f8\u5173\u6d4b\u8bd5",
    )
    try:
        assert user.jump_to_result_page(1) is True
        assert user.set_result_page_size(10) is True
        assert "10" in (user.get_current_page_size_text() or "")
    finally:
        user.set_result_page_size(15)
        user.jump_to_result_page(1)


def test_jump_user_page(user,user_pagination_data):
    require_minimum_records(
        user,
        minimum_total=11,
        module_name="\u7528\u6237\u7ba1\u7406",
        scenario_name="\u5206\u9875\u76f8\u5173\u6d4b\u8bd5",
    )
    try:
        assert user.jump_to_result_page(1) is True
        assert user.set_result_page_size(10) is True
        first_page_summary = user.get_pagination_summary_text()
        assert user.jump_to_result_page(2) is True
        assert user.get_current_page_text() == "2"
        second_page_summary = user.get_pagination_summary_text()
        assert second_page_summary
        assert second_page_summary != first_page_summary
        assert user.jump_to_result_page(1) is True
        assert user.get_current_page_text() == "1"
    finally:
        user.set_result_page_size(15)
        user.jump_to_result_page(1)


def test_export_user(user):
    assert user.export_user() is True


def test_user_import_supports_overwrite(user):
    dialog = user.inspect_user_import_dialog()
    assert dialog is not None
    assert "覆盖" in dialog["text"]


def test_user_import_template_download(user_import_template):
    assert user_import_template.suffix.lower() in {".xlsx", ".xls"}
    assert user_import_template.stat().st_size > 0


def test_user_import_workbook_generated_from_template(user, user_import_template, tmp_path):
    from common.runtime_artifacts import build_import_workbook

    output = tmp_path / "user_import_runtime.xlsx"
    result = build_import_workbook(
        user_import_template,
        output,
        [{"用户名*": "runtime_user", "密码*": "Runtime@123", "所属部门*": user.current_import_organization_path()}],
    )
    assert result.exists() and result.stat().st_size > 0


def test_user_import_executes_new_and_overwrite_paths(
    user, user_cleanup, user_import_template, tmp_path
):
    from common.runtime_artifacts import build_import_workbook

    stamp = time.time_ns() % 1000000000
    username = f"uiauto_imp_{stamp}"
    user_cleanup.append(username)
    original_nickname=f'impA_{stamp}'
    updated_nickname=f'impB_{stamp}'
    organization=user.current_import_organization_path()
    workbook = build_import_workbook(
        user_import_template, tmp_path / "user_import.xlsx",
        [{"用户名*": username, "密码*": "uipass12",'昵称':original_nickname, "所属部门*":organization}],
    )
    assert user.import_user_workbook(workbook, overwrite=False) is True, user.last_import_error
    assert user.search_user(username) is True
    profile=user.read_user_profile(username,refresh=True,expected_nickname=original_nickname)
    assert profile and profile['nickname']==original_nickname
    workbook=build_import_workbook(user_import_template,tmp_path/'user_edit.xlsx',
        [{'用户名*':username,'密码*':'uipass12','昵称':updated_nickname,'所属部门*':organization}])
    unchanged=user.import_user_workbook(workbook,overwrite=False)
    assert unchanged or any(word in user.last_import_error for word in ('已存在','重复','不覆盖')),user.last_import_error
    profile=user.read_user_profile(username,refresh=True,expected_nickname=original_nickname)
    assert profile and profile['nickname']==original_nickname, '不覆盖导入改变了既有昵称'
    assert user.import_user_workbook(workbook, overwrite=True) is True, user.last_import_error
    assert user.search_user(username) is True
    profile=user.read_user_profile(username,refresh=True,expected_nickname=updated_nickname)
    assert profile and profile['nickname']==updated_nickname, '覆盖导入未真实更新昵称'


def test_user_export_download(user):
    exported = user.download_user_export()
    assert exported is not None
    assert exported.stat().st_size > 0


def test_batch_add_two_users_and_search(user):
    """Exercise the real batch-add dialog before any batch deletion test."""
    prefix = f"uiauto_batch_{time.time_ns() % 1000000000}_"
    try:
        assert user.add_user_in_batches(prefix, "2", "uipass12", ADD_SUCCESS) is True
        assert user.search_users_by_keyword(prefix) is True
    finally:
        # The generated prefix is exclusive to this test, so this cannot
        # remove a pre-existing account.
        assert user.delete_users_by_keyword(prefix, DELETE_SUCCESS) is True


def test_batch_delete_only_created_users(user, user_cleanup):
    prefix = f"user_batch_{time.time_ns() % 1000000000}_"
    assert user.add_user_in_batches(prefix, "2", "uipass12", ADD_SUCCESS) is True
    try:
        assert user.delete_users_by_keyword(prefix, DELETE_SUCCESS) is True
    finally:
        # The prefix is unique to this invocation, so cleanup cannot affect
        # pre-existing users even if the batch-delete assertion fails.
        user.delete_users_by_keyword(prefix, DELETE_SUCCESS)


def test_find_user(user, managed_user):
    assert user.search_user(managed_user["username"]) is True


def test_find_missing_user(user):
    assert user.search_user(f"missing_user_{time.time_ns()}") is False


def test_cancel_add_user(user,user_cleanup):
    name=f'uicU_{time.time_ns()%1000000000}'
    user_cleanup.append(name)
    user.click_add_button()
    user.send_user_name(name)
    user.send_password("AutoCancel123!")
    assert user.click_cancel_button() is True
    assert user.search_user(name) is False, '取消新增后仍产生了用户'
    user_cleanup.remove(name)


def test_cancel_modify_user(user, managed_user):
    assert user.cancel_modify_user(
        managed_user["username"],
        managed_user["cancel_nickname"],
    ) is True


def test_modify_user(user, managed_user):
    assert user.modify_user(
        managed_user["username"],
        managed_user["modified_nickname"],
    ) is True,getattr(user,'last_modify_debug',{})


@pytest.mark.parametrize(
    "params", PHONE_COMPATIBILITY_CASES, ids=lambda item: item["scenario"]
)
def test_modify_user_phone_segment_compatibility(user, user_cleanup, params):
    username = f"upm_{params['prefix']}_{time.time_ns() % 1000000000}"
    phone_number = _build_phone_number(params)
    safe_nickname = f"pn_{params['prefix']}_{time.time_ns() % 1000000}"
    user_cleanup.append(username)
    allure.dynamic.parameter("号段分类", params["category"])
    allure.dynamic.parameter("用户昵称", safe_nickname)
    allure.dynamic.parameter("测试手机号", _masked_phone(phone_number))
    try:
        assert user.add_user(username, "uipass12", ADD_SUCCESS) is True
        modified = user.modify_user(
            username, safe_nickname, phone_number=phone_number
        )
        allure.attach(
            json.dumps(
                getattr(user, "last_modify_debug", {}),
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            "修改用户过程诊断",
            allure.attachment_type.JSON,
        )
        assert modified is True, getattr(user, "last_modify_debug", {})
        profile = user.read_user_profile(
            username,
            refresh=True,
            expected_phone=phone_number,
            expected_nickname=safe_nickname,
        )
        _attach_phone_evidence(params, phone_number, profile, "修改用户")
        _assert_profile(profile, phone_number, nickname=safe_nickname)
    finally:
        _cleanup_compatibility_user(
            user, user_cleanup, username, phone_number
        )


def test_modify_user_nickname_middle_dot_compatibility(user, user_cleanup):
    username = f"upn_{time.time_ns() % 1000000000}"
    phone_number = "15515873759"
    user_cleanup.append(username)
    allure.dynamic.parameter("用户昵称", SPECIAL_NICKNAME)
    allure.dynamic.parameter("测试手机号", _masked_phone(phone_number))
    try:
        assert user.add_user(username, "uipass12", ADD_SUCCESS) is True
        modified = user.modify_user(
            username, SPECIAL_NICKNAME, phone_number=phone_number
        )
        allure.attach(
            json.dumps(
                getattr(user, "last_modify_debug", {}),
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            "特殊昵称修改诊断",
            allure.attachment_type.JSON,
        )
        assert modified is True, getattr(user, "last_modify_debug", {})
        profile = user.read_user_profile(
            username,
            refresh=True,
            expected_phone=phone_number,
            expected_nickname=SPECIAL_NICKNAME,
        )
        _assert_profile(
            profile,
            phone_number,
            nickname=SPECIAL_NICKNAME,
            require_middle_dot=True,
        )
    finally:
        _cleanup_compatibility_user(
            user, user_cleanup, username, phone_number
        )


def test_delete_user(user, managed_user, user_cleanup):
    assert user.delete_user(managed_user["username"], DELETE_SUCCESS) is True
    if managed_user["username"] in user_cleanup:
        user_cleanup.remove(managed_user["username"])

