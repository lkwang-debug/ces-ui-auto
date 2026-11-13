# -*- coding: utf-8 -*-
"""Client feature permission page with snapshot-and-restore operations."""

from __future__ import annotations

from selenium.webdriver.common.by import By

from pages.FeatureActionsPage import FeatureActionsPage


class ClientFeaturePage(FeatureActionsPage):
    group_name = "功能权限管理"
    item_name = "客户端功能管理"

    def __init__(self, driver):
        super().__init__(driver=driver)
        self.last_scope_debug = {}

    def open_features(self):
        return self.open_page(self.group_name, self.item_name)

    def feature_names(self):
        if not self.open_features():
            return []
        return self.driver.execute_script(
            """
            return [...document.querySelectorAll('main .feature-item .feature-title')]
              .filter(item => item.offsetParent !== null)
              .map(item => (item.innerText || '').trim()).filter(Boolean);
            """
        )

    def feature_with_anonymous_switch(self):
        for name in self.feature_names():
            snapshot = self.snapshot(name)
            if snapshot and len(snapshot["switches"]) >= 2:
                return name
        return ""

    def ensure_switch(self, feature_name, index, expected):
        if not self.open_features():
            return False
        return self._toggle(feature_name, index, expected)

    def _row(self, feature_name):
        return self.driver.execute_script(
            """
            const expected = arguments[0];
            const leaf = [...document.querySelectorAll('main *')]
              .find(item => item.children.length === 0 && (item.innerText || '').trim() === expected);
            if (!leaf) return null;
            let parent = leaf.parentElement;
            for (let depth=0; parent && depth<8; depth++, parent=parent.parentElement) {
              const switches = parent.querySelectorAll('.ant-switch');
              const buttons = parent.querySelectorAll('button');
              if (switches.length || buttons.length) return parent;
            }
            return null;
            """,
            feature_name,
        )

    def snapshot(self, feature_name):
        row = self._row(feature_name)
        if row is None:
            return None
        return self.driver.execute_script(
            """
            const row = arguments[0];
            return {
              switches: [...row.querySelectorAll('.ant-switch')].map(item =>
                item.classList.contains('ant-switch-checked')),
              buttonCount: [...row.querySelectorAll('button')].filter(item => item.offsetParent !== null).length,
              text: (row.innerText || '').replace(/\\s+/g, ' ').trim()
            };
            """,
            row,
        )

    def _toggle(self, feature_name, index, expected):
        row = self._row(feature_name)
        if row is None:
            return False
        switches = [
            item
            for item in row.find_elements(By.CSS_SELECTOR, ".ant-switch")
            if item.is_displayed() and item.is_enabled()
        ]
        if len(switches) <= index:
            return False
        current = "ant-switch-checked" in (switches[index].get_attribute("class") or "")
        if current != expected:
            request_mark = self.driver.execute_script("return performance.now()")
            previous_notices = {
                item.id for item in self.driver.find_elements(
                    By.CSS_SELECTOR, ".ant-message-notice"
                ) if item.is_displayed()
            }
            self.driver.execute_script("arguments[0].click()", switches[index])
            layer = self.wait_until(
                lambda: self.driver.execute_script(
                    "return [...document.querySelectorAll('.ant-modal-confirm,.ant-modal-content,.ant-popover')].filter(x=>x.offsetParent!==null).at(-1) || null"
                ),
                timeout=1.5,
            )
            if layer:
                confirm = next(
                    (
                        item
                        for item in layer.find_elements(By.TAG_NAME, "button")
                        if item.is_displayed()
                        and any(
                            word in (item.text or "").replace(" ", "")
                            for word in ("确定", "确认", "保存")
                        )
                    ),
                    None,
                )
                if confirm is not None:
                    self.driver.execute_script("arguments[0].click()", confirm)
            evidence = self.wait_operation_evidence(
                [
                    (
                        "权限保存请求完成",
                        lambda: self.driver.execute_script(
                            """
                            const mark=arguments[0];
                            return performance.getEntriesByType('resource').some(item =>
                              item.startTime >= mark
                              && ['fetch', 'xmlhttprequest'].includes(item.initiatorType));
                            """,
                            request_mark,
                        ),
                    ),
                    (
                        "权限保存提示",
                        lambda: next(
                            (
                                item for item in self.driver.find_elements(
                                    By.CSS_SELECTOR, ".ant-message-notice"
                                )
                                if item.is_displayed() and item.id not in previous_notices
                            ),
                            None,
                        ),
                    ),
                ],
                timeout=8,
            )
            if not evidence:
                return False
        return bool(
            self.wait_until(
                lambda: (
                    self.snapshot(feature_name) is not None
                    and len(self.snapshot(feature_name)["switches"]) > index
                    and self.snapshot(feature_name)["switches"][index] == expected
                ),
                timeout=6,
            )
        )

    def verify_switch_persistence_and_restore(self, feature_name, index=0):
        if not self.open_features():
            return False
        original = self.snapshot(feature_name)
        if not original or len(original["switches"]) <= index:
            return False
        original_value = original["switches"][index]
        success = False
        try:
            if not self._toggle(feature_name, index, not original_value):
                success = False
            else:
                self.driver.refresh()
                self.wait_for_document_ready(timeout=5)
                self.wait_until(lambda: self._row(feature_name), timeout=6)
                changed = self.snapshot(feature_name)
                success = bool(
                    changed
                    and len(changed["switches"]) > index
                    and changed["switches"][index] != original_value
                )
        finally:
            self.wait_until(lambda: self._row(feature_name), timeout=6)
            self._toggle(feature_name, index, original_value)
            self.driver.refresh()
            self.wait_for_document_ready(timeout=5)
            self.wait_until(lambda: self._row(feature_name), timeout=6)
            restored = self.snapshot(feature_name)
            success = bool(
                success
                and restored
                and len(restored["switches"]) > index
                and restored["switches"][index] == original_value
            )
        return success

    def open_user_scope_and_cancel(self, feature_name):
        self.last_scope_debug = {"feature": feature_name, "stage": "open_page"}
        if not self.open_features():
            return False
        row = self.wait_until(lambda: self._row(feature_name), timeout=6)
        if not row:
            self.last_scope_debug["stage"] = "row_not_found"
            return False
        click_result = self.driver.execute_script(
            """
            const row = arguments[0];
            const header = [...document.querySelectorAll('main *')]
              .find(item => item.children.length === 0
                && (item.innerText || '').trim() === '指定用户范围');
            if (!header) return {clicked: false, reason: 'header_not_found'};
            const targetX = header.getBoundingClientRect().x
              + header.getBoundingClientRect().width / 2;
            const candidates = [...row.querySelectorAll('button,[role="button"],svg,.anticon')]
              .filter(item => {
                const rect = item.getBoundingClientRect();
                return item.offsetParent !== null && rect.width > 0 && rect.height > 0
                  && !item.closest('.ant-switch');
              });
            if (!candidates.length) return {clicked: false, reason: 'candidate_not_found'};
            candidates.sort((left, right) => {
              const leftRect = left.getBoundingClientRect();
              const rightRect = right.getBoundingClientRect();
              const leftDistance = Math.abs(leftRect.x + leftRect.width / 2 - targetX);
              const rightDistance = Math.abs(rightRect.x + rightRect.width / 2 - targetX);
              return leftDistance - rightDistance;
            });
            const candidate = candidates[0];
            const clickable = candidate.closest('button,[role="button"],a') || candidate;
            if (clickable.disabled) return {clicked: false, reason: 'candidate_disabled'};
            clickable.click();
            return {
              clicked: true,
              candidate: candidate.outerHTML.slice(0, 600),
              clickable: clickable.outerHTML.slice(0, 600),
              targetX,
              candidateX: candidate.getBoundingClientRect().x
            };
            """,
            row,
        )
        self.last_scope_debug.update(click_result or {})
        if not click_result or not click_result.get("clicked"):
            self.last_scope_debug["stage"] = "click_failed"
            return False
        layer = self.wait_until(
            lambda: self.driver.execute_script(
                """
                const visible = item => {
                  const rect = item.getBoundingClientRect();
                  if (rect.width <= 0 || rect.height <= 0) return false;
                  for (let node = item; node && node !== document.body; node = node.parentElement) {
                    const style = getComputedStyle(node);
                    if (style.display === 'none' || style.visibility === 'hidden') return false;
                  }
                  return true;
                };
                return [...document.querySelectorAll(
                  '.ant-modal-content,.ant-drawer.ant-drawer-open .ant-drawer-content'
                )].filter(item => visible(item)
                  && (item.innerText || '').trim().length > 0).at(-1) || null;
                """
            ),
            timeout=4,
        )
        if not layer:
            self.last_scope_debug["stage"] = "layer_not_found"
            return False
        text = (
            self.driver.execute_script(
                "return (arguments[0].innerText || '').trim()", layer
            )
            or ""
        ).strip()
        self.last_scope_debug.update({"stage": "layer_opened", "layer_text": text})
        valid_content = feature_name in text and any(
            expected in text for expected in ("用户列表", "终端列表", "选择用户", "授权用户")
        )
        close = next(
            (
                item
                for item in layer.find_elements(
                    By.CSS_SELECTOR, ".ant-modal-close,.ant-drawer-close,button"
                )
                if item.is_displayed()
                and (
                    "close" in (item.get_attribute("class") or "").lower()
                    or any(word in (item.text or "").replace(" ", "") for word in ("取消", "关闭"))
                )
            ),
            None,
        )
        if close is not None:
            self.driver.execute_script("arguments[0].click()", close)
        self.last_scope_debug["valid_content"] = valid_content
        return valid_content
