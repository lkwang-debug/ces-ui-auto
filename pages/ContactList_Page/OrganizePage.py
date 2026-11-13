# -*- coding:utf-8 -*-
import re
import time
import json

import allure
from selenium.common.exceptions import StaleElementReferenceException, ElementNotInteractableException, ElementClickInterceptedException

from selenium.webdriver.common.by import By as by
from selenium.webdriver.common.keys import Keys

from pages.Index_Page.index import LoginPage
from common.ui_state import click_toolbar_search, wait_query_finished, wait_stable_state,wait_control_unobscured
from common.semantic_controls import action_locator, exact_table_row


class OrganizeManagerPage(LoginPage):
    """缁勭粐绠＄悊椤甸潰瀵硅薄"""

    organize_route = "#/ui/organizational-management/department-management"

    # 通讯录菜单
    contactlist_button = (by.XPATH, "/html/body/div[1]/section/div/aside/div/ul/li[2]/div")
    contactlist_button_text = (
        by.XPATH,
        "//aside//li[contains(@class,'ant-menu-submenu')]"
        "//div[contains(@class,'ant-menu-submenu-title')]"
        "[.//span[normalize-space()='通讯录']]",
    )
    sidebar_menu_root = (by.CSS_SELECTOR, "aside ul.ant-menu")
    sidebar_expand_button = (by.CSS_SELECTOR, "aside .trigger.anticon-menu-unfold")

    # 缁勭粐绠＄悊鑿滃崟
    organize_button = (by.XPATH, "/html/body/div/section/div/aside/div/ul/li[2]/ul/li[1]")
    organize_button_alt = (
        by.XPATH,
        "/html/body/div[1]/section/div/aside/div/ul/li[2]/ul/li[1]",
    )
    organize_button_text = (
        by.XPATH,
        "//aside//li[contains(@class,'ant-menu-item')]"
        "[.//span[normalize-space()='组织管理']]",
    )

    # 页面按钮与搜索
    new_add = (
        by.XPATH,
        "/html/body/div/section/section/main/div/div[2]/div/div[2]/div[2]/div[1]/button[1]",
    )
    new_add_text = (
        by.XPATH,
        "//main//button[normalize-space(.)='新增' or contains(normalize-space(.),'新增')]",
    )
    delete_button = (
        by.XPATH,
        "/html/body/div[1]/section/section/main/div/div[2]/div/div[2]/div[2]/div[1]/button[2]",
    )
    delete_button_text = (
        by.XPATH,
        "//main//button[normalize-space(.)='删除' or contains(normalize-space(.),'删除')]",
    )
    locate_search = (
        by.CSS_SELECTOR,
        "main input.ant-input",
    )
    search_button = (
        by.XPATH,
        "//main//input[contains(@class,'ant-input')]"
        "/ancestor::div[contains(@class,'ant-input-search') or contains(@class,'search')][1]"
        "//button | //main//input[contains(@class,'ant-input')]/following::button[1]",
    )

    # 鏂板寮圭獥
    organize_name = (
        by.CSS_SELECTOR,
        ".ant-modal:not([style*='display: none']) .ant-modal-content input",
    )
    organize_describe = (
        by.CSS_SELECTOR,
        ".ant-modal:not([style*='display: none']) .ant-modal-content textarea",
    )
    save_button = (
        by.CSS_SELECTOR,
        ".ant-modal:not([style*='display: none']) .ant-modal-content "
        ".ant-modal-footer button.ant-btn-primary",
    )
    skip_button = (
        by.CSS_SELECTOR,
        ".ant-modal:not([style*='display: none']) .ant-modal-content "
        ".ant-modal-footer button.ant-btn:not(.ant-btn-primary), "
        ".ant-modal:not([style*='display: none']) .ant-modal-content button.ant-modal-close",
    )
    wrong_organize_name_msg = (
        by.CSS_SELECTOR,
        ".ant-modal:not([style*='display: none']) .ant-form-explain, "
        ".ant-modal:not([style*='display: none']) .ant-form-item-explain, "
        ".ant-modal:not([style*='display: none']) .ant-form-item-explain-error, "
        ".ant-modal:not([style*='display: none']) [role='alert']",
    )

    # 淇敼寮圭獥
    modify_organize_name = (
        by.XPATH,
        "//div[contains(@class,'ant-modal-content')]"
        "[.//div[contains(@class,'ant-modal-title') and normalize-space()='淇敼']]"
        "//input[@placeholder='閮ㄩ棬鍚嶇О']",
    )
    modify_save_button = (
        by.XPATH,
        "//div[contains(@class,'ant-modal-content')]"
        "[.//div[contains(@class,'ant-modal-title') and normalize-space()='淇敼']]"
        "//button[contains(., '淇濆瓨') or contains(., '淇?瀛?)]",
    )
    modify_cancel_button = (
        by.XPATH,
        "//div[contains(@class,'ant-modal-content')]"
        "[.//div[contains(@class,'ant-modal-title') and normalize-space()='淇敼']]"
        "//button[contains(., '鍏抽棴') or contains(., '鍏?闂?)]",
    )

    # 閫氱敤缁撴灉
    save_result = (
        by.XPATH,
        "//div[contains(@class,'ant-message-notice-content')]"
        "//div[contains(@class,'ant-message-custom-content')]//span[normalize-space()]",
    )
    delete_sure_button = (
        by.XPATH,
        "/html/body/div[6]/div/div[2]/div/div[2]/div/div/div[2]/button[2]",
    )
    delete_sure_button_text = (
        by.CSS_SELECTOR,
        ".ant-modal-confirm .ant-modal-confirm-btns .ant-btn-primary,"
        ".ant-confirm .ant-modal-confirm-btns .ant-btn-primary",
    )

    # 鍒嗛〉
    data_num = (
        by.CSS_SELECTOR,
        ".pagination-box>div:nth-child(2)>span, .ant-pagination-total-text",
    )
    page_size_changer = (by.CSS_SELECTOR, ".ant-pagination-options-size-changer")
    page_size_value = (
        by.CSS_SELECTOR,
        ".ant-pagination-options-size-changer .ant-select-selection-selected-value, "
        ".ant-pagination-options-size-changer .ant-select-selection-item",
    )
    quick_jump_input = (by.CSS_SELECTOR, ".ant-pagination-options-quick-jumper input")
    active_page_num = (by.CSS_SELECTOR, ".ant-pagination-item-active")
    first_result_page_button = (by.CSS_SELECTOR, ".ant-pagination-item-1")
    next_page_button = (by.CSS_SELECTOR, ".ant-pagination-next")

    def common_enter_organize(self):
        """Enter organize management page."""
        self.common_login()
        self.dismiss_intro_if_present()
        self._dismiss_blocking_layers()
        ready_locators = [self.new_add, self.new_add_text, self.locate_search]

        self._enter_organize_via_route()
        if self._visible_in_any(ready_locators, timeout=8):
            return self._wait_organize_table()

        if not self._ensure_sidebar_expanded(timeout=8):
            raise AssertionError("Sidebar is still collapsed after expand attempt")

        organize_locators = [
            self.organize_button_text,
            self.organize_button,
            self.organize_button_alt,
        ]
        if not self._visible_in_any(organize_locators, timeout=2):
            if not self._click_first_available_safe(
                [self.contactlist_button_text, self.contactlist_button], timeout=5
            ):
                raise AssertionError("Failed to open contact list menu")
            if not self._visible_in_any(organize_locators, timeout=4):
                raise AssertionError("Failed to display organize menu")

        if not self._click_first_available_safe(organize_locators, timeout=5):
            raise AssertionError("Failed to click organize menu")

        if not self._visible_in_any(ready_locators, timeout=10):
            raise AssertionError("Failed to enter organize management page")
        return self._wait_organize_table()

    def _wait_organize_table(self):
        assert self.wait_until(lambda:self.driver.execute_script(
            "const labels=[...document.querySelectorAll('main thead th')].map(e=>(e.innerText||'').replace(/\\s/g,''));return ['部门ID','部门名称'].every(x=>labels.includes(x));"
        ),timeout=8), '组织管理专属表头未就绪'
        return self.wait_loading_finished(timeout=10)

    def _enter_organize_via_route(self):
        current_url = self.driver.current_url or ""
        if "#" in current_url:
            base_url = current_url.split("#", 1)[0]
        else:
            base_url = current_url.rstrip("/") + "/"
        if not base_url:
            base_url = self.url
        self.open_spa_route(self.organize_route, timeout=5)

    def wait_for_operation_result(self, expected_text=None, timeout=20):
        if expected_text:
            return self.wait_text_contains(self.save_result, expected_text, timeout=timeout)
        return self.wait_visible(self.save_result, timeout=timeout) is not False

    def click_new_add(self):
        self._ensure_organize_page_ready()
        if not self._wait_organization_ready():
            raise AssertionError("组织树和部门列表未加载完成，禁止使用无效上级部门新增")
        if not self._click_first_available_safe([self.new_add_text, self.new_add], timeout=5):
            raise AssertionError("Failed to open add organize dialog")
        if self.wait_visible(self.organize_name, timeout=10) is False:
            raise AssertionError("Add organize dialog did not appear")
        return True

    def _wait_organization_ready(self, timeout=12):
        def snapshot():
            state = self.driver.execute_script(
                """
                const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                const main=document.querySelector('main');
                if(!main) return null;
                const headers=[...main.querySelectorAll('th')].filter(visible).map(e=>(e.innerText||'').trim());
                const nodes=[...main.querySelectorAll('.el-tree-node__content,.ant-tree-title,.custom-tree-node')]
                  .filter(visible).map(e=>(e.innerText||'').trim()).filter(Boolean);
                if(!headers.includes('部门名称')||!nodes.length) return null;
                return JSON.stringify({headers,nodes,rows:[...main.querySelectorAll('tbody tr')]
                  .filter(visible).map(e=>(e.innerText||'').trim())});
                """
            )
            return state if state and self.wait_loading_finished(timeout=0.2) else False
        return wait_stable_state(self, snapshot, timeout=timeout) is not False

    def send_organize_name(self, organize_name):
        self.send_keys(self.organize_name, organize_name)

    def send_organize_describe(self, organize_describe):
        self.send_keys(self.organize_describe, organize_describe)

    def click_save_button(self):
        if not self._click_visible_modal_button(primary=True, timeout=1):
            if not self._click_first_available_safe([self.save_button], timeout=1):
                raise AssertionError("Failed to click organize save button")
        return True

    def click_cancel_button(self):
        clicked = self._click_visible_modal_button(
            primary=False, timeout=1
        ) or self._click_first_available_safe([self.skip_button], timeout=1)
        return bool(clicked and self.wait_modal_state(False, timeout=2))

    def get_wrong_organize_name_msg(self):
        text = self.get_element_text(self.wrong_organize_name_msg, timeout=3)
        if text:
            return text
        return self.driver.execute_script(
            """
            const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
            const modal=[...document.querySelectorAll('.ant-modal-content')].filter(visible).at(-1);
            return [...(modal?.querySelectorAll('.ant-form-item-has-error *,[role=alert]')||[])]
              .filter(e=>visible(e)&&e.children.length===0).map(e=>(e.innerText||'').trim()).filter(Boolean).join(' ');
            """
        )

    def add_organize(self, organize_name, organize_describe, result):
        self._ensure_organize_page_ready()
        before_table = self.table_snapshot()
        self.click_new_add()
        self.clear_by_javascript(self.organize_name)
        self.clear_by_javascript(self.organize_describe)
        self.send_organize_name(organize_name)
        self.send_organize_describe(organize_describe)
        started = self.driver.execute_script('return performance.now()')
        self.click_save_button()
        completed = wait_query_finished(self, started, timeout=10)
        if not completed or not self.wait_modal_state(False, timeout=5):
            self.click_cancel_button()
            raise AssertionError("新增组织保存请求未完成或表单未关闭")
        if not self._wait_organization_ready():
            raise AssertionError("新增后组织树未恢复，不能确认父部门状态")
        found = self._find_exact_organize_row_with_search_priority(organize_name)
        if not found and self._has_visible_modal_content():
            self.click_cancel_button()
        self._restore_list_state()
        return found

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

    def add_duplicate_organize_expect_failed(self, organize_name, organize_describe):
        self._ensure_organize_page_ready()
        self._restore_list_state()
        before_count = 1 if self._find_exact_organize_row_with_search_priority(
            organize_name, allow_global_fallback=False
        ) else 0
        self.click_new_add()
        self.clear_by_javascript(self.organize_name)
        self.clear_by_javascript(self.organize_describe)
        self.send_organize_name(organize_name)
        self.send_organize_describe(organize_describe)
        self.click_save_button()
        message = self._latest_operation_message(timeout=2) or ""
        self.click_cancel_button()
        after_count = 1 if self._find_exact_organize_row_with_search_priority(
            organize_name, allow_global_fallback=False
        ) else 0
        self._restore_list_state()
        count_unchanged = after_count == before_count
        return {
            "blocked": count_unchanged,
            "message": message,
            "before_count": before_count,
            "after_count": after_count,
        }

    def search_organize(self, organize_name):
        self._ensure_organize_page_ready()
        found = self._find_exact_organize_row_with_search_priority(organize_name)
        self._restore_list_state()
        return found

    def cancel_modify_organize(self, old_name, new_name):
        self._ensure_organize_page_ready()
        if not self._open_organize_editor(old_name):
            self._restore_list_state()
            return False
        if not self._replace_visible_modal_input("部门名称", new_name, timeout=5):
            self._click_visible_modal_button(primary=False, timeout=2)
            self._restore_list_state()
            return False
        if not self._click_visible_modal_button(primary=False, timeout=3):
            self._restore_list_state()
            return False
        self.wait_until(
            lambda: not self._has_visible_modal_content(),
            timeout=5,
            poll_frequency=0.2,
        )
        deadline = time.time() + 10
        refreshed = False
        result = False
        while time.time() < deadline:
            old_exists = self._find_exact_organize_row_with_search_priority(
                old_name, allow_global_fallback=False
            )
            if old_exists:
                new_exists = self._find_exact_organize_row_with_search_priority(
                    new_name, allow_global_fallback=False
                )
                result = not new_exists
                break
            if not refreshed and time.time() + 6 < deadline:
                self.driver.refresh()
                self.wait_for_document_ready(timeout=5)
                self._ensure_organize_page_ready()
                refreshed = True
            else:
                time.sleep(0.25)
        self._restore_list_state()
        return result

    def modify_organize(self, old_name, new_name):
        self.last_organize_edit_debug = {"old_name": old_name, "new_name": new_name, "stage": "page_ready"}
        self._ensure_organize_page_ready()
        if old_name != new_name and not self.ensure_organize_absent(new_name):
            self._record_organize_edit_failure("target_already_exists")
            return False
        if not self._open_organize_editor(old_name):
            self._restore_list_state()
            return False
        if not self._replace_visible_modal_input("部门名称", new_name, timeout=5):
            self._record_organize_edit_failure("name_not_committed")
            self._click_visible_modal_button(primary=False, timeout=2)
            self._restore_list_state()
            return False
        if not self._click_visible_modal_button(primary=True, timeout=3):
            self._record_organize_edit_failure("save_not_clicked")
            self._click_visible_modal_button(primary=False, timeout=2)
            self._restore_list_state()
            return False
        self.wait_until(
            lambda: self.wait_for_operation_result(timeout=0.5)
            or not self._has_visible_modal_content(),
            timeout=6,
            poll_frequency=0.2,
        )
        for attempt in range(3):
            if self._find_exact_organize_row_with_search_priority(new_name):
                old_absent = not self._find_exact_organize_row_with_search_priority(
                    old_name, allow_global_fallback=False
                )
                self._restore_list_state()
                return old_absent
            if attempt < 2:
                self.driver.refresh()
                self.wait_for_document_ready(timeout=5)
                self._ensure_organize_page_ready()
        self._record_organize_edit_failure("persisted_name_not_found")
        self._restore_list_state()
        return False

    def _record_organize_edit_failure(self, stage):
        debug = getattr(self, "last_organize_edit_debug", {})
        debug["stage"] = stage
        field = self._visible_modal_input("部门名称")
        debug["current_name"] = field.get_attribute("value") if field is not False else None
        debug["table"] = self.table_snapshot()
        self.last_organize_edit_debug = debug
        allure.attach(json.dumps(debug, ensure_ascii=False, indent=2), "组织修改失败阶段", allure.attachment_type.JSON)
        allure.attach(self.driver.get_screenshot_as_png(), "组织修改清理前现场", allure.attachment_type.PNG)

    def _open_organize_editor(self, old_name):
        if not hasattr(self, "last_organize_edit_debug"):
            self.last_organize_edit_debug = {}
        self.last_organize_edit_debug["old_name"] = old_name
        if not self._find_exact_organize_row_with_search_priority(old_name):
            self._record_organize_edit_failure("source_row_not_found")
            return False
        started = self.driver.execute_script("return performance.now()")
        locator = self._exact_organize_modify_button_locator(old_name)
        if not self._click_first_available_safe([locator], timeout=6):
            self._record_organize_edit_failure("modify_not_clicked")
            return False
        if not wait_query_finished(self, started, timeout=8, request_path="/basis/v1/departInfo/departEdit"):
            self._record_organize_edit_failure("edit_request_not_completed")
            return False
        def hydrated():
            field = self._visible_modal_input("部门名称")
            if field is False or (field.get_attribute("value") or "") != old_name:
                return False
            return {"name": old_name}
        if wait_stable_state(self, hydrated, timeout=5, stable_for=0.2) is False:
            self._record_organize_edit_failure("source_name_not_loaded")
            return False
        self.last_organize_edit_debug["stage"] = "original_value_loaded"
        return True

    def delete_organize(self, organize_name, result):
        self._ensure_organize_page_ready()
        if not self._find_exact_organize_row_with_search_priority(organize_name):
            self._restore_list_state()
            return False
        delete_locator = self._exact_organize_delete_button_locator(organize_name)
        before_count = self.get_total_record_count()
        if not self._click_first_available_safe([delete_locator], timeout=10):
            self._restore_list_state()
            return False
        if not self._click_visible_delete_confirmation(timeout=10):
            self._restore_list_state()
            return False
        row_locator = self._exact_organize_row_locator(organize_name)
        evidence = self.wait_operation_evidence(
            [
                (
                    "row_absent",
                    lambda: self.wait_loading_finished(timeout=0.2)
                    and self.find_visible_now(row_locator) is False,
                ),
                ("toast", lambda: result in self._first_visible_text(self.save_result)),
                (
                    "count_changed",
                    lambda: before_count is not None
                    and self.get_total_record_count() < before_count,
                ),
            ],
            timeout=6,
        )
        self._restore_list_state()
        if evidence:
            return True
        deleted = not self._find_exact_organize_row_with_search_priority(
            organize_name, allow_global_fallback=False
        )
        self._restore_list_state()
        return deleted

    def ensure_organize_absent(self, organize_name, allow_global_fallback=True):
        self._ensure_organize_page_ready()

        for _ in range(3):
            if not self._find_exact_organize_row_with_search_priority(
                organize_name, allow_global_fallback=allow_global_fallback
            ):
                self._restore_list_state()
                return True

            delete_locator = self._exact_organize_delete_button_locator(organize_name)
            if not self._click_first_available_safe([delete_locator], timeout=4):
                self._restore_list_state()
                return False
            if not self._click_visible_delete_confirmation(timeout=4):
                self._restore_list_state()
                return False

            row_locator = self._exact_organize_row_locator(organize_name)
            removed = self.wait_operation_evidence(
                [
                    (
                        "row_absent",
                        lambda: self.wait_loading_finished(timeout=0.2)
                        and self.find_visible_now(row_locator) is False,
                    ),
                    ("toast", lambda: bool(self._first_visible_text(self.save_result))),
                ],
                timeout=4,
            )
            if not removed:
                self._restore_list_state()
                return False

        absent = not self._find_exact_organize_row_with_search_priority(
            organize_name, allow_global_fallback=allow_global_fallback
        )
        self._restore_list_state()
        return absent

    def get_total_record_count(self):
        self._ensure_organize_page_ready()
        text = self._first_visible_text(self.data_num)
        if text:
            numbers = re.findall(r"\d+", text)
            if numbers:
                return int(numbers[-1])
        return self.driver.execute_script(
            """
            const rows=[...document.querySelectorAll('main tbody tr')]
              .filter(e=>e.offsetParent!==null&&!e.classList.contains('ant-table-measure-row'));
            const pages=[...document.querySelectorAll('main .ant-pagination-item')]
              .map(e=>Number((e.innerText||'').trim())).filter(Number.isFinite);
            const selected=document.querySelector(
              'main .ant-pagination-options-size-changer .ant-select-selection-item, '
              + 'main .ant-pagination-options-size-changer .ant-select-selection-selected-value');
            const size=Number(((selected?.innerText||'').match(/\d+/)||['0'])[0]);
            const last=pages.length?Math.max(...pages):1;
            return last>1&&size ? (last-1)*size+1 : rows.length;
            """
        )

    def wait_for_record_count_change(self, previous_count, timeout=20):
        end = time.time() + timeout
        while time.time() < end:
            current_count = self.get_total_record_count()
            if current_count is not None and current_count != previous_count:
                return current_count
            time.sleep(0.2)
        return None

    def get_current_page_text(self):
        return self._get_visible_active_page_text()

    def get_pagination_summary_text(self):
        summary = self._first_visible_text(self.data_num) or ""
        if summary:
            return summary
        return self.driver.execute_script(
            """
            const page=(document.querySelector('main .ant-pagination-item-active')?.innerText||'').trim();
            const row=[...document.querySelectorAll('main tbody tr')]
              .find(e=>e.offsetParent!==null&&!e.classList.contains('ant-table-measure-row'));
            return page && row ? `page=${page};row=${(row.innerText||'').replace(/\s+/g,' ').trim()}` : '';
            """
        )

    def get_current_page_size_text(self):
        return self._first_visible_text(self.page_size_value) or ""

    def set_result_page_size(self, page_size, timeout=4):
        self._ensure_organize_page_ready()
        target_text = str(page_size)
        current_numbers = re.findall(r"\d+", self.get_current_page_size_text())
        if current_numbers and current_numbers[0] == target_text:
            return True

        if not self._click_first_available_safe([
            (by.CSS_SELECTOR, "main .ant-pagination-options-size-changer .ant-select-selector,main .ant-pagination-options-size-changer .ant-select-selection"),
        ], timeout=5):
            return False
        option=self.wait_until(lambda:self.driver.execute_script(
            """
            return [...document.querySelectorAll('.ant-select-dropdown .ant-select-item-option,.ant-select-dropdown li')]
              .find(e=>{if(e.offsetParent===null||(e.innerText||'').replace(/\s/g,'')!==arguments[0]+'条/页')return false;
                const r=e.getBoundingClientRect(),hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
                return r.width>5&&r.height>5&&hit&&(hit===e||e.contains(hit));})||null;
            """,target_text),timeout=timeout)
        if option is False:
            return False
        started=self.driver.execute_script('return performance.now()')
        option.click()
        if not wait_query_finished(self,started,timeout=8,request_path='/basis/v1/departInfo/queryDepartPage'):
            return False

        end = time.time() + timeout
        while time.time() < end:
            numbers = re.findall(r"\d+", self.get_current_page_size_text())
            if numbers and numbers[0] == target_text:
                return True
            time.sleep(0.2)
        return False

    def jump_to_result_page(self, page_num, timeout=4):
        self._ensure_organize_page_ready()
        target_page = str(page_num)
        if self.get_current_page_text() == target_page:
            return True

        input_element = self.wait_visible(self.quick_jump_input, timeout=timeout)
        if input_element is False:
            return False

        try:
            input_element.click()
            input_element.send_keys(Keys.CONTROL, "a")
            input_element.send_keys(Keys.DELETE)
            time.sleep(0.1)
            input_element.send_keys(target_page)
            input_element.send_keys(Keys.ENTER)
        except Exception:
            self.send_keys_enter_after_input_by_js(self.quick_jump_input, target_page)

        end = time.time() + timeout
        while time.time() < end:
            if self.get_current_page_text() == target_page:
                return True
            time.sleep(0.2)
        return False

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
        element = self.find_visible_now(self.locate_search)
        if element is not False and not (element.get_attribute("value") or "").strip():
            return True
        return self._search_keyword("")

    def _first_visible_text(self, locator):
        for element in self.driver.find_elements(*locator):
            try:
                if element.is_displayed():
                    return (element.text or "").strip()
            except Exception:
                continue
        return ""

    def _exact_organize_row_locator(self, organize_name):
        return (
            by.XPATH,
            f"//table//tbody//tr[td[3][normalize-space()='{organize_name}']]",
        )

    def _exact_organize_modify_button_locator(self, organize_name):
        return self._organize_action_locator(organize_name, "修改")

    def _exact_organize_delete_button_locator(self, organize_name):
        return self._organize_action_locator(organize_name, "删除")

    def _organize_action_locator(self, organize_name, action):
        row = exact_table_row(self.driver, "部门名称", organize_name)
        if row is None:
            raise AssertionError(f"组织操作前未找到准确部门: {organize_name}")
        # Both deployed versions render two unlabelled image buttons in
        # .dept-oper: edit, delete. Restrict the fallback to this inspected
        # structure; the editor still must load the exact original name.
        buttons = [button for button in row.find_elements(by.CSS_SELECTOR, '.dept-oper > button')
                   if button.is_displayed()]
        if len(buttons) == 2 and all(button.find_elements(by.TAG_NAME, 'img') and not button.text.strip()
                                     and not button.get_attribute('title') and not button.get_attribute('aria-label')
                                     for button in buttons):
            control = buttons[0 if action == "修改" else 1]
            token = f'org_{action}_{time.time_ns()}'
            self.driver.execute_script("arguments[0].setAttribute('data-ces-action',arguments[1])", control, token)
            return by.CSS_SELECTOR, f'[data-ces-action="{token}"]'
        return action_locator(self, "部门名称", organize_name, action)

    def _search_keyword(self, keyword):
        search = wait_control_unobscured(self, self.locate_search, timeout=5)
        if search is False:
            raise AssertionError("部门搜索框未显示")
        search.click()
        search.send_keys(Keys.CONTROL, 'a')
        search.send_keys(Keys.DELETE)
        if keyword:
            search.send_keys(str(keyword))
        started = self.driver.execute_script('return performance.now()')
        if not click_toolbar_search(self.driver, search):
            raise AssertionError("部门查询按钮未命中")
        if not wait_query_finished(self, started, timeout=10, request_path='/basis/v1/departInfo/queryDepartPage'):
            raise AssertionError("部门查询请求未完成")
        return True

    def _restore_list_state(self):
        self.reset_search()
        self._go_to_first_result_page(timeout=3)
        return True

    def delete_organizes_by_names(self, organize_names, result="删除成功"):
        ok = True
        for organize_name in dict.fromkeys(organize_names):
            ok = self.ensure_organize_absent(
                organize_name, allow_global_fallback=False
            ) and ok
        return ok

    def _get_visible_active_page_text(self):
        for element in self.driver.find_elements(*self.active_page_num):
            try:
                if element.is_displayed():
                    return (element.text or "").strip()
            except Exception:
                continue
        return None

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

    def _visible_modal_input(self, placeholder=None, index=0):
        script = r"""
        const placeholder = arguments[0];
        const isVisible = (el) => {
            if (!el) return false;
            const style = window.getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            return style.display !== 'none'
                && style.visibility !== 'hidden'
                && rect.width > 0
                && rect.height > 0;
        };
        const modals = Array.from(document.querySelectorAll('.ant-modal-content')).filter(isVisible);
        if (!modals.length) return null;
        const modal = modals[modals.length - 1];
        const inputs = Array.from(modal.querySelectorAll('input')).filter(isVisible);
        if (placeholder) {
            const item = Array.from(modal.querySelectorAll('.ant-form-item')).find(item =>
                Array.from(item.querySelectorAll('label,.ant-form-item-label')).some(label =>
                    (label.innerText || '').replace(/[\s:*：]/g, '') === placeholder));
            const labelled = item && Array.from(item.querySelectorAll('input')).find(isVisible);
            if (labelled) return labelled;
            const exact = inputs.find((input) => input.getAttribute('placeholder') === placeholder);
            if (exact) return exact;
            const partial = inputs.find((input) => String(input.getAttribute('placeholder') || '').includes(placeholder));
            if (partial) return partial;
        }
        return null;
        """
        try:
            element = self.driver.execute_script(script, placeholder, index)
            return element if element else False
        except Exception:
            return False

    def _replace_visible_modal_input(self, placeholder, value, timeout=5, index=0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            element = self._visible_modal_input(placeholder=placeholder)
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
                    current = self._visible_modal_input(placeholder=placeholder)
                    if current is False:
                        return False
                    return {"value": str(value)} if (current.get_attribute('value') or '') == str(value) else False
                remaining = max(0, deadline - time.monotonic())
                if wait_stable_state(self, committed, timeout=min(0.7, remaining), stable_for=0.2) is not False:
                    return True
            except (StaleElementReferenceException, ElementNotInteractableException, ElementClickInterceptedException):
                continue
        return False

    def _go_to_next_result_page(self, timeout=5):
        buttons = self.driver.find_elements(*self.next_page_button)
        for button in buttons:
            try:
                if not button.is_displayed():
                    continue
                class_name = button.get_attribute("class") or ""
                if "disabled" in class_name:
                    return False
                current_page = self._get_visible_active_page_text()
                try:
                    button.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", button)
                end = time.time() + timeout
                while time.time() < end:
                    next_page = self._get_visible_active_page_text()
                    if next_page and next_page != current_page:
                        return True
                    time.sleep(0.2)
                return False
            except Exception:
                continue
        return False

    def _go_to_first_result_page(self, timeout=5):
        current_page = self._get_visible_active_page_text()
        if current_page in (None, "", "1"):
            return True

        buttons = self.driver.find_elements(*self.first_result_page_button)
        for button in buttons:
            try:
                if not button.is_displayed():
                    continue
                class_name = button.get_attribute("class") or ""
                if "active" in class_name:
                    return True
                try:
                    button.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", button)

                end = time.time() + timeout
                while time.time() < end:
                    active_page = self._get_visible_active_page_text()
                    if active_page == "1":
                        return True
                    time.sleep(0.2)
            except Exception:
                continue

        return self._get_visible_active_page_text() in (None, "", "1")

    def _find_exact_organize_row_on_results_pages(self, organize_name, max_pages=20):
        row_locator = self._exact_organize_row_locator(organize_name)
        for _ in range(max_pages):
            rows = self.driver.find_elements(*row_locator)
            for row in rows:
                try:
                    if row.is_displayed():
                        return True
                except Exception:
                    continue
            if not self._go_to_next_result_page(timeout=5):
                return False
        return False

    def _find_exact_organize_row_on_current_page(self, organize_name):
        row_locator = self._exact_organize_row_locator(organize_name)
        rows = self.driver.find_elements(*row_locator)
        for row in rows:
            try:
                if row.is_displayed():
                    return True
            except Exception:
                continue
        return False

    def _wait_for_exact_organize_row_on_current_page(self, organize_name, timeout=3):
        end = time.time() + timeout
        while time.time() < end:
            if self._find_exact_organize_row_on_current_page(organize_name):
                return True
            time.sleep(0.2)
        return False

    def _find_exact_organize_row_with_search_priority(
        self, organize_name, short_scan_pages=2, allow_global_fallback=True
    ):
        self._ensure_organize_page_ready()
        if self._search_keyword(organize_name):
            self.wait_loading_finished(timeout=2)
            if self._find_exact_organize_row_on_current_page(organize_name):
                return True
            return False
        return False

    def _find_exact_organize_row_globally(self, organize_name, max_pages=20):
        return self._find_exact_organize_row_with_search_priority(
            organize_name,
            short_scan_pages=min(2, max_pages),
            allow_global_fallback=True,
        )

    def _click_visible_modal_button(self, primary=True, timeout=5):
        script = """
        const wantPrimary = arguments[0];
        const normalize = (value) => String(value || '').replace(/\\s+/g, '').trim();
        const isVisible = (el) => {
            if (!el) return false;
            const style = window.getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            return style.display !== 'none'
                && style.visibility !== 'hidden'
                && rect.width > 0
                && rect.height > 0;
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

    def _has_visible_modal_content(self):
        try:
            return bool(self.driver.execute_script("""
              const visible = el => !!(el && (el.offsetWidth || el.offsetHeight || el.getClientRects().length));
              return [...document.querySelectorAll('.ant-modal-content')].some(visible);
            """))
        except Exception:
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

    def _click_visible_delete_confirmation(self, timeout=4):
        """Confirm deletion in both legacy regular modals and modern confirm modals."""
        script = """
        const visible = el => !!(el && (el.offsetWidth || el.offsetHeight || el.getClientRects().length));
        const layers = [...document.querySelectorAll('.ant-modal-content,.ant-modal-confirm')]
          .filter(visible).reverse();
        const layer = layers.find(item => (item.innerText || '').includes('删除'));
        if (!layer) return false;
        const buttons = [...layer.querySelectorAll('button')].filter(visible);
        const button = buttons.find(item => ['确定','确认'].includes((item.innerText || '').trim()))
          || buttons.find(item => item.classList.contains('ant-btn-primary'));
        if (!button) return false;
        button.click();
        return true;
        """
        end = time.time() + timeout
        while time.time() < end:
            try:
                if self.driver.execute_script(script):
                    return True
            except Exception:
                pass
            time.sleep(0.2)
        return self._click_first_available_safe(
            [self.delete_sure_button_text, self.delete_sure_button], timeout=1
        )

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

    def _ensure_organize_page_ready(self):
        if self.organize_route not in (self.driver.current_url or ''):
            return self.common_enter_organize()
        ready_locators = [self.new_add, self.new_add_text, self.locate_search]
        if self._visible_in_any(ready_locators, timeout=2):
            return self._wait_organize_table()
        return self.common_enter_organize()
