# -*- coding:utf-8 -*-
import shutil
import time
from pathlib import Path

from selenium.webdriver.common.by import By as by

from common.runtime_artifacts import clean_directory, wait_for_download, prepare_download, configure_download_directory
from conf.conf import ConfigManager
from pages.Index_Page.index import LoginPage


class DataManagePage(LoginPage):
    data_manage_route = "#/ui/host-management/data-management"

    sidebar_menu_root = (by.CSS_SELECTOR, "aside ul.ant-menu")
    sidebar_expand_button = (by.CSS_SELECTOR, "aside .trigger.anticon-menu-unfold")

    page_root = (by.CSS_SELECTOR, "main .layout-content__main")
    page_title = (by.XPATH, "//main//*[normalize-space()='数据管理']")
    clear_button = (by.XPATH, "//main//button[normalize-space()='清 空']")
    add_button = (by.XPATH, "//main//button[normalize-space()='新增']")
    delete_button = (by.XPATH, "//main//button[normalize-space()='删除']")
    upload_button = (by.XPATH, "//main//button[normalize-space()='上传备份文件']")
    date_input = (
        by.CSS_SELECTOR,
        "main input.ant-calendar-picker-input.ant-input, "
        "main .ant-picker input[placeholder='备份日期'], "
        "main input[placeholder='备份日期']",
    )
    table_headers = (by.CSS_SELECTOR, "main table thead th")
    table_rows = (by.CSS_SELECTOR, "main table tbody tr")
    table_placeholder = (by.CSS_SELECTOR, "main .ant-table-placeholder")
    modal_content = (by.CSS_SELECTOR, ".ant-modal-content")
    modal_close_button = (by.CSS_SELECTOR, ".ant-modal-close")
    modal_primary_button = (
        by.CSS_SELECTOR,
        ".ant-modal-content button.ant-btn-primary",
    )
    modal_default_button = (
        by.CSS_SELECTOR,
        ".ant-modal-content button.ant-btn:not(.ant-btn-primary)",
    )
    upload_file_input = (by.CSS_SELECTOR, ".ant-modal-content input[type='file']")
    download_actions = (
        by.XPATH,
        ".//button[contains(normalize-space(.), '下载')] | "
        ".//a[contains(normalize-space(.), '下载')] | "
        ".//*[@title='下载']",
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

    def _enter_data_manage_via_route(self):
        current_url = self.driver.current_url or ""
        if "#" in current_url:
            base_url = current_url.split("#", 1)[0]
        else:
            base_url = current_url.rstrip("/") + "/"
        if not base_url:
            base_url = self.url
        self.driver.get(base_url + self.data_manage_route)
        self.wait_for_document_ready(timeout=5)
        time.sleep(0.3)

    def _hard_reload_data_manage_page(self):
        self._enter_data_manage_via_route()
        self.driver.refresh()
        self.wait_for_document_ready(timeout=5)
        time.sleep(0.5)
        return True

    def _is_on_data_manage_page(self):
        return self.data_manage_route in (self.driver.current_url or "")

    def _ensure_page_ready(self):
        if self.data_manage_route not in (self.driver.current_url or ''):
            return self.common_enter_data()
        ready_locators = [
            self.add_button,
            self.upload_button,
            self.date_input,
        ]
        if self._is_on_data_manage_page() and self._visible_in_any(ready_locators, timeout=2):
            return True
        for _ in range(2):
            self._hard_reload_data_manage_page()
            if self._is_on_data_manage_page() and self._visible_in_any(ready_locators, timeout=5):
                return True
            if self.common_enter_data():
                if self._is_on_data_manage_page() and self._visible_in_any(ready_locators, timeout=8):
                    return True
        return False

    def common_enter_data(self):
        self.common_login()
        self.dismiss_intro_if_present()
        self._dismiss_blocking_layers()
        self._ensure_sidebar_expanded(timeout=8)
        ready_locators = [
            self.add_button,
            self.upload_button,
            self.date_input,
        ]
        for _ in range(2):
            self._enter_data_manage_via_route()
            if self._is_on_data_manage_page() and self._visible_in_any(ready_locators, timeout=10):
                return True
            self.driver.refresh()
            self.wait_for_document_ready(timeout=5)
            time.sleep(0.5)
            self.dismiss_intro_if_present()
            self._dismiss_blocking_layers()
            if self._is_on_data_manage_page() and self._visible_in_any(ready_locators, timeout=10):
                return True
        raise AssertionError("Failed to enter data manage page")
        return True

    def get_table_headers(self):
        self._ensure_page_ready()
        headers = self._collect_table_headers()
        if self._is_expected_table_headers(headers):
            return headers

        for _ in range(2):
            self._hard_reload_data_manage_page()
            self._dismiss_blocking_layers()
            self._ensure_page_ready()
            headers = self._collect_table_headers()
            if self._is_expected_table_headers(headers):
                return headers
            if self.common_enter_data():
                headers = self._collect_table_headers()
                if self._is_expected_table_headers(headers):
                    return headers
        return headers

    def has_no_data(self):
        self._ensure_page_ready()
        for element in self.driver.find_elements(*self.table_placeholder):
            try:
                if element.is_displayed() and "暂无数据" in (element.text or ""):
                    return True
            except Exception:
                continue
        return False

    def get_visible_row_count(self):
        self._ensure_page_ready()
        count = 0
        for row in self.driver.find_elements(*self.table_rows):
            try:
                if row.is_displayed():
                    count += 1
            except Exception:
                continue
        return count

    def get_date_input_placeholder(self):
        self._ensure_page_ready()
        element = self.wait_visible(self.date_input, timeout=8)
        if element is False:
            return ""
        return element.get_attribute("placeholder") or ""

    def open_add_backup_dialog(self):
        self._ensure_page_ready()
        self._dismiss_blocking_layers()
        if not self._click_first_available_safe([self.add_button], timeout=5):
            return ""
        modal = self.wait_visible(self.modal_content, timeout=5)
        if modal is False:
            return ""
        return " ".join((modal.text or "").split())

    def cancel_active_dialog(self):
        if self._click_first_available_safe([self.modal_default_button], timeout=3):
            return self.wait_for_dialog_closed(timeout=3)
        return self.close_active_dialog()

    def close_active_dialog(self):
        if self._click_first_available_safe(
            [self.modal_close_button, self.modal_default_button], timeout=3
        ):
            return self.wait_for_dialog_closed(timeout=3)
        return False

    def open_upload_dialog(self):
        self._ensure_page_ready()
        self._dismiss_blocking_layers()

        if self._click_first_available_safe([self.upload_button], timeout=5):
            modal = self.wait_visible(self.modal_content, timeout=3)
            if modal is not False:
                return " ".join((modal.text or "").split())

        self._hard_reload_data_manage_page()
        self._dismiss_blocking_layers()
        if not self._click_first_available_safe([self.upload_button], timeout=5):
            return ""
        modal = self.wait_visible(self.modal_content, timeout=5)
        if modal is False:
            return ""
        return " ".join((modal.text or "").split())

    def get_upload_accept_extensions(self):
        self._ensure_page_ready()
        end = time.time() + 5
        while time.time() < end:
            for element in self.driver.find_elements(*self.upload_file_input):
                try:
                    accept = element.get_attribute("accept") or ""
                    if accept:
                        return accept
                except Exception:
                    continue
            time.sleep(0.2)
        return ""

    def download_existing_backup(self, timeout=30):
        """Download one existing backup and return its table name and local path."""
        try:
            return self._download_existing_backup(timeout)
        finally:
            # Covers missing data, rejected download and exceptions, including
            # failures before the test body can enter its own cleanup block.
            self.restore_default_download_dir()

    def _download_existing_backup(self, timeout):
        self._ensure_page_ready()
        directory = self._prepare_backup_download_dir()
        before = {path.name for path in directory.iterdir()}

        for row in self.driver.find_elements(*self.table_rows):
            try:
                if not row.is_displayed():
                    continue
                cells = [cell.text.strip() for cell in row.find_elements(by.CSS_SELECTOR, "td")]
                file_name = next((text for text in cells if text.endswith((".sql", ".dmp"))), "")
                if not file_name:
                    continue
                action = self._first_visible_in(row, self.download_actions)
                if action is None:
                    continue
                self._safe_click(action)
                downloaded = wait_for_download(
                    directory,
                    existing=before,
                    extensions={".sql", ".dmp"},
                    timeout=timeout,
                    driver=self.driver,
                )
                if downloaded is not None:
                    return {"file_name": file_name, "path": downloaded, "directory": directory}
            except Exception:
                continue
        return None

    def make_unique_upload_copy(self, source_path):
        source = Path(source_path)
        directory = Path(source.parent)
        target = directory / f"uiauto_upload_{int(time.time_ns())}{source.suffix.lower()}"
        shutil.copy2(source, target)
        return target

    def upload_backup_file(self, file_path, timeout=30):
        upload_file = Path(file_path)
        if upload_file.suffix.lower() not in {".sql", ".dmp"}:
            raise AssertionError(f"不支持的备份文件类型：{upload_file.suffix}")
        dialog_text = self.open_upload_dialog()
        if not dialog_text:
            return None
        existing_names = set(self.get_backup_file_names())
        file_input = self.wait_until(
            lambda: next(
                iter(self.driver.find_elements(*self.upload_file_input)), None
            ),
            timeout=5,
            poll_frequency=0.2,
        )
        if file_input is False or file_input is None:
            return None
        file_input.send_keys(str(upload_file.resolve()))
        modal = self.wait_visible(self.modal_content, timeout=3)
        if modal is False:
            return None
        if not self._click_first_available_safe([self.modal_primary_button], timeout=5):
            return None
        if not self.wait_for_dialog_closed(timeout=10):
            return None

        def uploaded_record():
            current_names = self.get_backup_file_names()
            new_names = [name for name in current_names if name not in existing_names]
            if new_names:
                return {"file_name": new_names[0], "all_names": current_names}
            return None

        return self.wait_until(uploaded_record, timeout=timeout, poll_frequency=0.3)

    def get_backup_file_names(self):
        names = []
        for row in self.driver.find_elements(*self.table_rows):
            try:
                if not row.is_displayed():
                    continue
                cells = row.find_elements(by.CSS_SELECTOR, "td")
                for cell in cells:
                    name = (cell.text or "").strip()
                    if name:
                        names.append(name)
                        break
            except Exception:
                continue
        return names

    def delete_backup_by_name(self, file_name):
        self._ensure_page_ready()
        for row in self.driver.find_elements(*self.table_rows):
            try:
                if not row.is_displayed() or file_name not in (row.text or ""):
                    continue
                delete = self._first_visible_in(
                    row,
                    (
                        by.XPATH,
                        ".//button[contains(normalize-space(.), '删除')] | "
                        ".//a[contains(normalize-space(.), '删除')] | .//*[@title='删除']",
                    ),
                )
                if delete is None:
                    buttons = [
                        button
                        for button in row.find_elements(by.CSS_SELECTOR, "button")
                        if button.is_displayed() and button.is_enabled()
                    ]
                    delete = buttons[-1] if buttons else None
                if delete is None:
                    return False
                self._safe_click(delete)
                if not self._click_first_available_safe([self.modal_primary_button], timeout=5):
                    return False
                return self.wait_until(
                    lambda: file_name not in self._table_text(), timeout=10, poll_frequency=0.3
                ) is not False
            except Exception:
                continue
        return True

    def restore_default_download_dir(self):
        return configure_download_directory(self.driver, ConfigManager.DOWNLOAD_DIR)

    def wait_for_dialog_closed(self, timeout=3):
        end = time.time() + timeout
        while time.time() < end:
            visible_modal = False
            for element in self.driver.find_elements(*self.modal_content):
                try:
                    if element.is_displayed():
                        visible_modal = True
                        break
                except Exception:
                    continue
            if not visible_modal:
                return True
            time.sleep(0.2)
        return False

    def _collect_table_headers(self):
        headers = []
        for element in self.driver.find_elements(*self.table_headers):
            try:
                if not element.is_displayed():
                    continue
                text = (element.text or "").strip()
                if text:
                    headers.append(text)
            except Exception:
                continue
        return headers

    def _is_expected_table_headers(self, headers):
        if len(headers) != 6:
            return False
        return headers[-1] == "操作"

    def _prepare_backup_download_dir(self):
        return prepare_download(self.driver, Path(ConfigManager.DOWNLOAD_DIR) / "data_backup")

    def _table_text(self):
        texts = []
        for row in self.driver.find_elements(*self.table_rows):
            try:
                if row.is_displayed():
                    texts.append(row.text or "")
            except Exception:
                continue
        return " ".join(texts)

    @staticmethod
    def _first_visible_in(parent, locator):
        for element in parent.find_elements(*locator):
            try:
                if element.is_displayed() and element.is_enabled():
                    return element
            except Exception:
                continue
        return None

    def _safe_click(self, element):
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        try:
            element.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", element)
