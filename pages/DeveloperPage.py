# -*- coding: utf-8 -*-
"""Developer centre page object scoped to the target application row."""
import time
import re
from common.semantic_controls import exact_table_row
from common.ui_state import wait_query_finished
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from pages.FeatureActionsPage import FeatureActionsPage


class DeveloperPage(FeatureActionsPage):
    group_name, item_name = "开发者中心", "开发者"
    feature_id = "developer_sdk"

    def use_channel(self, feature_id):
        from common.product_profile import detect_build_profile, profile_entry
        from conf.conf import ConfigManager

        entry = profile_entry(feature_id, detect_build_profile(ConfigManager.HST_URL))
        if not entry:
            return False
        self.feature_id = feature_id
        self.group_name, self.item_name = entry["group"], entry["item"]
        return True

    def open_developer(self):
        page = self.open_page(self.group_name, self.item_name)
        opened = page or self.open_page(self.group_name, self.item_name)
        if opened:
            self.driver.execute_script(
                "window.scrollTo(0, 0); "
                "document.querySelectorAll('main, .ant-layout-content').forEach(e => e.scrollTop = 0);"
            )
        return opened

    def _row(self, name):
        return exact_table_row(self.driver,'应用名称',name)

    def _modal(self):
        return next((item for item in reversed(self.driver.find_elements(By.CSS_SELECTOR, ".ant-modal-content")) if item.is_displayed()), None)

    def _application_name_input(self,modal):
        fields=[field for field in modal.find_elements(By.CSS_SELECTOR,'input:not([type=hidden])') if field.is_displayed() and field.is_enabled() and not field.get_attribute('readonly')]
        named=[field for field in fields if '应用' in (field.get_attribute('placeholder') or '') or (field.get_attribute('id') or '') in {'form_item_name','form_item_appName'}]
        candidates=named or fields
        if len(candidates)!=1:
            raise AssertionError('应用名称控件未唯一定位')
        return candidates[0]

    def _refresh_persisted(self,name):
        self.driver.refresh();self.wait_for_document_ready(timeout=5)
        if not self.open_developer():return False
        path='/serv/v1/cesApiPower/page' if self.feature_id=='developer_ces' else '/serv/v1/apiPowerInfo/page'
        if not wait_query_finished(self,0,timeout=10,request_path=path):
            raise AssertionError('应用列表刷新请求未完成')
        return self.wait_until(lambda:self._row(name),timeout=6) is not False

    def _modal_primary(self):
        modal = self.wait_until(self._modal, timeout=6)
        if modal is None:
            return False
        # 4.39.7 places the confirmation controls in `.footer` inside the
        # modal body; 4.39.8 uses the standard ant-modal-footer.
        return self._click_first_available_safe([
            (By.CSS_SELECTOR, ".ant-modal-content .ant-modal-footer .ant-btn-primary"),
            (By.CSS_SELECTOR, ".ant-modal-content .footer .ant-btn-primary"),
        ], timeout=4)

    def _row_action(self, name, action):
        row = self._row(name)
        if row is None:
            return False
        expected=''.join(action.split()).casefold()
        control = next((item for item in row.find_elements(By.CSS_SELECTOR,'a,button')
            if item.is_displayed() and item.is_enabled() and ''.join((item.text or '').split()).casefold()==expected),None)
        if control is None:
            return False
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", control)
        try:
            control.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", control)
        return True

    def create_temporary(self, name):
        self.last_action_error = ""
        if not self.open_developer():
            self.last_action_error = "开发者页面未加载完成"
            return False
        add_button = next((item for item in self.driver.find_elements(
            By.CSS_SELECTOR, "main .hst-add-button, main .add-button"
        ) if item.is_displayed() and item.is_enabled()), None)
        if add_button is None:
            self.last_action_error = "未找到新增按钮"
            return False
        # The tab animation leaves the button visible before its Vue click
        # handler is attached on 4.39.7.
        time.sleep(0.5)
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", add_button)
        try:
            add_button.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", add_button)
        modal = self.wait_until(self._modal, timeout=8)
        if not modal:
            self.last_action_error = "点击新增后未出现弹窗"
            return False
        inputs = [item for item in modal.find_elements(By.CSS_SELECTOR, "input:not([type=hidden])") if item.is_displayed() and item.is_enabled()]
        if not inputs:
            self.last_action_error = "新增弹窗没有可编辑的应用名称输入框"
            return False
        # The Vue form only updates its model from real keyboard events.
        field=self._application_name_input(modal)
        field.clear()
        field.send_keys(name)
        if not self._modal_primary():
            self.last_action_error = "新增弹窗没有确认按钮"
            return False
        created = bool(self.wait_until(lambda: self._row(name) is not None, timeout=8))
        if not created:
            notices = [
                (item.text or "").strip()
                for item in self.driver.find_elements(
                    By.CSS_SELECTOR, ".ant-message, .ant-notification, .ant-modal-content"
                ) if item.is_displayed() and (item.text or "").strip()
            ]
            self.last_action_error = f"确认后列表未出现应用 {name!r}；页面提示: {' | '.join(notices)}"
        return created and self.wait_modal_state(False,timeout=4) and self._refresh_persisted(name)

    def query_client_id(self, name):
        self.open_developer()
        self.last_client_id_evidence={'application':name,'stage':'row'}
        row=self._row(name)
        if row is None:
            return None
        identity=self.driver.execute_script(
            """
            const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
            const headers=[...document.querySelectorAll('main thead tr')].find(e=>visible(e)&&e.querySelectorAll('th').length>1);
            const labels=[...(headers?.querySelectorAll('th')||[])].map(e=>(e.innerText||'').replace(/\s/g,''));
            const kind=labels.includes('Key')?'Key':'ClientID';
            const index=labels.findIndex(e=>e.toLowerCase()===kind.toLowerCase());
            return {kind,value:arguments[0].querySelectorAll('td')[index]?.textContent?.trim()||''};
            """,row,
        )
        kind,expected=identity['kind'],identity['value']
        if not self._row_action(name, "查询"+kind):
            self.last_client_id_evidence['stage']='query-control'
            return None
        modal = self.wait_until(self._modal, timeout=6)
        if not modal:
            return None
        text = modal.text or ""
        values=self.driver.execute_script("return [...arguments[0].querySelectorAll('input')].map(e=>e.value)",modal)
        valid=bool(re.fullmatch(r'[0-9a-fA-F-]{32,36}' if kind=='ClientID' else r'[A-Za-z0-9_-]{16,128}',expected))
        matched=valid and (expected in text or expected in values) and name in text
        lines=[line.strip() for line in text.splitlines() if line.strip()]
        secret_present=kind!='Key' or ('Secret' in lines and lines.index('Secret')+1<len(lines) and lines[lines.index('Secret')+1] not in {'关闭','关 闭'})
        self.last_client_id_evidence.update(stage='popup',kind=kind,identifier_length=len(expected),matches_list=matched,secret_present=secret_present)
        close_button = next((item for item in modal.find_elements(
            By.CSS_SELECTOR, ".ant-modal-close, [aria-label='Close']"
        ) if item.is_displayed()), None)
        if close_button is not None:
            close_button.click()
            self.wait_until(lambda: self._modal() is None, timeout=2)
        return {'kind':kind,'matches_list':True,'identifier_length':len(expected),'secret_present':secret_present} if matched and secret_present else None

    def modify(self, old_name, new_name):
        self.last_action_error = ""
        self.open_developer()
        if not self._row_action(old_name, "修改"):
            self.last_action_error = "未点击到目标应用的修改链接"
            return False
        modal = self.wait_until(self._modal, timeout=6)
        if not modal:
            self.last_action_error = "点击修改后未出现应用名称弹窗"
            return False
        inputs = [item for item in modal.find_elements(By.CSS_SELECTOR, "input:not([type=hidden])") if item.is_displayed() and item.is_enabled()]
        if not inputs:
            self.last_action_error = "修改弹窗没有应用名称输入框"
            return False
        field=self._application_name_input(modal)
        field.click()
        field.send_keys(Keys.CONTROL, "a")
        field.send_keys(Keys.DELETE)
        field.send_keys(new_name)
        self.driver.execute_script("arguments[0].blur()", field)
        if not self._modal_primary():
            self.last_action_error = "修改弹窗没有保存按钮"
            return False
        updated = bool(self.wait_until(lambda: self._row(new_name) is not None, timeout=8))
        if not updated:
            self.last_action_error = f"保存后列表未出现新应用名称 {new_name!r}"
        return updated and self.wait_modal_state(False,timeout=4) and self._refresh_persisted(new_name) and self._row(old_name) is None

    def disable_and_delete(self, name):
        self.open_developer()
        if self._row(name) is None:
            return True
        if self._row_action(name, "停用"):
            self._modal_primary()
        if not self._row_action(name, "删除"):
            return False
        if not self._modal_primary():
            return False
        return bool(self.wait_until(lambda: self._row(name) is None, timeout=8))

    def change_status(self, name, action):
        self.open_developer()
        if not self._row_action(name, action):
            return False
        self._modal_primary()
        opposite = "启用" if action == "停用" else "停用"
        return bool(
            self.wait_until(
                lambda: self._row(name) is not None
                and opposite in (self._row(name).text or ""),
                timeout=8,
            )
        )

    def delete(self, name):
        self.open_developer()
        if self._row(name) is None:
            return True
        if not self._row_action(name, "删除"):
            return False
        if not self._modal_primary():
            return False
        return bool(self.wait_until(lambda: self._row(name) is None, timeout=8))
