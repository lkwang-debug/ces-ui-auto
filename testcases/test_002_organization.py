# -*- coding:utf-8 -*-
import time
import json
import allure

import pytest

from common.base_analyze import analyze_data
from common.test_preconditions import require_minimum_records,pagination_records


ADD_SUCCESS = "\u64cd\u4f5c\u6210\u529f"
DELETE_SUCCESS = "\u5220\u9664\u6210\u529f"


def assert_duplicate_blocked(result):
    assert result.get("blocked") is True
    assert isinstance(result.get('before_count'),int) and result['before_count'] > 0
    assert result.get('after_count') == result['before_count']

SUCCESS_CASES = [
    params
    for params in analyze_data("add_success_organization_data.json")
    if params.get("msg") == ADD_SUCCESS
]

@pytest.fixture(scope="module")
def organize_cleanup(organize):
    names = []
    yield names

    seen = set()
    cleanup_names = []
    for name in reversed(names):
        if name in seen:
            continue
        seen.add(name)
        cleanup_names.append(name)
    allure.attach(json.dumps({"登记记录": cleanup_names}, ensure_ascii=False, indent=2), "组织清理登记", allure.attachment_type.JSON)
    completed = []
    try:
        for name in cleanup_names:
            absent = organize.ensure_organize_absent(name, allow_global_fallback=False)
            completed.append({"部门名称": name, "清理成功": absent})
            assert absent is True, name
    finally:
        allure.attach(json.dumps({"清理结果": completed, "待处理记录": cleanup_names[len(completed):]}, ensure_ascii=False, indent=2),
                      "组织清理结果", allure.attachment_type.JSON)


@pytest.fixture
def managed_organize(organize, organize_cleanup):
    stamp = time.time_ns() % 1000000000
    state = {
        "name": f"org_{stamp}",
        "cancel_name": f"org_cancel_{stamp}",
        "modified_name": f"org_mod_{stamp}",
        "describe": f"auto_desc_{stamp}",
    }

    organize_cleanup.append(state["name"])
    created = organize.add_organize(
        state["name"], state["describe"], ADD_SUCCESS
    )
    persisted = organize.search_organize(state["name"])
    if not created or not persisted:
        organize._enter_organize_via_route()
        organize.driver.refresh()
        organize.wait_for_document_ready(timeout=5)
        organize._ensure_organize_page_ready()
        if not organize.search_organize(state["name"]):
            created = organize.add_organize(
                state["name"], state["describe"], ADD_SUCCESS
            )
        persisted = organize.search_organize(state["name"])
    assert created is True and persisted is True

    try:
        yield state
    finally:
        for name in dict.fromkeys([state['name'],state['modified_name']]):
            assert organize.ensure_organize_absent(name,allow_global_fallback=False) is True, name
            while name in organize_cleanup:organize_cleanup.remove(name)


def test_enter_organize(organize):
    assert organize.common_enter_organize() is True


@pytest.mark.parametrize("params", SUCCESS_CASES)
def test_add_success_organize(organize, organize_cleanup, params):
    unique_name = f"{params['organize_name']}_{time.time_ns() % 1000000000}"
    organize_cleanup.append(unique_name)
    assert organize.add_organize(
        unique_name, params["organize_describe"], params["msg"]
    ) is True




def test_add_duplicate_organize_failed(organize, organize_cleanup):
    stamp = time.time_ns() % 1000000000
    duplicate_name = f"org_dup_{stamp}"
    describe = f"auto_desc_{stamp}"
    organize_cleanup.append(duplicate_name)
    assert organize.add_organize(duplicate_name, describe, ADD_SUCCESS) is True
    result = organize.add_duplicate_organize_expect_failed(
        duplicate_name,
        f"{describe}_again",
    )
    assert_duplicate_blocked(result)

@pytest.mark.parametrize("params", analyze_data("organization_data.json"))
def test_add_failed_organize(organize, params):
    organize.click_new_add()
    organize.send_organize_name(params["organize_name"])
    organize.send_organize_describe(params["organize_describe"])
    assert organize.wait_visible(organize.wrong_organize_name_msg, timeout=10) is not False
    msg = organize.get_wrong_organize_name_msg()
    assert params["msg"] in msg
    assert organize.click_cancel_button() is True


def test_find_organize(organize, managed_organize):
    assert organize.search_organize(managed_organize["name"]) is True


def test_find_missing_organize(organize):
    assert organize.search_organize(f"missing_org_{time.time_ns()}") is False


def test_cancel_add_organize(organize,organize_cleanup):
    name=f'uicO_{time.time_ns()%1000000000}'
    organize_cleanup.append(name)
    organize.click_new_add()
    organize.send_organize_name(name)
    assert organize.click_cancel_button() is True
    assert organize.search_organize(name) is False, '取消新增后仍产生了组织'
    organize_cleanup.remove(name)


@pytest.fixture
def organize_pagination_data(organize):
    with pagination_records(organize,organize.common_enter_organize,
        lambda value:organize.add_organize(value,'分页独立数据',ADD_SUCCESS),
        lambda value:organize.ensure_organize_absent(value,allow_global_fallback=False),'UIO'):
        yield


def test_change_organize_page_size(organize,organize_pagination_data):
    require_minimum_records(
        organize,
        minimum_total=11,
        module_name="缁勭粐绠＄悊",
        scenario_name="鍒嗛〉鐩稿叧娴嬭瘯",
    )
    try:
        assert organize.jump_to_result_page(1) is True
        assert organize.set_result_page_size(10) is True
        assert "10" in (organize.get_current_page_size_text() or "")
    finally:
        organize.set_result_page_size(15)
        organize.jump_to_result_page(1)


def test_jump_organize_page(organize,organize_pagination_data):
    require_minimum_records(
        organize,
        minimum_total=11,
        module_name="缁勭粐绠＄悊",
        scenario_name="鍒嗛〉鐩稿叧娴嬭瘯",
    )
    try:
        assert organize.jump_to_result_page(1) is True
        assert organize.set_result_page_size(10) is True
        first_page_summary = organize.get_pagination_summary_text()
        assert organize.jump_to_result_page(2) is True
        assert organize.get_current_page_text() == "2"
        second_page_summary = organize.get_pagination_summary_text()
        assert second_page_summary
        assert second_page_summary != first_page_summary
        assert organize.jump_to_result_page(1) is True
        assert organize.get_current_page_text() == "1"
    finally:
        organize.set_result_page_size(15)
        organize.jump_to_result_page(1)


def test_cancel_modify_organize(organize, managed_organize):
    assert organize.cancel_modify_organize(
        managed_organize["name"], managed_organize["cancel_name"]
    ) is True


def test_modify_organize(organize, managed_organize, organize_cleanup):
    old_name = managed_organize["name"]
    organize_cleanup.append(managed_organize['modified_name'])
    assert organize.modify_organize(
        old_name, managed_organize["modified_name"]
    ) is True
    managed_organize["name"] = managed_organize["modified_name"]
    if old_name in organize_cleanup:
        organize_cleanup.remove(old_name)
    organize_cleanup.append(managed_organize["name"])


def test_delete_organize(organize, managed_organize, organize_cleanup):
    assert organize.delete_organize(managed_organize["name"], DELETE_SUCCESS) is True
    if managed_organize["name"] in organize_cleanup:
        organize_cleanup.remove(managed_organize["name"])

