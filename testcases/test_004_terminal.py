# -*- coding:utf-8 -*-
import time

import allure
import pytest
from conf.conf import ConfigManager


ADD_SUCCESS = "\u65b0\u5efa\u6210\u529f"
DELETE_SUCCESS = "\u5220\u9664\u6210\u529f"
SEARCH_FIELD_SERIAL = "\u7ec8\u7aef\u5e8f\u5217\u53f7"
TERMINAL_TYPE_SELF_OWNED = "\u81ea\u6709\u8bbe\u5907"
def assert_duplicate_blocked(result):
    assert result.get("blocked") is True
    assert isinstance(result.get('before_count'),int) and result['before_count'] > 0
    assert result.get('after_count') == result['before_count']


@pytest.fixture(scope="module")
def terminal_cleanup(terminal):
    names = []
    yield names

    seen = set()
    cleanup_names = []
    for name in reversed(names):
        if name in seen:
            continue
        seen.add(name)
        cleanup_names.append(name)
    failed = [name for name in cleanup_names if not terminal.ensure_terminal_absent(name)]
    allure.attach(str(failed), "终端清理失败清单", allure.attachment_type.TEXT)
    assert not failed, f"终端清理失败: {failed}"


@pytest.fixture
def managed_terminal(terminal, terminal_cleanup):
    stamp = time.time_ns() % 1000000000
    state = {
        "name": f"terminal_{stamp}",
        "serial": f"T{stamp}",
        "cancel_name": f"terminal_cancel_{stamp}",
        "modified_name": f"terminal_mod_{stamp}",
    }

    with allure.step("终端管理模块前置：创建独立基准终端"):
        terminal_cleanup.append(state["name"])
        assert terminal.add_terminal(state["name"], state["serial"], ADD_SUCCESS) is True

    try:
        yield state
    finally:
        for name in dict.fromkeys([state['name'],state['modified_name']]):
            assert terminal.ensure_terminal_absent(name) is True, name
            while name in terminal_cleanup:terminal_cleanup.remove(name)


@pytest.fixture(scope="module")
def terminal_import_template(terminal):
    template = terminal.download_terminal_import_template()
    assert template is not None
    assert template.stat().st_size > 0
    return template


def test_enter_terminal(terminal):
    assert terminal.common_enter_terminal() is True


def test_add_terminal_success(terminal, terminal_cleanup):
    stamp = time.time_ns() % 1000000000
    unique_name = f"terminal_add_{stamp}"
    unique_serial = f"TS{stamp}"
    terminal_cleanup.append(unique_name)
    assert terminal.add_terminal(unique_name, unique_serial, ADD_SUCCESS) is True


def test_terminal_import_supports_overwrite(terminal):
    dialog = terminal.inspect_terminal_import_dialog()
    assert dialog is not None
    assert "覆盖" in dialog["text"]


def test_terminal_import_template_download(terminal_import_template):
    assert terminal_import_template.suffix.lower() in {".xlsx", ".xls"}
    assert terminal_import_template.stat().st_size > 0


def test_terminal_import_workbook_generated_from_template(
    terminal, terminal_import_template, tmp_path
):
    from common.runtime_artifacts import build_import_workbook

    output = tmp_path / "terminal_import_runtime.xlsx"
    result = build_import_workbook(
        terminal_import_template,
        output,
        [{
            "终端名称（必填）": "runtime_terminal",
            "终端序列号（必填）": "RUNTIME0001",
            "所属部门（必填）": ConfigManager.IMPORT_ORGANIZATION_PATH,
            "设备类型": TERMINAL_TYPE_SELF_OWNED,
        }],
    )
    assert result.exists() and result.stat().st_size > 0



def test_terminal_export_download(terminal):
    exported = terminal.download_terminal_export()
    assert exported is not None
    assert exported.stat().st_size > 0


def test_batch_delete_only_created_terminals(terminal, terminal_cleanup):
    stamp = time.time_ns() % 1000000000
    prefix = f"terminal_batch_{stamp}_"
    names = [f"{prefix}01", f"{prefix}02"]
    terminal_cleanup.extend(names)
    for index, name in enumerate(names, 1):
        assert terminal.add_terminal(name, f"TB{stamp}{index}", ADD_SUCCESS) is True
    assert terminal.delete_terminals_by_keyword(prefix, DELETE_SUCCESS) is True
    for name in names:
        if name in terminal_cleanup:
            terminal_cleanup.remove(name)




