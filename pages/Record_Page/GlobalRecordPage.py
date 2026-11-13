# -*- coding:utf-8 -*-
import time
import json
import allure

from selenium.webdriver.common.by import By as by
from selenium.webdriver.common.keys import Keys

from pages.Index_Page.index import LoginPage
from common.ui_state import wait_stable_state


class GlobalRecordPage(LoginPage):
    global_record_route = "#/ui/recording/whole-situation-recording-setting"

    sidebar_menu_root = (by.CSS_SELECTOR, "aside ul.ant-menu")
    sidebar_expand_button = (by.CSS_SELECTOR, "aside .trigger.anticon-menu-unfold")

    page_root = (by.CSS_SELECTOR, "main .layout-content__main")
    page_title = (
        by.XPATH,
        "//main//*[normalize-space()='全局录制设置' or normalize-space()='录制服务设置']",
    )
    number_inputs = (by.CSS_SELECTOR, "main input.ant-input-number-input")
    radio_wrappers = (by.CSS_SELECTOR, "main .ant-radio-wrapper")
    checked_radio_wrappers = (by.CSS_SELECTOR, "main .ant-radio-wrapper-checked")
    save_button = (by.CSS_SELECTOR, "main button.submit-btn.ant-btn-primary")
    save_result = (
        by.XPATH,
        "//div[contains(@class,'ant-message-notice')]//*[normalize-space()='设置成功']",
    )

    RESOLUTION_OPTIONS = {"720*576", "1280*720", "1920*1080"}
    DISPLAY_MODE_OPTIONS = {"等比完整显示", "等比裁剪显示", "平铺显示"}
    RECORD_MODE_OPTIONS = {
        "完整录制", "仅录共享者", "仅录主持人", "仅录音频",
        "指定用户合流录制", "指定用户分流录制",
    }
    LAYOUT_MODE_OPTIONS = {"默认布局", "跟随会议"}

    def _dismiss_blocking_layers(self):
        close_locators = [
            (by.CLASS_NAME, "introjs-skipbutton"),
            (by.CSS_SELECTOR, ".ant-modal-close"),
            (by.CSS_SELECTOR, ".ant-drawer-close"),
        ]
        for locator in close_locators:
            for element in self.driver.find_elements(*locator):
                try:
                    if not element.is_displayed():
                        continue
                    try:
                        element.click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", element)
                except Exception:
                    continue

    def _is_sidebar_collapsed(self):
        for menu in self.driver.find_elements(*self.sidebar_menu_root):
            class_name = menu.get_attribute("class") or ""
            if "ant-menu-inline-collapsed" in class_name:
                return True
        return False

    def _ensure_sidebar_expanded(self, timeout=8):
        end = time.time() + timeout
        while time.time() < end:
            if not self._is_sidebar_collapsed():
                return True
            self._click_first_available_safe([self.sidebar_expand_button], timeout=1.5)
            time.sleep(0.3)
        return not self._is_sidebar_collapsed()

    def _visible_in_any(self, locators, timeout=4):
        end = time.time() + timeout
        while time.time() < end:
            for locator in locators:
                for element in self.driver.find_elements(*locator):
                    try:
                        if element.is_displayed():
                            return True
                    except Exception:
                        continue
            time.sleep(0.2)
        return False

    def _click_first_available_safe(self, locators, timeout=4):
        end = time.time() + timeout
        while time.time() < end:
            for locator in locators:
                for element in self.driver.find_elements(*locator):
                    try:
                        if not element.is_displayed():
                            continue
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block:'center'});", element
                        )
                        try:
                            element.click()
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", element)
                        return True
                    except Exception:
                        continue
            time.sleep(0.2)
        return False

    def _replace_element_value(self, element, value):
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", element
            )
            try:
                element.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", element)
            element.send_keys(Keys.CONTROL, "a")
            element.send_keys(Keys.DELETE)
            time.sleep(0.2)
            element.send_keys(str(value))
            time.sleep(0.2)
            return (element.get_attribute("value") or "") == str(value)
        except Exception:
            return False

    def _enter_global_record_via_route(self):
        current_url = self.driver.current_url or ""
        if "#" in current_url:
            base_url = current_url.split("#", 1)[0]
        else:
            base_url = current_url.rstrip("/") + "/"
        if not base_url:
            base_url = self.url
        self.open_spa_route(self.global_record_route, timeout=5)

    def _hard_reload_global_record_page(self):
        self._enter_global_record_via_route()
        self.driver.refresh()
        self.wait_for_document_ready(timeout=5)
        return True

    def _ensure_page_ready(self):
        ready_locators = [self.page_root, self.page_title, self.save_button]
        if self.global_record_route in (self.driver.current_url or "") and self._visible_in_any(ready_locators, timeout=2):
            return True
        self._hard_reload_global_record_page()
        if self._visible_in_any(ready_locators, timeout=5):
            return True
        return self.common_enter_global_record()

    def common_enter_global_record(self):
        self.common_login()
        self.dismiss_intro_if_present()
        self._dismiss_blocking_layers()
        self._enter_global_record_via_route()
        ready_locators = [self.page_root, self.page_title, self.save_button]
        if not self._visible_in_any(ready_locators, timeout=10):
            raise AssertionError("Failed to enter global record page")
        return True

    def _visible_number_inputs(self):
        inputs = []
        for element in self.driver.find_elements(*self.number_inputs):
            try:
                if element.is_displayed():
                    inputs.append(element)
            except Exception:
                continue
        return inputs

    def _visible_radio_wrappers(self):
        wrappers = []
        for element in self.driver.find_elements(*self.radio_wrappers):
            try:
                if element.is_displayed():
                    wrappers.append(element)
            except Exception:
                    continue
        return wrappers

    def _checked_radio_texts(self, minimum_count=3, timeout=5):
        end = time.time() + timeout
        best = []
        while time.time() < end:
            checked = []
            for element in self.driver.find_elements(*self.checked_radio_wrappers):
                try:
                    text = (element.text or "").strip()
                    if text:
                        checked.append(text)
                except Exception:
                    continue
            if len(checked) >= minimum_count:
                return checked
            if len(checked) > len(best):
                best = checked
            time.sleep(0.2)
        return best

    def _visible_number_values(self, minimum_count=2, timeout=5):
        end = time.time() + timeout
        best = []
        while time.time() < end:
            values = []
            for element in self._visible_number_inputs():
                try:
                    values.append(element.get_attribute("value") or "")
                except Exception:
                    continue
            if len(values) >= minimum_count and all(
                str(value).strip() != "" for value in values[:minimum_count]
            ):
                return values
            if len(values) > len(best):
                best = values
            time.sleep(0.2)
        return best

    def get_current_settings(self):
        self._ensure_page_ready()
        settings = self._wait_configuration_loaded()
        if settings is False:
            raise AssertionError("录制配置未完整加载，禁止用空值或初始值进行修改/恢复")
        return settings

    def _wait_configuration_loaded(self, timeout=12):
        def snapshot():
            data = self.driver.execute_script(
                r"""
                const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
                const main = document.querySelector('main');
                if (!main) return null;
                const inputs = [...main.querySelectorAll('input.ant-input-number-input')].filter(visible);
                const checked = [...main.querySelectorAll('.ant-radio-wrapper')].filter(visible)
                  .filter(e => e.querySelector('input')?.checked || e.classList.contains('ant-radio-wrapper-checked'))
                  .map(e => (e.innerText || '').trim());
                const model = main.querySelector('.global-record-setting-form')?.__vue__?.$props?.model;
                const selectedWidth = checked.find(text => /^\d+\*\d+$/.test(text));
                const licensed = !model?.maxVideoWidth || !selectedWidth ||
                  parseInt(selectedWidth, 10) <= Number(model.maxVideoWidth);
                const resources = performance.getEntriesByType('resource');
                const paths = ['/serv/v1/recording/universal', '/serv/v1/recording/layout',
                  '/meeting/v1/roominfo/license'];
                return {numbers: inputs.map(e => e.value), checked,
                  readCompleted: licensed && paths.every(path => resources.some(item =>
                    item.name.includes(path) && item.responseEnd > 0))};
                """
            )
            if not data or not data['readCompleted'] or len(data['numbers']) < 2:
                return False
            selected = lambda options: next((text for text in data['checked'] if text in options), '')
            settings = {
                'slice_duration': data['numbers'][0],
                'without_stream_over_record_time': data['numbers'][1],
                'resolution': selected(self.RESOLUTION_OPTIONS),
                'display_mode': selected(self.DISPLAY_MODE_OPTIONS),
                'record_mode': selected(self.RECORD_MODE_OPTIONS),
                'layout_mode': selected(self.LAYOUT_MODE_OPTIONS),
            }
            required = ('slice_duration', 'without_stream_over_record_time',
                        'resolution', 'display_mode', 'record_mode')
            return settings if all(settings[key] for key in required) and self.wait_loading_finished(timeout=0.2) else False

        return wait_stable_state(self, snapshot, timeout=timeout, stable_for=0.4)

    def available_resolution_options(self):
        self.get_current_settings()
        return [
            (wrapper.text or '').strip()
            for wrapper in self._visible_radio_wrappers()
            if (wrapper.text or '').strip() in self.RESOLUTION_OPTIONS
        ]

    def _select_radio(self, option_text, timeout=4):
        if not option_text:
            return False
        end = time.time() + timeout
        while time.time() < end:
            for wrapper in self._visible_radio_wrappers():
                try:
                    if (wrapper.text or "").strip() != option_text:
                        continue
                    if "ant-radio-wrapper-checked" not in (wrapper.get_attribute("class") or ""):
                        self.driver.execute_script("arguments[0].click();", wrapper)
                    return self.wait_until(
                        lambda: "ant-radio-wrapper-checked"
                        in (wrapper.get_attribute("class") or ""),
                        timeout=2,
                        poll_frequency=.1,
                    ) is not False
                except Exception:
                    continue
            time.sleep(.1)
        return False

    def set_basic_settings(
        self,
        slice_duration,
        without_stream_over_record_time,
        resolution,
        display_mode,
        record_mode,
    ):
        self._ensure_page_ready()
        self.get_current_settings()
        expected = {
            'slice_duration': str(slice_duration),
            'without_stream_over_record_time': str(without_stream_over_record_time),
            'resolution': resolution, 'display_mode': display_mode, 'record_mode': record_mode,
        }

        def failed(stage):
            evidence = self.driver.execute_script(
                """
                return {numbers:[...document.querySelectorAll('main input.ant-input-number-input')].map(e=>e.value),
                  radios:[...document.querySelectorAll('main .ant-radio-wrapper')].map(e=>({
                    text:(e.innerText||'').trim(),checked:e.querySelector('input')?.checked,
                    disabled:e.querySelector('input')?.disabled,visible:e.offsetParent!==null}))};
                """
            )
            allure.attach(json.dumps({'stage':stage,'expected':expected,'actual':evidence},ensure_ascii=False),
                          '录制字段设置失败诊断', allure.attachment_type.JSON)
            return False

        inputs = self._visible_number_inputs()
        if len(inputs) < 2:
            return failed('number_inputs_missing')

        if not self._replace_element_value(inputs[0], slice_duration):
            return failed('slice_duration')
        inputs = self._visible_number_inputs()
        if len(inputs) < 2 or not self._replace_element_value(inputs[1], without_stream_over_record_time):
            return failed('no_stream_timeout')

        current_mode = self.get_current_settings()["record_mode"]
        # Audio-only mode can disable the video fields. Leave it first when
        # restoring a video mode; enter it last because it may normalize them.
        if current_mode == "仅录音频" and record_mode != "仅录音频":
            if not self._select_radio(record_mode):
                return failed('leave_audio_mode')
        if not self._select_radio(resolution):
            return failed('resolution')
        if not self._select_radio(display_mode):
            return failed('display_mode')
        if not self._select_radio(record_mode):
            return failed('record_mode')

        current = self.get_current_settings()
        matched = (
            current["slice_duration"] == str(slice_duration)
            and current["without_stream_over_record_time"]
            == str(without_stream_over_record_time)
            and current["resolution"] == resolution
            and current["display_mode"] == display_mode
            and current["record_mode"] == record_mode
        )
        return matched or failed('values_not_matched')

    def save_changes(self, expected_text="设置成功", timeout=8):
        self._ensure_page_ready()
        request_mark = self.driver.execute_script("return performance.now()")
        previous = {
            element.id
            for element in self.driver.find_elements(*self.save_result)
            if element.is_displayed()
        }
        if not self._click_first_available_safe([self.save_button], timeout=5):
            return False
        end = time.time() + timeout
        while time.time() < end:
            for element in self.driver.find_elements(*self.save_result):
                try:
                    if (
                        element.is_displayed()
                        and element.id not in previous
                        and expected_text in (element.text or "")
                    ):
                        request_finished = self.wait_until(
                            lambda: self.driver.execute_script(
                                """
                                const mark=arguments[0];
                                return performance.getEntriesByType('resource').some(item =>
                                  item.startTime >= mark
                                  && ['fetch', 'xmlhttprequest'].includes(item.initiatorType));
                                """,
                                request_mark,
                            ),
                            timeout=timeout,
                            poll_frequency=.1,
                        )
                        return bool(
                            request_finished and self.wait_loading_finished(timeout=3)
                        )
                except Exception:
                    continue
            time.sleep(0.2)
        return False

    def restore_basic_settings(self, original):
        """Leave audio-only mode before restoring its disabled video fields."""
        self._ensure_page_ready()
        if not self._select_radio(original['record_mode']):
            return False
        if not self._select_radio(original['resolution']):
            return False
        fields = ('slice_duration', 'without_stream_over_record_time',
                  'resolution', 'display_mode', 'record_mode')
        if not self.set_basic_settings(**{key: original[key] for key in fields}):
            return False
        return (
            self.save_changes('设置成功') and self.refresh_and_wait()
            and self.settings_match({key: original[key] for key in fields})
        )

    def refresh_and_wait(self):
        self.driver.refresh()
        self.wait_for_document_ready(timeout=5)
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
        self.wait_loading_finished(timeout=5)
        if not self._ensure_page_ready():
            return False
        return self._wait_configuration_loaded() is not False

    def settings_match(self, expected):
        current = self.get_current_settings()
        return all(str(current.get(key, "")) == str(value) for key, value in expected.items())

    def modern_settings_snapshot(self):
        self._ensure_page_ready()
        return self.driver.execute_script(
            """
            const clean=v=>(v||'').replace(/\s+/g,'').replace(/[：:]/g,'');
            const rows=[...document.querySelectorAll('main .ant-row')];
            const switches=rows.map(row=>({
              label:clean(row.querySelector('.ant-col-4,.col')?.innerText),
              checked:row.querySelector('[role=switch]')?.getAttribute('aria-checked') === 'true'
            })).filter(item=>item.label && rows.some(row=>clean(row.querySelector('.ant-col-4,.col')?.innerText)===item.label && row.querySelector('[role=switch]')));
            const numbers=[...document.querySelectorAll('main input.ant-input-number-input')].map(e=>({
              value:e.value, min:e.getAttribute('aria-valuemin'), max:e.getAttribute('aria-valuemax')
            }));
            return {text:(document.querySelector('main')?.innerText||'').replace(/\s+/g,' ').trim(), switches, numbers};
            """
        )

    def get_switch_state(self, label):
        snapshot = self.modern_settings_snapshot()
        clean = label.replace("：", "").replace(":", "").replace(" ", "")
        item = next((item for item in snapshot["switches"] if item["label"] == clean), None)
        return None if item is None else bool(item["checked"])

    def set_switch_state(self, label, enabled):
        self._ensure_page_ready()
        changed = self.driver.execute_script(
            """
            const expected=arguments[0].replace(/\s+/g,'').replace(/[：:]/g,'');
            const enabled=arguments[1]; const clean=v=>(v||'').replace(/\s+/g,'').replace(/[：:]/g,'');
            const row=[...document.querySelectorAll('main .ant-row')]
              .find(e=>clean(e.querySelector('.ant-col-4,.col')?.innerText)===expected && e.querySelector('[role=switch]'));
            const button=row?.querySelector('[role=switch]'); if(!button) return false;
            if ((button.getAttribute('aria-checked')==='true') !== enabled) button.click();
            return true;
            """,
            label,
            bool(enabled),
        )
        if not changed:
            return False
        return self.wait_until(
            lambda: self.get_switch_state(label) == bool(enabled), timeout=5, poll_frequency=.2
        ) is not False

    def set_number_value(self, index, value):
        inputs = self._visible_number_inputs()
        if index >= len(inputs):
            return False
        return self._replace_element_value(inputs[index], value)

    def visible_validation_messages(self):
        return self.driver.execute_script(
            """
            const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
            return [...document.querySelectorAll('.ant-form-item-explain-error,.ant-message-notice-content')]
              .filter(visible).map(e=>(e.innerText||'').trim()).filter(Boolean);
            """
        )
