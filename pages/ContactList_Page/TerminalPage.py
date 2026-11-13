# -*- coding:utf-8 -*-
import re
import time
import json
import allure
from pathlib import Path
from common.runtime_artifacts import clean_directory, wait_for_download, prepare_download
from conf.conf import ConfigManager

from selenium.webdriver.common.by import By as by
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import StaleElementReferenceException, ElementNotInteractableException, ElementClickInterceptedException

from pages.Index_Page.index import LoginPage
from common.ui_state import click_toolbar_search, wait_query_finished, wait_stable_state,wait_page_layout,wait_control_unobscured
from common.operation_metrics import timed_operation
from common.semantic_controls import exact_table_row


class TerminalManagerPage(LoginPage):
    """Terminal management page object."""

    terminal_route = "#/ui/organizational-management/terminal-management"

    # 侧边栏
    contactlist_button_text = (
        by.XPATH,
        "//aside//span[contains(@class,'title-text') and normalize-space()='通讯录']"
        "/ancestor::div[contains(@class,'ant-menu-submenu-title')][1]",
    )
    terminal_button_text = (
        by.XPATH,
        "//aside//li[contains(@class,'ant-menu-item')]"
        "[.//span[normalize-space()='终端管理']]",
    )
    sidebar_menu_root = (by.CSS_SELECTOR, "aside ul.ant-menu")
    sidebar_expand_button = (by.CSS_SELECTOR, "aside .trigger.anticon-menu-unfold")

    # 页面主元素
    locate_search = (by.CSS_SELECTOR, "main input.ant-input")
    search_button = (
        by.XPATH,
        "//main//input[contains(@class,'ant-input')]/following::button[1]",
    )
    clear_button_text = (by.XPATH, "//main//button[normalize-space()='清空' or contains(normalize-space(.),'清空')]")
    import_button_text = (
        by.XPATH,
        "//main//button[normalize-space()='批量导入' or contains(normalize-space(.),'批量导入')]",
    )
    export_button_text = (
        by.XPATH,
        "//main//button[normalize-space()='导出']",
    )
    new_add_text = (by.XPATH, "//main//button[normalize-space()='新增' or contains(normalize-space(.),'新增')]")
    delete_button_text = (by.XPATH, "//main//button[normalize-space()='删除' or contains(normalize-space(.),'删除')]")
    select_all_terminal = (
        by.XPATH,
        "//main//table//thead//th[1]//span[contains(@class,'ant-checkbox')]",
    )
    save_result = (
        by.XPATH,
        "//div[contains(@class,'ant-message-notice-content')]"
        "//div[contains(@class,'ant-message-custom-content')]//*[normalize-space()]",
    )
    delete_sure_button_text = (
        by.CSS_SELECTOR,
        ".ant-modal-confirm .ant-modal-confirm-btns .ant-btn-primary,"
        ".ant-confirm .ant-modal-confirm-btns .ant-btn-primary",
    )
    page_size_value = (
        by.CSS_SELECTOR,
        ".ant-pagination-options-size-changer .ant-select-selection-selected-value,"
        ".ant-pagination-options-size-changer .ant-select-selection-item",
    )
    page_size_changer = (
        by.CSS_SELECTOR,
        ".ant-pagination-options-size-changer",
    )
    data_num = (by.CSS_SELECTOR, ".pagination-box>div:nth-child(2)>span")
    terminal_type_select = (
        by.XPATH,
        "//main//*[contains(concat(' ',normalize-space(@class),' '),' search-box ')]"
        "[./*[normalize-space()='终端类型']]//*[contains(concat(' ',normalize-space(@class),' '),' ant-select ')]",
    )
    search_field_select = (
        by.XPATH,
        "//main//*[contains(concat(' ',normalize-space(@class),' '),' search-box ')]"
        "[.//input[contains(@placeholder,'搜索')]]//*[contains(concat(' ',normalize-space(@class),' '),' ant-select ')]",
    )
    search_field_default = "终端名称"
    terminal_type_self_owned = "自有设备"

    # 寮圭獥
    add_modal_title = "新增"
    modify_modal_title = "修改"
    terminal_name_label = "终端名称"
    terminal_serial_label = "终端序列号"
    terminal_position_label = "缁堢浣嶇疆"
    auth_code_label = "授权码"
    log_level_label = "鏃ュ織绛夌骇"
    save_button_text = "保存"
    close_button_text = "关闭"

    @timed_operation
    def common_enter_terminal(self):
        """Enter terminal management page."""
        self.common_login()
        self.dismiss_intro_if_present()
        self._dismiss_blocking_layers()

        ready_locators = self._terminal_page_identity_locators()
        if self.ensure_page_ready_fast(self.terminal_route, ready_locators):
            return True

        for _ in range(2):
            self._enter_terminal_via_route()
            if self._is_on_terminal_page() and self._visible_in_any(ready_locators, timeout=6):
                return True
            if self._enter_terminal_via_sidebar(timeout=4):
                if self._is_on_terminal_page() and self._visible_in_any(ready_locators, timeout=6):
                    return True

        raise AssertionError("Failed to enter terminal management page")

    def inspect_terminal_import_dialog(self):
        self._ensure_terminal_page_ready()
        if not self._click_first_available_safe([self.import_button_text], timeout=5):
            return None
        modal = self._active_modal_content(timeout=8)
        if modal is None:
            return None
        result = {
            "text": " ".join((modal.text or "").split()),
            "accept": ",".join(
                element.get_attribute("accept") or ""
                for element in modal.find_elements(by.CSS_SELECTOR, "input[type='file']")
            ),
        }
        self.click_cancel_button()
        return result

    @timed_operation
    def download_terminal_import_template(self):
        self._ensure_terminal_page_ready()
        directory = prepare_download(self.driver)
        if not self._click_first_available_safe([self.import_button_text], timeout=5):
            return None
        if self._active_modal_content(timeout=8) is None:
            return None
        link = (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]//*[normalize-space()='下载模板']",
        )
        if not self._click_first_available_safe([link], timeout=5):
            self.click_cancel_button()
            return None
        downloaded = wait_for_download(directory, extensions={".xlsx", ".xls"}, driver=self.driver)
        self.click_cancel_button()
        if downloaded is None:
            return None
        target_dir = Path(ConfigManager.IMPORT_TEMPLATE_DIR)/'terminal'
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / downloaded.name
        downloaded.replace(target)
        return target

    def import_terminal_workbook(self, workbook, overwrite=False, timeout=10):
        self.last_import_error = ""
        self._ensure_terminal_page_ready()
        if not self._click_first_available_safe([self.import_button_text], timeout=5):
            self.last_import_error = "未找到终端批量导入按钮"
            return False
        modal_locator = (by.CSS_SELECTOR, ".ant-modal-content")
        if not self._visible_in_any([modal_locator], timeout=12):
            self.last_import_error = "终端批量导入弹窗未出现"
            return False
        modal = next(
            (item for item in self.driver.find_elements(*modal_locator) if item.is_displayed()),
            None,
        )
        if modal is None:
            self.last_import_error = "终端批量导入弹窗不可见"
            return False
        try:
            modal.find_element(by.CSS_SELECTOR, "input[type='file']").send_keys(str(Path(workbook).resolve()))
            modal = next(
                (item for item in self.driver.find_elements(*modal_locator) if item.is_displayed()),
                None,
            )
            if modal is None:
                return False
            select = modal.find_element(by.CSS_SELECTOR, ".ant-select")
            trigger = select.find_element(by.CSS_SELECTOR, ".ant-select-selection, .ant-select-selector")
            try:
                trigger.click()
            except Exception:
                self.driver.execute_script("arguments[0].click()", trigger)
            option_text = "是" if overwrite else "否"
            option = (
                by.XPATH,
                "//div[contains(@class,'ant-select-dropdown') and not(contains(@style,'display: none'))]"
                f"//li[normalize-space()='{option_text}'] | "
                "//div[contains(@class,'ant-select-dropdown') and not(contains(@style,'display: none'))]"
                f"//*[normalize-space()='{option_text}']",
            )
            if not self._click_first_available_safe([option], timeout=4):
                self.last_import_error = f"未找到覆盖选项: {option_text}"
                return False
            # Ant Design keeps the option popup above the modal footer until
            # it receives Escape; otherwise the Import button cannot be hit.
            self.driver.find_element(by.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            # Choosing an option re-renders the upload modal in 4.39.7.
            modal = next(
                (item for item in self.driver.find_elements(*modal_locator) if item.is_displayed()),
                None,
            )
            if modal is None:
                self.last_import_error = "选择覆盖选项后弹窗消失"
                return False
            primary = next(
                (
                    item
                    for item in modal.find_elements(by.CSS_SELECTOR, "button")
                    if item.is_displayed() and "关闭" not in (item.text or "") and "取消" not in (item.text or "")
                ),
                None,
            )
            if primary is None:
                self.last_import_error = "未找到导入确认按钮"
                return False
            self.driver.execute_script("arguments[0].click()", primary)
            message = self._latest_operation_message(timeout=timeout)
            imported = any(word in message for word in ("成功", "success", "Success"))
            if not imported:
                visible_modal = next(
                    (item for item in self.driver.find_elements(*modal_locator) if item.is_displayed()),
                    None,
                )
                modal_text = visible_modal.text if visible_modal is not None else ""
                self.last_import_error = f"导入未成功，后台提示: {message!r}；弹窗内容: {modal_text!r}"
            return imported
        except Exception as exc:
            self.last_import_error = f"导入交互异常: {type(exc).__name__}: {exc}"
            return False

    @timed_operation
    def download_terminal_export(self):
        self._ensure_terminal_page_ready()
        directory = prepare_download(self.driver)
        existing = {path.name for path in directory.iterdir()}
        if not self._click_first_available_safe([self.export_button_text], timeout=5):
            return None
        return wait_for_download(directory, existing, {".xlsx", ".xls", ".csv"}, driver=self.driver)

    def wait_for_operation_result(self, expected_text=None, timeout=20):
        if expected_text:
            return self.wait_text_contains(self.save_result, expected_text, timeout=timeout)
        return self.wait_visible(self.save_result, timeout=timeout) is not False

    def click_new_add(self):
        self._ensure_terminal_page_ready()
        for _ in range(3):
            self._dismiss_blocking_layers()
            if self._add_terminal_dialog_visible(timeout=1.5):
                return True
            if self._click_first_available_safe([self.new_add_text], timeout=5):
                if self._add_terminal_dialog_visible(timeout=8):
                    return True
            self._enter_terminal_via_route()
            self.driver.refresh()
            self.wait_for_document_ready(timeout=5)
            self.dismiss_intro_if_present()
            self._dismiss_blocking_layers()
            self._ensure_terminal_page_ready()
        raise AssertionError("Add terminal dialog did not appear")
        return True

    def send_terminal_name(self, terminal_name):
        return self._replace_visible_modal_input("终端名称", terminal_name, timeout=10)

    def send_terminal_number(self, terminal_number):
        return self._replace_visible_modal_input("终端序列号", terminal_number, timeout=10)

    def click_save_button(self):
        if not self._click_visible_modal_button(primary=True, timeout=3):
            raise AssertionError("Failed to click add terminal save button")
        return True

    def click_cancel_button(self):
        return self._click_visible_modal_button(primary=False, timeout=3)

    @timed_operation
    def add_terminal(self, terminal_name, terminal_number, result="鏂板缓鎴愬姛"):
        self._ensure_terminal_page_ready()
        self.click_new_add()
        if not self.send_terminal_name(terminal_name):
            self.click_cancel_button()
            return False
        if not self.send_terminal_number(terminal_number):
            self.click_cancel_button()
            return False
        self.click_save_button()
        if not self._wait_for_visible_modal_closed(timeout=8):
            self.click_cancel_button()
            return False
        # A toast/closed form is not persistence evidence. Query the unique
        # serial and require both fields in the same completed result row.
        if not self._select_search_field(self.terminal_serial_label, timeout=3):
            return False
        if not self._search_keyword(terminal_number):
            return False
        row = self.find_visible_now(self._exact_terminal_serial_row_locator(terminal_number))
        persisted = row is not False and terminal_name in row.text
        self._restore_list_state()
        return persisted

    def _latest_operation_message(self, timeout=8):
        end = time.time() + timeout
        latest_text = ""
        while time.time() < end:
            for element in self.driver.find_elements(*self.save_result):
                try:
                    text = element.text.strip()
                    if text:
                        latest_text = text
                    if element.is_displayed() and text:
                        return text
                except Exception:
                    continue
            time.sleep(0.2)
        return latest_text

    def add_duplicate_terminal_expect_failed(self, terminal_name, terminal_number):
        self._ensure_terminal_page_ready()
        self._restore_list_state()
        before_count = self.count_terminal_by_search(
            terminal_number,
            search_field=self.terminal_serial_label,
            timeout=1.5,
            restore=False,
        )
        if before_count == 0:
            self.driver.refresh()
            self.wait_for_document_ready(timeout=5)
            self._ensure_terminal_page_ready()
            before_count = self.count_terminal_by_search(
                terminal_number,
                search_field=self.terminal_serial_label,
                timeout=2,
                restore=False,
            )
        if before_count == 0:
            return {
                "blocked": False,
                "message": "重复校验前未查询到序列号源记录",
                "before_count": 0,
                "after_count": 0,
            }
        self.click_new_add()
        if not self.send_terminal_name(terminal_name):
            self.click_cancel_button()
            return {"blocked": False, "message": "", "before_count": before_count, "after_count": before_count}
        if not self.send_terminal_number(terminal_number):
            self.click_cancel_button()
            return {"blocked": False, "message": "", "before_count": before_count, "after_count": before_count}
        self.click_save_button()
        message = self._latest_operation_message(timeout=2) or ""
        self.click_cancel_button()
        after_count = self.count_terminal_by_search(
            terminal_number,
            search_field=self.terminal_serial_label,
            timeout=1.5,
            restore=False,
        )
        created_name_count = self.count_terminal_by_search(
            terminal_name,
            timeout=0.8,
            restore=True,
        )
        count_unchanged = after_count == before_count and created_name_count == 0
        return {
            "blocked": count_unchanged,
            "message": message,
            "before_count": before_count,
            "after_count": after_count,
        }

    def add_duplicate_terminal_serial_expect_failed(self, terminal_name, terminal_number):
        return self.add_duplicate_terminal_expect_failed(terminal_name, terminal_number)

    @timed_operation
    def search_terminal(self, terminal_name, search_field=None, terminal_type=None):
        self._ensure_terminal_page_ready()
        found = self._search_terminal_with_filters(
            keyword=terminal_name,
            search_field=search_field or self.search_field_default,
            terminal_type=terminal_type,
        )
        self._restore_list_state()
        return found

    def cancel_modify_terminal(self, old_name, new_name):
        self._ensure_terminal_page_ready()
        if not self._open_terminal_editor(old_name):
            self._restore_list_state()
            return False
        if not self._replace_visible_modal_input(self.terminal_name_label, new_name, timeout=8):
            self._click_visible_modal_button(primary=False, timeout=3)
            self._restore_list_state()
            return False
        if not self._click_visible_modal_button(primary=False, timeout=5):
            self._restore_list_state()
            return False
        result = self.wait_until(
            lambda: self._find_exact_terminal_row_via_search(old_name),
            timeout=3,
        )
        unchanged = result is not False and not self._find_exact_terminal_row_via_search(new_name)
        self._restore_list_state()
        return unchanged

    @timed_operation
    def modify_terminal(self, old_name, new_name, result="淇敼鎴愬姛"):
        self.last_terminal_edit_debug = {"old_name": old_name, "new_name": new_name, "stage": "page_ready"}
        self._ensure_terminal_page_ready()
        if old_name != new_name and not self.ensure_terminal_absent(new_name):
            return False
        if not self._open_terminal_editor(old_name):
            self._restore_list_state()
            return False
        if not self._replace_visible_modal_input(self.terminal_name_label, new_name, timeout=8):
            self._record_terminal_edit_failure("name_not_committed")
            self._click_visible_modal_button(primary=False, timeout=3)
            self._restore_list_state()
            return False
        if not self._click_visible_modal_button(primary=True, timeout=5):
            self._record_terminal_edit_failure("save_not_clicked")
            self._click_visible_modal_button(primary=False, timeout=3)
            self._restore_list_state()
            return False
        evidence = self.wait_operation_evidence(
            [
                ("toast", lambda: result in self._first_visible_text(self.save_result)),
                (
                    "modal_closed",
                    lambda: self.find_visible_now(
                        (by.CSS_SELECTOR, ".ant-modal-content")
                    ) is False,
                ),
            ],
            timeout=4,
        )
        if evidence and self.wait_modal_state(False, timeout=3):
            self.driver.refresh()
            self._ensure_terminal_page_ready()
        persisted = self._find_exact_terminal_row_via_search(new_name, timeout=1)
        if not persisted:
            self._record_terminal_edit_failure("persisted_name_not_found")
        if not persisted and not evidence:
            self._click_visible_modal_button(primary=False, timeout=3)
            self._restore_list_state()
            return False
        self._restore_list_state()
        return persisted

    def _record_terminal_edit_failure(self, stage):
        debug = getattr(self, "last_terminal_edit_debug", {})
        debug["stage"] = stage
        debug["table"] = self.table_snapshot()
        debug["modal"] = self.driver.execute_script("""
          return [...document.querySelectorAll('.ant-modal-content')].filter(e=>e.offsetWidth||e.offsetHeight)
            .map(e=>({text:e.innerText,fields:[...e.querySelectorAll('input')].map(i=>({placeholder:i.placeholder,value:i.value}))}));
        """)
        self.last_terminal_edit_debug = debug
        allure.attach(json.dumps(debug, ensure_ascii=False, indent=2), "终端修改失败阶段", allure.attachment_type.JSON)
        allure.attach(self.driver.get_screenshot_as_png(), "终端修改清理前现场", allure.attachment_type.PNG)

    def _open_terminal_editor(self, old_name):
        self.last_terminal_edit_debug = {"old_name": old_name, "stage": "locate_source"}
        if not self._find_exact_terminal_row_via_search(old_name):
            self._record_terminal_edit_failure("source_row_not_found")
            return False
        row = exact_table_row(self.driver, "终端名称", old_name)
        serial = self.driver.execute_script("""
            const row=arguments[0],main=document.querySelector('main');
            const header=[...main.querySelectorAll('thead tr')].find(e=>(e.offsetWidth||e.offsetHeight)&&e.querySelectorAll('th').length>1);
            const index=[...(header?.querySelectorAll('th')||[])].findIndex(e=>(e.innerText||'').trim()==='终端序列号');
            return index>=0 ? (row.querySelectorAll('td')[index]?.innerText||'').trim() : null;
        """, row)
        if not serial:
            self._record_terminal_edit_failure("source_serial_not_found")
            return False
        self.last_terminal_edit_debug["serial"] = serial
        if not self._click_first_available_safe([self._exact_terminal_modify_button_locator(old_name)], timeout=6):
            self._record_terminal_edit_failure("modify_not_clicked")
            return False
        def hydrated():
            name_field = self._visible_modal_input(self.terminal_name_label)
            serial_field = self._visible_modal_input("终端序列号")
            if name_field is False or serial_field is False:
                return False
            if (name_field.get_attribute("value") or "") != old_name or (serial_field.get_attribute("value") or "") != serial:
                return False
            return {"name": old_name, "serial": serial}
        if wait_stable_state(self, hydrated, timeout=6, stable_for=0.3) is False:
            self._record_terminal_edit_failure("original_fields_not_loaded")
            return False
        self.last_terminal_edit_debug["stage"] = "original_fields_loaded"
        return True

    def delete_terminal(self, terminal_name, result="鍒犻櫎鎴愬姛"):
        self._ensure_terminal_page_ready()
        if not self._find_exact_terminal_row_via_search(terminal_name):
            self._restore_list_state()
            return False
        if not self._select_terminal_checkbox(terminal_name):
            self._restore_list_state()
            return False
        if not self._click_first_available_safe([self.delete_button_text], timeout=5):
            self._restore_list_state()
            return False
        if not self._click_active_confirmation(timeout=5):
            self._restore_list_state()
            return False
        row_locator = self._exact_terminal_row_locator(terminal_name)
        self.wait_operation_evidence(
            [
                (
                    "row_absent",
                    lambda: self.wait_loading_finished(timeout=0.2)
                    and self.find_visible_now(row_locator) is False,
                ),
                ("toast", lambda: result in self._first_visible_text(self.save_result)),
            ],
            timeout=4,
        )
        absent = not self._find_exact_terminal_row_via_search(terminal_name, timeout=0.5)
        self._restore_list_state()
        return absent

    @timed_operation
    def ensure_terminal_absent(self, terminal_name):
        self._ensure_terminal_page_ready()
        for _ in range(3):
            if not self._find_exact_terminal_row_via_search(terminal_name, timeout=1):
                self._restore_list_state()
                return True
            if not self._select_terminal_checkbox(terminal_name):
                self._restore_list_state()
                return False
            if not self._click_first_available_safe([self.delete_button_text], timeout=3):
                self._restore_list_state()
                return False
            if not self._click_active_confirmation(timeout=4):
                self._restore_list_state()
                return False
            row_locator = self._exact_terminal_row_locator(terminal_name)
            if not self.wait_operation_evidence(
                [
                    (
                        "row_absent",
                        lambda: self.wait_loading_finished(timeout=0.2)
                        and self.find_visible_now(row_locator) is False,
                    ),
                    ("toast", lambda: bool(self._first_visible_text(self.save_result))),
                ],
                timeout=3,
            ):
                self._restore_list_state()
                return False

        absent = not self._find_exact_terminal_row_via_search(terminal_name, timeout=1)
        self._restore_list_state()
        return absent

    def delete_terminals_by_names(self, terminal_names, result="删除成功"):
        ok = True
        for terminal_name in dict.fromkeys(terminal_names):
            ok = self.ensure_terminal_absent(terminal_name) and ok
        return ok

    def delete_terminals_by_keyword(self, keyword, result="删除成功"):
        """Delete only rows matching a unique test prefix in one batch action."""
        self._ensure_terminal_page_ready()
        self._search_keyword(keyword)
        matching_rows = (
            by.XPATH,
            f"//main//table//tbody//tr[.//td[contains(normalize-space(.),'{keyword}')]]",
        )
        if not self._visible_in_any([matching_rows], timeout=4):
            self._restore_list_state()
            return True
        before = len([
            row for row in self.driver.find_elements(*matching_rows) if row.is_displayed()
        ])
        if before < 2:
            self._restore_list_state()
            return False
        if not self._click_first_available_safe([self.select_all_terminal], timeout=5):
            self._restore_list_state()
            return False
        if not self._click_first_available_safe([self.delete_button_text], timeout=5):
            self._restore_list_state()
            return False
        if not self._click_active_confirmation(timeout=5):
            self._restore_list_state()
            return False
        self.wait_operation_evidence(
            [
                (
                    "rows_absent",
                    lambda: self.wait_loading_finished(timeout=0.2)
                    and self.find_visible_now(matching_rows) is False,
                ),
                ("toast", lambda: result in self._first_visible_text(self.save_result)),
            ],
            timeout=5,
        )
        self._search_keyword(keyword)
        absent = self.find_visible_now(matching_rows) is False
        self._restore_list_state()
        return absent

    def get_total_record_count(self):
        self._ensure_terminal_page_ready()
        text = self._first_visible_text(self.data_num)
        if not text:
            return None
        numbers = re.findall(r"\d+", text)
        if not numbers:
            return None
        return int(numbers[-1])

    def wait_for_record_count_change(self, previous_count, timeout=20):
        end = time.time() + timeout
        while time.time() < end:
            current_count = self.get_total_record_count()
            if current_count is not None and current_count != previous_count:
                return current_count
            time.sleep(0.2)
        return None
    def get_current_page_size_text(self):
        text = self._first_visible_text(self.page_size_value)
        if text:
            return text

        # 4.39.7 renders the selected page size in a plain span on some
        # builds, without the ``ant-select-selection-selected-value`` class.
        # Read the visible size changer as a fallback instead of treating the
        # control as absent.
        for element in self.driver.find_elements(*self.page_size_changer):
            try:
                if element.is_displayed():
                    return " ".join((element.text or "").split())
            except Exception:
                continue
        try:
            return (
                self.driver.execute_script(
                    "const el = document.querySelector("
                    "'.ant-pagination-options-size-changer "
                    ".ant-select-selection-selected-value');"
                    "return el ? (el.getAttribute('title') || el.textContent || '').trim() : '';"
                )
                or ""
            )
        except Exception:
            return ""

    def has_pagination_controls(self):
        return self._visible_in_any(
            [(by.CSS_SELECTOR, "ul.ant-pagination, main .pagination-box")],
            timeout=1,
        )

    def get_available_page_sizes(self, timeout=4):
        """Open the terminal page-size selector and return its numeric options."""
        self._ensure_terminal_page_ready()
        changer = next(
            (
                element
                for element in self.driver.find_elements(*self.page_size_changer)
                if element.is_displayed()
            ),
            None,
        )
        if changer is None:
            return []
        self.driver.execute_script(
            """
            document.activeElement?.blur();
            const root = arguments[0];
            const trigger = root.querySelector(
              '.ant-select-selector,.ant-select-selection,.ant-select-selection__rendered'
            ) || root;
            trigger.dispatchEvent(new MouseEvent('mousedown', {bubbles:true, button:0}));
            trigger.dispatchEvent(new MouseEvent('mouseup', {bubbles:true, button:0}));
            trigger.click();
            """,
            changer,
        )
        end = time.time() + timeout
        while time.time() < end:
            values = self.driver.execute_script(
                """
                const visible = el => !!(el && (el.offsetWidth || el.offsetHeight || el.getClientRects().length));
                const roots = [...document.querySelectorAll('.ant-select-dropdown')].filter(visible);
                return roots.flatMap(root => [...root.querySelectorAll(
                    '[role=option],.ant-select-item-option,li.ant-select-dropdown-menu-item'
                  )])
                  .filter(visible)
                  .map(e=>Number(((e.innerText||'').match(/\d+/)||[''])[0]))
                  .filter(Number.isFinite);
                """
            )
            if values:
                # Close the menu without changing the existing page size.
                try:
                    self.driver.execute_script("document.body.click()")
                except Exception:
                    pass
                return list(dict.fromkeys(values))
            time.sleep(0.2)
        return []

    def set_result_page_size(self, page_size, timeout=3):
        self._ensure_terminal_page_ready()
        option_text = f"{page_size} 条/页"
        if str(page_size) in (self.get_current_page_size_text() or ""):
            return True

        if not self._click_first_available_safe([self.page_size_changer], timeout=5):
            return False

        option_locator = (
            by.XPATH,
            "//div[contains(@class,'ant-select-dropdown') and not(contains(@style,'display: none'))]"
            f"//li[starts-with(normalize-space(),'{page_size}')]",
        )
        if not self._click_first_available_safe([option_locator], timeout=timeout):
            # Different Ant Design builds render this option in ``div`` rather
            # than ``li``.  Search the active dropdown by text before failing.
            fallback_option = (
                by.XPATH,
                "//*[contains(@class,'ant-select-dropdown') "
                "and not(contains(@style,'display: none'))]"
                f"//*[starts-with(normalize-space(),'{page_size}')]",
            )
            if not self._click_first_available_safe([fallback_option], timeout=timeout):
                return False

        end = time.time() + timeout
        while time.time() < end:
            if str(page_size) in (self.get_current_page_size_text() or ""):
                return True
            time.sleep(0.2)
        return False

    def _enter_terminal_via_sidebar(self, timeout=10):
        self._dismiss_blocking_layers()
        if not self._ensure_sidebar_expanded(timeout=8):
            return False

        if not self._click_first_available_safe([self.contactlist_button_text], timeout=5):
            return False

        end = time.time() + timeout
        while time.time() < end:
            if self._click_first_available_safe([self.terminal_button_text], timeout=2):
                return True
            if self._click_first_available_safe([self.contactlist_button_text], timeout=2):
                time.sleep(0.3)
            time.sleep(0.2)
        return False

    def _enter_terminal_via_route(self):
        current_url = self.driver.current_url or ""
        if "#" in current_url:
            base_url = current_url.split("#", 1)[0]
        else:
            base_url = current_url.rstrip("/") + "/"
        if not base_url:
            base_url = self.url
        self.open_spa_route(self.terminal_route, timeout=5)

    def _ensure_terminal_page_ready(self):
        ready_locators = self._terminal_page_identity_locators()
        if self.ensure_page_ready_fast(self.terminal_route, ready_locators):
            return self._wait_terminal_list_loaded(allow_cached=True)
        if self.common_enter_terminal():
            return self._wait_terminal_list_loaded(allow_cached=True)
        return False

    def _wait_terminal_list_loaded(self, timeout=12,allow_cached=False):
        return wait_page_layout(self,self.terminal_route,[['终端名称'],['终端序列号']],
            '.el-tree-node__content,.ant-tree-title,.custom-tree-node',timeout=timeout,allow_cached=allow_cached)

    def _is_on_terminal_page(self):
        return self.terminal_route in (self.driver.current_url or "")

    def _terminal_page_ready_locators(self):
        return [
            self.new_add_text,
            self.locate_search,
            self.delete_button_text,
            (
                by.XPATH,
                "//main//table//thead//th[normalize-space()='缁堢鍚嶇О']",
            ),
        ]

    def _terminal_page_identity_locators(self):
        return [
            (
                by.XPATH,
                "//main//*[self::th or self::label or self::span]"
                "[normalize-space()='终端名称']",
            ),
            (
                by.XPATH,
                "//main//*[contains(normalize-space(.),'终端未注册') or "
                "contains(normalize-space(.),'终端序列号')]",
            ),
        ]

    def _terminal_name_input_locator(self, modal_title):
        return (
            by.XPATH,
            "(//div[contains(@class,'ant-modal-content') and not(ancestor::*[contains(@style,'display: none')])]//input)[1]",
        )

    def _terminal_serial_input_locator(self, modal_title):
        return (
            by.XPATH,
            "(//div[contains(@class,'ant-modal-content') and not(ancestor::*[contains(@style,'display: none')])]//input)[2]",
        )

    def _add_terminal_dialog_visible(self, timeout=5):
        end = time.time() + timeout
        while time.time() < end:
            if self._visible_modal_input("终端名称") is not False:
                return True
            time.sleep(0.2)
        return False

    def _modal_action_button_locator(self, modal_title, button_text):
        if button_text == self.save_button_text:
            return (
                by.CSS_SELECTOR,
                ".ant-modal:not([style*='display: none']) .ant-modal-content "
                ".ant-modal-footer button.ant-btn-primary",
            )
        if button_text == self.close_button_text:
            return (
                by.CSS_SELECTOR,
                ".ant-modal:not([style*='display: none']) .ant-modal-content "
                ".ant-modal-footer button.ant-btn:not(.ant-btn-primary), "
                ".ant-modal:not([style*='display: none']) .ant-modal-content button.ant-modal-close",
            )
        return (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content') and not(ancestor::*[contains(@style,'display: none')])]"
            f"//button[contains(., '{button_text}') or .//span[contains(., '{button_text}')]]",
        )

    def _exact_terminal_row_locator(self, terminal_name):
        return (
            by.XPATH,
            f"//table//tbody//tr[td[2][normalize-space()='{terminal_name}']]",
        )

    def _exact_terminal_modify_button_locator(self, terminal_name):
        row = exact_table_row(self.driver, "终端名称", terminal_name)
        if row is None:
            raise AssertionError(f"编辑前未找到准确终端: {terminal_name}")
        for control in row.find_elements(by.CSS_SELECTOR, 'img[title="编辑"],img[title="修改"],[data-icon="edit"],.anticon-edit'):
            if control.is_displayed():
                token=f'terminal_edit_{time.time_ns()}'
                self.driver.execute_script("arguments[0].setAttribute('data-ces-action',arguments[1])",control,token)
                return by.CSS_SELECTOR, f'[data-ces-action="{token}"]'
        raise AssertionError(f"目标准确行缺少编辑控件: {terminal_name}")

    def _exact_terminal_checkbox_locator(self, terminal_name):
        return (
            by.XPATH,
            f"//table//tbody//tr[td[2][normalize-space()='{terminal_name}']]"
            "//td[1]//span[contains(@class,'ant-checkbox')]",
        )

    def _exact_terminal_serial_row_locator(self, terminal_serial):
        return (
            by.XPATH,
            f"//table//tbody//tr[td[3][normalize-space()='{terminal_serial}']]",
        )

    def _search_keyword(self, keyword):
        if not self._ensure_terminal_page_ready():
            raise AssertionError("终端查询前列表未加载完成")
        search = wait_control_unobscured(self, self.locate_search, timeout=5)
        if search is False:
            raise AssertionError("终端搜索输入框未显示")
        search.click()
        search.send_keys(Keys.CONTROL, 'a')
        search.send_keys(Keys.DELETE)
        if keyword:
            search.send_keys(str(keyword))
        started = self.driver.execute_script('return performance.now()')
        if not click_toolbar_search(self.driver, search):
            raise AssertionError("终端查询按钮未命中")
        if not wait_query_finished(self, started, timeout=10, request_path='/serv/v1/terminal/page'):
            raise AssertionError("终端查询请求或结果未完成")
        actual = self.wait_visible(self.locate_search, timeout=2)
        if actual is False or actual.get_attribute('value') != str(keyword):
            raise AssertionError("终端查询条件被重绘覆盖")
        return True

    def submit_search(self):
        before = self.table_snapshot()
        try:
            self.send_keys_enter(self.locate_search)
        except Exception:
            pass
        if not self.wait_table_changed(before, timeout=0.7, poll_frequency=0.05):
            self._click_first_available_safe([self.search_button], timeout=0.3)
        self.wait_loading_finished(timeout=2)

    def reset_search(self):
        return self._search_keyword("")

    def _restore_list_state(self):
        search_input = self.find_visible_now(self.locate_search)
        has_keyword = bool(
            search_input is not False
            and (search_input.get_attribute("value") or "").strip()
        )
        clear_button = self.find_visible_now(self.clear_button_text) if has_keyword else False
        if has_keyword and clear_button is False:
            self.reset_search()
        elif clear_button is not False:
            started = self.driver.execute_script('return performance.now()')
            try:
                clear_button.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", clear_button)
            if not wait_query_finished(self, started, timeout=10, request_path='/serv/v1/terminal/page'):
                raise AssertionError("终端清空查询未完成")
        self._select_search_field(self.search_field_default, timeout=2)
        return True

    def _find_exact_terminal_row_via_search(self, terminal_name, timeout=2):
        self._select_search_field(self.search_field_default, timeout=2)
        self._search_keyword(terminal_name)
        locator = self._exact_terminal_row_locator(terminal_name)
        return self.find_visible_now(locator) is not False

    def _get_select_text(self, select_locator):
        elements = self.driver.find_elements(*select_locator)
        for element in elements:
            try:
                if not element.is_displayed():
                    continue
                text = self.driver.execute_script(
                    "const value = arguments[0].querySelector('.ant-select-selection-selected-value, .ant-select-selection-item');"
                    "return value ? (value.innerText || value.textContent || '').trim() : '';",
                    element,
                )
                return (text or "").strip()
            except Exception:
                continue
        return ""

    def _select_dropdown_option(self, select_locator, option_text, timeout=8):
        current_text = self._get_select_text(select_locator)
        if current_text == option_text:
            return True
        if not self._click_first_available_safe([select_locator], timeout=timeout):
            return False
        option_locator = (
            by.XPATH,
            "//div[contains(@class,'ant-select-dropdown') and not(contains(@style,'display: none'))]"
            f"//*[self::li or contains(@class,'ant-select-item-option')][normalize-space()='{option_text}' "
            f"or .//*[normalize-space()='{option_text}']]",
        )
        if not self._click_first_available_safe([option_locator], timeout=timeout):
            return False
        end = time.time() + timeout
        while time.time() < end:
            if self._get_select_text(select_locator) == option_text:
                return True
            time.sleep(0.2)
        return False

    def _first_visible_text(self, locator):
        for element in self.driver.find_elements(*locator):
            try:
                if element.is_displayed():
                    return (element.text or "").strip()
            except Exception:
                continue
        return ""

    def _select_terminal_type(self, terminal_type, timeout=8):
        return self._select_dropdown_option(self.terminal_type_select, terminal_type, timeout=timeout)

    def _select_search_field(self, search_field, timeout=3):
        return self._select_dropdown_option(self.search_field_select, search_field, timeout=timeout)

    def _search_result_locator(self, keyword, search_field):
        if search_field == self.terminal_serial_label:
            return self._exact_terminal_serial_row_locator(keyword)
        return self._exact_terminal_row_locator(keyword)

    def _search_terminal_with_filters(self, keyword, search_field, terminal_type=None):
        self._restore_list_state()
        if terminal_type and not self._select_terminal_type(terminal_type):
            return False
        search_field = search_field or self.search_field_default
        if not self._select_search_field(search_field):
            return False
        self._search_keyword(keyword)
        locator = self._search_result_locator(keyword, search_field)
        return self.find_visible_now(locator) is not False

    def count_terminal_by_search(self, keyword, search_field=None, timeout=1.5, restore=False):
        self._ensure_terminal_page_ready()
        search_field = search_field or self.search_field_default
        if not self._select_search_field(search_field, timeout=2):
            return 0
        self._search_keyword(keyword)
        locator = self._search_result_locator(keyword, search_field)
        count = sum(
            1 for row in self.driver.find_elements(*locator) if row.is_displayed()
        )
        if not count and timeout:
            self._visible_in_any([locator], timeout=min(timeout, 0.4))
            count = sum(
                1 for row in self.driver.find_elements(*locator) if row.is_displayed()
            )
        if restore:
            self._restore_list_state()
        return count

    def _select_terminal_checkbox(self, terminal_name):
        locator = self._exact_terminal_checkbox_locator(terminal_name)
        end = time.time() + 10
        while time.time() < end:
            elements = self.driver.find_elements(*locator)
            for element in elements:
                try:
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});", element
                    )
                    class_name = element.get_attribute("class") or ""
                    if "checked" in class_name:
                        return True
                    try:
                        element.click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", element)
                    time.sleep(0.2)
                    class_name = element.get_attribute("class") or ""
                    if "checked" in class_name:
                        return True
                except Exception:
                    continue
            time.sleep(0.2)
        return False

    def _replace_input_value(self, locator, value, timeout=10):
        element = self.wait_visible(locator, timeout)
        if element is False:
            return False
        try:
            element.click()
            element.send_keys(Keys.CONTROL, "a")
            element.send_keys(Keys.DELETE)
            time.sleep(0.1)
            element.send_keys(str(value))
        except Exception:
            self.clear_by_javascript(locator)
            self.send_keys(locator, value)
            element = self.wait_visible(locator, timeout)
            if element is False:
                return False
        time.sleep(0.1)
        current_value = element.get_attribute("value") or ""
        return current_value == str(value)

    def _visible_modal_input(self, placeholder):
        script = r"""
        const placeholder = arguments[0];
        const isVisible = (el) => {
            if (!el) return false;
            const rect = el.getBoundingClientRect();
            if (rect.width <= 0 || rect.height <= 0) return false;
            for (let node = el; node && node !== document.body; node = node.parentElement) {
                const style = window.getComputedStyle(node);
                if (style.display === 'none' || style.visibility === 'hidden') return false;
            }
            return true;
        };
        const modals = Array.from(document.querySelectorAll('.ant-modal-content'))
            .filter(isVisible);
        for (const modal of modals.reverse()) {
            const normalize = text => String(text || '').replace(/[\s:*：]/g, '');
            const item = Array.from(modal.querySelectorAll('.ant-form-item')).find(e =>
                Array.from(e.querySelectorAll('label,.ant-form-item-label')).some(label => normalize(label.innerText) === placeholder));
            const labelled = item && Array.from(item.querySelectorAll('input')).find(isVisible);
            if (labelled) return labelled;
            const inputs = Array.from(modal.querySelectorAll('input'))
                .filter(isVisible);
            const exact = inputs.find((input) => input.getAttribute('placeholder') === placeholder);
            if (exact) return exact;
            const partial = inputs.find((input) => String(input.getAttribute('placeholder') || '').includes(placeholder));
            if (partial) return partial;
        }
        return null;
        """
        try:
            element = self.driver.execute_script(script, placeholder)
            return element if element else False
        except Exception:
            return False

    def _active_modal_content(self, timeout=5):
        end = time.time() + timeout
        while time.time() < end:
            modals = self.driver.find_elements(by.CSS_SELECTOR, ".ant-modal-content")
            for modal in reversed(modals):
                try:
                    if modal.is_displayed():
                        return modal
                except Exception:
                    continue
            time.sleep(0.2)
        return None

    def _wait_for_visible_modal_closed(self, timeout=2):
        script = """
        const isVisible = (el) => {
            if (!el) return false;
            const rect = el.getBoundingClientRect();
            if (rect.width <= 0 || rect.height <= 0) return false;
            for (let node = el; node && node !== document.body; node = node.parentElement) {
                const style = window.getComputedStyle(node);
                if (style.display === 'none' || style.visibility === 'hidden') return false;
            }
            return true;
        };
        return !Array.from(document.querySelectorAll('.ant-modal-content')).some(isVisible);
        """
        end = time.time() + timeout
        while time.time() < end:
            try:
                if self.driver.execute_script(script):
                    return True
            except Exception:
                pass
            time.sleep(0.2)
        return False

    def _replace_visible_modal_input(self, placeholder, value, timeout=10):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            element = self._visible_modal_input(placeholder)
            if element is False:
                time.sleep(0.1)
                continue
            try:
                element.click()
                element.send_keys(Keys.CONTROL, "a")
                element.send_keys(Keys.DELETE)
                element.send_keys(str(value))
                element.send_keys(Keys.TAB)
                def committed():
                    field = self._visible_modal_input(placeholder)
                    return {"value": str(value)} if field is not False and (field.get_attribute('value') or '') == str(value) else False
                if wait_stable_state(self, committed, timeout=min(0.7, max(0,deadline-time.monotonic())), stable_for=0.2) is not False:
                    return True
            except (StaleElementReferenceException, ElementNotInteractableException, ElementClickInterceptedException):
                continue
        return False

    def _click_visible_modal_button(self, primary=True, timeout=5):
        script = """
        const wantPrimary = arguments[0];
        const normalize = (value) => String(value || '').replace(/\\s+/g, '').trim();
        const isVisible = (el) => {
            if (!el) return false;
            const rect = el.getBoundingClientRect();
            if (rect.width <= 0 || rect.height <= 0) return false;
            for (let node = el; node && node !== document.body; node = node.parentElement) {
                const style = window.getComputedStyle(node);
                if (style.display === 'none' || style.visibility === 'hidden') return false;
            }
            return true;
        };
        const modalContents = Array.from(document.querySelectorAll('.ant-modal-content'))
            .filter(isVisible);
        if (!modalContents.length) return false;
        const modal = modalContents[modalContents.length - 1];
        const footer = modal.querySelector('.ant-modal-footer') || modal;
        const buttons = Array.from(footer.querySelectorAll('button'))
            .filter((button) => isVisible(button) && !button.disabled);
        const hasPrimaryClass = (button) => String(button.className || '').includes('ant-btn-primary');
        const textOf = (button) => normalize(button.innerText || button.textContent);
        let button = null;
        if (wantPrimary) {
            button = buttons.find((item) => hasPrimaryClass(item))
                || buttons.find((item) => ['保存', '确定'].some((text) => textOf(item).includes(text)))
                || buttons[0];
        } else {
            button = buttons.find((item) => ['关闭', '取消'].some((text) => textOf(item).includes(text)))
                || buttons.slice().reverse().find((item) => !hasPrimaryClass(item))
                || modal.querySelector('button.ant-modal-close');
        }
        if (!button || !isVisible(button)) return false;
        button.scrollIntoView({block: 'center'});
        button.click();
        return true;
        """
        end = time.time() + timeout
        while time.time() < end:
            try:
                if self.driver.execute_script(script, primary):
                    return True
            except Exception:
                pass
            time.sleep(0.2)
        return False

    def _click_active_confirmation(self, timeout=5):
        script = """
        const visible = item => {
          const rect = item.getBoundingClientRect();
          if (rect.width <= 0 || rect.height <= 0) return false;
          for (let node = item; node && node !== document.body; node = node.parentElement) {
            const style = getComputedStyle(node);
            if (style.display === 'none' || style.visibility === 'hidden') return false;
          }
          return true;
        };
        const layers = [...document.querySelectorAll(
          '.ant-modal-confirm,.ant-modal-content,.ant-popover:not(.ant-popover-hidden)'
        )].filter(visible);
        for (const layer of layers.reverse()) {
          const buttons = [...layer.querySelectorAll('button')]
            .filter(button => visible(button) && !button.disabled);
          const normalize = value => String(value || '').replace(/\\s+/g, '');
          const button = buttons.find(item => ['确定', '确认', '删除']
            .some(word => normalize(item.innerText).includes(word)))
            || buttons.find(item => item.classList.contains('ant-btn-primary'));
          if (button) { button.click(); return true; }
        }
        return false;
        """
        end = time.time() + timeout
        while time.time() < end:
            try:
                if self.driver.execute_script(script):
                    return True
            except Exception:
                pass
            time.sleep(0.2)
        return False
    def _click_first_available_safe(self, locators, timeout=4):
        end = time.time() + timeout
        while time.time() < end:
            for locator in locators:
                elements = self.driver.find_elements(*locator)
                for element in elements:
                    try:
                        if not element.is_displayed():
                            continue
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block:'center'});", element
                        )
                        try:
                            element.click()
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", element)
                        return True
                    except Exception:
                        continue
            time.sleep(0.2)
        return False

    def _visible_in_any(self, locators, timeout=4):
        end = time.time() + timeout
        while time.time() < end:
            for locator in locators:
                elements = self.driver.find_elements(*locator)
                for element in elements:
                    try:
                        if element.is_displayed():
                            return True
                    except Exception:
                        continue
            time.sleep(0.2)
        return False

    def _dismiss_blocking_layers(self):
        close_locators = [
            (by.CLASS_NAME, "introjs-skipbutton"),
            (by.CSS_SELECTOR, ".ant-modal-close"),
            (by.CSS_SELECTOR, ".ant-drawer-close"),
        ]
        for locator in close_locators:
            elements = self.driver.find_elements(*locator)
            for element in elements:
                if not element.is_displayed():
                    continue
                try:
                    element.click()
                except Exception:
                    try:
                        self.driver.execute_script("arguments[0].click();", element)
                    except Exception:
                        continue

    def _is_sidebar_collapsed(self):
        menus = self.driver.find_elements(*self.sidebar_menu_root)
        for menu in menus:
            class_name = menu.get_attribute("class") or ""
            if "ant-menu-inline-collapsed" in class_name:
                return True
        return False

    def _ensure_sidebar_expanded(self, timeout=8):
        end = time.time() + timeout
        while time.time() < end:
            if not self._is_sidebar_collapsed():
                return True
            self._click_first_available_safe([self.sidebar_expand_button], timeout=1.5)
            time.sleep(0.3)
        return not self._is_sidebar_collapsed()







