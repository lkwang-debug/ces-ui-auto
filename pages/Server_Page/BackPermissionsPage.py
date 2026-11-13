# -*- coding:utf-8 -*-
import re
import time

from selenium.webdriver.common.by import By as by
from selenium.webdriver.common.keys import Keys

from common.product_profile import detect_build_profile, profile_entry
from conf.conf import ConfigManager
from pages.Index_Page.index import LoginPage
from common.ui_state import wait_query_finished


class BackPermissionsManagerPage(LoginPage):
    @property
    def back_permissions_route(self):
        entry = profile_entry(
            "back_permissions", detect_build_profile(ConfigManager.HST_URL)
        )
        return entry["route"]

    sidebar_menu_root = (by.CSS_SELECTOR, "aside ul.ant-menu")
    sidebar_expand_button = (by.CSS_SELECTOR, "aside .trigger.anticon-menu-unfold")

    search_input = (by.XPATH, "//main//input[@placeholder='请输入搜索内容']")
    search_button = (
        by.XPATH,
        "//main//input[@placeholder='请输入搜索内容']"
        "/ancestor::span[contains(@class,'ant-input-search')]//button | "
        "//main//button[contains(@class,'search-btn')]",
    )
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

    def _visible_modal_inputs(self, modal_title, timeout=10):
        modal = self.wait_visible(self._modal_locator(modal_title), timeout=timeout)
        if modal is False:
            return []
        inputs = []
        for element in modal.find_elements(by.XPATH, ".//input"):
            try:
                if element.is_displayed():
                    inputs.append(element)
            except Exception:
                continue
        return inputs

    def _replace_visible_modal_input(self, modal_title, input_index, value, timeout=10):
        end = time.time() + timeout
        while time.time() < end:
            inputs = self._visible_modal_inputs(modal_title, timeout=2)
            if len(inputs) >= input_index:
                element = inputs[input_index - 1]
                try:
                    element.click()
                    element.send_keys(Keys.CONTROL, "a")
                    element.send_keys(Keys.DELETE)
                    time.sleep(0.2)
                    element.send_keys(str(value))
                    time.sleep(0.2)
                    return (element.get_attribute("value") or "") == str(value)
                except Exception:
                    pass
            time.sleep(0.2)
        return False

    def _modal_permission_checkbox_locator(self, modal_title, permission_name):
        return (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{modal_title}']]"
            f"//span[contains(@class,'ant-tree-title') and normalize-space()='{permission_name}']"
            "/ancestor::li[1]//span[contains(@class,'ant-tree-checkbox')]",
        )

    def _modal_action_button_locator(self, modal_title, button_text):
        return (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{modal_title}']]"
            f"//button[normalize-space()='{button_text}']",
        )

    def _exact_role_row_locator(self, role_name):
        return (
            by.XPATH,
            f"//table//tbody//tr[td[4][normalize-space()='{role_name}']]",
        )

    def _exact_role_desc_cell_locator(self, role_name):
        return (
            by.XPATH,
            f"//table//tbody//tr[td[4][normalize-space()='{role_name}']]/td[5]",
        )

    def _exact_role_action_image_locator(self, role_name, action_index):
        return (
            by.XPATH,
            f"(//table//tbody//tr[td[4][normalize-space()='{role_name}']]"
            f"//td[last()]//img)[{action_index}]",
        )

    def wait_for_operation_result(self, expected_text=None, timeout=20):
        if expected_text:
            return self.wait_text_contains(self.save_result, expected_text, timeout=timeout)
        return self.wait_visible(self.save_result, timeout=timeout) is not False

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

    def _dispatch_mouse_click(self, element):
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", element
        )
        try:
            rect = self.driver.execute_script(
                """
                const r = arguments[0].getBoundingClientRect();
                return {x: r.x, y: r.y, width: r.width, height: r.height};
                """,
                element,
            )
            center_x = int(rect["x"] + rect["width"] / 2)
            center_y = int(rect["y"] + rect["height"] / 2)
            self.driver.execute_cdp_cmd(
                "Input.dispatchMouseEvent",
                {"type": "mouseMoved", "x": center_x, "y": center_y, "button": "none"},
            )
            self.driver.execute_cdp_cmd(
                "Input.dispatchMouseEvent",
                {
                    "type": "mousePressed",
                    "x": center_x,
                    "y": center_y,
                    "button": "left",
                    "clickCount": 1,
                },
            )
            self.driver.execute_cdp_cmd(
                "Input.dispatchMouseEvent",
                {
                    "type": "mouseReleased",
                    "x": center_x,
                    "y": center_y,
                    "button": "left",
                    "clickCount": 1,
                },
            )
            return True
        except Exception:
            try:
                element.click()
                return True
            except Exception:
                try:
                    self.driver.execute_script("arguments[0].click();", element)
                    return True
                except Exception:
                    return False

    def _click_role_action(self, role_name, action_index, timeout=8):
        locator = self._exact_role_action_image_locator(role_name, action_index)
        end = time.time() + timeout
        while time.time() < end:
            for element in self.driver.find_elements(*locator):
                try:
                    if not element.is_displayed():
                        continue
                    if self._dispatch_mouse_click(element):
                        return True
                except Exception:
                    continue
            time.sleep(0.2)
        return False

    def _enter_back_permissions_via_route(self):
        current_url = self.driver.current_url or ""
        if "#" in current_url:
            base_url = current_url.split("#", 1)[0]
        else:
            base_url = current_url.rstrip("/") + "/"
        if not base_url:
            base_url = self.url
        self.driver.get(base_url + self.back_permissions_route)
        self.wait_for_document_ready(timeout=5)
        time.sleep(0.3)

    def _hard_reload_back_permissions_page(self):
        self._enter_back_permissions_via_route()
        self.driver.refresh()
        self.wait_for_document_ready(timeout=5)
        time.sleep(0.5)
        return True

    def _ensure_page_ready(self):
        if self.back_permissions_route not in (self.driver.current_url or ''):
            return self.common_enter_back_permissions()
        ready_locators = [self.search_input, self.add_button, self.delete_button]
        if self._visible_in_any(ready_locators, timeout=2):
            return True
        self._hard_reload_back_permissions_page()
        if self._visible_in_any(ready_locators, timeout=5):
            return True
        return self.common_enter_back_permissions()

    def common_enter_back_permissions(self):
        self.common_login()
        self.dismiss_intro_if_present()
        self._dismiss_blocking_layers()
        self._ensure_sidebar_expanded(timeout=8)
        self._enter_back_permissions_via_route()
        ready_locators = [self.search_input, self.add_button, self.delete_button]
        if not self._visible_in_any(ready_locators, timeout=10):
            raise AssertionError("Failed to enter back permissions page")
        return True

    def submit_search(self):
        started=self.driver.execute_script('return performance.now()')
        if not self._click_first_available_safe([self.search_button],timeout=2) or not wait_query_finished(self,started):
            raise AssertionError('后台角色查询未完成')

    def reset_search(self):
        self._ensure_page_ready()
        self.clear_by_javascript(self.search_input)
        self.submit_search()
        return True

    def _search_keyword(self, keyword):
        self._ensure_page_ready()
        if self.wait_visible(self.search_input, timeout=8) is False:
            self._hard_reload_back_permissions_page()
            if self.wait_visible(self.search_input, timeout=10) is False:
                return False
        self.clear_by_javascript(self.search_input)
        self.send_keys(self.search_input, keyword)
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

    def search_role(self, role_name):
        self._ensure_page_ready()
        self._search_keyword(role_name)
        found = self._visible_in_any([self._exact_role_row_locator(role_name)], timeout=5)
        self.reset_search()
        return found

    def add_role(self, role_name, role_desc, permission_names=None, result="操作成功"):
        if permission_names is None:
            permission_names = ["系统信息"]
        self._ensure_page_ready()
        self.reset_search()
        before_count = self.get_total_record_count()
        if not self._click_first_available_safe([self.add_button], timeout=5):
            return False

        add_modal = self._modal_locator("新增角色")
        if self.wait_visible(add_modal, timeout=10) is False:
            return False

        if not self._replace_visible_modal_input("新增角色", 1, role_name, timeout=10):
            return False
        if not self._replace_visible_modal_input("新增角色", 2, role_desc, timeout=10):
            return False

        for permission_name in permission_names:
            self._click_first_available_safe(
                [self._modal_permission_checkbox_locator("新增角色", permission_name)],
                timeout=5,
            )

        if not self._click_first_available_safe(
            [self._modal_action_button_locator("新增角色", "保 存")], timeout=5
        ):
            return False

        toast_ok = self.wait_for_operation_result(result, timeout=8)
        after_count = None
        if before_count is not None:
            after_count = self.wait_for_record_count_change(before_count, timeout=10)

        if toast_ok:
            return self.search_role(role_name)
        if before_count is not None and after_count is not None and after_count > before_count:
            return self.search_role(role_name)
        return self.search_role(role_name)

    def modify_role_description(self, role_name, new_desc, result="修改成功"):
        self._ensure_page_ready()
        self._search_keyword(role_name)
        if not self._visible_in_any([self._exact_role_row_locator(role_name)], timeout=5):
            self.reset_search()
            return False

        if not self._click_role_action(role_name, 2, timeout=8):
            self.reset_search()
            return False

        edit_modal = self._modal_locator("编辑角色")
        if self.wait_visible(edit_modal, timeout=10) is False:
            self.reset_search()
            return False

        if not self._replace_visible_modal_input("编辑角色", 2, new_desc, timeout=10):
            self.reset_search()
            return False

        if not self._click_first_available_safe(
            [self._modal_action_button_locator("编辑角色", "保 存")], timeout=5
        ):
            self.reset_search()
            return False

        toast_ok = self.wait_for_operation_result(result, timeout=8)
        self._search_keyword(role_name)
        desc_ok = self.get_text_assert(new_desc, self._exact_role_desc_cell_locator(role_name))
        self.reset_search()
        return toast_ok or desc_ok

    def delete_role(self, role_name, result="删除成功"):
        self._ensure_page_ready()
        self._search_keyword(role_name)
        if not self._visible_in_any([self._exact_role_row_locator(role_name)], timeout=5):
            self.reset_search()
            return False

        before_count = self.get_total_record_count()
        if not self._click_role_action(role_name, 3, timeout=8):
            self.reset_search()
            return False

        confirm_locators = [
            (by.XPATH, "//div[contains(@class,'ant-modal-confirm')]//button[normalize-space()='确 定' or normalize-space()='确定']"),
            (by.XPATH, "//div[contains(@class,'ant-modal-content')][.//*[normalize-space()='提示']]//button[normalize-space()='确 定' or normalize-space()='确定']"),
        ]
        if not self._click_first_available_safe(confirm_locators, timeout=10):
            self.reset_search()
            return False

        toast_ok = self.wait_for_operation_result(result, timeout=8)
        after_count = None
        if before_count is not None:
            after_count = self.wait_for_record_count_change(before_count, timeout=10)

        self._search_keyword(role_name)
        still_exists = self._visible_in_any([self._exact_role_row_locator(role_name)], timeout=3)
        self.reset_search()

        if not still_exists:
            return True
        if before_count is not None and after_count is not None and after_count < before_count:
            return True
        return toast_ok and not still_exists
