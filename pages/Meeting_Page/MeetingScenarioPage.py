# -*- coding: utf-8 -*-
from pages.FeatureActionsPage import FeatureActionsPage


class MeetingScenarioPage(FeatureActionsPage):
    group_name, item_name = "会议管理", "会议场景管理"

    def open_scenarios(self):
        return self.open_page(self.group_name, self.item_name)

    def enterprise_templates_visible(self):
        return "企业拥有的场景模板" in self._main_text()

    def _default_scene_select(self):
        template_names = {"会控", "培训", "讨论", "自定义"}
        candidates = [
            item for item in self.driver.find_elements("css selector", "main .ant-select")
            if item.is_displayed()
        ]
        return next(
            (item for item in candidates if (item.text or "").strip() in template_names),
            None,
        )

    def _save_default_scene(self):
        request_mark = self.driver.execute_script("return performance.now()")
        previous_notices = {
            item.id
            for item in self.driver.find_elements(
                "css selector", ".ant-message-notice,.ant-notification-notice"
            )
            if item.is_displayed()
        }
        buttons = [
            item for item in self.driver.find_elements(
                "css selector", "main button.ant-btn-primary, button.ant-btn-primary"
            )
            if item.is_displayed() and "保存" in (item.text or "").replace(" ", "")
        ]
        if not buttons:
            return False
        self.driver.execute_script("arguments[0].click()", buttons[-1])
        evidence = self.wait_operation_evidence(
            [
                (
                    "保存成功提示",
                    lambda: next(
                        (
                            item
                            for item in self.driver.find_elements(
                                "css selector",
                                ".ant-message-notice,.ant-notification-notice",
                            )
                            if item.is_displayed()
                            and item.id not in previous_notices
                            and "成功" in (item.text or "")
                        ),
                        None,
                    ),
                ),
                (
                    "保存请求完成",
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
            ],
            timeout=6,
        )
        return bool(evidence and self.wait_loading_finished(timeout=5))

    def _refresh_and_wait_data(self):
        self.driver.refresh()
        self.wait_for_document_ready(timeout=6)
        self.wait_until(
            lambda: self.driver.execute_script(
                """
                return performance.getEntriesByType('resource').some(item =>
                  ['fetch', 'xmlhttprequest'].includes(item.initiatorType));
                """
            ),
            timeout=5,
            poll_frequency=.1,
        )
        return self.wait_loading_finished(timeout=5)

    def set_default_and_restore(self):
        self.last_default_error = ""
        self.open_scenarios()
        # The templates are checkboxes; the default is a separate Ant select.
        select = self.wait_until(
            lambda: self._default_scene_select() or False,
            timeout=8,
            poll_frequency=.2,
        )
        if select is False:
            self.last_default_error = "未找到默认场景下拉框"
            return False
        original = (select.text or "").strip()
        self.driver.execute_script("arguments[0].click()", select)
        # 4.39.7 uses Ant Design's menu-item class; it does not expose
        # role=option on this select.  Keep both forms for 4.39.8.
        options = self.wait_until(
            lambda: [
                item for item in self.driver.find_elements(
                    "css selector",
                    ".ant-select-dropdown-menu-item, .ant-select-item-option, [role=option]",
                )
                if item.is_displayed()
            ],
            timeout=3,
        ) or []
        target = next((item for item in options if (item.text or "").strip() != original), None)
        target_name = original
        if target is not None:
            target_name = (target.text or "").strip()
            self.driver.execute_script("arguments[0].click()", target)
        else:
            # Some licensed environments expose only one enterprise template.
            # Saving the current value still verifies the real save/refresh path.
            current = next(
                (item for item in options if (item.text or "").strip() == original),
                None,
            )
            if current is not None:
                self.driver.execute_script("arguments[0].click()", current)
            else:
                self.driver.execute_script("document.body.click()")
        if not self._save_default_scene():
            self.last_default_error = "未找到默认场景保存按钮"
            return False
        self._refresh_and_wait_data()
        self.open_scenarios()
        select = self.wait_until(
            lambda: (
                current
                if current is not None and target_name in (current.text or "")
                else False
            )
            if (current := self._default_scene_select()) is not None
            else False,
            timeout=8,
            poll_frequency=.2,
        )
        if select is False:
            self.last_default_error = f"首次保存后刷新未持久化，期望: {target_name!r}"
            return False
        if target_name == original:
            return True
        self.driver.execute_script("arguments[0].click()", select)
        restore_options = self.wait_until(
            lambda: [
                item for item in self.driver.find_elements(
                    "css selector",
                    ".ant-select-dropdown-menu-item, .ant-select-item-option, [role=option]",
                )
                if item.is_displayed()
            ],
            timeout=3,
        ) or []
        restore = next((item for item in restore_options if (item.text or "").strip() == original), None)
        if restore is None:
            self.last_default_error = f"无法在下拉框中恢复原默认场景: {original!r}"
            return False
        self.driver.execute_script("arguments[0].click()", restore)
        if not self._save_default_scene():
            self.last_default_error = "恢复原默认场景时未找到保存按钮"
            return False
        self._refresh_and_wait_data()
        self.open_scenarios()
        restored = self.wait_until(
            lambda: (
                current
                if current is not None and original in (current.text or "")
                else False
            )
            if (current := self._default_scene_select()) is not None
            else False,
            timeout=8,
            poll_frequency=.2,
        ) is not False
        if not restored:
            self.last_default_error = f"恢复后刷新未显示原默认场景: {original!r}"
        return restored
