# -*- coding: utf-8 -*-
"""Face library page object shared by legacy and 4.39.8 builds."""

from __future__ import annotations

from pathlib import Path
from os.path import commonprefix

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from pages.FeatureActionsPage import FeatureActionsPage
from common.ui_state import click_toolbar_search, wait_query_finished, wait_stable_state


class FaceLibraryPage(FeatureActionsPage):
    group_name = "人脸库管理"
    item_name = "人脸库"

    def __init__(self, driver):
        super().__init__(driver=driver)
        self.last_messages = []
        self.last_save_disabled = False
        self.last_privacy_checked = None
        self.last_modify_evidence = {}
        self.last_create_evidence = {}

    def open_faces(self):
        if self._modal() is not None:
            self.close_modal()
        return self.open_page(self.group_name, self.item_name)

    def _modal(self):
        return self.driver.execute_script(
            "return [...document.querySelectorAll('.ant-modal-content')].filter(x=>x.offsetParent!==null).at(-1) || null"
        )

    def _row(self, name):
        if not name:
            return None
        for row in self.driver.find_elements(By.CSS_SELECTOR, "main tbody tr"):
            try:
                if row.is_displayed() and any(
                    (cell.text or "").strip() == name
                    for cell in row.find_elements(By.TAG_NAME, "td")
                ):
                    return row
            except Exception:
                continue
        return None

    def exists(self, name, refresh=False):
        if refresh:
            self.open_faces()
        return self._row(name) is not None

    def _replace(self, field_id, value):
        modal = self._modal()
        if modal is None:
            raise RuntimeError("人脸表单弹窗未显示")
        field = self._field(field_id)
        if field is None:
            raise RuntimeError(f"人脸表单字段未显示: {field_id}")
        self.driver.execute_script(
            """
            const field=arguments[0], value=arguments[1];
            const setter=Object.getOwnPropertyDescriptor(
              HTMLInputElement.prototype, 'value').set;
            setter.call(field, value);
            field.dispatchEvent(new Event('input', {bubbles:true}));
            field.dispatchEvent(new Event('change', {bubbles:true}));
            field.dispatchEvent(new Event('blur', {bubbles:true}));
            """,
            field,
            str(value or ""),
        )
        expected = str(value or "")

        def settled_value():
            current = self._field(field_id)
            if current is None or current.get_attribute("value") != expected:
                return False
            return {"value": expected}

        # Vue/Ant may replace the input after its input/change/blur handlers.
        # Reacquire it and observe the committed value through a render cycle.
        if wait_stable_state(self, settled_value, timeout=4, stable_for=0.25) is False:
            raise AssertionError(f"人脸字段写入后未稳定: {field_id}")

    def _field(self, field_id):
        modal = self._modal()
        if modal is None:
            return None
        labels = {
            "form_item_name": ("姓名",),
            "form_item_position": ("职位",),
        }
        return self.driver.execute_script(
            """
            const modal=arguments[0], id=arguments[1], labels=arguments[2];
            const direct=modal.querySelector('#'+CSS.escape(id));
            if(direct) return direct;
            const clean=v=>String(v||'').replace(/[\s*：:]/g,'');
            for(const item of modal.querySelectorAll('.ant-form-item')){
              const label=clean(item.querySelector('label')?.innerText);
              if(labels.includes(label)){
                const field=item.querySelector('input,textarea');
                if(field) return field;
              }
            }
            return [...modal.querySelectorAll('input,textarea')].find(field=>
              labels.some(label=>(field.placeholder||'').includes(label)))||null;
            """,
            modal,
            field_id,
            list(labels.get(field_id, ())),
        )

    def _upload_input(self):
        modal = self._modal()
        if modal is None:
            return None
        return self.driver.execute_script(
            "return arguments[0].querySelector('#form_item_image,input[type=file]');",
            modal,
        )

    def _privacy_checkbox(self):
        modal = self._modal()
        if modal is None:
            return None
        return self.driver.execute_script(
            "return arguments[0].querySelector('#form_item_checkState,input[type=checkbox]');",
            modal,
        )

    def _open_add(self):
        if not self.open_faces():
            return False
        search = next(
            (
                item for item in self.driver.find_elements(
                    By.CSS_SELECTOR, "main input[placeholder*='搜索内容']"
                ) if item.is_displayed()
            ),
            None,
        )
        if search is not None and (search.get_attribute("value") or "").strip():
            if not self._set_search(""):
                return False
        if not self.click_text("新增", timeout=4):
            return False
        return bool(self.wait_until(self._modal, timeout=4))

    def _save(self):
        result = self.driver.execute_script(
            """
            const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
            const modal=[...document.querySelectorAll('.ant-modal-content')].filter(visible).at(-1);
            const button=[...(modal?.querySelectorAll('button')||[])].find(e=>
              visible(e) && (e.innerText||'').replace(/\s/g,'')==='保存');
            if(!button) return {clicked:false,disabled:false};
            if(button.disabled) return {clicked:false,disabled:true};
            button.click(); return {clicked:true,disabled:false};
            """
        )
        self.last_save_disabled = result["disabled"]
        return result["clicked"]

    def close_modal(self):
        modal = self._modal()
        if modal is None:
            return True
        button = next(
            (
                item
                for item in modal.find_elements(By.CSS_SELECTOR, ".ant-modal-close,button")
                if item.is_displayed()
                and (
                    "ant-modal-close" in (item.get_attribute("class") or "")
                    or "关闭" in (item.text or "").replace(" ", "")
                )
            ),
            None,
        )
        if button is not None:
            self.driver.execute_script("arguments[0].click()", button)
        return bool(self.wait_until(lambda: self._modal() is None, timeout=3))

    def messages(self):
        # One browser-side snapshot avoids stale WebElements between is_displayed
        # and text reads, and excludes the previous hidden form's validation.
        return self.driver.execute_script(
            """
            const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
            const modal=[...document.querySelectorAll('.ant-modal-content')].filter(visible).at(-1);
            const errors=[...(modal?.querySelectorAll(
              '.ant-form-item-explain-error,.ant-form-explain,[role=alert]')||[])];
            const notices=[...document.querySelectorAll(
              '.ant-message-notice-content,.ant-notification-notice-message')];
            return [...new Set([...errors,...notices].filter(visible)
              .map(e=>(e.innerText||'').trim()).filter(Boolean))];
            """
        ) or []

    def field_errors(self):
        return self.driver.execute_script(
            r"""
            const clean = value => String(value || '').replace(/[\s*：:]/g, '');
            const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
            const result = {};
            const modal=[...document.querySelectorAll('.ant-modal-content')].filter(visible).at(-1);
            for (const item of modal?.querySelectorAll('.ant-form-item') || []) {
              const error = item.querySelector('.ant-form-explain,.ant-form-item-explain-error,[role=alert]');
              const label = clean(item.querySelector('label')?.innerText);
              if (label && visible(error)) result[label] = (error.innerText || '').trim();
            }
            return result;
            """,
        ) or {}

    def create(self, name, position, image_path, accept_privacy=True, timeout=15):
        self.last_messages = []
        self.last_save_disabled = False
        self.last_create_evidence = {"name": name, "position": position}
        if not self._open_add():
            self.last_create_evidence["failure"] = "新增弹窗未打开"
            return False
        self._replace("form_item_name", name)
        self._replace("form_item_position", position)
        if image_path:
            modal = self._modal()
            upload = self._upload_input()
            if upload is None:
                raise RuntimeError("人脸照片上传控件未显示")
            upload_messages = set(self.messages())
            upload_started = self.driver.execute_script("return performance.now()")
            upload.send_keys(str(Path(image_path).resolve()))
            upload_ready = self.wait_until(
                lambda: self.driver.execute_script(
                    r"""
                    const visible = element => !!(element && (
                      element.offsetWidth || element.offsetHeight ||
                      element.getClientRects().length));
                    const modal = [...document.querySelectorAll('.ant-modal-content')]
                      .filter(visible).at(-1);
                    if (!modal) return false;
                    if (modal.querySelector(
                      '.ant-upload-list-item-uploading,.ant-upload-list-item-progress')) return false;
                    const completed = performance.getEntriesByType('resource').some(item =>
                      item.startTime >= arguments[0] && item.responseEnd > 0 &&
                      ['fetch','xmlhttprequest'].includes(item.initiatorType));
                    const item = modal.querySelector(
                      '.ant-upload-list-item-done,.ant-image img,img[src^="data:image"],.avatar img');
                    const localPreview = modal.querySelector('.ant-upload img[src^="data:image"]');
                    const localReady = localPreview?.complete && localPreview.naturalWidth > 0;
                    return localReady || (completed && !!item);
                    """,
                    upload_started,
                ) or any(message not in upload_messages for message in self.messages()),
                timeout=12,
                poll_frequency=0.15,
            )
            self.last_create_evidence["upload_ready"] = upload_ready is not False
            if upload_ready is False:
                self.last_create_evidence["failure"] = "人脸照片上传未完成"
                return False
        modal = self._modal()
        checkbox = self._privacy_checkbox()
        if checkbox is None:
            raise RuntimeError("隐私协议复选框未显示")
        if checkbox.is_selected() != bool(accept_privacy):
            self.driver.execute_script("arguments[0].click()", checkbox)
        self.last_privacy_checked = checkbox.is_selected()
        self.last_create_evidence["privacy_checked"] = self.last_privacy_checked
        previous_messages = set(self.messages())
        saved = self._save()
        effective_timeout = min(timeout, 4) if not accept_privacy else timeout
        required_errors = {
            label for label, missing in (
                ("姓名", not name), ("职位", not position),
                ("人脸照片", not image_path),
            ) if missing
        }
        observed_messages = []

        def save_outcome():
            # Backend photo validation can close the modal while displaying its
            # failure toast. Preserve that evidence across the close transition.
            for message in self.messages():
                if message not in previous_messages and message not in observed_messages:
                    observed_messages.append(message)
            if self._modal() is None:
                return {"closed": True, "messages": list(observed_messages)}
            errors = self.field_errors()
            # A previous field's async validation is not the result of the
            # current required-field scenario. Wait for its own field evidence.
            if required_errors and not required_errors.issubset(errors):
                return False
            return {"errors": errors, "messages": list(observed_messages)} if errors or observed_messages else False

        outcome = wait_stable_state(self, save_outcome, timeout=effective_timeout, stable_for=0.25)
        self.last_messages = (
            outcome["messages"] if isinstance(outcome, dict) else [
                message for message in self.messages() if message not in previous_messages
            ]
        )
        self.last_create_evidence.update({
            "save_clicked": bool(saved),
            "save_disabled": self.last_save_disabled,
            "messages": list(self.last_messages),
            "modal_open": self._modal() is not None,
        })
        if self._modal() is not None and any(
            "成功" in message for message in self.last_messages
        ):
            self.wait_until(lambda: self._modal() is None, timeout=1)
            if self._modal() is not None:
                self.close_modal()
        if not saved or self._modal() is not None:
            self.last_create_evidence["failure"] = "保存未完成或弹窗未关闭"
            return False
        if not self._set_search(name):
            self.last_create_evidence["failure"] = "保存后搜索未完成"
            return False
        found = self.wait_until(lambda: self._row(name), timeout=6) is not False
        self.last_create_evidence.update({
            "record_found": found,
            "table": self.table_snapshot(),
        })
        if not found:
            self.last_create_evidence["failure"] = "保存后未检索到目标记录"
        return found

    def create_rejected(self, name, position, image_path=None, accept_privacy=True, timeout=12):
        created = self.create(name, position, image_path, accept_privacy, timeout=timeout)
        messages = self.last_messages or self.messages()
        self.last_field_errors = self.field_errors()
        if self.last_save_disabled:
            messages = ["保存按钮已禁用"]
        self.close_modal()
        if name and not self._set_search(name):
            return False, messages
        rejected = not created and self._row(name) is None
        return rejected, messages

    def input_length_snapshot(self, name, position):
        if not self._open_add():
            return {}
        try:
            result = {}
            for field_id, value in (
                ("form_item_name", name),
                ("form_item_position", position),
            ):
                self._replace(field_id, value)
                modal = self._modal()
                field = self._field(field_id)
                if field is None:
                    return {}
                result[field_id] = {
                    "maxlength": int(field.get_attribute("maxlength") or -1),
                    "length": len(field.get_attribute("value") or ""),
                }
            return result
        finally:
            self.close_modal()

    def _set_search(self, keyword):
        if not self.open_faces():
            return False
        search = next(
            (
                item
                for item in self.driver.find_elements(
                    By.CSS_SELECTOR, "main input[placeholder*='搜索内容']"
                )
                if item.is_displayed()
            ),
            None,
        )
        if search is None:
            return False
        search.click()
        search.send_keys(Keys.CONTROL, 'a')
        search.send_keys(Keys.DELETE)
        if keyword:
            search.send_keys(keyword)
        started = self.driver.execute_script("return performance.now()")
        if not click_toolbar_search(self.driver, search):
            return False
        return wait_query_finished(self, started, timeout=10)

    def search(self, name):
        if not self._set_search(name):
            return False
        return bool(self.wait_until(lambda: self._row(name), timeout=6))

    def modify(self, old_name, new_name, new_position, image_path):
        self.last_modify_evidence = {"old_name": old_name, "new_name": new_name}
        if not self.open_faces():
            self.last_modify_evidence["failure"] = "页面未打开"
            return False
        row = self._row(old_name)
        if row is None:
            self.last_modify_evidence["failure"] = "未找到原记录"
            return False
        icon = next(
            (
                item
                for name in ("edit", "form")
                for item in row.find_elements(By.CSS_SELECTOR, f"[data-icon='{name}']")
            ),
            None,
        )
        if icon is None:
            buttons = [item for item in row.find_elements(By.CSS_SELECTOR, "button,a") if item.is_displayed()]
            if not buttons:
                self.last_modify_evidence["failure"] = "没有修改操作按钮"
                return False
            button = buttons[0]
        else:
            button = icon.find_element(By.XPATH, "ancestor::*[self::button or self::a][1]")
        self.driver.execute_script("arguments[0].click()", button)
        if not self.wait_until(self._modal, timeout=4):
            self.last_modify_evidence["failure"] = "修改弹窗未出现"
            return False
        self._replace("form_item_name", new_name)
        self._replace("form_item_position", new_position)
        if image_path:
            modal = self._modal()
            old_image = self.driver.execute_script(
                "return arguments[0].querySelector('img')?.src || '';", modal
            )
            upload = self._upload_input()
            if upload is None:
                self.last_modify_evidence["failure"] = "修改弹窗没有照片上传控件"
                return False
            upload.send_keys(str(Path(image_path).resolve()))
            self.wait_until(
                lambda: self.driver.execute_script(
                    "return arguments[0].querySelector('img')?.src || '';", modal
                ) != old_image
                or bool(self.messages()),
                timeout=5,
            )
        previous_messages = set(self.messages())
        if not self._save():
            self.last_modify_evidence["failure"] = "保存按钮不可用"
            return False
        outcome = self.wait_until(
            lambda: self._modal() is None
            or [message for message in self.messages() if message not in previous_messages],
            timeout=8,
        )
        observed_messages = outcome if isinstance(outcome, list) else [
            message for message in self.messages() if message not in previous_messages
        ]
        self.last_modify_evidence["messages"] = observed_messages
        if self._modal() is not None and any(
            "成功" in message for message in observed_messages
        ):
            self.wait_until(lambda: self._modal() is None, timeout=1)
            if self._modal() is not None:
                self.close_modal()
        if self._modal() is not None:
            self.close_modal()
        self.driver.refresh()
        self.wait_for_document_ready(timeout=5)
        self.open_faces()
        if not self._set_search(new_name):
            self.last_modify_evidence["failure"] = "修改后查询未执行"
            return False
        row = self.wait_until(lambda: self._row(new_name), timeout=4)
        if row is False:
            self.last_modify_evidence["failure"] = "修改后未查询到目标记录"
            return False
        self.last_modify_evidence["row_text"] = row.text or ""
        persisted = new_position in (row.text or "")
        if not persisted:
            self.last_modify_evidence["failure"] = "职位未持久化"
        return persisted

    def delete_batch(self, names):
        names = list(dict.fromkeys(names))
        if not names:
            return True
        keyword = commonprefix(names)
        if not self._set_search(keyword):
            return False
        if not self.wait_until(
            lambda: all(self._row(name) is not None for name in names), timeout=6
        ):
            return False
        for name in names:
            row = self._row(name)
            if row is None:
                return False
            checkbox = row.find_element(By.CSS_SELECTOR, "input[type=checkbox]")
            if not checkbox.is_selected():
                wrapper = checkbox.find_element(By.XPATH, "ancestor::label[1]")
                self.driver.execute_script("arguments[0].click()", wrapper)
            if self.wait_until(lambda: checkbox.is_selected(), timeout=2) is False:
                return False
        delete_button = self.driver.execute_script(
            """
            return [...document.querySelectorAll('main button.hst-delete-button,main button')]
              .find(button => button.offsetParent !== null && (
                button.classList.contains('hst-delete-button')
                || (button.innerText || '').replace(/\s/g, '').startsWith('删除')
              )) || null;
            """
        )
        if delete_button is None:
            return False
        self.driver.execute_script("arguments[0].click()", delete_button)
        layer = self.wait_until(
            lambda: self.driver.execute_script(
                "return [...document.querySelectorAll('.ant-modal-content,.ant-popover')].filter(x=>x.offsetParent!==null).at(-1) || null"
            ),
            timeout=3,
        )
        if not layer:
            return False
        confirmed = self.driver.execute_script(
            """
            const layer = arguments[0];
            const buttons = [...layer.querySelectorAll('button')]
              .filter(item => item.offsetParent !== null && !item.disabled);
            const button = buttons.find(item =>
              ['确定', '删除'].includes((item.innerText || '').replace(/\s+/g, '')))
              || buttons.find(item => item.classList.contains('ant-btn-primary'));
            if (!button) return false;
            button.click();
            return true;
            """,
            layer,
        )
        if not confirmed:
            return False
        return bool(
            self.wait_until(
                lambda: all(self._row(name) is None for name in names), timeout=10
            )
        )

    def cleanup_prefix(self, prefix="uiauto_face_"):
        if not self._set_search(prefix):
            return False
        names = [
            (cell.text or "").strip()
            for row in self.driver.find_elements(By.CSS_SELECTOR, "main tbody tr")
            if row.is_displayed()
            for cell in row.find_elements(By.TAG_NAME, "td")
            if (cell.text or "").strip().startswith(prefix)
        ]
        return self.delete_batch(list(dict.fromkeys(names))) if names else True

    def cleanup_records(self, names):
        """Verify and remove only records registered by the current case."""
        if not self.close_modal():
            return False
        for name in dict.fromkeys(names):
            if not name:
                continue
            if not self._set_search(name):
                return False
            if self._row(name) is not None and not self.delete_batch([name]):
                return False
            if not self._set_search(name) or self._row(name) is not None:
                return False
        return True
