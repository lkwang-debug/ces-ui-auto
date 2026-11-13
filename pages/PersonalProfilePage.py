# -*- coding: utf-8 -*-
"""Personal profile and password-change operations shared by all account types."""

from __future__ import annotations

import time
import hashlib

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from pages.Index_Page.index import LoginPage
from common.operation_metrics import timed_operation


class PersonalProfilePage(LoginPage):
    profile_trigger = (
        By.CSS_SELECTOR,
        "header .ant-dropdown-trigger, header [class*='user-info'], "
        "header [class*='userInfo']",
    )
    profile_menu_item = (
        By.XPATH,
        "//*[contains(@class,'ant-dropdown') or contains(@class,'ant-popover')]"
        "//button[normalize-space()='修改资料']",
    )
    logout_menu_item = (
        By.XPATH,
        "//*[contains(@class,'ant-dropdown') or contains(@class,'ant-popover')]"
        "//button[normalize-space()='退出登录']",
    )
    profile_modal = (
        By.XPATH,
        "//div[contains(@class,'ant-modal-content')]"
        "[.//*[contains(@class,'ant-modal-title') and normalize-space()='修改个人信息']]",
    )

    @timed_operation
    def login_as(self, username, password):
        self._verified_identity=None
        self.reset_login_state()
        verified=self.login_with_optional_captcha(username, password)
        if verified:self._verified_identity=hashlib.sha256((username+'\0'+password).encode()).hexdigest()
        return verified

    def has_verified_login(self,username,password):
        identity=hashlib.sha256((username+'\0'+password).encode()).hexdigest()
        return (not getattr(self.driver,'_ces_session_invalidated',False) and getattr(self,'_verified_identity',None)==identity and self.is_logged_in(timeout=0.1)
            and self.get_index_user_name_text()==username)

    def _visible_profile_modal(self):
        for modal in self.driver.find_elements(*self.profile_modal):
            try:
                if modal.is_displayed():
                    return modal
            except Exception:
                continue
        return None

    def _open_user_dropdown(self):
        username = self.last_authenticated_username or ""
        clicked = self.driver.execute_script(
            """
            const expected=arguments[0];
            const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
            const leaves=[...document.querySelectorAll('header span,header div')]
              .filter(e=>visible(e)&&(e.innerText||'').trim()===expected);
            const leaf=leaves.find(e=>e.classList.contains('hst-user-name'))
              || leaves.at(-1);
            if(!leaf) return false;
            const trigger=leaf.parentElement?.matches('span[style*="cursor"]')
              ? leaf.parentElement : leaf;
            if(!trigger) return false;
            trigger.click();
            return true;
            """,
            username,
        )
        if clicked and self.wait_until(
            lambda: any(
                item.is_displayed()
                for item in self.driver.find_elements(*self.profile_menu_item)
            ),
            timeout=3,
            poll_frequency=0.1,
        ) is not False:
            return True
        for trigger in self.driver.find_elements(*self.profile_trigger):
            try:
                if not trigger.is_displayed():
                    continue
                self.driver.execute_script("arguments[0].click();", trigger)
                if self.wait_until(
                    lambda: any(
                        item.is_displayed()
                        for item in self.driver.find_elements(*self.profile_menu_item)
                    ),
                    timeout=3,
                    poll_frequency=0.1,
                ) is not False:
                    return True
            except Exception:
                continue
        return False

    def open_profile(self):
        if not self.is_logged_in(timeout=1):
            return False
        if not self._open_user_dropdown():
            return False
        item = self._visible_menu_item(self.profile_menu_item, timeout=3)
        if item is None:
            return False
        self.driver.execute_script("arguments[0].click();", item)
        return self.wait_until(
            lambda: self._visible_profile_modal() or False,
            timeout=5,
            poll_frequency=0.1,
        ) is not False

    def _visible_menu_item(self, locator, timeout=3):
        end = time.time() + timeout
        while time.time() < end:
            for item in self.driver.find_elements(*locator):
                try:
                    if item.is_displayed() and item.is_enabled():
                        return item
                except Exception:
                    continue
            time.sleep(0.1)
        return None

    def enable_password_change(self):
        modal = self._visible_profile_modal()
        if modal is None:
            return False
        clicked = self.driver.execute_script(
            """
            const modal=arguments[0];
            const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
            const clean=v=>String(v||'').replace(/[\s*：:]/g,'');
            const item=[...modal.querySelectorAll('.ant-form-item')].find(row=>
              clean(row.querySelector('label')?.innerText)==='修改密码');
            if(!item) return false;
            const yes=[...item.querySelectorAll('.ant-radio-wrapper,label')].find(node=>
              visible(node)&&clean(node.innerText)==='是');
            if(!yes) return false;
            const checked=yes.classList.contains('ant-radio-wrapper-checked')
              || !!yes.querySelector('input:checked');
            if(!checked) yes.click();
            return true;
            """,
            modal,
        )
        if not clicked:
            return False
        return self.wait_until(
            lambda: self._modal_field("原密码") is not None
            and self._modal_field("新密码") is not None
            and self._modal_field("确认新密码") is not None,
            timeout=4,
            poll_frequency=0.1,
        ) is not False

    def _modal_field(self, label):
        modal = self._visible_profile_modal()
        if modal is None:
            return None
        return self.driver.execute_script(
            """
            const modal=arguments[0], expected=arguments[1];
            const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
            const clean=v=>String(v||'').replace(/[\s*：:]/g,'');
            const item=[...modal.querySelectorAll('.ant-form-item')].find(row=>
              clean(row.querySelector('label')?.innerText)===clean(expected));
            return [...(item?.querySelectorAll('input')||[])].find(visible)||null;
            """,
            modal,
            label,
        )

    def _set_field(self, label, value):
        deadline = time.time() + 4
        expected = str(value)
        while time.time() < deadline:
            field = self._modal_field(label)
            if field is None:
                time.sleep(0.1)
                continue
            try:
                self.driver.execute_script(
                    """
                    const field=arguments[0], value=arguments[1];
                    const setter=Object.getOwnPropertyDescriptor(
                      HTMLInputElement.prototype,'value').set;
                    setter.call(field,value);
                    field.dispatchEvent(new Event('input',{bubbles:true}));
                    field.dispatchEvent(new Event('change',{bubbles:true}));
                    field.dispatchEvent(new Event('blur',{bubbles:true}));
                    """,
                    field,
                    expected,
                )
                if expected == "":
                    return True
                current = self._modal_field(label)
                if current is not None and (
                    current.get_attribute("value") or ""
                ) == expected:
                    return True
            except Exception:
                pass
            time.sleep(0.1)
        return False

    def field_errors(self):
        modal = self._visible_profile_modal()
        if modal is None:
            return {}
        return self.driver.execute_script(
            """
            const modal=arguments[0];
            const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
            const clean=v=>String(v||'').replace(/[\s*：:]/g,'');
            const result={};
            for(const item of [...modal.querySelectorAll('.ant-form-item')].filter(visible)){
              const label=clean(item.querySelector('label')?.innerText);
              const error=item.querySelector(
                '.ant-form-item-explain-error,.ant-form-explain,[role="alert"]');
              if(label&&visible(error)) result[label]=(error.innerText||'').trim();
            }
            return result;
            """,
            modal,
        ) or {}

    def _notice_texts(self):
        return self.driver.execute_script(
            """
            const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
            return [...document.querySelectorAll(
              '.ant-message-notice-content,.ant-notification-notice-message')]
              .filter(visible).map(e=>(e.innerText||'').trim()).filter(Boolean);
            """
        ) or []

    @timed_operation
    def change_password(self, old_password, new_password, confirm_password=None):
        result = {
            "saved": False,
            "field_errors": {},
            "message": "",
            "modal_closed": False,
        }
        if not self.open_profile():
            result["message"] = "修改资料弹窗未打开"
            result["visible_layers"] = self._visible_layer_texts()
            return result
        if not self.enable_password_change():
            result["message"] = "修改密码字段未显示"
            result["visible_layers"] = self._visible_layer_texts()
            return result
        confirm_value = new_password if confirm_password is None else confirm_password
        for label, value in (
            ("原密码", old_password),
            ("新密码", new_password),
            ("确认新密码", confirm_value),
        ):
            if not self._set_field(label, value):
                result["message"] = f"字段未写入：{label}"
                return result

        previous_notices = set(self._notice_texts())
        modal = self._visible_profile_modal()
        buttons = [
            button
            for button in modal.find_elements(By.CSS_SELECTOR, "button")
            if button.is_displayed()
            and "保存" in (button.text or "").replace(" ", "")
        ]
        if not buttons:
            result["message"] = "未找到保存按钮"
            return result
        self.driver.execute_script("arguments[0].click();", buttons[0])

        evidence = self.wait_until(
            lambda: (
                ("closed", None)
                if self._visible_profile_modal() is None
                else ("errors", self.field_errors())
                if self.field_errors()
                else ("notice", notices)
                if (
                    notices := [
                        text
                        for text in self._notice_texts()
                        if text not in previous_notices
                    ]
                )
                else False
            ),
            timeout=8,
            poll_frequency=0.15,
        )
        result["modal_closed"] = self._visible_profile_modal() is None
        result["field_errors"] = self.field_errors()
        new_notices = [
            text for text in self._notice_texts() if text not in previous_notices
        ]
        result["message"] = " ".join(new_notices)
        success_message = any(
            word in result["message"] for word in ("修改成功", "操作成功")
        )
        if success_message:
            self.wait_until(
                lambda: self._visible_profile_modal() is None,
                timeout=4,
                poll_frequency=0.1,
            )
            result["modal_closed"] = self._visible_profile_modal() is None
        result["saved"] = bool(
            success_message
            or (result["modal_closed"] and not result["field_errors"])
        )
        if evidence is False and not result["message"]:
            result["message"] = "保存后没有可观察结果"
        return result

    def _visible_layer_texts(self):
        return self.driver.execute_script(
            """
            const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
            return [...document.querySelectorAll(
              '.ant-dropdown,.ant-modal-content,.ant-popover,header')]
              .filter(visible).map(e=>(e.innerText||'').replace(/\s+/g,' ').trim())
              .filter(Boolean);
            """
        ) or []

    def close_profile(self):
        modal = self._visible_profile_modal()
        if modal is None:
            return True
        close = next(
            (
                button
                for button in modal.find_elements(By.CSS_SELECTOR, "button")
                if button.is_displayed()
                and (
                    "关闭" in (button.text or "").replace(" ", "")
                    or "ant-modal-close" in (button.get_attribute("class") or "")
                )
            ),
            None,
        )
        if close is None:
            return False
        self.driver.execute_script("arguments[0].click();", close)
        return self.wait_until(
            lambda: self._visible_profile_modal() is None,
            timeout=3,
            poll_frequency=0.1,
        ) is not False

    def logout(self):
        if not self._open_user_dropdown():
            return False
        item = self._visible_menu_item(self.logout_menu_item, timeout=3)
        if item is None:
            return False
        self.driver.execute_script("arguments[0].click();", item)
        return self.wait_until(
            lambda: "login" in (self.driver.current_url or "").lower(),
            timeout=6,
            poll_frequency=0.2,
        ) is not False
