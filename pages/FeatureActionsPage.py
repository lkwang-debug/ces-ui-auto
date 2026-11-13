# -*- coding: utf-8 -*-
"""Reusable label-driven actions for CES list, log and statistic pages."""

from __future__ import annotations

from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from common.runtime_artifacts import clean_directory, wait_for_download, prepare_download
from conf.conf import ConfigManager
from pages.FeatureCatalogPage import FeatureCatalogPage


class FeatureActionsPage(FeatureCatalogPage):
    def open_page(self, group, item):
        return self.open_feature(group, item)

    def click_text(self, text, root="main", timeout=5):
        locator = (By.XPATH, f"//{root}//*[self::button or self::a or @role='button'][contains(normalize-space(.),'{text}')]")
        if self._click_first_available_safe([locator], timeout=timeout):
            return True
        # Several CES controls render visual spacing inside their label, such
        # as "导 出" and "清 空". Match the displayed text with whitespace
        # removed, while still limiting the lookup to actionable elements.
        element = self.driver.execute_script(
            """
            const root = document.querySelector(arguments[0]);
            const expected = String(arguments[1]).replace(/\\s/g, '');
            if (!root) return null;
            return [...root.querySelectorAll('button, a, [role="button"]')]
              .find(item => item.offsetParent !== null &&
                (item.innerText || '').replace(/\\s/g, '').includes(expected)) || null;
            """,
            root,
            text,
        )
        if element is None:
            return False
        self.driver.execute_script("arguments[0].click()", element)
        return True

    def fill_input(self, label, value):
        element = self.driver.execute_script(
            """
            const label = arguments[0], value = arguments[1];
            const clean = text => (text || '').replace(/[\\s*：:]/g, '');
            const nodes = [...document.querySelectorAll('main label, main .ant-form-item-label, main .label')];
            const node = nodes.find(node => clean(node.innerText).includes(clean(label)));
            let scope = node && (node.closest('.ant-form-item, .search-item, .search-box, div'));
            let input = scope && scope.querySelector('input:not([type=hidden]):not([readonly]), textarea');
            if (!input) input = [...document.querySelectorAll('main input:not([type=hidden]):not([readonly]), main textarea')]
              .find(input => (input.placeholder || '').includes(label));
            if (!input) return null;
            input.focus(); input.value = ''; input.dispatchEvent(new Event('input', {bubbles:true}));
            input.value = value; input.dispatchEvent(new Event('input', {bubbles:true})); input.dispatchEvent(new Event('change', {bubbles:true}));
            return input;
            """, label, str(value),
        )
        return element is not None

    def fill_first_inputs(self, values):
        inputs = [
            item
            for item in self.driver.find_elements(By.CSS_SELECTOR, "main input:not([type=hidden])")
            if item.is_displayed()
        ]
        if len(inputs) < len(values):
            return False
        for input_, value in zip(inputs, values):
            # Ant Design date fields are often readonly.  Set through the
            # native value setter and dispatch both React-observed events.
            self.driver.execute_script(
                """
                const input = arguments[0], value = arguments[1];
                const setter = Object.getOwnPropertyDescriptor(
                    HTMLInputElement.prototype, 'value'
                ).set;
                setter.call(input, value);
                input.dispatchEvent(new Event('input', {bubbles: true}));
                input.dispatchEvent(new Event('change', {bubbles: true}));
                input.dispatchEvent(new Event('blur', {bubbles: true}));
                """,
                input_, str(value),
            )
        return True

    def submit_and_wait(self, expected=None, timeout=6):
        before = self._main_text()
        clicked = (
            self.click_text("搜索", timeout=2)
            or self.click_text("查询", timeout=2)
            or self._click_first_available_safe(
                [(By.CSS_SELECTOR, "main button.ant-btn-primary")], timeout=2
            )
        )
        if not clicked:
            return False
        # Some valid searches return the same rows.  Waiting for a text change
        # would then turn a real operation into a false failure, so wait for the
        # loading mask to disappear and accept either a changed result or the
        # requested value being visible.
        self.wait_until(
            lambda: not self.driver.execute_script(
                "return [...document.querySelectorAll('.ant-spin-spinning,.ant-spin-nested-loading')].some(x => x.offsetParent && x.classList.contains('ant-spin-spinning'))"
            ),
            timeout=timeout,
            poll_frequency=.2,
        )
        after = self._main_text()
        return after != before or not expected or expected in after

    def reset_filters(self):
        return self.click_text("清空", timeout=3) or self.click_text("重置", timeout=3)

    def download(self, labels=("导出", "下载"), extensions=None):
        directory = prepare_download(self.driver)
        existing = {path.name for path in directory.iterdir()}
        for label in labels:
            if self.click_text(label, timeout=3):
                return wait_for_download(directory, existing, extensions or {".xlsx", ".xls", ".csv", ".zip", ".log", ".txt", ".gz"}, timeout=20, driver=self.driver)
        return None

    def upload_in_modal(self, path, overwrite=False):
        path = Path(path).resolve()
        file_input = self.driver.execute_script("return [...document.querySelectorAll('.ant-modal-content input[type=file]')].find(x => x.offsetParent) || null")
        if file_input is None:
            return False
        file_input.send_keys(str(path))
        if overwrite:
            checkbox = self.driver.execute_script("return [...document.querySelectorAll('.ant-modal-content label, .ant-modal-content span')].find(x => (x.innerText || '').includes('覆盖')) || null")
            if checkbox is not None:
                self.driver.execute_script("arguments[0].click()", checkbox)
        return self._click_first_available_safe([(By.CSS_SELECTOR, ".ant-modal-content .ant-modal-footer .ant-btn-primary")], timeout=5)

    def _main_text(self):
        return self.driver.execute_script("return (document.querySelector('main')?.innerText || '').replace(/\\s+/g, ' ').trim()")