def test_add_duplicate_terminal_name_allowed(terminal, terminal_cleanup):
    stamp = time.time_ns() % 1000000000
    duplicate_name = f"terminal_same_name_{stamp}"
    serial_one = f"TDN{stamp}A"
    serial_two = f"TDN{stamp}B"
    terminal_cleanup.append(duplicate_name)
    assert terminal.add_terminal(duplicate_name, serial_one, ADD_SUCCESS) is True
    # The toast can disappear before Selenium observes it. Verify persisted
    # records by their unique serial numbers instead of relying on that toast.
    terminal.add_terminal(duplicate_name, serial_two, ADD_SUCCESS)
    assert terminal.search_terminal(serial_one, search_field=SEARCH_FIELD_SERIAL) is True
    assert terminal.search_terminal(serial_two, search_field=SEARCH_FIELD_SERIAL) is True


def test_add_duplicate_terminal_serial_failed(terminal, terminal_cleanup):
    stamp = time.time_ns() % 1000000000
    first_name = f"terminal_serial_src_{stamp}"
    second_name = f"terminal_serial_dup_{stamp}"
    duplicate_serial = f"TDS{stamp}"
    terminal_cleanup.append(first_name)
    assert terminal.add_terminal(first_name, duplicate_serial, ADD_SUCCESS) is True
    result = terminal.add_duplicate_terminal_serial_expect_failed(
        second_name,
        duplicate_serial,
    )
    assert_duplicate_blocked(result)
    assert terminal.search_terminal(duplicate_serial, search_field=SEARCH_FIELD_SERIAL) is True

def test_find_terminal(terminal, managed_terminal):
    assert terminal.search_terminal(managed_terminal["name"]) is True


def test_find_missing_terminal(terminal):
    assert terminal.search_terminal(f"missing_terminal_{time.time_ns()}") is False


def test_cancel_add_terminal(terminal,terminal_cleanup):
    stamp=time.time_ns()%1000000000
    name=f'uicT_{stamp}'
    terminal_cleanup.append(name)
    terminal.click_new_add()
    terminal.send_terminal_name(name)
    terminal.send_terminal_number(f'CT{stamp}')
    assert terminal.click_cancel_button() is True
    assert terminal.search_terminal(name) is False, '取消新增后仍产生了终端'
    terminal_cleanup.remove(name)


def test_find_terminal_by_serial_dropdown(terminal, managed_terminal):
    assert terminal.search_terminal(
        managed_terminal["serial"],
        search_field=SEARCH_FIELD_SERIAL,
    ) is True


def test_filter_terminal_by_type_dropdown(terminal, managed_terminal):
    assert terminal.search_terminal(
        managed_terminal["name"],
        terminal_type=TERMINAL_TYPE_SELF_OWNED,
    ) is True


def test_find_terminal_by_serial_and_type_dropdowns(terminal, managed_terminal):
    assert terminal.search_terminal(
        managed_terminal["serial"],
        search_field=SEARCH_FIELD_SERIAL,
        terminal_type=TERMINAL_TYPE_SELF_OWNED,
    ) is True


def test_terminal_page_size_options(terminal):
    """Verify actual pagination controls without claiming an unsupported save action."""
    options = terminal.get_available_page_sizes()
    assert {10, 15}.issubset(set(options))


def test_cancel_modify_terminal(terminal, managed_terminal):
    assert terminal.cancel_modify_terminal(
        managed_terminal["name"],
        managed_terminal["cancel_name"],
    ) is True


def test_modify_terminal(terminal, managed_terminal, terminal_cleanup):
    old_name = managed_terminal["name"]
    terminal_cleanup.append(managed_terminal['modified_name'])
    assert terminal.modify_terminal(
        old_name,
        managed_terminal["modified_name"],
    ) is True
    managed_terminal["name"] = managed_terminal["modified_name"]
    if old_name in terminal_cleanup:
        terminal_cleanup.remove(old_name)
    terminal_cleanup.append(managed_terminal["name"])


def test_delete_terminal(terminal, managed_terminal, terminal_cleanup):
    assert terminal.delete_terminal(
        managed_terminal["name"],
        DELETE_SUCCESS,
    ) is True
    if managed_terminal["name"] in terminal_cleanup:
        terminal_cleanup.remove(managed_terminal["name"])

