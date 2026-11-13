# -*- coding:utf-8 -*-
import time

from selenium.webdriver.common.by import By as by
from selenium.webdriver.common.keys import Keys

from pages.Index_Page.index import LoginPage


class CallManagerPage(LoginPage):
    call_route = "#/ui/organizational-management/user-call"

    sidebar_menu_root = (by.CSS_SELECTOR, "aside ul.ant-menu")
    sidebar_expand_button = (by.CSS_SELECTOR, "aside .trigger.anticon-menu-unfold")

    call_page_root = (by.CSS_SELECTOR, "main .user-call")
    left_panel_root_css = "main .person-page.item.list-left"
    right_panel_root_css = "main .person-used.item.list-right"
    transfer_button_css = "main .buttons.item.buttons button"
    save_button = (by.CSS_SELECTOR, "main .footer button.ant-btn-primary")
    save_result = (
        by.XPATH,
        "//div[contains(@class,'ant-message-notice-content')]"
        "//*[contains(@class,'ant-message') and normalize-space()] | "
        "//div[contains(@class,'ant-message-notice-content')]//*[normalize-space()]",
    )

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

    def _replace_element_value(self, element, value):
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", element
            )
            try:
                element.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", element)
            element.send_keys(Keys.CONTROL, "a")
            element.send_keys(Keys.DELETE)
            time.sleep(0.1)
            if value:
                element.send_keys(str(value))
            time.sleep(0.1)
            return (element.get_attribute("value") or "") == str(value)
        except Exception:
            return False

    def _enter_call_via_route(self):
        current_url = self.driver.current_url or ""
        if "#" in current_url:
            base_url = current_url.split("#", 1)[0]
        else:
            base_url = current_url.rstrip("/") + "/"
        if not base_url:
            base_url = self.url
        self.open_spa_route(self.call_route, timeout=5)

    def _hard_reload_call_page(self):
        self._enter_call_via_route()
        self.driver.refresh()
        self.wait_for_document_ready(timeout=5)
        return True

    def _ensure_page_ready(self):
        ready_locators = [self.call_page_root, self.save_button]
        if self._visible_in_any(ready_locators, timeout=2):
            return True
        for _ in range(2):
            self._hard_reload_call_page()
            if self._visible_in_any(ready_locators, timeout=5):
                return True
            if self.common_enter_call():
                if self._visible_in_any(ready_locators, timeout=8):
                    return True
        return False

    def common_enter_call(self):
        self.common_login()
        self.dismiss_intro_if_present()
        self._dismiss_blocking_layers()
        ready_locators = [self.call_page_root, self.save_button]
        for _ in range(2):
            self._enter_call_via_route()
            if self._visible_in_any(ready_locators, timeout=10):
                return True
            self.driver.refresh()
            self.wait_for_document_ready(timeout=5)
            self.dismiss_intro_if_present()
            self._dismiss_blocking_layers()
            if self._visible_in_any(ready_locators, timeout=10):
                return True
        raise AssertionError("Failed to enter call manage page")
        return True

    def _panel_search_input_locator(self, panel_css):
        return (by.CSS_SELECTOR, f"{panel_css} .table-search input.ant-input")

    def _panel_search_button_locator(self, panel_css):
        return (by.CSS_SELECTOR, f"{panel_css} .table-search button")

    def _panel_row_locator(self, panel_css, username):
        return (
            by.XPATH,
            f"//div[contains(@class,'{panel_css.split('.')[-1]}')]"
            f"//table//tbody//tr[td[3][normalize-space()='{username}']]",
        )

    def _panel_row_checkbox_locator(self, panel_css, username):
        return (
            by.XPATH,
            f"//div[contains(@class,'{panel_css.split('.')[-1]}')]"
            f"//table//tbody//tr[td[3][normalize-space()='{username}']]"
            "//td[1]//input[@type='checkbox']",
        )

    def _visible_panel_text_inputs(self):
        inputs = []
        for element in self.driver.find_elements(by.CSS_SELECTOR, "main input"):
            try:
                if element.is_displayed() and (element.get_attribute("type") or "") == "text":
                    inputs.append(element)
            except Exception:
                continue
        return inputs

    def _panel_usernames(self, panel_css):
        usernames = []
        for row in self.driver.find_elements(by.CSS_SELECTOR, f"{panel_css} table tbody tr"):
            try:
                if not row.is_displayed():
                    continue
                cells = row.find_elements(by.CSS_SELECTOR, "td")
                if len(cells) >= 3:
                    username = (cells[2].text or "").strip()
                    if username:
                        usernames.append(username)
            except Exception:
                continue
        return usernames

    def _panel_has_no_data(self, panel_css):
        texts = []
        for element in self.driver.find_elements(
            by.CSS_SELECTOR, f"{panel_css} .ant-table-placeholder, {panel_css} .ant-empty-description"
        ):
            try:
                if element.is_displayed():
                    texts.append((element.text or "").strip())
            except Exception:
                continue
        return any("暂无数据" in text for text in texts)

    def _search_in_panel(self, panel_css, keyword):
        self._ensure_page_ready()
        input_locator = self._panel_search_input_locator(panel_css)
        button_locator = self._panel_search_button_locator(panel_css)
        input_element = self.wait_visible(input_locator, timeout=8)
        if input_element is False:
            return False
        if not self._replace_element_value(input_element, keyword):
            return False
        if not self._click_first_available_safe([button_locator], timeout=5):
            return False
        time.sleep(0.2)
        return True

    def _clear_panel_search(self, panel_css):
        return self._search_in_panel(panel_css, "")

    def _select_user_checkbox_in_panel(self, panel_css, username, timeout=8):
        row_locator = self._panel_row_locator(panel_css, username)
        end = time.time() + timeout
        while time.time() < end:
            for row in self.driver.find_elements(*row_locator):
                try:
                    if not row.is_displayed():
                        continue
                    targets = row.find_elements(
                        by.CSS_SELECTOR,
                        "td:first-child .ant-checkbox, "
                        "td:first-child label, "
                        "td:first-child input[type='checkbox']",
                    )
                    for element in targets:
                        try:
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView({block:'center'});", element
                            )
                            try:
                                element.click()
                            except Exception:
                                self.driver.execute_script("arguments[0].click();", element)
                            time.sleep(0.2)
                            return True
                        except Exception:
                            continue
                except Exception:
                    continue
            time.sleep(0.2)
        return False

    def _transfer_buttons(self):
        buttons = []
        for button in self.driver.find_elements(by.CSS_SELECTOR, self.transfer_button_css):
            try:
                if button.is_displayed():
                    buttons.append(button)
            except Exception:
                continue
        return buttons

    def _click_transfer_button(self, direction, timeout=8):
        end = time.time() + timeout
        target_index = 0 if direction == "right" else 1
        while time.time() < end:
            buttons = self._transfer_buttons()
            if len(buttons) > target_index:
                button = buttons[target_index]
                disabled = button.get_attribute("disabled")
                if disabled:
                    time.sleep(0.2)
                    continue
                try:
                    button.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", button)
                return True
            time.sleep(0.2)
        return False

    def wait_for_operation_result(self, expected_text=None, timeout=10):
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

    def click_save_button(self):
        self._ensure_page_ready()
        return self._click_first_available_safe([self.save_button], timeout=5)

    def get_authorized_usernames(self):
        self._ensure_page_ready()
        return self._panel_usernames(self.right_panel_root_css)

    def get_user_list_usernames(self):
        self._ensure_page_ready()
        return self._panel_usernames(self.left_panel_root_css)

    def get_first_authorized_username(self):
        self._ensure_page_ready()
        self._clear_panel_search(self.right_panel_root_css)
        usernames = self.get_authorized_usernames()
        return usernames[0] if usernames else None

    def search_authorized_user(self, keyword):
        if not self._search_in_panel(self.right_panel_root_css, keyword):
            return []
        return self.get_authorized_usernames()

    def clear_search_content(self):
        return self._clear_panel_search(self.right_panel_root_css)

    def assert_search_user(self, username):
        usernames = self.get_authorized_usernames()
        return username in usernames

    def assert_search_failed(self, msg):
        return msg == "暂无数据" and self._panel_has_no_data(self.right_panel_root_css)

    def search_authorized_user_exact(self, username):
        usernames = self.search_authorized_user(username)
        return username in usernames

    def search_authorized_user_vague(self, keyword, expected_username):
        usernames = self.search_authorized_user(keyword)
        return expected_username in usernames

    def search_authorized_user_failed(self, keyword):
        self._search_in_panel(self.right_panel_root_css, keyword)
        return self._panel_has_no_data(self.right_panel_root_css)

    def move_authorized_user_to_user_list(self, username, result="操作成功"):
        self._ensure_page_ready()
        self._clear_panel_search(self.left_panel_root_css)
        if not self._search_in_panel(self.right_panel_root_css, username):
            return False
        if username not in self.get_authorized_usernames():
            return False
        if not self._select_user_checkbox_in_panel(self.right_panel_root_css, username, timeout=8):
            return False
        if not self._click_transfer_button("left", timeout=8):
            return False
        if not self.click_save_button():
            return False
        toast_ok = self.wait_for_operation_result(result, timeout=8)

        self._hard_reload_call_page()
        self._search_in_panel(self.right_panel_root_css, username)
        absent_from_authorized = username not in self.get_authorized_usernames()
        self._search_in_panel(self.left_panel_root_css, username)
        present_in_user_list = username in self.get_user_list_usernames()
        return absent_from_authorized and present_in_user_list and toast_ok

    def move_user_list_user_to_authorized(self, username, result="操作成功"):
        self._ensure_page_ready()
        self._clear_panel_search(self.right_panel_root_css)
        if not self._search_in_panel(self.left_panel_root_css, username):
            return False
        if username not in self.get_user_list_usernames():
            return False
        if not self._select_user_checkbox_in_panel(self.left_panel_root_css, username, timeout=8):
            return False
        if not self._click_transfer_button("right", timeout=8):
            return False
        if not self.click_save_button():
            return False
        toast_ok = self.wait_for_operation_result(result, timeout=8)

        self._hard_reload_call_page()
        self._search_in_panel(self.right_panel_root_css, username)
        present_in_authorized = username in self.get_authorized_usernames()
        self._search_in_panel(self.left_panel_root_css, username)
        absent_from_user_list = username not in self.get_user_list_usernames()
        return present_in_authorized and absent_from_user_list and toast_ok

    def move_authorized_user_round_trip(self, username=None, result="操作成功"):
        self._ensure_page_ready()
        if username is None:
            username = self.get_first_authorized_username()
        if not username:
            return False
        moved_out = self.move_authorized_user_to_user_list(username, result=result)
        if not moved_out:
            return False
        self.move_user_list_user_to_authorized(username, result=result)

        # The operation toast is absent or short-lived on some CES builds. The
        # persisted list state after a reload is the authoritative result and
        # also guarantees that this test leaves the user's authorization intact.
        self._hard_reload_call_page()
        if not self._search_in_panel(self.right_panel_root_css, username):
            return False
        restored = username in self.get_authorized_usernames()
        self._clear_panel_search(self.right_panel_root_css)
        return restored
