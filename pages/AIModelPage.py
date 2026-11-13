# -*- coding: utf-8 -*-
"""4.39.8 AI model settings, scoped to temporary model cards."""

from __future__ import annotations

import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import StaleElementReferenceException

from pages.FeatureActionsPage import FeatureActionsPage
from common.ui_state import wait_stable_state, wait_query_finished


class AIModelPage(FeatureActionsPage):
    group_name = "AI模型配置"
    item_name = "模型设置"

    def __init__(self, driver):
        super().__init__(driver=driver)
        self.last_messages = []

    def open_models(self):
        return self.open_page(self.group_name, self.item_name)

    def _active_modal(self):
        return self.driver.execute_script(
            "return [...document.querySelectorAll('.ant-modal-content')].filter(x => x.offsetParent !== null).at(-1) || null"
        )

    def _open_add(self):
        if not self.open_models():
            return False
        if not self.click_text("新增模型", timeout=4):
            return False
        return self.wait_until(self._active_modal, timeout=4) is not False

    def _set_input(self, field_id, value):
        for _ in range(3):
            modal = self._active_modal()
            if modal is None:
                return False
            try:
                field = modal.find_element(By.CSS_SELECTOR, f"#{field_id}")
                self.driver.execute_script(
                    """
                    const field=arguments[0], value=arguments[1];
                    const setter=Object.getOwnPropertyDescriptor(
                      HTMLInputElement.prototype, 'value').set;
                    setter.call(field, value);
                    field.dispatchEvent(new Event('input',{bubbles:true}));
                    field.dispatchEvent(new Event('change',{bubbles:true}));
                    field.dispatchEvent(new Event('blur',{bubbles:true}));
                    """,
                    field,
                    str(value or ""),
                )
                committed=wait_stable_state(self,lambda: self.driver.execute_script(
                    "const input=[...document.querySelectorAll('.ant-modal-content #'+CSS.escape(arguments[0]))].find(e=>e.offsetParent!==null);return input&&input.value===arguments[1]?{committed:true}:null;",
                    field_id,str(value or '')),timeout=3,stable_for=0.2)
                if committed is not False:
                    return True
            except Exception:
                time.sleep(0.1)
        return False

    def _select_vendor(self, vendor):
        modal = self._active_modal()
        if modal is None:
            return False
        control = modal.find_element(By.CSS_SELECTOR, "#form_item_provider")
        selector = self.driver.execute_script(
            "return arguments[0].closest('.ant-select')?.querySelector('.ant-select-selector') || null",
            control,
        )
        if selector is None:
            return False
        try:
            selector.click()
        except Exception:
            self.driver.execute_script("arguments[0].click()", selector)
        expected = str(vendor).replace(" ", "").lower()
        option = self.wait_until(
            lambda: self.driver.execute_script(
                """
                const expected = arguments[0];
                return [...document.querySelectorAll(
                  '.ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option'
                )].find(item => (item.innerText || '').replace(/\s/g, '').toLowerCase() === expected) || null;
                """,
                expected,
            ),
            timeout=4,
        )
        if not option:
            return False
        try:
            option.click()
        except Exception:
            self.driver.execute_script("arguments[0].click()", option)
        return bool(
            self.wait_until(
                lambda: expected
                in (
                    self.driver.execute_script(
                        "return [...document.querySelectorAll('.ant-modal-content #form_item_provider')].find(e=>e.offsetParent!==null)?.closest('.ant-select')?.innerText || ''",
                    )
                    or ""
                )
                .replace(" ", "")
                .lower(),
                timeout=3,
            )
        )

    def _submit_modal(self, label="立即新增"):
        modal = self._active_modal()
        if modal is None:
            return False
        buttons = [
            button
            for button in modal.find_elements(By.CSS_SELECTOR, "button")
            if button.is_displayed()
            and label.replace(" ", "") in (button.text or "").replace(" ", "")
        ]
        if len(buttons)!=1:
            return False
        buttons[0].click()
        return True

    def modal_errors(self):
        return self.driver.execute_script(
            """
            const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
            const modal=[...document.querySelectorAll('.ant-modal-content')].filter(visible).at(-1);
            return [...(modal?.querySelectorAll('.ant-form-item-explain-error,.ant-form-item-explain,.ant-form-explain,[role=alert]')||[])]
              .filter(visible).map(e=>(e.innerText||'').trim()).filter(Boolean);
            """
        ) or []

    def _notices(self,include_modals=False):
        return self.driver.execute_script(
            """
            window.__cesNoticeIds ||= new WeakMap(); window.__cesNoticeSequence ||= 0;
            let selector='.ant-message-notice-content,.ant-notification-notice-message,.ant-notification-notice-description';
            if(arguments[0])selector+=',.ant-modal-content';
            return [...document.querySelectorAll(selector)].filter(e=>e.offsetParent!==null).map(e=>{
              if(!window.__cesNoticeIds.has(e))window.__cesNoticeIds.set(e,++window.__cesNoticeSequence);
              return {id:window.__cesNoticeIds.get(e),text:(e.innerText||'').trim()};}).filter(e=>e.text);
            """,include_modals,
        ) or []

    def page_messages(self):
        return [item['text'] for item in self._notices()]

    def close_modal(self):
        self.driver.execute_script(
            """
            const modal=[...document.querySelectorAll('.ant-modal-content')].filter(e=>e.offsetParent!==null).at(-1);
            if(!modal)return;
            const button=[...modal.querySelectorAll('button')].find(e=>e.offsetParent!==null&&
              (e.matches('.ant-modal-close')||['关闭','取消'].includes((e.innerText||'').replace(/\s/g,''))));
            button?.click();
            """
        )
        return wait_stable_state(self,lambda: {'closed':True} if self._active_modal() is None else False,timeout=4) is not False

    def _card(self, name):
        if not name:
            return None
        return self.driver.execute_script(
            """
            const expected = arguments[0];
            const candidates = [...document.querySelectorAll('main *')]
              .filter(item => item.children.length === 0 && (item.innerText || '').trim() === expected);
            for (const label of candidates) {
              let parent = label.parentElement;
              for (let depth = 0; parent && depth < 8; depth++, parent = parent.parentElement) {
                const text = parent.innerText || '';
                if (text.includes('连通性测试') && parent.querySelectorAll('button').length >= 2) return parent;
              }
            }
            return null;
            """,
            name,
        )

    def exists(self, name, refresh=False):
        if refresh:
            self.driver.refresh()
            self.wait_for_document_ready(timeout=5)
            self.open_models()
            if not wait_query_finished(self,0,timeout=10,request_path='/serv/v1/ai/model/page'):
                raise AssertionError('AI刷新后的列表请求未完成')
            if wait_stable_state(self,lambda:self.driver.execute_script("return (document.querySelector('main')?.innerText||'').trim()"),timeout=6) is False:
                raise AssertionError('AI刷新后的卡片内容未稳定')
        return self._card(name) is not None

    def create(self, payload):
        self.last_messages = []
        if not self._open_add():
            return False
        previous_messages = {item['id']:item['text'] for item in self._notices()}
        self._set_input("form_item_name", payload.get("name", ""))
        if payload.get("vendor") and not self._select_vendor(payload["vendor"]):
            self.last_messages = ["厂商下拉选项未匹配"]
            return False
        self._set_input("form_item_modelId", payload.get("model", ""))
        self._set_input("form_item_apiUrl", payload.get("url", ""))
        self._set_input("form_item_apiKey", payload.get("api_key", ""))
        self._submit_modal()
        def current_messages():
            return [item['text'] for item in self._notices()
                    if item['text'] != previous_messages.get(item['id'])]
        created = self.wait_until(
            lambda: self._card(payload["name"])
            or current_messages()
            or self.modal_errors(),
            timeout=10,
        )
        self.last_messages = current_messages() or self.modal_errors()
        if self._card(payload["name"]) is None and any(
            "成功" in message for message in self.last_messages
        ):
            self.wait_until(lambda: self._card(payload["name"]), timeout=4)
        return wait_stable_state(self,lambda: {'created':True} if self._card(payload['name']) is not None and self._active_modal() is None else False,timeout=6) is not False

    def validate_rejected(self, payload, target_field=None):
        self.last_validation_fields={}
        if target_field is None:
            # Compatibility for existing callers: identify the single changed
            # field only to wait for its UI error, never validate it locally.
            target_field=next((key for key in ('name','vendor','model','url','api_key') if not payload.get(key)),None)
            if target_field is None:
                import re
                target_field=('name' if re.search(r'[_@.\-]',payload.get('name','')) else
                    'model' if re.search(r'[^A-Za-z0-9._-]',payload.get('model','')) else
                    'url' if not payload.get('url','').startswith(('http://','https://')) or ':///' in payload.get('url','') else 'api_key')
        name=payload.get('name','')
        if name and self._card(name) is not None:
            raise AssertionError('前置条件：本次异常模型名称已存在，禁止覆盖或清理既有记录')
        if not self._open_add():
            return False, []
        previous_notices={item['id']:item['text'] for item in self._notices()}
        for field_id, key in (
            ("form_item_name", "name"),
            ("form_item_modelId", "model"),
            ("form_item_apiUrl", "url"),
            ("form_item_apiKey", "api_key"),
        ):
            self._set_input(field_id, payload.get(key, ""))
        if payload.get("vendor"):
            self._select_vendor(payload["vendor"])
        self._submit_modal()
        def field_errors():
            result=self.driver.execute_script(
                """
                const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                const modal=[...document.querySelectorAll('.ant-modal-content')].filter(visible).at(-1);
                if(!modal)return {};
                const result={};
                for(const [key,id] of Object.entries({name:'name',vendor:'provider',model:'modelId',url:'apiUrl',api_key:'apiKey'})){
                  const field=modal.querySelector('#form_item_'+id);
                  const item=field?.closest('.ant-form-item');
                  const errors=[...(item?.querySelectorAll('.ant-form-item-explain-error,.ant-form-explain,[role=alert]')||[])];
                  const text=errors.filter(visible).map(e=>(e.innerText||'').trim()).filter(Boolean).join(' ');
                  if(text)result[key]=text;
                }return result;
                """
            ) or {}
            words={'name':('名称',),'vendor':('厂商',),'model':('模型标识','模型ID','模型仅支持'),
                'url':('接口地址',),'api_key':('密钥','api key','apikey')}
            for notice in self._notices():
                message=notice['text']
                if message==previous_notices.get(notice['id']):continue
                if any(word.casefold() in message.casefold() for word in words.get(target_field,())) and not any(word in message for word in ('新增成功','修改成功','删除成功')):
                    result[target_field]=message
            return result
        name = payload.get("name", "")
        observed_fields={}
        def validation_outcome():
            fields=field_errors()
            if fields.get(target_field):
                observed_fields.update(fields)
                return fields
            return (bool(name) and self._card(name) is not None) or self._active_modal() is None
        self.wait_until(
            validation_outcome,
            timeout=6,
        )
        self.last_validation_fields=observed_fields or field_errors()
        errors = list(dict.fromkeys(list(self.last_validation_fields.values())+self.modal_errors() + self.page_messages()))
        rejected = bool(self.last_validation_fields.get(target_field)) and (not name or self._card(name) is None)
        if self._active_modal() is not None:
            self.close_modal()
        if not rejected and name and self._card(name) is not None:
            assert self.delete(name), '本次异常模型意外保存，清理失败'
        return rejected, errors

    def input_length_snapshot(self, name, model, api_key):
        if not self._open_add():
            return {}
        result = {}
        try:
            for field_id, value in (
                ("form_item_name", name),
                ("form_item_modelId", model),
                ("form_item_apiKey", api_key),
            ):
                modal = self._active_modal()
                field = modal.find_element(By.CSS_SELECTOR, f"#{field_id}")
                field.click()
                field.send_keys(Keys.CONTROL, "a")
                field.send_keys(Keys.DELETE)
                field.send_keys(str(value))
                field.send_keys(Keys.TAB)
                modal = self._active_modal()
                field = modal.find_element(By.CSS_SELECTOR, f"#{field_id}")
                result[field_id] = {
                    "maxlength": int(field.get_attribute("maxlength") or -1),
                    "length": len(field.get_attribute("value") or ""),
                }
            return result
        finally:
            self.close_modal()

    def _icon_action(self, name, icon_names):
        for attempt in range(3):
            try:
                return self._icon_action_once(name,icon_names)
            except StaleElementReferenceException:
                if self._active_modal() is not None:
                    return True  # The requested editor/confirmation already opened.
                if attempt==2:raise
        return False

    def _icon_action_once(self, name, icon_names):
        if self._active_modal() is not None:
            raise AssertionError('AI卡片操作前仍有活动弹窗')
        card = self._card(name)
        if card is None:
            return False
        for icon_name in icon_names:
            icons = card.find_elements(By.CSS_SELECTOR, f"[data-icon='{icon_name}']")
            if icons:
                button = icons[0].find_element(By.XPATH, "ancestor::button[1]")
                button.click()
                return True
            suffix = "table_edit" if icon_name in {"edit", "form"} else "table_delete"
            use = next(
                (
                    item
                    for item in card.find_elements(By.TAG_NAME, "use")
                    if (
                        item.get_attribute("href")
                        or item.get_attribute("xlink:href")
                        or ""
                    ).endswith(suffix)
                ),
                None,
            )
            if use is not None:
                button = use.find_element(By.XPATH, "ancestor::button[1]")
                button.click()
                return True
        return False

    def modify_name_keep_key(self, old_name, new_name):
        self.last_modify_evidence={'old_name':old_name,'new_name':new_name,'stage':'edit-control'}
        if not self._icon_action(old_name, ("edit", "form")):
            return False
        if not self.wait_until(self._active_modal, timeout=4):
            return False
        if not self._set_input("form_item_name", new_name):
            self.last_modify_evidence['stage']='name-input'
            return False
        has_key=self.driver.execute_script(
            "const modal=[...document.querySelectorAll('.ant-modal-content')].filter(e=>e.offsetParent!==null).at(-1);return !!modal?.querySelector('#form_item_apiKey')?.value;"
        )
        if has_key:
            self._set_input("form_item_apiKey", "")
        clicked=self._submit_modal("保存")
        self.last_modify_evidence.update(stage='save',save_clicked=clicked)
        updated=wait_stable_state(self,lambda: {'updated':True} if self._card(new_name) is not None and self._active_modal() is None else False,timeout=8) is not False if clicked else False
        self.last_modify_evidence.update(updated=updated,errors=self.modal_errors(),messages=self.page_messages())
        return updated

    def test_connectivity(self, name, expected, timeout):
        card = self._card(name)
        if card is None:
            return None
        button = next(
            (
                item
                for item in card.find_elements(By.TAG_NAME, "button")
                if "连通性测试" in (item.text or "")
            ),
            None,
        )
        if button is None:
            return None
        previous_elements = {item['id']:item['text'] for item in self._notices(True)}
        started = time.monotonic()
        self.driver.execute_script("arguments[0].click()", button)
        observed = []

        def result():
            texts = [item['text'] for item in self._notices(True)
                     if item['text'] != previous_elements.get(item['id'])]
            for text in texts:
                if text and text not in observed:
                    observed.append(text)
            terminal = next(
                (
                    text
                    for text in texts
                    if expected in text
                    or text in {'连接失败','连接成功','连接超时'}
                    or (
                        "连通性" in text
                        and any(word in text for word in ("通过", "成功", "失败", "异常", "超时"))
                    )
                ),
                False,
            )
            return terminal

        message = self.wait_until(result, timeout=timeout, poll_frequency=0.25)
        return {
            "message": message or "",
            "elapsed": time.monotonic() - started,
            "observed": observed,
            "matched": bool(message and expected in message),
        }

    def default_model_name(self):
        return self.driver.execute_script(
            """
            const marker = [...document.querySelectorAll('main *')]
              .find(item => item.children.length === 0 && (item.innerText || '').trim() === '默认模型');
            if (!marker) return '';
            let parent = marker.parentElement;
            while (parent && !parent.innerText.includes('连通性测试')) parent = parent.parentElement;
            if (!parent) return '';
            const lines = (parent.innerText || '').split(String.fromCharCode(10))
              .map(x => x.trim()).filter(Boolean);
            return lines.find(line => !['默认模型','连通性测试'].includes(line) && !line.includes(':')) || '';
            """
        )

    def set_default(self, name):
        card = self._card(name)
        if card is None:
            return False
        button = next(
            (
                item
                for item in card.find_elements(By.TAG_NAME, "button")
                if "设为默认" in (item.text or "")
            ),
            None,
        )
        if button is None:
            return "默认模型" in (card.text or "")
        self.driver.execute_script("arguments[0].click()", button)
        return bool(
            self.wait_until(
                lambda: self._card(name) is not None
                and "默认模型" in (self._card(name).text or ""),
                timeout=6,
            )
        )

    def delete(self, name):
        if self._active_modal() is not None:
            assert self.close_modal(), 'AI清理前编辑弹窗无法取消'
        if not self.open_models():
            return False
        if self._card(name) is None:
            return True
        if not self._icon_action(name, ("delete",)):
            return False
        confirm = self.wait_until(
            lambda: self.driver.execute_script(
                "return [...document.querySelectorAll('.ant-modal-content,.ant-popover')].filter(x=>x.offsetParent!==null).at(-1) || null"
            ),
            timeout=3,
        )
        if confirm:
            clicked = self.driver.execute_script(
                """
                const buttons = [...arguments[0].querySelectorAll('button')]
                  .filter(item => item.offsetParent !== null && !item.disabled);
                const button = buttons.find(item =>
                  ['确定', '删除'].includes((item.innerText || '').replace(/\s+/g, '')))
                  || buttons.find(item => item.classList.contains('ant-btn-primary'));
                if (!button) return false;
                button.click(); return true;
                """,
                confirm,
            )
            if not clicked:
                return False
        removed=wait_stable_state(self,lambda: {'removed':True} if self._card(name) is None and self._active_modal() is None else False,timeout=8) is not False
        return removed and not self.exists(name,refresh=True)

    def cleanup_prefix(self, prefix=None):
        if not prefix:
            raise AssertionError('AI清理必须提供本次用例唯一前缀，禁止全局前缀清理')
        self.open_models()
        names = self.driver.execute_script(
            """
            const prefix = arguments[0];
            return [...document.querySelectorAll('main *')]
              .filter(item => item.children.length === 0 && (item.innerText || '').trim().startsWith(prefix))
              .map(item => (item.innerText || '').trim()).filter((x,i,a) => a.indexOf(x) === i);
            """,
            prefix,
        )
        return {name: self.delete(name) for name in names}
