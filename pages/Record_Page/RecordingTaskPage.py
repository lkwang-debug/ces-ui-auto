# -*- coding: utf-8 -*-
import re

from pages.FeatureActionsPage import FeatureActionsPage
from common.runtime_artifacts import clean_directory, wait_for_download, prepare_download
from conf.conf import ConfigManager
from common.ui_state import click_toolbar_search, wait_query_finished
from selenium.webdriver.common.keys import Keys


class RecordingTaskPage(FeatureActionsPage):
    group_name, item_name = "录制管理", "录制任务管理"

    def open_tasks(self):
        page = self.open_page(self.group_name, self.item_name)
        return page or self.open_page(self.group_name, self.item_name)

    def search_task(self, keyword):
        # The toolbar searches by meeting-room ID. Prefer an ID embedded in a
        # configured full task name; otherwise resolve the newest visible task
        # containing the cross-version keyword and read its room ID.
        embedded_id = re.search(r"_(\d{4,})_", keyword)
        room_id = embedded_id.group(1) if embedded_id else ""
        if not room_id:
            target_row = self._visible_row_containing(keyword)
            if target_row is None:
                return False
            cells = target_row.find_elements("css selector", "td")
            if len(cells) < 2:
                return False
            room_id = (cells[1].text or "").strip()
        if not room_id:
            return False
        # The toolbar filters by meeting-room ID rather than recording-file
        # name. Preserve it so the download targets the same rerendered row.
        self._target_room_id = room_id
        self._target_keyword = keyword
        inputs = [
            item for item in self.driver.find_elements(
                "css selector", "main input[placeholder*='搜索']"
            )
            if item.is_displayed() and item.is_enabled() and not item.get_attribute("readonly")
        ]
        if not inputs:
            return False
        target = inputs[0]
        target.click()
        target.send_keys(Keys.CONTROL, 'a')
        target.send_keys(Keys.DELETE)
        target.send_keys(room_id)
        if (target.get_attribute('value') or '') != room_id:
            return False
        started = self.driver.execute_script("return performance.now()")
        if not click_toolbar_search(self.driver, target):
            return False
        return wait_query_finished(self, started) and self.wait_until(
            lambda: self._target_row_after_search(keyword) is not None,
            timeout=5,
            poll_frequency=.25,
        )

    def clear_search(self):
        clear_button = self.driver.execute_script(
            """
            return [...document.querySelectorAll('main button')].find(button =>
              button.offsetParent !== null &&
              (button.innerText || '').replace(/\\s/g, '') === '清空'
            ) || null;
            """
        )
        if clear_button is None:
            return False
        self.driver.execute_script("arguments[0].click()", clear_button)
        return self.wait_until(
            lambda: all(
                not (item.get_attribute("value") or "").strip()
                for item in self.driver.find_elements("css selector", "main input[placeholder]")
                if item.is_displayed() and item.get_attribute("placeholder")
            ),
            timeout=5,
        )

    def download_target_task(self, keyword):
        self.last_download_error = ""
        directory = prepare_download(self.driver)
        existing = {path.name for path in directory.iterdir()}
        row = self._target_row_after_search(getattr(self, "_target_keyword", keyword))
        if row is None:
            self.last_download_error = "筛选后未找到目标录制任务"
            return None
        # The row's first action opens the recording-file modal. The modal's
        # last action image is the actual download control.
        inspect_control = self.driver.execute_script(
            "return arguments[0].querySelector('img');", row
        )
        if inspect_control is None:
            self.last_download_error = "目标录制任务没有查看图标"
            return None
        self.driver.execute_script("arguments[0].click()", inspect_control)
        modal = self.wait_until(
            lambda: next(
                (
                    item
                    for item in self.driver.find_elements(
                        "css selector", ".ant-modal-content"
                    )
                    if item.is_displayed()
                ),
                None,
            ),
            timeout=8,
        )
        if modal is None:
            self.last_download_error = "点击查看图标后没有出现录制文件弹窗"
            return None
        download_control = self.wait_until(
            lambda: self.driver.execute_script(
                "return arguments[0].querySelector('i.down,.anticon-download,[data-icon=download]');",
                modal,
            ),
            timeout=5,
        )
        if download_control is False:
            self.last_download_error = "录制文件弹窗没有下载图标"
            return None
        self.driver.execute_script("arguments[0].click()", download_control)
        downloaded = wait_for_download(directory, existing, timeout=30, driver=self.driver)
        if downloaded is None:
            self.last_download_error = "已点击下载图标，但下载目录未出现完成文件"
        else:
            close = self.driver.execute_script(
                "return arguments[0].querySelector('.ant-modal-close');", modal
            )
            if close is not None:
                self.driver.execute_script("arguments[0].click()", close)
                self.wait_until(lambda: not modal.is_displayed(), timeout=3)
        return downloaded

    def target_task_is_visible(self):
        return self._target_row_after_search(getattr(self, "_target_keyword", "")) is not None

    def _visible_row_containing(self, keyword):
        return next(
            (
                row for row in self.driver.find_elements("css selector", "main table tbody tr")
                if row.is_displayed()
                and not "ant-table-measure-row" in (row.get_attribute("class") or "")
                and keyword in (row.get_attribute("textContent") or "")
            ),
            None,
        )

    def _target_row_after_search(self, keyword=""):
        room_id = getattr(self, "_target_room_id", "")
        if not room_id:
            return None
        return self.driver.execute_script(
            """
            const expected = arguments[0];
            const keyword = arguments[1];
            const rows = [...document.querySelectorAll('main table tbody tr')]
              .filter(row => row.offsetParent !== null && !row.classList.contains('ant-table-measure-row'));
            return rows.find(row => {
              const cells = row.querySelectorAll('td');
              // innerText inserts visual line breaks into a long task name.
              // textContent preserves the configured recording-file identity.
              const text = row.textContent || '';
              return cells.length > 1 && cells[1].innerText.trim() === expected
                && (!keyword || text.includes(keyword));
            }) || null;
            """,
            room_id,
            keyword,
        )
