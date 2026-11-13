# -*- coding:utf-8 -*-
import re
import time

from selenium.webdriver.common.by import By as by
from selenium.webdriver.common.keys import Keys

from pages.Index_Page.index import LoginPage
from common.ui_state import wait_query_finished


class FeatureManagePage(LoginPage):
    feature_manage_route = "#/ui/configuration-center/property-management"

    sidebar_menu_root = (by.CSS_SELECTOR, "aside ul.ant-menu")
    sidebar_expand_button = (by.CSS_SELECTOR, "aside .trigger.anticon-menu-unfold")

    feature_code_search_input = (
        by.XPATH,
        "(//main//input[@placeholder='请输入搜索内容'])[1]",
    )
    feature_name_search_input = (
        by.XPATH,
        "(//main//input[@placeholder='请输入搜索内容'])[2]",
    )
    search_button = (by.CSS_SELECTOR, "main button.search-btn")
    clear_button = (by.XPATH, "//main//button[normalize-space()='清 空']")
    add_button = (by.XPATH, "//main//button[normalize-space()='新增']")
    delete_button = (by.XPATH, "//main//button[normalize-space()='删除']")
    save_result = (
        by.XPATH,
        "//div[contains(@class,'ant-message-notice-content')]"
        "//*[contains(@class,'ant-message') and normalize-space()] | "
        "//div[contains(@class,'ant-message-notice-content')]//*[normalize-space()]",
    )
    data_num = (by.CSS_SELECTOR, ".pagination-box>div:nth-child(2)>span")

    def _modal_locator(self, modal_title):
        return (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{modal_title}']]",
        )

    def _modal_input_locator(self, modal_title, placeholder):
        return (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{modal_title}']]"
            f"//input[@placeholder='{placeholder}']",
        )

    def _modal_action_button_locator(self, modal_title, button_text):
        return (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{modal_title}']]"
            f"//button[normalize-space()='{button_text}']",
        )

    def _exact_feature_row_locator(self, feature_code):
        return (
            by.XPATH,
            f"//table//tbody//tr[td[2][normalize-space()='{feature_code}']]",
        )

    def _exact_feature_name_cell_locator(self, feature_code):
        return (
            by.XPATH,
            f"//table//tbody//tr[td[2][normalize-space()='{feature_code}']]/td[3]",
        )

    def _exact_feature_value_cell_locator(self, feature_code):
        return (
            by.XPATH,
            f"//table//tbody//tr[td[2][normalize-space()='{feature_code}']]/td[5]",
        )

    def _exact_feature_action_locator(self, feature_code, action_index):
        return (
            by.XPATH,
            f"//table//tbody//tr[td[2][normalize-space()='{feature_code}']]"
            f"//td[last()]//a[{action_index}]",
        )

    def wait_for_operation_result(self, expected_text=None, timeout=20):
        end = time.time() + timeout
        while time.time() < end:
            for element in self.driver.find_elements(*self.save_result):
                try:
                    if not element.is_displayed():
                        continue
                    text = (element.text or "").strip()
                    if not text:
                        continue
                    if expected_text is None or expected_text in text:
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
            for element in self.driver.find_elements(*locator):
                try:
                    if not element.is_displayed():
                        continue
                    try:
                        element.click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", element)
                except Exception:
                    continue

    def _is_sidebar_collapsed(self):
        for menu in self.driver.find_elements(*self.sidebar_menu_root):
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

    def _visible_in_any(self, locators, timeout=4):
        end = time.time() + timeout
        while time.time() < end:
            for locator in locators:
                for element in self.driver.find_elements(*locator):
                    try:
                        if element.is_displayed():
                            return True
                    except Exception:
                        continue
            time.sleep(0.2)
        return False

    def _click_first_available_safe(self, locators, timeout=4):
        end = time.time() + timeout
        while time.time() < end:
            for locator in locators:
                for element in self.driver.find_elements(*locator):
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

    def _enter_feature_manage_via_route(self):
        current_url = self.driver.current_url or ""
        if "#" in current_url:
            base_url = current_url.split("#", 1)[0]
        else:
            base_url = current_url.rstrip("/") + "/"
        if not base_url:
            base_url = self.url
        self.open_spa_route(self.feature_manage_route, timeout=5)

    def _hard_reload_feature_manage_page(self):
        self._enter_feature_manage_via_route()
        self.driver.refresh()
        self.wait_for_document_ready(timeout=5)
        time.sleep(0.5)
        return True

    def _ensure_page_ready(self):
        if self.feature_manage_route not in (self.driver.current_url or ''):
            return self.common_enter_feature_manage()
        ready_locators = [
            self.feature_code_search_input,
            self.feature_name_search_input,
            self.add_button,
            self.delete_button,
        ]
        if self._visible_in_any(ready_locators, timeout=2):
            return True
        self._hard_reload_feature_manage_page()
        if self._visible_in_any(ready_locators, timeout=5):
            return True
        return self.common_enter_feature_manage()

    def common_enter_feature_manage(self):
        self.common_login()
        self.dismiss_intro_if_present()
        self._dismiss_blocking_layers()
        self._enter_feature_manage_via_route()
        ready_locators = [
            self.feature_code_search_input,
            self.feature_name_search_input,
            self.add_button,
            self.delete_button,
        ]
        if not self._visible_in_any(ready_locators, timeout=10):
            raise AssertionError("Failed to enter feature manage page")
        return True

    def submit_search(self):
        started=self.driver.execute_script('return performance.now()')
        if not self._click_first_available_safe([self.search_button],timeout=2) or not wait_query_finished(self,started,request_path='/conf/v1/feature/page'):
            raise AssertionError('特性查询未完成')

    def reset_search(self):
        self._ensure_page_ready()
        self.clear_by_javascript(self.feature_code_search_input)
        self.clear_by_javascript(self.feature_name_search_input)
        self.submit_search()
        return True

    def _search_feature(self, feature_code="", feature_name=""):
        self._ensure_page_ready()
        if self.wait_visible(self.feature_code_search_input, timeout=8) is False:
            self._hard_reload_feature_manage_page()
            if self.wait_visible(self.feature_code_search_input, timeout=10) is False:
                return False
        self.clear_by_javascript(self.feature_code_search_input)
        self.clear_by_javascript(self.feature_name_search_input)
        if feature_code:
            self.send_keys(self.feature_code_search_input, feature_code)
        if feature_name:
            self.send_keys(self.feature_name_search_input, feature_name)
        self.submit_search()
        return True

    def get_total_record_count(self):
        self._ensure_page_ready()
        text = None
        for element in self.driver.find_elements(*self.data_num):
            try:
                if element.is_displayed():
                    text = element.text
                    break
            except Exception:
                continue
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

    def enter_feature_manage(self):
        return self.common_enter_feature_manage()

    def search_feature(self, feature_code):
        self._ensure_page_ready()
        if not self._search_feature(feature_code=feature_code):raise AssertionError('特性准确查询未完成')
        self.wait_loading_finished(timeout=2)
        locator = self._exact_feature_row_locator(feature_code)
        found = self.find_visible_now(locator) is not False
        self.reset_search()
        return found

    def add_feature(
        self,
        feature_code,
        feature_name,
        feature_value,
        result="新增成功",
    ):
        self._ensure_page_ready()
        self.reset_search()
        before_count = self.get_total_record_count()
        before_table = self.table_snapshot()
        if not self._click_first_available_safe([self.add_button], timeout=5):
            return False

        add_modal = self._modal_locator("新增特性")
        if self.wait_visible(add_modal, timeout=10) is False:
            return False

        if not self._replace_input_value(
            self._modal_input_locator("新增特性", "特性编码"), feature_code, timeout=10
        ):
            return False
        if not self._replace_input_value(
            self._modal_input_locator("新增特性", "特性名称"), feature_name, timeout=10
        ):
            return False
        if not self._replace_input_value(
            self._modal_input_locator("新增特性", "请输入取值类型的特性值"),
            feature_value,
            timeout=10,
        ):
            return False

        if not self._click_first_available_safe(
            [self._modal_action_button_locator("新增特性", "保 存")], timeout=5
        ):
            return False

        evidence = self.wait_operation_evidence(
            [
                ("modal_closed", lambda: self.wait_modal_state(False, timeout=0.05)),
                ("table_changed", lambda: self.table_snapshot() != before_table),
                (
                    "count_changed",
                    lambda: before_count is not None
                    and self.get_total_record_count() > before_count,
                ),
                ("toast", lambda: self.wait_for_operation_result(result, timeout=0.05)),
            ],
            timeout=6,
        )

        if self.search_feature(feature_code):
            return True
        return False

    def modify_feature(self, feature_code, new_feature_value, result="修改成功"):
        self._ensure_page_ready()
        self._search_feature(feature_code=feature_code)
        if not self._visible_in_any([self._exact_feature_row_locator(feature_code)], timeout=5):
            self.reset_search()
            return False

        if not self._click_first_available_safe(
            [self._exact_feature_action_locator(feature_code, 1)], timeout=8
        ):
            self.reset_search()
            return False

        edit_modal = self._modal_locator("修改特性")
        if self.wait_visible(edit_modal, timeout=10) is False:
            self.reset_search()
            return False

        if not self._replace_input_value(
            self._modal_input_locator("修改特性", "请输入取值类型的特性值"),
            new_feature_value,
            timeout=10,
        ):
            self.reset_search()
            return False

        if not self._click_first_available_safe(
            [self._modal_action_button_locator("修改特性", "保 存")], timeout=5
        ):
            self.reset_search()
            return False

        if not self.wait_modal_state(False,timeout=8):return False
        self._search_feature(feature_code=feature_code)
        value_ok = self.get_text_assert(
            str(new_feature_value), self._exact_feature_value_cell_locator(feature_code)
        )
        self.reset_search()
        return value_ok

    def delete_feature(self, feature_code, result="删除成功"):
        self._ensure_page_ready()
        self._search_feature(feature_code=feature_code)
        if not self._visible_in_any([self._exact_feature_row_locator(feature_code)], timeout=5):
            self.reset_search()
            return False

        before_count = self.get_total_record_count()
        row = self.wait_visible(self._exact_feature_row_locator(feature_code), timeout=5)
        delete_opened = False
        if row is not False:
            checkboxes = row.find_elements(by.CSS_SELECTOR, "input[type='checkbox']")
            if checkboxes:
                if not checkboxes[0].is_selected():
                    wrapper = checkboxes[0].find_element(by.XPATH, "ancestor::label[1]")
                    self.driver.execute_script("arguments[0].click();", wrapper)
                selected = self.wait_until(
                    lambda: checkboxes[0].is_selected(), timeout=2, poll_frequency=0.1
                )
                if selected:
                    delete_opened = self._click_first_available_safe(
                        [self.delete_button], timeout=2
                    )
        if not delete_opened:
            delete_opened = self._click_first_available_safe(
                [self._exact_feature_action_locator(feature_code, 2)], timeout=5
            )
        if not delete_opened:
            self.reset_search()
            return False

        confirm_locators = [
            (by.XPATH, "//div[contains(@class,'ant-modal-confirm')]//button[normalize-space()='确 定']"),
            (by.XPATH, "//div[contains(@class,'ant-modal-confirm')]//button[contains(@class,'ant-btn-primary')]"),
            (by.CSS_SELECTOR, ".ant-popover:not(.ant-popover-hidden) button.ant-btn-primary"),
            (by.CSS_SELECTOR, ".ant-modal-content button.ant-btn-primary"),
        ]
        if not self._click_first_available_safe(confirm_locators, timeout=10):
            self.reset_search()
            return False

        row_locator = self._exact_feature_row_locator(feature_code)
        evidence = self.wait_operation_evidence(
            [
                (
                    "row_absent",
                    lambda: self.wait_loading_finished(timeout=0.2)
                    and self.find_visible_now(row_locator) is False,
                ),
                ("toast", lambda: self.wait_for_operation_result(result, timeout=0.05)),
                (
                    "count_changed",
                    lambda: before_count is not None
                    and self.get_total_record_count() < before_count,
                ),
            ],
            timeout=6,
        )
        self._search_feature(feature_code=feature_code)
        self.wait_loading_finished(timeout=2)
        still_exists = self.find_visible_now(row_locator) is not False
        self.reset_search()

        if not still_exists:
            return True
        return bool(evidence and not still_exists)
