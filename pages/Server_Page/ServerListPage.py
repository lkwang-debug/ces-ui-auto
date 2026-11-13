# -*- coding: utf-8 -*-
"""Page object for server management's server list.

The server form differs slightly between CES versions.  All form controls are
therefore resolved from their visible Chinese label inside the active modal,
instead of relying on a position in the input list.
"""

from __future__ import annotations

import time
import json
import allure

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import StaleElementReferenceException, ElementClickInterceptedException, ElementNotInteractableException

from pages.FeatureCatalogPage import FeatureCatalogPage, PAGE_FEATURES
from common.ui_state import wait_stable_state, wait_control_unobscured, wait_query_finished, strict_wait
from common.privacy import masked_screenshot


class ServerListPage(FeatureCatalogPage):
    group_name = "服务器管理"
    item_name = "服务器列表"
    create_labels = ("新增", "新增服务器", "添加服务器")
    update_labels = ("修改", "编辑", "修改服务器")
    delete_labels = ("删除", "移除")
    save_labels = ("确定", "保存", "提交")
    cancel_labels = ("取消", "关闭")
    add_server_item = (By.CSS_SELECTOR, "main .add-server-item")
    server_category_items = (By.CSS_SELECTOR, "main .left-box-tree .sitem")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._created_server_names = {}
        self._created_server_profiles = {}
        self._server_name_history = {}
        self._pending_server_cleanup = set()

    def _remember_payload(self, profile, payload):
        identifier, name = payload['设备ID'], payload['设备名称']
        self._created_server_names[identifier] = name
        self._created_server_profiles[identifier] = profile
        self._pending_server_cleanup.add(identifier)
        history = self._server_name_history.setdefault(identifier, [])
        if name not in history:
            history.append(name)

    def common_enter_server_list(self):
        return self.open_server_list() is not None

    def open_server_list(self):
        # Server CRUD scenarios run consecutively in one browser session.  Once
        # the target page has mounted, keep using it instead of resetting via
        # the user-management route before every form action.  The route and
        # visible page title remain mandatory checks, so this does not weaken
        # the page-reachability assertion.
        current = self._current_server_list_snapshot()
        if current is not None:
            return current
        snapshot = self.open_feature(self.group_name, self.item_name)
        if snapshot is not None:
            return snapshot
        # The first lazy route transition after a fresh login on 4.39.7 can
        # resolve before the server-card view mounts. Retry the same page
        # once; later calls still fail normally if the feature is unavailable.
        return self.open_feature(self.group_name, self.item_name)

    def _current_server_list_snapshot(self):
        profile = PAGE_FEATURES[self.group_name][self.item_name]
        if profile["route"] not in (self.driver.current_url or ""):
            return None
        main = self.wait_visible(self.main, timeout=1)
        if main is False:
            return None
        try:
            if profile["title"] not in (main.text or ""):
                return None
        except StaleElementReferenceException:
            return None
        return self.snapshot_main(main)

    def visible_server_categories(self):
        snapshot = self.open_server_list()
        if not snapshot:
            return []
        return [
            name
            for name in ("会议服务器", "录制服务器", "资源平台服务器")
            if name in snapshot["text"]
        ]

    def build_server_payload(self, profile, suffix):
        prefix = "meet" if profile["key"] == "meeting" else "record"
        identifier = f"{prefix}{suffix}"[-28:]
        return {
            "设备ID": identifier,
            "设备名称": f"uiauto_{prefix}_{suffix}"[-48:],
            "设备验证码": f"Auto{str(suffix)[-8:]}",
            "服务器地址": profile["address"],
            **profile.get("numbers", {}),
            **profile.get("selects", {}),
        }

    def open_create_server_dialog(self, profile=None):
        self.open_server_list()
        if profile and not self._select_server_category(profile):
            raise AssertionError(f"无法切换服务器分类：{profile['name']}")
        modal = None
        for attempt in range(2):
            if not self._click_create_entry():
                if attempt == 0 and profile and self._select_server_category(profile):
                    continue
                available = self._visible_button_texts()
                raise AssertionError(
                    "服务器列表未提供新增服务器入口；当前可见操作："
                    + ("、".join(available) or "无")
                )
            modal = self._wait_active_modal(timeout=4)
            if modal is not None:
                break
            if profile:
                self._select_server_category(profile)
        if modal is None:
            raise AssertionError("已点击新增服务器，但新增服务器弹窗未出现")
        return modal

    def has_server_crud_entry(self):
        self.open_server_list()
        return self.wait_visible(self.add_server_item, timeout=2) is not False or any(
            label in self._visible_button_texts() for label in self.create_labels
        )

    def server_list_actions(self):
        self.open_server_list()
        return self._visible_button_texts()

    def cancel_active_dialog(self):
        modal = self._wait_active_modal(timeout=2)
        if modal is None:
            return True
        if not self._click_modal_button(modal, self.cancel_labels):
            close_buttons = modal.find_elements(By.CSS_SELECTOR, ".ant-modal-close")
            if close_buttons:
                self._safe_click(close_buttons[0])
            else:
                return False
        return self._wait_modal_closed(timeout=4)

    def create_server(self, profile, payload):
        self._remember_payload(profile, payload)
        modal = self.open_create_server_dialog(profile)
        try:
            self.fill_server_form(modal, profile, payload)
            self._submit_modal(modal)
            if not self._wait_modal_closed(timeout=8):
                return False
            self._wait_server_mutation_refresh(self._server_submit_started, '/serv/v1/conf/add')
            self._created_server_names[payload["设备ID"]] = payload["设备名称"]
            self._created_server_profiles[payload["设备ID"]] = profile
            return self.search_server(payload["设备ID"])
        finally:
            if self._wait_active_modal(timeout=0.2) is not None:
                self.cancel_active_dialog()

    def validate_required_field(self, profile, payload, field_name):
        self._remember_payload(profile, payload)
        modal = self.open_create_server_dialog(profile)
        rejected = False
        try:
            data = dict(payload)
            data[field_name] = ""
            self.fill_server_form(modal, profile, data, allow_empty={field_name})
            self._submit_modal(modal)
            evidence = self._validation_evidence(modal, field_name)
            # A missing mandatory field must keep the dialog open and show an error.
            rejected = bool(evidence) and self._current_active_modal() is not None
            return rejected
        finally:
            self._verify_server_validation_left_no_record(payload, field_name, '')

    def validate_invalid_value(self, profile, payload, field_name, invalid_value):
        self._remember_payload(profile, payload)
        modal = self.open_create_server_dialog(profile)
        rejected = False
        try:
            data = dict(payload)
            data[field_name] = invalid_value
            self.fill_server_form(modal, profile, data)
            self._submit_modal(modal)
            evidence = self._validation_evidence(modal, field_name)
            rejected = bool(evidence) and self._current_active_modal() is not None
            return rejected
        finally:
            self._verify_server_validation_left_no_record(payload, field_name, invalid_value)

    def _verify_server_validation_left_no_record(self, payload, field_name, attempted_value):
        if self._current_active_modal() is None:
            self._wait_server_mutation_refresh(self._server_submit_started, '/serv/v1/conf/add')
        assert self.cancel_active_dialog(), '服务器字段校验后弹窗未关闭'
        created = self.search_server(payload['设备ID'])
        allure.attach(json.dumps({'设备ID':payload['设备ID'],'设备名称':payload['设备名称'],'产生记录':created},ensure_ascii=False),
                      '服务器负向校验后的查询结果',allure.attachment_type.JSON)
        if created:
            try:
                modal = self._open_edit_dialog(payload['设备ID'])
                stored = self._field_input(modal, field_name) if modal is not None else None
                stored_value = stored.get_attribute('value') if stored is not None else None
                allure.attach(json.dumps({'字段':field_name,'尝试输入':attempted_value,'保存后读值':stored_value,
                                         '提交前数值控件':getattr(self,'last_server_submit_numeric',[])},ensure_ascii=False),
                              '服务器负向输入实际保存值',allure.attachment_type.JSON)
            finally:
                assert self.cancel_active_dialog(), '读取意外保存值后未关闭弹窗'
                assert self.ensure_server_absent(payload['设备ID']), '负向校验意外保存的服务器未清理成功'
            raise AssertionError('服务器非法或必填输入校验后实际产生了记录，已清理；不能判为通过')
        self._pending_server_cleanup.discard(payload['设备ID'])

    def field_maxlength(self, field_name, profile=None):
        modal = self.open_create_server_dialog(profile)
        try:
            element = self._field_input(modal, field_name)
            if element is None:
                return None
            value = element.get_attribute("maxlength")
            try:
                maximum = int(value)
            except (TypeError, ValueError):
                return None
            return maximum if maximum > 0 else None
        finally:
            self.cancel_active_dialog()

    def validate_text_maxlength(self, profile, payload, field_name):
        maximum = self.field_maxlength(field_name)
        if not maximum:
            return None
        too_long = "X" * (maximum + 1)
        return self.validate_invalid_value(profile, payload, field_name, too_long)

    def modify_server(self, identifier, changes):
        modal = self._open_edit_dialog(identifier)
        if modal is None:
            return False
        try:
            if '设备名称' in changes:
                history = self._server_name_history.setdefault(identifier, [self._created_server_names[identifier]])
                if changes['设备名称'] not in history:
                    history.append(changes['设备名称'])
            for field_name, value in changes.items():
                if not self._fill_field(modal, field_name, value):
                    return False
            self._submit_modal(modal)
            if not self._wait_modal_closed(timeout=8):
                return False
            self._wait_server_mutation_refresh(self._server_submit_started, '/serv/v1/conf/add')
            if "设备名称" in changes:
                self._created_server_names[identifier] = changes["设备名称"]
            # Numeric fields are intentionally not rendered on the collapsed
            # card. Reopen the edit form and read the stored values instead
            # of treating an invisible field as a page-text assertion.
            verification_modal = self._open_edit_dialog(identifier)
            if verification_modal is None:
                return False
            try:
                return all(
                    (element := self._field_input(verification_modal, field_name))
                    is not None
                    and (element.get_attribute("value") or "") == str(value)
                    for field_name, value in changes.items()
                )
            finally:
                self.cancel_active_dialog()
        finally:
            self.cancel_active_dialog()
            self._clear_search()

    def read_server_field(self, identifier, field_name, refresh=True):
        if refresh:
            self.driver.refresh()
            self.wait_for_document_ready(timeout=5)
        modal = self._open_edit_dialog(identifier)
        if modal is None:
            raise AssertionError(f'未打开本次服务器编辑框：{identifier}')
        try:
            field = self._field_input(modal, field_name)
            if field is None:
                raise AssertionError(f'本次服务器缺少可读取字段：{field_name}')
            value = field.get_attribute('value') or ''
            allure.attach(json.dumps({'设备ID':identifier,'字段':field_name,'刷新后保存值':value},ensure_ascii=False),
                          '服务器刷新回读值',allure.attachment_type.JSON)
            return value
        finally:
            assert self.cancel_active_dialog(), '服务器字段回读后弹窗未关闭'
            self._clear_search()

    def _open_edit_dialog(self, identifier):
        self.open_server_list()
        if not self.search_server(identifier, restore=False):
            return None
        if not self._expand_server_card(identifier):
            return None
        container = self._server_container(identifier)
        if container is None or not self._click_in_container(container, self.update_labels):
            return None
        modal = self._wait_active_modal(timeout=6)
        if modal is None:
            return None
        expected = self._created_server_names.get(identifier, identifier)
        def identity():
            state = self.driver.execute_script(r"""
                const modal=arguments[0],read=label=>{
                  const item=[...modal.querySelectorAll('.ant-form-item')].find(e=>
                    (e.querySelector('label')?.innerText||'').replace(/[\s*:：]/g,'')===label);
                  return item?.querySelector('input')?.value??null;};
                return {name:read('设备名称'),id:read('设备ID')};
            """, modal)
            self.last_server_edit_identity = state
            if state['name'] != expected or (state['id'] is not None and state['id'] != identifier):
                return False
            return state
        if wait_stable_state(self, identity, timeout=6, stable_for=0.2) is False:
            allure.attach(json.dumps({'设备ID':identifier,'预期名称':expected,'实际表单':getattr(self,'last_server_edit_identity',{})},ensure_ascii=False),
                          '服务器编辑身份校验失败',allure.attachment_type.JSON)
            with masked_screenshot(self.driver):
                allure.attach(self.driver.get_screenshot_as_png(),'服务器编辑身份校验现场',allure.attachment_type.PNG)
            self.cancel_active_dialog()
            raise AssertionError(f'编辑框未加载准确服务器 {identifier}/{expected}，禁止修改')
        return modal

    def search_server(self, identifier, restore=True):
        self.open_server_list()
        profile = self._created_server_profiles.get(identifier)
        if profile and not self._select_server_category(profile):
            raise AssertionError(f'服务器分类未就绪，不能判定记录不存在：{profile["name"]}')
        query = self._created_server_names.get(identifier, identifier)
        self._query_server_cards(query)
        found = self._server_container(identifier) is not None
        if restore:
            self._clear_search()
        return bool(found)

    def delete_server(self, identifier):
        self.open_server_list()
        if not self.search_server(identifier, restore=False):
            self._clear_search()
            return True
        container = self._server_container(identifier)
        if container is None or not self._expand_server_card(identifier):
            return False
        container = self._server_container(identifier)
        if container is None or not self._click_in_container(container, self.delete_labels):
            return False
        started = self.driver.execute_script('return performance.now()')
        if not self._confirm_delete():
            raise AssertionError(f'未确认删除本次服务器：{identifier}')
        self._wait_server_mutation_refresh(started, '/serv/v1/conf/delete')
        absent = self.wait_until(lambda: self._server_container(identifier) is None, timeout=10, poll_frequency=0.3)
        if absent:
            absent = not self.search_server(identifier, restore=False)
        self._clear_search()
        return bool(absent)

    def ensure_server_absent(self, identifier):
        latest = self._created_server_names.get(identifier)
        if latest is None:
            raise AssertionError(f'未登记本次服务器名称，不能判定清理完成：{identifier}')
        try:
            for name in self._server_name_history.get(identifier, [latest]):
                self._created_server_names[identifier] = name
                if not self.delete_server(identifier):
                    return False
            self._pending_server_cleanup.discard(identifier)
            return True
        finally:
            self._created_server_names[identifier] = latest

    def cleanup_registered_servers(self):
        outcomes = []
        for identifier in list(self._pending_server_cleanup):
            try:
                cleared = self.ensure_server_absent(identifier)
                outcomes.append({'设备ID':identifier,'本次登记名称':self._server_name_history.get(identifier,[]),'清理成功':cleared})
            except Exception as error:
                outcomes.append({'设备ID':identifier,'本次登记名称':self._server_name_history.get(identifier,[]),'清理成功':False,'原因':str(error)})
        allure.attach(json.dumps(outcomes,ensure_ascii=False,indent=2),'服务器模块兜底清理结果',allure.attachment_type.JSON)
        assert all(item['清理成功'] is True for item in outcomes), f'服务器模块兜底清理失败：{outcomes}'

    def fill_server_form(self, modal, profile, payload, allow_empty=None):
        allow_empty = allow_empty or set()
        # Type controls the presence/defaults of the numeric fields. Confirm
        # it before entering boundary values so a later type change cannot
        # reset zero/negative inputs back to valid defaults.
        if not self._choose_first_available_option(modal, "设备类型", profile["type_names"]):
            raise AssertionError(f"无法选择服务器类型：{profile['type_names']}")
        for field_name, value in payload.items():
            if field_name == "设备类型":
                continue
            if field_name in profile.get("selects", {}):
                if not self._select_field(modal, field_name, value):
                    raise AssertionError(f"无法选择字段：{field_name}={value}")
                continue
            if value == "" and field_name in allow_empty:
                if not self._fill_field(modal, field_name, ""):
                    raise AssertionError(f"无法清空字段：{field_name}")
                continue
            if not self._fill_field(modal, field_name, value):
                raise AssertionError(f"无法填写字段：{field_name}")
        return True

    def _main_text(self):
        return self.driver.execute_script(
            "return (document.querySelector('main')?.innerText || '').replace(/\\s+/g, ' ').trim()"
        )

    def _visible_button_texts(self):
        result = []
        for button in self.driver.find_elements(By.CSS_SELECTOR, "main button"):
            try:
                if button.is_displayed() and (button.text or "").strip():
                    result.append(button.text.strip())
            except Exception:
                continue
        return result

    def _click_page_button(self, labels):
        for button in self.driver.find_elements(By.CSS_SELECTOR, "main button"):
            try:
                if button.is_displayed() and button.is_enabled() and button.text.strip() in labels:
                    self._safe_click(button)
                    return True
            except Exception:
                continue
        return False

    def _click_create_entry(self):
        """Click the category card's plus icon, used by 4.39.7 and 4.39.8."""
        if self._click_first_available_safe([self.add_server_item], timeout=4):
            return True
        return self._click_page_button(self.create_labels)

    def _select_server_category(self, profile):
        target = self._normalise_label(profile["name"])
        for item in self.driver.find_elements(*self.server_category_items):
            try:
                if not item.is_displayed():
                    continue
                text = self._normalise_label(item.text)
                if target in text:
                    if 'active' in (item.get_attribute('class') or '').split():
                        return True
                    self._safe_click(item)
                    return self.wait_until(
                        lambda: "active" in (item.get_attribute("class") or ""),
                        timeout=3,
                        poll_frequency=0.2,
                    ) is not False
            except Exception:
                continue
        return False

    def _wait_active_modal(self, timeout=5):
        result = self.wait_until(
            self._current_active_modal, timeout=timeout, poll_frequency=0.2
        )
        return result or None

    def _wait_modal_closed(self, timeout=5):
        return bool(
            self.wait_until(
                lambda: self._current_active_modal() is None,
                timeout=timeout,
                poll_frequency=0.2,
            )
        )

    def _current_active_modal(self):
        for modal in reversed(self.driver.find_elements(By.CSS_SELECTOR, ".ant-modal-content")):
            try:
                if modal.is_displayed():
                    return modal
            except Exception:
                continue
        return None

    @staticmethod
    def _normalise_label(value):
        return "".join(str(value or "").replace("*", "").replace("：", "").replace(":", "").split())

    def _form_item(self, modal, field_name):
        target = self._normalise_label(field_name)
        return self.driver.execute_script(
            """
            const modal = arguments[0];
            const target = arguments[1];
            const clean = value => (value || '').replace(/[\\s*:：]/g, '');
            const items = [...modal.querySelectorAll('.ant-form-item')];
            return items.find(item => {
              const label = item.querySelector('label, .ant-form-item-label');
              const text = clean(label ? label.innerText : '');
              return text === target || text.startsWith(target);
            }) || null;
            """,
            modal,
            target,
        )

    def _field_input(self, modal, field_name):
        item = self._form_item(modal, field_name)
        if item is None:
            return None
        return self.driver.execute_script(
            """
            return arguments[0].querySelector(
              'input:not([type=hidden]):not([disabled]), textarea:not([disabled])'
            );
            """,
            item,
        )

    def _fill_field(self, modal, field_name, value):
        element = self._field_input(modal, field_name)
        if element is None:
            return False
        try:
            self._replace_text(element, value)
            return (element.get_attribute("value") or "") == str(value)
        except Exception:
            return False

    def _select_field(self, modal, field_name, value):
        return self._choose_first_available_option(modal, field_name, (str(value),))

    def _choose_first_available_option(self, modal, field_name, candidates, timeout=6):
        expected = {self._normalise_label(value) for value in candidates}
        self.last_server_select_debug = {"字段": field_name, "允许值": list(candidates)}

        def choose():
            active = self._current_active_modal()
            item = self._form_item(active, field_name) if active is not None else None
            if item is None:
                return False
            state = self.driver.execute_script(r"""
                const item=arguments[0];
                const clean=value=>String(value||'').replace(/[\s*:：]/g,'');
                const selected=[...item.querySelectorAll('.ant-select-selection-item,.ant-select-selection-selected-value,.ant-select-selection-placeholder')]
                  .map(e=>clean(e.innerText||e.getAttribute('title'))).filter(Boolean);
                selected.push(...[...item.querySelectorAll('input[readonly]:not([role=combobox])')].map(e=>clean(e.value)).filter(Boolean));
                const select=item.querySelector('.ant-select')||item.querySelector('[role=combobox],.ant-select-selection,input[readonly]');
                const controller=item.querySelector('[aria-controls],[aria-owns]');
                const owner=controller?.getAttribute('aria-controls')||controller?.getAttribute('aria-owns')||'';
                const opened=!!(select&&(select.classList.contains('ant-select-open')||select.getAttribute('aria-expanded')==='true'||item.querySelector('[aria-expanded=true]')));
                return {selected,select,owner,opened};
            """, item)
            self.last_server_select_debug.update({"实际值": state['selected'], "选项关联ID": state['owner'], "下拉已展开": state['opened']})
            selected = next((value for value in state['selected'] if value in expected), None)
            control = state['select']
            if selected is not None and not state['opened']:
                return {"selected": selected}
            if control is None:
                return False
            if not state['opened'] or selected is not None:
                target = wait_control_unobscured(self, lambda: control, timeout=0.3)
                if target is not False:
                    target.click()
                return False
            option = self.driver.execute_script(r"""
                const owner=arguments[0],allowed=arguments[1];
                const clean=value=>String(value||'').replace(/[\s*:：]/g,'');
                const visible=e=>!!(e&&e.getBoundingClientRect().width>2&&e.getBoundingClientRect().height>2&&getComputedStyle(e).visibility!=='hidden');
                let popups=[];
                if(owner){const list=document.getElementById(owner);const popup=list?.closest('.ant-select-dropdown');if(popup)popups=[popup];}
                else{popups=[...document.querySelectorAll('.ant-select-dropdown')].filter(visible);if(popups.length!==1)return null;}
                for(const value of allowed){
                  for(const popup of popups){
                    for(const option of popup.querySelectorAll('.ant-select-item-option,li.ant-select-dropdown-menu-item,[role=option]')){
                      if(!visible(option)||option.getAttribute('aria-disabled')==='true'||/option-disabled|menu-item-disabled/.test(option.className)||clean(option.innerText)!==value)continue;
                      const r=option.getBoundingClientRect(),hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
                      if(hit===option||option.contains(hit))return option;
                    }
                  }
                }
                return null;
            """, state['owner'], [self._normalise_label(value) for value in candidates])
            if option is not None:
                option.click()
            return False

        def render_safe_choice():
            try:
                return choose()
            except (StaleElementReferenceException, ElementClickInterceptedException, ElementNotInteractableException):
                return False

        chosen = wait_stable_state(self, render_safe_choice, timeout=timeout, stable_for=0.2) is not False
        if not chosen:
            allure.attach(json.dumps(self.last_server_select_debug, ensure_ascii=False, indent=2), "服务器下拉选择失败诊断", allure.attachment_type.JSON)
            with masked_screenshot(self.driver):
                allure.attach(self.driver.get_screenshot_as_png(), "服务器下拉选择清理前现场", allure.attachment_type.PNG)
        return chosen

    def _submit_modal(self, modal):
        self.last_server_submit_numeric = self.driver.execute_script(r"""
            return [...arguments[0].querySelectorAll('.ant-form-item')].map(item=>{
              const label=(item.querySelector('label')?.innerText||'').replace(/[\s*:：]/g,'');
              const input=item.querySelector('input');
              return input&&/人数|用户数|最大数|带宽/.test(label)?{label,value:input.value,type:input.type,
                min:input.getAttribute('min'),max:input.getAttribute('max'),role:input.getAttribute('role')}:null;
            }).filter(Boolean);
        """,modal)
        self._server_submit_started = self.driver.execute_script('return performance.now()')
        if not self._click_modal_button(modal, self.save_labels, primary=True):
            raise AssertionError("服务器弹窗未找到确定/保存按钮")

    def _click_modal_button(self, modal, labels, primary=False):
        candidates = modal.find_elements(By.CSS_SELECTOR, "button")
        if primary:
            candidates = sorted(
                candidates,
                key=lambda item: "ant-btn-primary" not in (item.get_attribute("class") or ""),
            )
        for button in candidates:
            try:
                if not button.is_displayed() or not button.is_enabled():
                    continue
                button_class = button.get_attribute("class") or ""
                # The current 4.39.7 response header makes Selenium expose
                # some Chinese button text as mojibake. The primary-footer
                # class is stable across both supported versions.
                if primary and "ant-btn-primary" in button_class:
                    self._safe_click(button)
                    return True
                if button.text.strip() in labels:
                    self._safe_click(button)
                    return True
            except Exception:
                continue
        return False

    def _validation_evidence(self, modal, field_name, timeout=4):
        def evidence():
            active = self._current_active_modal()
            item = self._form_item(active, field_name) if active is not None else None
            if item is None:
                return False
            return self.driver.execute_script("""
                const item=arguments[0],visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                const messages=[...item.querySelectorAll('.ant-form-explain,.ant-form-item-explain,.ant-form-item-explain-error,.ant-form-item-explain-connected,[role=alert]')]
                  .filter(visible).map(e=>(e.innerText||'').trim()).filter(Boolean);
                const input=item.querySelector('input');
                if(input&&!input.validity.valid&&input.validationMessage)messages.push(input.validationMessage);
                return [...new Set(messages)].join(' ');
            """, item) or False
        message = strict_wait(evidence, timeout=timeout) or ''
        allure.attach(json.dumps({'字段':field_name,'目标字段错误':message},ensure_ascii=False), '服务器目标字段校验证据',allure.attachment_type.JSON)
        if not message:
            with masked_screenshot(self.driver):
                allure.attach(self.driver.get_screenshot_as_png(),'服务器字段未出现错误时的现场',allure.attachment_type.PNG)
        return message

    def _visible_search_inputs(self):
        inputs = []
        for element in self.driver.find_elements(By.CSS_SELECTOR, "main input"):
            try:
                input_type = (element.get_attribute("type") or "text").lower()
                if element.is_displayed() and element.is_enabled() and input_type in {"text", "search"}:
                    inputs.append(element)
            except Exception:
                continue
        return inputs

    def _clear_search(self):
        self._query_server_cards('', reset=True)

    def _query_server_cards(self, query, reset=False):
        def field():
            inputs = self._visible_search_inputs()
            return inputs[0] if len(inputs) == 1 else False
        control = wait_control_unobscured(self, field, timeout=5)
        if control is False:
            raise AssertionError('服务器查询控件未就绪，禁止据此判定记录不存在')
        if not reset and (control.get_attribute('value') or '') != str(query):
            # Clearing the search emits an automatic unfiltered GET in CES.
            # Replace the selection directly so no empty intermediate value
            # can launch a response that later overwrites this query.
            control.click()
            control.send_keys(Keys.CONTROL, 'a')
            if query:
                control.send_keys(str(query))
            else:
                control.send_keys(Keys.DELETE)
        started = self.driver.execute_script('return performance.now()')
        if reset:
            category = next((item for item in self.driver.find_elements(*self.server_category_items)
                             if item.is_displayed() and 'active' in (item.get_attribute('class') or '').split()), None)
            if category is None:
                raise AssertionError('服务器当前分类未确认，不能恢复完整列表')
            self._safe_click(category)
        else:
            control.send_keys(Keys.ENTER)
        if not wait_query_finished(self, started, timeout=10, request_path='/serv/v1/conf/list'):
            raise AssertionError('服务器本次查询请求未完成，禁止判定记录不存在')
        def settled():
            state = self.driver.execute_script("""
                const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                const main=document.querySelector('main');
                const inputs=[...(main?.querySelectorAll('input')||[])].filter(e=>visible(e)&&!e.disabled&&['text','search'].includes(e.type));
                const titles=[...(main?.querySelectorAll('.server-item .title')||[])].filter(visible).map(e=>(e.getAttribute('title')||e.innerText||'').trim());
                const empty=/没有找到匹配的记录|暂无数据|暂无服务器|服务器数量[:：]\\s*0(?:\\D|$)/.test(main?.innerText||'');
                return {titles,empty,input_value:inputs.length===1?inputs[0].value:null};
            """)
            self.last_server_query_debug = {'query':query,'reset':reset,**state}
            if state['input_value'] != str(query):
                return False
            if reset and self.find_visible_now(self.add_server_item) is False:
                return False
            if query and any(query not in title for title in state['titles']):
                return False
            return state if state['titles'] or state['empty'] or reset else False
        result = wait_stable_state(self, settled, timeout=6, stable_for=0.2)
        if result is False:
            allure.attach(json.dumps(getattr(self,'last_server_query_debug',{}),ensure_ascii=False),
                          '服务器本次查询未匹配时的状态',allure.attachment_type.JSON)
            with masked_screenshot(self.driver):
                allure.attach(self.driver.get_screenshot_as_png(),'服务器查询清理前现场',allure.attachment_type.PNG)
            raise AssertionError(f'服务器查询结果未按本次条件更新：{query}')
        return result

    def _wait_server_mutation_refresh(self, started, mutation_path, timeout=10):
        """Wait for CES's save/delete -> category -> list callback chain."""
        def completed():
            state = self.driver.execute_script("""
                const all=performance.getEntriesByType('resource').filter(e=>['fetch','xmlhttprequest'].includes(e.initiatorType)&&e.responseEnd>0);
                const latest=(path,after)=>all.filter(e=>e.startTime>=after&&new URL(e.name,location.href).pathname===path).at(-1);
                const mutation=latest(arguments[1],arguments[0]);
                const category=mutation&&latest('/serv/v1/conf/category',mutation.responseEnd);
                const list=category&&latest('/serv/v1/conf/list',category.responseEnd);
                const info=(entry,path)=>({path,complete:!!entry,status:entry?.responseStatus??null});
                return [info(mutation,arguments[1]),info(category,'/serv/v1/conf/category'),info(list,'/serv/v1/conf/list')];
            """, started, mutation_path)
            self.last_server_refresh_state = state
            for item in state:
                if (item['status'] or 0) >= 400:
                    raise AssertionError(f"服务器操作接口HTTP {item['status']}：{item['path']}")
            return all(item['complete'] for item in state)
        if not strict_wait(completed,timeout=timeout):
            allure.attach(json.dumps(getattr(self,'last_server_refresh_state',[]),ensure_ascii=False),
                          '服务器保存删除后的刷新链未完成',allure.attachment_type.JSON)
            raise AssertionError('服务器保存/删除后的分类及列表刷新未完成，未执行后续查询')
        return True

    def _server_container(self, identifier):
        query = self._created_server_names.get(identifier, identifier)
        return self.driver.execute_script(
            """
            const identifier = arguments[0];
            if(!identifier)return null;
            const matches = text => text === identifier ||
              (text.startsWith(identifier) && /^\\s*[（(][^（）()]+[）)]$/.test(text.slice(identifier.length)));
            const visible = element => !!(element.offsetWidth || element.offsetHeight || element.getClientRects().length);
            const serverCards = [...document.querySelectorAll('main .server-item')]
              .filter(visible)
              .filter(element => matches((element.querySelector('.title')?.getAttribute('title')||element.querySelector('.title')?.innerText||'').trim()));
            if (serverCards.length) return serverCards[0];
            const rows = [...document.querySelectorAll('main tr, main .ant-card, main li')]
              .filter(visible)
              .filter(element => [...element.querySelectorAll('[title],td,span')]
                .some(node => matches((node.getAttribute('title')||node.innerText||'').trim())));
            return rows.sort((left, right) => left.innerText.length - right.innerText.length)[0] || null;
            """,
            query,
        )

    def _expand_and_verify_identifier(self, identifier):
        """Verify the persisted card by its unique user-visible name.

        The server card in 4.39.7/4.39.8 deliberately does not expose the
        device ID after save.  The ID remains the submission uniqueness key;
        the generated name is the observable identifier for UI verification.
        """
        expected_name = self._created_server_names.get(identifier, identifier)
        for _ in range(3):
            container = self._server_container(identifier)
            if container is None:
                return False
            try:
                if expected_name in (container.text or ""):
                    return True
            except StaleElementReferenceException:
                continue
        return False

    def _expand_server_card(self, identifier):
        """Open a card before clicking its edit/delete action."""
        if self._server_actions_visible(identifier):
            return True
        for _ in range(3):
            container = self._server_container(identifier)
            if container is None:
                return False
            try:
                arrows = container.find_elements(By.CSS_SELECTOR, ".item-arrow")
                if arrows:
                    self._safe_click(arrows[0])
                return bool(
                    self.wait_until(
                        lambda: self._server_actions_visible(identifier),
                        timeout=4,
                        poll_frequency=0.2,
                    )
                )
            except StaleElementReferenceException:
                continue
        return False

    def _server_actions_visible(self, identifier):
        container = self._server_container(identifier)
        if container is None:
            return False
        try:
            return any(element.is_displayed() and element.is_enabled() for element in
                container.find_elements(
                    By.CSS_SELECTOR, ".icon-edit, .icon-delete, button, [role=button]"
                )
            )
        except StaleElementReferenceException:
            return False

    def _identifier_is_visible(self, identifier):
        container = self._server_container(identifier)
        if container is None:
            return False
        try:
            return identifier in (container.text or "")
        except StaleElementReferenceException:
            return False

    def _click_in_container(self, container, labels):
        action_selector = None
        if labels == self.update_labels:
            action_selector = ".icon-edit"
        elif labels == self.delete_labels:
            action_selector = ".icon-delete"
        if action_selector:
            button = self.driver.execute_script(
                """
                const icon = arguments[0].querySelector(arguments[1]);
                return icon ? icon.closest('button, a, [role=button]') : null;
                """,
                container,
                action_selector,
            )
            if button is not None and button.is_displayed() and button.is_enabled():
                self._safe_click(button)
                return True
        for button in container.find_elements(By.CSS_SELECTOR, "button"):
            try:
                if button.is_displayed() and button.is_enabled() and button.text.strip() in labels:
                    self._safe_click(button)
                    return True
            except Exception:
                continue
        return False

    def _confirm_delete(self):
        end = time.time() + 5
        while time.time() < end:
            for modal in self.driver.find_elements(
                By.CSS_SELECTOR, ".ant-modal-confirm, .ant-modal-content"
            ):
                try:
                    if not modal.is_displayed():
                        continue
                    if self._click_modal_button(modal, ("确定", "删 除", "删除"), primary=True):
                        return True
                except Exception:
                    continue
            time.sleep(0.2)
        return False

    def _replace_text(self, element, value):
        self._safe_click(element)
        element.send_keys(Keys.CONTROL, "a")
        element.send_keys(Keys.DELETE)
        if value:
            element.send_keys(str(value))
        self.driver.execute_script(
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));"
            "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
            element,
        )

    def _safe_click(self, element):
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        try:
            element.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", element)
