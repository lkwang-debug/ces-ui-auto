# -*- coding:utf-8 -*-
import re
import time

from selenium.webdriver.common.by import By as by
from selenium.webdriver.common.keys import Keys

from pages.Index_Page.index import LoginPage
from common.ui_state import wait_query_finished


class FeatureParamsManagePage(LoginPage):
    feature_params_route = "#/ui/configuration-center/characteristic-parameter-management"

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
    vendor_name_search_input = (
        by.XPATH,
        "(//main//input[@placeholder='请输入搜索内容'])[3]",
    )
    os_search_input = (
        by.XPATH,
        "(//main//input[@placeholder='请输入搜索内容'])[4]",
    )
    search_button = (by.CSS_SELECTOR, "main button.search-btn")
    clear_button = (by.XPATH, "//main//button[normalize-space()='清 空']")
    add_button = (by.CSS_SELECTOR, "main button.hst-add-button")
    delete_button = (by.CSS_SELECTOR, "main button.hst-delete-button")
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

    def _modal_feature_name_select_locator(self, modal_title):
        return (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{modal_title}']]"
            "//label[normalize-space()='特性名称']"
            "/ancestor::div[contains(@class,'ant-form-item')][1]"
            "//div[contains(@class,'ant-select')]",
        )

    def _modal_action_button_locator(self, modal_title, button_text):
        return (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{modal_title}']]"
            f"//button[normalize-space()='{button_text}']",
        )

    def _visible_dropdown_option_locator(self, option_text):
        return (
            by.XPATH,
            "//div[contains(@class,'ant-select-dropdown') and not(contains(@style,'display: none'))]"
            f"//li[normalize-space()='{option_text}']",
        )

    def _visible_modal(self, timeout=10):
        end = time.time() + timeout
        while time.time() < end:
            for modal in self.driver.find_elements(by.CSS_SELECTOR, ".ant-modal-content"):
                try:
                    if modal.is_displayed():
                        return modal
                except Exception:
                    continue
            time.sleep(0.2)
        return None

    def _visible_main_text_inputs(self, timeout=8):
        end = time.time() + timeout
        while time.time() < end:
            inputs = []
            for element in self.driver.find_elements(by.CSS_SELECTOR, "main input[type='text']"):
                try:
                    if element.is_displayed():
                        inputs.append(element)
                except Exception:
                    continue
            if inputs:
                return inputs
            time.sleep(0.2)
        return []

    def _replace_visible_input(self, element, value):
        try:
            element.click()
            element.send_keys(Keys.CONTROL, "a")
            element.send_keys(Keys.DELETE)
            time.sleep(0.1)
            element.send_keys(str(value))
            time.sleep(0.2)
            current_value = element.get_attribute("value") or ""
            return current_value == str(value)
        except Exception:
            return False

    def _replace_modal_input_by_placeholder(self, placeholder, value, timeout=10):
        end = time.time() + timeout
        while time.time() < end:
            modal = self._visible_modal(timeout=1)
            if modal is not None:
                for element in modal.find_elements(by.CSS_SELECTOR, "input"):
                    try:
                        if not element.is_displayed():
                            continue
                        if (element.get_attribute("placeholder") or "") != placeholder:
                            continue
                        return self._replace_visible_input(element, value)
                    except Exception:
                        continue
            time.sleep(0.2)
        return False

    def _click_modal_button(self, button_text, timeout=5):
        end = time.time() + timeout
        while time.time() < end:
            modal = self._visible_modal(timeout=1)
            if modal is not None:
                for button in modal.find_elements(by.CSS_SELECTOR, "button"):
                    try:
                        if not button.is_displayed():
                            continue
                        if (button.text or "").strip() != button_text:
                            continue
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block:'center'});", button
                        )
                        try:
                            button.click()
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", button)
                        return True
                    except Exception:
                        continue
            time.sleep(0.2)
        return False

    def _exact_feature_param_row_locator(self, feature_code, vendor_name):
        return (
            by.XPATH,
            "//table//tbody//tr["
            f"td[2][normalize-space()='{feature_code}'] and "
            f"td[4][normalize-space()='{vendor_name}']"
            "]",
        )

    def _exact_feature_param_return_cell_locator(self, feature_code, vendor_name):
        return (
            by.XPATH,
            "//table//tbody//tr["
            f"td[2][normalize-space()='{feature_code}'] and "
            f"td[4][normalize-space()='{vendor_name}']"
            "]/td[14]",
        )

    def _exact_feature_param_action_locator(self, feature_code, vendor_name, action_index):
        return (
            by.XPATH,
            "//table//tbody//tr["
            f"td[2][normalize-space()='{feature_code}'] and "
            f"td[4][normalize-space()='{vendor_name}']"
            f"]//td[last()]//a[{action_index}]",
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
            time.sleep(0.2)
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

    def _select_feature_name_in_modal(self, modal_title, feature_name, timeout=8):
        end = time.time() + timeout
        clicked = False
        while time.time() < end and not clicked:
            modal = self._visible_modal(timeout=1)
            if modal is not None:
                for select in modal.find_elements(by.CSS_SELECTOR, ".ant-select"):
                    try:
                        if not select.is_displayed():
                            continue
                        if feature_name in (select.text or ""):
                            return True
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block:'center'});", select
                        )
                        try:
                            select.click()
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", select)
                        clicked = True
                        break
                    except Exception:
                        continue
            time.sleep(0.2)
        if not clicked:
            return False
        option_locator = self._visible_dropdown_option_locator(feature_name)
        if not self._click_first_available_safe([option_locator], timeout=timeout):
            return False
        time.sleep(0.2)
        return True

    def _enter_feature_params_via_route(self):
        current_url = self.driver.current_url or ""
        if "#" in current_url:
            base_url = current_url.split("#", 1)[0]
        else:
            base_url = current_url.rstrip("/") + "/"
        if not base_url:
            base_url = self.url
        self.open_spa_route(self.feature_params_route, timeout=5)

    def _hard_reload_feature_params_page(self):
        self._enter_feature_params_via_route()
        self.driver.refresh()
        self.wait_for_document_ready(timeout=5)
        time.sleep(0.5)
        return True

    def _ensure_page_ready(self):
        if self.feature_params_route not in (self.driver.current_url or ''):
            return self.common_enter_feature_params_manage()
        ready_locators = [
            self.feature_code_search_input,
            self.feature_name_search_input,
            self.vendor_name_search_input,
            self.add_button,
            self.delete_button,
        ]
        if self._visible_in_any(ready_locators, timeout=2):
            return True
        self._hard_reload_feature_params_page()
        if self._visible_in_any(ready_locators, timeout=5):
            return True
        return self.common_enter_feature_params_manage()

    def common_enter_feature_params_manage(self):
        self.common_login()
        self.dismiss_intro_if_present()
        self._dismiss_blocking_layers()
        self._enter_feature_params_via_route()
        ready_locators = [
            self.feature_code_search_input,
            self.feature_name_search_input,
            self.vendor_name_search_input,
            self.add_button,
            self.delete_button,
        ]
        if not self._visible_in_any(ready_locators, timeout=10):
            raise AssertionError("Failed to enter feature params manage page")
        return True

    def submit_search(self):
        started=self.driver.execute_script('return performance.now()')
        if not self._click_first_available_safe([self.search_button],timeout=2) or not wait_query_finished(self,started,request_path='/conf/v1/feature/param/page'):
            raise AssertionError('特性参数查询未完成')

    def reset_search(self):
        self._ensure_page_ready()
        for element in self._visible_main_text_inputs(timeout=3):
            try:
                element.click()
                element.send_keys(Keys.CONTROL, "a")
                element.send_keys(Keys.DELETE)
            except Exception:
                continue
        self.submit_search()
        return True

    def _search_feature_param(
        self,
        feature_code="",
        feature_name="",
        vendor_name="",
        os_name="",
    ):
        self._ensure_page_ready()
        inputs = self._visible_main_text_inputs(timeout=8)
        if not inputs:
            self._hard_reload_feature_params_page()
            inputs = self._visible_main_text_inputs(timeout=10)
            if not inputs:
                return False
        for element in inputs:
            try:
                element.click()
                element.send_keys(Keys.CONTROL, "a")
                element.send_keys(Keys.DELETE)
            except Exception:
                continue
        values = [feature_code, feature_name, vendor_name, os_name]
        for idx, value in enumerate(values):
            if not value:
                continue
            if len(inputs) <= idx:
                return False
            if not self._replace_visible_input(inputs[idx], value):
                return False
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

    def enter_feature_params_manage(self):
        return self.common_enter_feature_params_manage()

    def search_feature_param(self, feature_code, vendor_name):
        self._ensure_page_ready()
        if not self._search_feature_param(feature_code=feature_code, vendor_name=vendor_name):raise AssertionError('特性参数准确查询未完成')
        self.wait_loading_finished(timeout=2)
        locator = self._exact_feature_param_row_locator(feature_code, vendor_name)
        found = self.find_visible_now(locator) is not False
        self.reset_search()
        return found

    def add_feature_param(
        self,
        feature_name,
        vendor_name,
        return_value,
        feature_code="VNCAudio",
        result="添加成功",
    ):
        self._ensure_page_ready()
        self.reset_search()
        before_count = self.get_total_record_count()
        if not self._click_first_available_safe([self.add_button], timeout=5):
            return False

        if self._visible_modal(timeout=10) is None:
            return False

        if not self._select_feature_name_in_modal("新增特性参数", feature_name, timeout=8):
            return False

        if not self._replace_modal_input_by_placeholder("厂商名称", vendor_name, timeout=10):
            return False
        if not self._replace_modal_input_by_placeholder("返回值", return_value, timeout=10):
            return False

        if not self._click_modal_button("保 存", timeout=5):
            return False

        if not self.wait_modal_state(False,timeout=8):return False
        return self.search_feature_param(feature_code,vendor_name)

    def modify_feature_param(
        self,
        feature_code,
        vendor_name,
        new_return_value,
        result="修改成功",
    ):
        self._ensure_page_ready()
        self._search_feature_param(feature_code=feature_code, vendor_name=vendor_name)
        if not self._visible_in_any(
            [self._exact_feature_param_row_locator(feature_code, vendor_name)], timeout=5
        ):
            self.reset_search()
            return False

        if not self._click_first_available_safe(
            [self._exact_feature_param_action_locator(feature_code, vendor_name, 1)],
            timeout=8,
        ):
            self.reset_search()
            return False

        if self._visible_modal(timeout=10) is None:
            self.reset_search()
            return False

        if not self._replace_modal_input_by_placeholder("返回值", new_return_value, timeout=10):
            self.reset_search()
            return False

        if not self._click_modal_button("保 存", timeout=5):
            self.reset_search()
            return False

        if not self.wait_modal_state(False,timeout=8):return False
        self._search_feature_param(feature_code=feature_code, vendor_name=vendor_name)
        value_ok = self.get_text_assert(
            str(new_return_value),
            self._exact_feature_param_return_cell_locator(feature_code, vendor_name),
        )
        self.reset_search()
        return value_ok

    def delete_feature_param(self, feature_code, vendor_name, result="删除成功"):
        self._ensure_page_ready()
        self._search_feature_param(feature_code=feature_code, vendor_name=vendor_name)
        if not self._visible_in_any(
            [self._exact_feature_param_row_locator(feature_code, vendor_name)], timeout=5
        ):
            self.reset_search()
            return False

        before_count = self.get_total_record_count()
        row = self.wait_visible(
            self._exact_feature_param_row_locator(feature_code, vendor_name), timeout=5
        )
        delete_opened = False
        if row is not False:
            checkboxes = row.find_elements(by.CSS_SELECTOR, "input[type='checkbox']")
            if checkboxes:
                if not checkboxes[0].is_selected():
                    self.driver.execute_script("arguments[0].click();", checkboxes[0])
                delete_opened = self._click_first_available_safe([self.delete_button], timeout=5)
        if not delete_opened:
            delete_opened = self._click_first_available_safe(
                [self._exact_feature_param_action_locator(feature_code, vendor_name, 2)],
                timeout=5,
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

        row_locator = self._exact_feature_param_row_locator(feature_code, vendor_name)
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
        current_count = self.get_total_record_count()
        still_exists = self.find_visible_now(row_locator) is not False
        self.reset_search()

        if not still_exists and (
            evidence
            or (
                before_count is not None
                and current_count is not None
                and current_count < before_count
            )
        ):
            return True
        return False
