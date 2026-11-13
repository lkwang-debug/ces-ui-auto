# -*- coding: utf-8 -*-
import allure

from pages.FeatureActionsPage import FeatureActionsPage


class TerminalLogPage(FeatureActionsPage):
    group_name, item_name = "日志管理", "终端日志"
    def open_logs(self): return self.open_page(self.group_name, self.item_name)

    def validate_configured_log(self, configured_username, device_id, log_type):
        if not self.open_logs():
            return False
        row = self._row_by_device(device_id)
        if row is None and configured_username:
            self._search_employee(configured_username)
            row = self._row_by_device(device_id)
        if row is None:
            return False
        cells = row.find_elements("css selector", "td")
        if len(cells) < 2:
            return False
        actual_username = (cells[0].text or "").strip()
        row_text = row.get_attribute("textContent") or ""
        if not actual_username or device_id not in row_text:
            return False
        if log_type not in {"终端日志", "终端巡检日志"} and log_type not in row_text:
            return False
        if actual_username != configured_username:
            allure.attach(
                f"配置账号：{configured_username}\n设备实际账号：{actual_username}",
                "跨环境终端日志账号解析",
                allure.attachment_type.TEXT,
            )
        if not self._search_employee(actual_username):
            return False
        filtered_rows = self._visible_rows()
        return bool(filtered_rows) and all(
            actual_username in (item.get_attribute("textContent") or "")
            for item in filtered_rows
        ) and self._row_by_device(device_id) is not None

    def _search_employee(self, username):
        inputs = [
            item for item in self.driver.find_elements("css selector", "main input")
            if item.is_displayed() and item.is_enabled() and not item.get_attribute("readonly")
        ]
        if not inputs:
            return False
        target = inputs[0]
        target.click()
        target.clear()
        target.send_keys(username)
        return self.submit_and_wait(username)

    def _visible_rows(self):
        self.wait_loading_finished(timeout=3)
        rows = []
        for row in self.driver.find_elements("css selector", "main table tbody tr"):
            try:
                if (
                    row.is_displayed()
                    and "ant-table-measure-row" not in (row.get_attribute("class") or "")
                    and row.find_elements("css selector", "td")
                ):
                    rows.append(row)
            except Exception:
                continue
        return rows

    def _row_by_device(self, device_id):
        return next(
            (
                row for row in self._visible_rows()
                if device_id in (row.get_attribute("textContent") or "")
            ),
            None,
        )
    def open_check(self):
        # In 4.39.7 the check page is the sibling "terminal inspection log"
        # menu, not an action link in an ordinary terminal-log row.
        inspection = self.driver.execute_script(
            """
            return [...document.querySelectorAll('li.ant-menu-item')].find(item =>
              item.offsetParent !== null &&
              (item.innerText || '').trim() === arguments[0]
            ) || null;
            """,
            "终端巡检日志",
        )
        if inspection is None:
            return False
        self.driver.execute_script("arguments[0].click()", inspection)
        return bool(self.wait_until(
            lambda: "巡检状态" in self._main_text()
            and "网络检测" in self._main_text(),
            timeout=6,
        ))
