# -*- coding:utf-8 -*-
import json
import time

import allure
from selenium.webdriver.common.by import By as by

from pages.Index_Page.index import LoginPage
from conf.conf import ConfigManager
from common.runtime_artifacts import clean_directory, wait_for_download, prepare_download


class ServerLogPage(LoginPage):
    server_log_route = "#/ui/log-management/host-log"
    no_data_text = "暂无数据"

    sidebar_menu_root = (by.CSS_SELECTOR, "aside ul.ant-menu")
    sidebar_expand_button = (by.CSS_SELECTOR, "aside .trigger.anticon-menu-unfold")
    table_rows = (by.CSS_SELECTOR, "main table tbody tr")
    table_placeholder = (
        by.CSS_SELECTOR,
        "main .ant-table-placeholder, main .ant-empty-description",
    )
    receiver_button = (by.XPATH, "//main//button[normalize-space()='设置邮箱接收者']")
    modal_root = (by.CSS_SELECTOR, ".ant-modal-content")
    modal_close_button = (by.CSS_SELECTOR, ".ant-modal-close")

    meeting_server_tab = "会议服务器"
    web_server_tab = "Web服务器"
    node_server_tab = "节点服务器"
    warning_tab = "服务器告警"

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
                            "arguments[0].scrollIntoView({block:'center'});",
                            element,
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

    def _enter_server_log_via_route(self):
        current_url = self.driver.current_url or ""
        if "#" in current_url:
            base_url = current_url.split("#", 1)[0]
        else:
            base_url = current_url.rstrip("/") + "/"
        if not base_url:
            base_url = self.url
        self.open_spa_route(self.server_log_route, timeout=5)

    def _hard_reload_server_log_page(self):
        self._enter_server_log_via_route()
        self.driver.refresh()
        self.wait_for_document_ready(timeout=5)
        return True

    def _ensure_page_ready(self):
        ready_locators = [
            self._tab_locator(self.meeting_server_tab),
            self._tab_locator(self.web_server_tab),
            self._tab_locator(self.node_server_tab),
            self._tab_locator(self.warning_tab),
        ]
        if self._visible_in_any(ready_locators, timeout=2):
            return True
        self._hard_reload_server_log_page()
        if self._visible_in_any(ready_locators, timeout=5):
            return True
        return self.common_enter_server_log()

    def common_enter_server_log(self):
        self.common_login()
        self.dismiss_intro_if_present()
        self._dismiss_blocking_layers()
        self._enter_server_log_via_route()
        ready_locators = [
            self._tab_locator(self.meeting_server_tab),
            self._tab_locator(self.web_server_tab),
            self._tab_locator(self.node_server_tab),
            self._tab_locator(self.warning_tab),
        ]
        if not self._visible_in_any(ready_locators, timeout=10):
            raise AssertionError("Failed to enter server log page")
        return True

    def _tab_locator(self, tab_name):
        return (
            by.XPATH,
            f"//main//li[normalize-space()='{tab_name}']"
            f" | //main//*[contains(@class,'ant-tabs-tab') and normalize-space()='{tab_name}']"
            f" | //main//span[normalize-space()='{tab_name}']/ancestor::li[1]",
        )

    def switch_to_tab(self, tab_name):
        self._ensure_page_ready()
        clicked = self._click_first_available_safe([self._tab_locator(tab_name)], timeout=5)
        time.sleep(0.3)
        return clicked

    def get_visible_rows(self):
        self._ensure_page_ready()
        rows = []
        for row in self.driver.find_elements(*self.table_rows):
            try:
                if not row.is_displayed():
                    continue
                cells = [cell.text.strip() for cell in row.find_elements(by.CSS_SELECTOR, "td")]
                if cells:
                    rows.append(cells)
            except Exception:
                continue
        return rows

    def current_tab_has_no_data(self, timeout=3):
        self._ensure_page_ready()
        end = time.time() + timeout
        while time.time() < end:
            if self.get_visible_rows():
                return False
            for element in self.driver.find_elements(*self.table_placeholder):
                try:
                    if not element.is_displayed():
                        continue
                    text = (element.text or "").strip()
                    class_name = element.get_attribute("class") or ""
                    if self.no_data_text in text or "ant-empty" in class_name or "ant-table-placeholder" in class_name:
                        return True
                except Exception:
                    continue
            time.sleep(0.2)
        return False

    def meeting_server_rows_valid(self):
        self.switch_to_tab(self.meeting_server_tab)
        rows = self.get_visible_rows()
        return bool(rows) and all(len(row) >= 2 for row in rows)

    def web_server_rows_valid(self):
        self.switch_to_tab(self.web_server_tab)
        rows = self.get_visible_rows()
        return bool(rows) and all(len(row) >= 2 for row in rows)

    def node_server_rows_valid(self):
        self.switch_to_tab(self.node_server_tab)
        rows = self.get_visible_rows()
        return bool(rows) and all(len(row) >= 1 for row in rows)

    def open_warning_receiver_modal(self):
        self.switch_to_tab(self.warning_tab)
        if self.wait_visible(self.receiver_button, timeout=5) is False:
            return ""
        if not self._click_first_available_safe([self.receiver_button], timeout=5):
            return ""
        end = time.time() + 5
        while time.time() < end:
            for modal in self.driver.find_elements(*self.modal_root):
                try:
                    if modal.is_displayed():
                        return (modal.text or "").strip()
                except Exception:
                    continue
            time.sleep(0.2)
        return ""

    def close_receiver_modal(self):
        return self._click_first_available_safe([self.modal_close_button], timeout=5)

    def download_current_server_log(self):
        return self.download_server_log(self.meeting_server_tab)

    def download_server_log(self, tab_name):
        self.last_download_error = ""
        self._ensure_page_ready()
        if not self.switch_to_tab(tab_name):
            return None
        directory = prepare_download(self.driver)
        existing = {path.name for path in directory.iterdir()}
        downloads = (
            by.XPATH,
            "//main//tbody/tr[not(contains(@class,'ant-table-measure-row'))]"
            "//*[self::button or self::a][contains(normalize-space(.),'下载')]",
        )
        candidates = []
        for element in self.driver.find_elements(*downloads):
            try:
                if element.is_displayed() and element.is_enabled():
                    candidates.append(element)
            except Exception:
                continue
        attempts = []
        selected_candidates = candidates[:1] if tab_name == self.node_server_tab else candidates[:5]
        for index, element in enumerate(selected_candidates, 1):
            try:
                row = element.find_element(by.XPATH, "ancestor::tr[1]")
                row_text = (row.text or "").strip()
                href = element.get_attribute("href") or ""
                outer_html = element.get_attribute("outerHTML") or ""
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", element
                )
                try:
                    element.click()
                    click_method = "WebDriver点击"
                except Exception:
                    self.driver.execute_script("arguments[0].click();", element)
                    click_method = "JavaScript点击"
                # 节点服务器由后台跨节点打包，4.39.7 的网关超时边界约为 60 秒。
                # 等待必须覆盖该边界，才能区分慢下载、网关 504 和 UI 未触发。
                downloaded = wait_for_download(
                    directory,
                    existing,
                    {".log", ".txt", ".zip", ".gz", ".xlsx", ".csv"},
                    timeout=70 if tab_name == self.node_server_tab else 30,
                    driver=self.driver,
                )
                messages = self.driver.execute_script(
                    r"""
                    const visible = element => !!(element && element.offsetParent !== null);
                    return [...document.querySelectorAll(
                      '.ant-message-notice-content,.ant-notification-notice-message,.ant-modal-content'
                    )].filter(visible).map(element => (element.innerText || '').trim()).filter(Boolean);
                    """
                )
                try:
                    browser_logs = [
                        item
                        for item in self.driver.get_log("browser")
                        if item.get("level") in {"SEVERE", "WARNING"}
                    ][-10:]
                except Exception:
                    browser_logs = []
                backend_errors = [
                    item.get("message", "")
                    for item in browser_logs
                    if "/logger/v1/server/" in item.get("message", "")
                    and "Failed to load resource" in item.get("message", "")
                ]
                if backend_errors:
                    self.last_download_error = backend_errors[-1]
                network_logs = []
                try:
                    for item in self.driver.get_log("performance"):
                        payload = json.loads(item.get("message", "{}"))
                        message = payload.get("message", {})
                        method = message.get("method", "")
                        params = message.get("params", {})
                        if method == "Network.responseReceived":
                            response = params.get("response", {})
                            url = response.get("url", "")
                            if "log" in url.lower() or int(response.get("status", 0)) >= 400:
                                network_logs.append(
                                    {
                                        "method": method,
                                        "url": url,
                                        "status": response.get("status"),
                                        "mimeType": response.get("mimeType"),
                                    }
                                )
                        elif method == "Network.loadingFailed":
                            network_logs.append(
                                {
                                    "method": method,
                                    "error": params.get("errorText"),
                                    "blockedReason": params.get("blockedReason"),
                                }
                            )
                except Exception:
                    network_logs = []
                attempts.append(
                    {
                        "序号": index,
                        "日志行": row_text,
                        "链接": href,
                        "控件": outer_html,
                        "点击方式": click_method,
                        "下载结果": str(downloaded) if downloaded else "未生成文件",
                        "页面提示": messages,
                        "窗口数量": len(self.driver.window_handles),
                        "当前地址": self.driver.current_url,
                        "浏览器日志": browser_logs,
                        "网络日志": network_logs[-30:],
                    }
                )
                if downloaded is not None:
                    allure.attach(
                        json.dumps(attempts, ensure_ascii=False, indent=2),
                        f"{tab_name}日志下载过程",
                        allure.attachment_type.JSON,
                    )
                    return downloaded
                if any(
                    int(item.get("status") or 0) >= 500
                    for item in network_logs
                    if item.get("method") == "Network.responseReceived"
                ):
                    break
            except Exception as exc:
                attempts.append({"序号": index, "异常": repr(exc)})
        allure.attach(
            json.dumps(
                {
                    "标签": tab_name,
                    "可见下载按钮数": len(candidates),
                    "尝试记录": attempts,
                    "页面文本": self.driver.execute_script(
                        "return (document.querySelector('main')?.innerText || '').slice(0, 5000)"
                    ),
                },
                ensure_ascii=False,
                indent=2,
            ),
            f"{tab_name}日志下载失败诊断",
            allure.attachment_type.JSON,
        )
        if not self.last_download_error:
            self.last_download_error = f"{tab_name}下载操作未生成文件"
        return None

    def enter_operation_log(self):
        return self.common_enter_server_log()
