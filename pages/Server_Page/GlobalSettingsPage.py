# -*- coding: utf-8 -*-
"""Global settings operations used by real business-flow tests."""

import json
import time

import allure
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from pages.FeatureCatalogPage import FeatureCatalogPage


class GlobalSettingsPage(FeatureCatalogPage):
    last_email_error = ""
    email_server = (
        By.XPATH,
        "//*[@id='form_item_smtpServer']"
        " | //main//label[normalize-space()='邮件服务器地址']"
        "/ancestor::*[contains(@class,'ant-form-item')][1]//input",
    )
    email_account = (
        By.XPATH,
        "//*[@id='form_item_account']"
        " | //main//label[normalize-space()='邮箱帐号']"
        "/ancestor::*[contains(@class,'ant-form-item')][1]//input",
    )
    email_password = (
        By.XPATH,
        "//*[@id='form_item_password']"
        " | //main//label[normalize-space()='邮箱密码']"
        "/ancestor::*[contains(@class,'ant-form-item')][1]//input",
    )
    ssl_port = (
        By.XPATH,
        "//*[@id='form_item_smtpPort']"
        " | //main//label[contains(normalize-space(.),'SSL') and contains(normalize-space(.),'端口')]"
        "/ancestor::*[contains(@class,'ant-form-item')][1]//input[not(@type='checkbox')]",
    )
    ssl_checkbox = (
        By.CSS_SELECTOR,
        "#form_item_smtpPort"
        "~ *, .ssl-checkbox input[type='checkbox']",
    )
    operation_message = (
        By.CSS_SELECTOR,
        ".ant-message-notice-content, .ant-notification-notice-message",
    )

    def open_email_service(self):
        opened = self.open_feature("服务器管理", "全局设置")
        if not opened and "#/ui/host-management/global-setting" not in (
            self.driver.current_url or ""
        ):
            return False
        if self._email_input(self.email_server, "邮件服务器地址", timeout=2) is not False:
            return True
        clicked = self.driver.execute_script(
            r"""
            const clean = value => String(value || '').replace(/\s+/g, '').trim();
            const visible = element => !!(element && element.offsetParent !== null);
            const candidates = [...document.querySelectorAll('main button,main a,main li,main div,main span')]
              .filter(element => visible(element) && clean(element.innerText) === '邮件发送服务')
              .sort((left, right) => left.children.length - right.children.length);
            const target = candidates[0];
            if (!target) return false;
            (target.closest('button,a,li') || target).click();
            return true;
            """
        )
        if not clicked:
            return False
        return self._email_input(
            self.email_server, "邮件服务器地址", timeout=8
        ) is not False

    def _email_input(self, locator, label_text, timeout=5):
        end = time.time() + timeout
        while time.time() < end:
            for element in self.driver.find_elements(*locator):
                try:
                    if element.is_displayed() and element.is_enabled():
                        return element
                except Exception:
                    continue
            try:
                element = self.driver.execute_script(
                    r"""
                    const expected = String(arguments[0] || '').replace(/\s+/g, '');
                    const visible = node => !!(node && node.offsetParent !== null);
                    const label = [...document.querySelectorAll('main label')].find(node =>
                      visible(node) && (node.innerText || '').replace(/\s+/g, '') === expected);
                    return label?.closest('.ant-form-item')?.querySelector('input') || null;
                    """,
                    label_text,
                )
                if element and element.is_displayed() and element.is_enabled():
                    return element
            except Exception:
                pass
            time.sleep(0.2)
        return False

    def _replace_input(self, locator, value, label_text):
        element = self._email_input(locator, label_text, timeout=5)
        if element is False:
            return False
        element.click()
        element.send_keys(Keys.CONTROL, "a")
        element.send_keys(Keys.DELETE)
        element.send_keys(str(value))
        return (element.get_attribute("value") or "") == str(value)

    def _ensure_ssl_enabled(self):
        return bool(
            self.driver.execute_script(
                r"""
                const visible = element => !!(element && element.offsetParent !== null);
                const preferred = document.querySelector('.ssl-checkbox input[type=checkbox]');
                const visibleInputs = [...document.querySelectorAll('main input[type=checkbox]')]
                  .filter(visible);
                const contextual = visibleInputs.find(input => {
                  let node = input.parentElement;
                  for (let index = 0; node && index < 5; index += 1, node = node.parentElement) {
                    if ((node.innerText || '').replace(/\s+/g, '').includes('SSL端口')) return true;
                  }
                  return false;
                });
                const input = (preferred && visible(preferred) && preferred) || contextual
                  || (visibleInputs.length === 1 ? visibleInputs[0] : null);
                if (!input) return false;
                if (!input.checked) (input.closest('label') || input).click();
                return input.checked;
                """
            )
        )

    def _click_email_save(self):
        return bool(
            self.driver.execute_script(
                r"""
                const clean = value => String(value || '').replace(/\s+/g, '').trim();
                const visible = element => !!(element && element.offsetParent !== null);
                const section = document.querySelector('main');
                const button = section && [...section.querySelectorAll('button')]
                  .find(element => visible(element) && clean(element.innerText) === '保存');
                if (!button || button.disabled) return false;
                button.click(); return true;
                """
            )
        )

    def configure_email_service(self, email_info):
        self.last_email_error = ""

        def failed(stage):
            self.last_email_error = stage
            allure.attach(
                json.dumps(
                    {
                        "失败阶段": stage,
                        "当前路由": self.driver.current_url,
                        "页面可见文本": self.driver.execute_script(
                            "return (document.querySelector('main')?.innerText || '').slice(0, 5000)"
                        ),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                "邮件发送服务失败诊断",
                allure.attachment_type.JSON,
            )
            return False

        required = ("smtp_host", "username", "password", "smtp_port")
        missing = [key for key in required if str(email_info.get(key, "")).strip() == ""]
        if missing:
            raise AssertionError(f"邮件服务配置缺少字段：{', '.join(missing)}")
        if not self.open_email_service():
            return failed("未进入邮件发送服务页签")

        field_values = (
            ("邮件服务器地址", self.email_server, email_info["smtp_host"]),
            ("邮箱帐号", self.email_account, email_info["username"]),
            ("邮箱密码", self.email_password, email_info["password"]),
            ("SSL端口", self.ssl_port, email_info["smtp_port"]),
        )
        for label, locator, value in field_values:
            if not self._replace_input(locator, value, label):
                return failed(f"{label}输入失败")
        if not self._ensure_ssl_enabled():
            return failed("SSL复选框未选中")

        before_messages = self._visible_messages()
        if not self._click_email_save():
            return failed("未点击到邮件服务保存按钮")
        message = self.wait_until(
            lambda: next(
                (
                    item
                    for item in self._visible_messages()
                    if item not in before_messages
                ),
                False,
            ),
            timeout=12,
            poll_frequency=0.2,
        )
        diagnostic = {
            "邮件服务器地址": email_info["smtp_host"],
            "邮箱帐号": email_info["username"],
            "SSL端口": str(email_info["smtp_port"]),
            "SSL": True,
            "保存提示": message or "未捕获到提示",
        }
        allure.attach(
            json.dumps(diagnostic, ensure_ascii=False, indent=2),
            "邮件发送服务配置结果",
            allure.attachment_type.JSON,
        )
        if message:
            return any(keyword in str(message) for keyword in ("成功", "完成", "生效"))
        # Some builds close the loading layer without a toast. The form values
        # still provide observable evidence that the save request completed.
        time.sleep(0.5)
        return not self.driver.execute_script(
            "return !!document.querySelector('.ant-spin-spinning,.ant-btn-loading')"
        )

    def _visible_messages(self):
        return tuple(
            self.driver.execute_script(
                r"""
                const visible = element => !!(element && element.offsetParent !== null);
                return [...document.querySelectorAll(
                  '.ant-message-notice-content,.ant-notification-notice-message'
                )].filter(visible).map(element => (element.innerText || '').trim()).filter(Boolean);
                """
            )
            or []
        )
