# -*- coding:utf-8 -*-
import os
import re
import time
import json
from datetime import datetime

import allure
from selenium.webdriver.common.by import By as by
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import StaleElementReferenceException, ElementNotInteractableException, ElementClickInterceptedException

from pages.Index_Page.index import LoginPage
from common.semantic_controls import action_locator
from common.ui_state import click_toolbar_search, wait_query_finished,wait_page_layout,wait_control_unobscured,wait_stable_state
from common.privacy import masked_screenshot


class MeetingInfoPage(LoginPage):
    meeting_info_route = "#/ui/conference-management/conference-room-info"
    """会议室信息页面对象。"""

    # 侧边栏
    meeting_manager_button = (by.XPATH, "/html/body/div[1]/section/div/aside/div/ul/li[3]/div")
    meeting_manager_button_text = (
        by.XPATH,
        "//aside//li[contains(@class,'ant-menu-submenu')]"
        "//div[contains(@class,'ant-menu-submenu-title')]"
        "[.//span[normalize-space()='会议管理']]",
    )
    meeting_info_button = (
        by.XPATH,
        "/html/body/div[1]/section/div/aside/div/ul/li[3]/ul/li[1]",
    )
    meeting_info_button_text = (
        by.XPATH,
        "//aside//li[contains(@class,'ant-menu-item')]"
        "[.//span[normalize-space()='会议室信息']]",
    )
    sidebar_menu_root = (
        by.CSS_SELECTOR,
        "aside ul.ant-menu, .ant-layout-sider ul.ant-menu",
    )
    sidebar_expand_button = (
        by.CSS_SELECTOR,
        "aside .trigger.anticon-menu-unfold, "
        ".ant-layout-sider .trigger.anticon-menu-unfold, "
        ".ant-layout-sider [aria-label='menu-unfold']",
    )

    # 列表页
    new_add_text = (
        by.XPATH,
        "//button[contains(concat(' ',normalize-space(@class),' '),' hst-add-button ') "
        "or normalize-space()='新增' or normalize-space()='新 增']",
    )
    new_add = (
        by.XPATH,
        "/html/body/div[1]/section/section/main/div/div[2]/div/div[2]/div[2]/div[1]/div[1]/button[1]",
    )
    locate_search = (by.XPATH, "//input[@placeholder='请输入搜索内容']")
    search_button = (
        by.XPATH,
        "//main//input[@placeholder='请输入搜索内容']/following-sibling::button[1]",
    )
    clear_button_text = (by.XPATH, "//main//button[normalize-space()='清 空']")

    save_result = (
        by.XPATH,
        "//div[contains(@class,'ant-message-notice-content')]"
        "//div[contains(@class,'ant-message-custom-content')]//*[normalize-space()]",
    )
    delete_sure_button_text = (
        by.CSS_SELECTOR,
        ".ant-modal-confirm .ant-modal-confirm-btns .ant-btn-primary,"
        ".ant-confirm .ant-modal-confirm-btns .ant-btn-primary",
    )

    data_num = (
        by.CSS_SELECTOR,
        ".pagination-box>div:nth-child(2)>span, main .pagination-desc, "
        "main [class*='pagination'] > p",
    )
    page_size_changer = (by.CSS_SELECTOR, ".ant-pagination-options-size-changer")
    page_size_value = (
        by.CSS_SELECTOR,
        ".ant-pagination-options-size-changer .ant-select-selection-selected-value, "
        ".ant-pagination-options-size-changer .ant-select-selection-item",
    )
    quick_jump_input = (by.CSS_SELECTOR, ".ant-pagination-options-quick-jumper input")
    active_page_num = (by.CSS_SELECTOR, ".ant-pagination-item-active")
    first_result_page_button = (by.CSS_SELECTOR, ".ant-pagination-item-1")
    next_page_button = (by.CSS_SELECTOR, ".ant-pagination-next")

    # 弹窗
    add_modal_title = "添加会议室"
    modify_modal_title = "修改会议室"
    authorize_modal_title = "会议室授权用户"
    sort_modal_title = "用户排序"
    meeting_setting_section_title = "会议室设置"
    login_type_label = "登录类型"
    login_type_label_aliases = ("登录类型", "登录校验类型", "登录验证类型")
    admin_password_label = "管理员密码"
    meeting_password_label = "会议登录密码"
    meeting_password_verify_option = "会议室密码验证"
    meeting_name_label = "会议室名称"
    save_button_text = "保 存"
    close_button_text = "关 闭"
    advanced_section_titles = (
        "会议室设置", "默认视频参数", "H.323会议参数", "会议室参数",
        "录制设置", "指定主服务器",
    )
    version_specific_section_titles = ("会议纪要", "文字转写", "人脸签到")
    create_basic_recording_modes = ("完整录制", "仅录音频")
    create_auto_recording_modes = ("完整录制", "仅录共享者", "仅录主持人", "仅录音频")
    modify_auto_recording_modes = create_auto_recording_modes + (
        "指定用户合流录制", "指定用户分流录制",
    )

    def common_enter_meeting_info(self):
        """稳定进入会议室信息页面。"""
        self.common_login()
        self.dismiss_intro_if_present()
        self._dismiss_blocking_layers()
        if not self._ensure_sidebar_expanded(timeout=8):
            raise AssertionError("Sidebar is still collapsed after expand attempt")

        meeting_menu_locators = [
            self.meeting_manager_button_text,
            self.meeting_manager_button,
        ]
        meeting_info_locators = [
            self.meeting_info_button_text,
            self.meeting_info_button,
        ]
        ready_locators = [self.new_add_text, self.new_add]

        if not self._visible_in_any(meeting_info_locators, timeout=2):
            opened = False
            for _ in range(4):
                if self._click_first_available_safe(meeting_menu_locators, timeout=5):
                    if self._visible_in_any(meeting_info_locators, timeout=4):
                        opened = True
                        break
            if not opened:
                self._enter_meeting_info_via_route()
                if not self._visible_in_any(ready_locators, timeout=10):
                    raise AssertionError("Failed to open meeting management menu")
                return True

        if not self._click_first_available_safe(meeting_info_locators, timeout=5):
            self._enter_meeting_info_via_route()
            if not self._visible_in_any(ready_locators, timeout=10):
                raise AssertionError("Failed to click meeting info menu")
            return True

        if not self._visible_in_any(ready_locators, timeout=10):
            self._enter_meeting_info_via_route()
            if not self._visible_in_any(ready_locators, timeout=10):
                raise AssertionError("Failed to enter meeting info page")
        return True

    def _enter_meeting_info_via_route(self):
        current_url = self.driver.current_url or ""
        if "#" in current_url:
            base_url = current_url.split("#", 1)[0]
        else:
            base_url = current_url.rstrip("/") + "/"
        if not base_url:
            base_url = self.url
        self.open_spa_route(self.meeting_info_route, timeout=5)

    def wait_for_operation_result(self, expected_text=None, timeout=20):
        if expected_text:
            return self.wait_text_contains(self.save_result, expected_text, timeout=timeout)
        return self.wait_visible(self.save_result, timeout=timeout) is not False

    def click_new_add(self):
        self._expected_add_meeting_name = None
        self._ensure_meeting_page_ready()
        self._dismiss_blocking_layers()
        if not self._wait_meeting_list_loaded():
            raise AssertionError("会议室列表和组织数据尚未加载完成")
        dialog_locator = self._meeting_name_input_locator(self.add_modal_title)
        for _ in range(2):
            if not self._click_first_available_safe([self.new_add_text, self.new_add], timeout=5):
                continue
            if self.wait_visible(dialog_locator, timeout=8) is not False:
                return True
            self._enter_meeting_info_via_route()
            self.driver.refresh()
            self.wait_for_document_ready(timeout=5)
            time.sleep(0.5)
            self._dismiss_blocking_layers()
            self._ensure_meeting_page_ready()
        raise AssertionError("Add meeting dialog did not appear")
        return True

    def send_meeting_name(self, meeting_name):
        value = str(meeting_name)
        locator = self._meeting_name_input_locator(self.add_modal_title)
        deadline = time.monotonic() + 8
        attempts = 0
        def committed():
            field = self.find_visible_now(locator)
            return {"name": value} if field is not False and (field.get_attribute('value') or '') == value else False
        while time.monotonic() < deadline:
            attempts += 1
            self.last_meeting_name_input = {"expected": value, "attempts": attempts}
            try:
                field = wait_control_unobscured(self, locator, timeout=min(1, max(0, deadline-time.monotonic())))
                if field is False:
                    continue
                field.click()
                field.send_keys(Keys.CONTROL, 'a')
                field.send_keys(Keys.DELETE)
                field.send_keys(value)
                field.send_keys(Keys.TAB)
                if wait_stable_state(self, committed, timeout=min(1, max(0, deadline-time.monotonic())), stable_for=0.3) is not False:
                    self._expected_add_meeting_name = value
                    return True
            except (StaleElementReferenceException, ElementNotInteractableException, ElementClickInterceptedException):
                continue
        self._capture_add_meeting_failure_state(value)
        raise AssertionError('会议室名称未稳定写入，未提交保存')

    def click_save_button(self):
        expected = getattr(self, '_expected_add_meeting_name', None)
        if self._top_visible_modal_title() == self.add_modal_title and expected is not None:
            if self._meeting_modal_name_value() != expected:
                self._capture_add_meeting_failure_state(expected)
                raise AssertionError('保存前会议室名称已变化，未提交保存')
        self._meeting_save_started = self.driver.execute_script('return performance.now()')
        if not self._click_visible_modal_button(primary=True, timeout=3):
            raise AssertionError("Failed to click add meeting save button")
        return True

    def click_cancel_button(self):
        clicked = self._click_visible_modal_button(primary=False, timeout=3)
        if clicked:
            self.wait_loading_finished(timeout=3)
        return clicked

    def wait_meeting_saved(self, timeout=30):
        started = getattr(self, '_meeting_save_started', None)
        if started is None:
            return False
        completed = self.wait_until(
            lambda: self.driver.execute_script(
                r"""
                const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
                const requestDone = performance.getEntriesByType('resource').some(item =>
                  item.startTime >= arguments[0] && item.responseEnd > 0 &&
                  item.name.includes('/meeting/v1/roominfo') &&
                  ['fetch','xmlhttprequest'].includes(item.initiatorType));
                return requestDone && ![...document.querySelectorAll('.ant-modal-content')].some(visible);
                """,
                started,
            ),
            timeout=timeout,
            poll_frequency=0.2,
        ) is not False
        if not completed:
            allure.attach(self._visible_modal_text(), '会议室保存未完成时的表单', allure.attachment_type.TEXT)
            allure.attach(self.driver.get_screenshot_as_png(), '会议室保存未完成截图', allure.attachment_type.PNG)
        return completed

    def advanced_meeting_settings_snapshot(self):
        """Read all advanced sections from the active add/edit modal."""
        return self.driver.execute_script("""
          const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
          const modal = [...document.querySelectorAll('.ant-modal-content')].filter(visible).at(-1);
          if (!modal) return null;
          const clean = value => (value || '').replace(/\\s+/g, ' ').trim();
          const headers = [...modal.querySelectorAll('.item-header')];
          return headers.map(header => {
            const form = header.closest('form');
            return {title: clean(header.innerText), controls: form ? form.querySelectorAll('input,button,[role=switch],.ant-select-selection').length : 0};
          });
        """)

    def expand_advanced_meeting_sections(self):
        """Expand every advanced section and return its visible control count."""
        sections = []
        for title in self.advanced_section_names():
            if not self._open_advanced_section(title):
                sections.append({"title": title, "visible_controls": 0})
                continue
            time.sleep(0.15)
            controls = self.driver.execute_script("""
              const title = arguments[0];
              const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
              const modal = [...document.querySelectorAll('.ant-modal-content')].filter(visible).at(-1);
              const header = modal && [...modal.querySelectorAll('.item-header')].find(e => (e.innerText || '').includes(title));
              const form = header && header.closest('form');
              return form ? [...form.querySelectorAll('input, button, [role=switch], .ant-switch, .ant-select-selection')].filter(visible).length : 0;
            """, title)
            sections.append({"title": title, "visible_controls": controls})
        return sections

    def advanced_section_names(self):
        """Return semantic section names shown by the current product version."""
        snapshot = self.advanced_meeting_settings_snapshot() or []
        candidates = self.advanced_section_titles + self.version_specific_section_titles
        names = []
        for item in snapshot:
            displayed = item.get("title", "")
            matched = next((name for name in candidates if displayed.startswith(name)), None)
            if matched and matched not in names:
                names.append(matched)
        return tuple(names)

    def advanced_section_text(self, title):
        """Return the visible business text of one expanded advanced section."""
        if not self._open_advanced_section(title):
            return ""
        time.sleep(0.1)
        return self.driver.execute_script("""
          const title = arguments[0];
          const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
          const modal = [...document.querySelectorAll('.ant-modal-content')].filter(visible).at(-1);
          const header = modal && [...modal.querySelectorAll('.item-header')].find(e => (e.innerText || '').includes(title));
          return header && header.closest('form') ? header.closest('form').innerText.replace(/\s+/g, ' ').trim() : '';
        """, title)

    def recording_modes(self):
        self._open_advanced_section("录制设置")
        return self.driver.execute_script("""
          const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
          const modal = [...document.querySelectorAll('.ant-modal-content')].filter(visible).at(-1);
          if (!modal) return [];
          const header = [...modal.querySelectorAll('.item-header')].find(e => (e.innerText || '').includes('录制设置'));
          const form = header && header.closest('form');
          if (!form) return [];
          return [...form.querySelectorAll('label')].map(e => (e.innerText || '').replace(/\\s+/g, ' ').trim()).filter(Boolean);
        """)

    def recording_option_is_selected(self, text):
        self._open_advanced_section("录制设置")
        return bool(self.driver.execute_script("""
          const text = arguments[0]; const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
          const modal = [...document.querySelectorAll('.ant-modal-content')].filter(visible).at(-1);
          const header = modal && [...modal.querySelectorAll('.item-header')].find(e => (e.innerText || '').includes('录制设置'));
          const form = header && header.closest('form');
          const label = form && [...form.querySelectorAll('label')].find(e => visible(e) && (e.innerText || '').trim() === text);
          if (!label) return false;
          const input = label.querySelector('input[type=radio], input[type=checkbox]');
          return !!(input && input.checked) || !!label.querySelector('.ant-radio-checked, .ant-checkbox-checked');
        """, text))

    def visible_recording_mode_options(self):
        """Return only recording-mode labels, preserving their business display order."""
        available = set(self.recording_modes())
        return tuple(mode for mode in self.modify_auto_recording_modes if mode in available)

    def choose_recording_template(self, template):
        self._open_advanced_section("录制设置")
        return self._click_modal_text(template)

    def choose_recording_mode(self, mode):
        self._open_advanced_section("录制设置")
        return self._click_modal_text(mode)

    def open_designated_recording_user_dialog(self, mode):
        """Expand the blue-arrow panel for a designated-user recording mode."""
        if not self.choose_recording_mode(mode):
            return False
        opened = bool(self.driver.execute_script("""
          const mode = arguments[0]; const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
          const modal = [...document.querySelectorAll('.ant-modal-content')].filter(visible).at(-1);
          const header = modal && [...modal.querySelectorAll('.item-header')].find(e => (e.innerText || '').includes('录制设置'));
          const form = header && header.closest('form');
          const label = (form && [...form.querySelectorAll('label')].find(e => visible(e) && (e.innerText || '').trim() === mode))
            || [...document.querySelectorAll('label')].find(e => visible(e) && (e.innerText || '').trim() === mode);
          if (!label) return false;
          let container = label.parentElement;
          while (container && container !== form) {
            const icon = [...container.querySelectorAll('i, span, svg')].find(e => {
              const classes = String(e.className && e.className.baseVal || e.className || '');
              return visible(e) && /(down|arrow)/i.test(classes) && e !== label;
            });
            if (icon) { icon.click(); return true; }
            container = container.parentElement;
          }
          return false;
        """, mode))
        if not opened:
            allure.attach(
                self._recording_section_html(),
                "指定录制方式图标定位诊断",
                allure.attachment_type.HTML,
            )
            return False
        appeared = self.wait_until(
            lambda: self._visible_overlay_text_contains("授权用户")
            or self._visible_modal_title_contains("指定用户录制"),
            timeout=5,
        ) is not False
        if appeared and not self._ensure_active_meeting_name():
            return False
        if not appeared:
            allure.attach(
                self._recording_section_html(),
                "指定录制方式弹出层诊断",
                allure.attachment_type.HTML,
            )
        return appeared

    def select_designated_recording_user(self, username):
        """Open the selector from the recording panel and assign one authorized user."""
        if not self._visible_modal_title_contains("指定用户录制") and not self._click_visible_overlay_text_button("授权用户"):
            allure.attach(json.dumps(self._visible_overlay_diagnostics(), ensure_ascii=False), "授权用户控件定位诊断", allure.attachment_type.TEXT)
            return self._designated_stage_failed("打开授权用户按钮")
        if self.wait_until(lambda: self._select_designated_user_native(username), timeout=15) is False:
            allure.attach(
                self._visible_modal_text(),
                "指定用户录制列表加载诊断",
                allure.attachment_type.TEXT,
            )
            return self._designated_stage_failed("加载指定用户列表")
        if self.wait_until(lambda: self._designated_user_selected_native(username), timeout=5) is False:
            allure.attach(
                json.dumps(self._designated_dialog_diagnostics(), ensure_ascii=False, indent=2),
                "指定用户复选框状态诊断",
                allure.attachment_type.TEXT,
            )
            return self._designated_stage_failed("选中指定用户")
        if not self._ensure_active_meeting_name():
            return self._designated_stage_failed("校验父表单会议室名称")
        if not self._confirm_designated_user_dialog(username):
            allure.attach(
                json.dumps(self._confirm_button_diagnostics(), ensure_ascii=False, indent=2),
                "指定用户确认按钮诊断",
                allure.attachment_type.TEXT,
            )
            return self._designated_stage_failed("点击二层确认")
        if self.wait_until(lambda: self._top_visible_modal_title() == "授权用户", timeout=20) is False:
            allure.attach(
                json.dumps(self._designated_confirm_result_diagnostics(username), ensure_ascii=False, indent=2),
                "指定用户确认结果诊断",
                allure.attachment_type.TEXT,
            )
            return self._designated_stage_failed("等待二层弹窗关闭")
        if self.wait_until(
            lambda: not self._designated_user_dialog_visible()
            and self._authorized_user_panel_contains(username),
            timeout=8,
            poll_frequency=0.15,
        ) is False:
            allure.attach(
                json.dumps(self._designated_dialog_diagnostics(), ensure_ascii=False),
                "一层已选用户等待失败诊断",
                allure.attachment_type.JSON,
            )
            return self._designated_stage_failed("校验一层已选用户")
        if not self._close_authorized_user_panel():
            return self._designated_stage_failed("关闭一层弹窗")
        closed = self.wait_until(lambda: self._top_visible_modal_title() != "授权用户", timeout=5) is not False
        if not closed:
            return self._designated_stage_failed("等待一层弹窗关闭")
        return True

    @staticmethod
    def _designated_stage_failed(stage):
        allure.attach(stage, "指定用户录制失败阶段", allure.attachment_type.TEXT)
        return False

    def _click_visible_designated_user_row(self, username):
        return bool(self.driver.execute_script("""
          const username = arguments[0];
          const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
          const row = [...document.querySelectorAll('tbody tr')]
            .find(e => visible(e) && (e.innerText || '').includes(username));
          const input = row && row.querySelector('input[type=checkbox]');
          if (!input) return false;
          if (!input.checked) (input.closest('label') || input).click();
          return true;
        """, username))

    def _visible_designated_modal(self):
        modals = self.driver.find_elements(by.CSS_SELECTOR, ".ant-modal-content")
        for modal in reversed(modals):
            try:
                text = modal.text.replace("\n", " ")
                if modal.is_displayed() and "指定用户录制" in text:
                    return modal
            except Exception:
                continue
        return False

    def _select_designated_user_native(self, username):
        modal = self._visible_designated_modal()
        if modal is False:
            return False
        try:
            return bool(self.driver.execute_script("""
              const modal = arguments[0];
              const username = arguments[1];
              const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
              const rows = [...modal.querySelectorAll('tbody tr')].filter(visible);
              const row = rows.find(item => [...item.querySelectorAll('td')]
                .some(cell => (cell.innerText || '').trim() === username));
              if (!row) return false;
              const input = row.querySelector("input[type='checkbox']");
              const checkbox = row.querySelector('.ant-checkbox');
              if (!input && !checkbox) return false;
              if (input?.checked || checkbox?.classList.contains('ant-checkbox-checked')) return true;
              const target = input?.closest('label') || checkbox || input;
              target.click();
              return true;
            """, modal, username))
        except Exception:
            return False

    def _designated_user_selected_native(self, username):
        modal = self._visible_designated_modal()
        if modal is False:
            return False
        try:
            return bool(self.driver.execute_script("""
              const modal = arguments[0];
              const username = arguments[1];
              const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
              const row = [...modal.querySelectorAll('tbody tr')].filter(visible)
                .find(item => [...item.querySelectorAll('td')]
                  .some(cell => (cell.innerText || '').trim() === username));
              if (!row) return false;
              const input = row.querySelector("input[type='checkbox']");
              const checkbox = row.querySelector('.ant-checkbox');
              return !!(input?.checked || checkbox?.classList.contains('ant-checkbox-checked'));
            """, modal, username))
        except Exception:
            return False

    def _visible_designated_user_checked(self, username):
        return bool(self.driver.execute_script("""
          const username = arguments[0];
          const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
          const row = [...document.querySelectorAll('tbody tr')]
            .find(e => visible(e) && (e.innerText || '').includes(username));
          const input = row && row.querySelector('input[type=checkbox]');
          return !!input && (input.checked || !!input.closest('label')?.querySelector('.ant-checkbox-checked'));
        """, username))

    def _confirm_designated_user_dialog(self, username):
        modals = self.driver.find_elements(
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            "[.//div[contains(@class,'ant-modal-title') and normalize-space()='指定用户录制']]",
        )
        for modal in reversed(modals):
            try:
                if not modal.is_displayed():
                    continue
                button = modal.find_element(
                    by.XPATH,
                    ".//button[translate(normalize-space(.), ' ', '')='确认']",
                )
                self.driver.execute_script("""
                  window.__uiautoDesignatedConfirmClicked = false;
                  arguments[0].addEventListener('click', () => {
                    window.__uiautoDesignatedConfirmClicked = true;
                  }, {once: true, capture: true});
                """, button)
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", button)
                ActionChains(self.driver).move_to_element(button).click().perform()
                time.sleep(0.3)
                if modal.is_displayed():
                    self.driver.execute_script("""
                      const button = arguments[0];
                      for (const type of ['mousedown', 'mouseup', 'click']) {
                        button.dispatchEvent(new MouseEvent(type, {bubbles: true, cancelable: true, view: window}));
                      }
                    """, button)
                return True
            except Exception:
                continue
        return False

    def _designated_confirm_result_diagnostics(self, username):
        return self.driver.execute_script("""
          const username = arguments[0];
          const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
          const rows = [...document.querySelectorAll('tbody tr')]
            .filter(e => visible(e) && (e.innerText || '').includes(username));
          const meetingModal = [...document.querySelectorAll('.ant-modal-content')].filter(visible)
            .find(e => (e.querySelector('.ant-modal-title')?.innerText || '').includes('修改会议室'));
          const nameLabel = meetingModal && [...meetingModal.querySelectorAll('label')]
            .find(e => (e.innerText || '').trim() === '会议室名称');
          return {
            clickCaptured: !!window.__uiautoDesignatedConfirmClicked,
            meetingName: nameLabel?.closest('.ant-form-item')?.querySelector('input')?.value || '',
            rows: rows.map(row => ({
              text: (row.innerText || '').trim(),
              checked: row.querySelector('input[type=checkbox]')?.checked ?? null,
              checkboxClass: row.querySelector('.ant-checkbox')?.className || '',
              modalTitle: row.closest('.ant-modal-content')?.querySelector('.ant-modal-title')?.innerText || '',
            })),
            messages: [...document.querySelectorAll('.ant-message-notice-content, .ant-form-explain')]
              .filter(visible).map(e => (e.innerText || '').trim()),
          };
        """, username)

    def _visible_designated_user_row(self, username):
        return bool(self.driver.execute_script("""
          const username = arguments[0];
          const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
          return [...document.querySelectorAll('tbody tr')]
            .some(e => visible(e) && (e.innerText || '').includes(username));
        """, username))

    def _designated_dialog_diagnostics(self):
        return self.driver.execute_script("""
          const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
          return [...document.querySelectorAll('.ant-modal-content')].map((modal, index) => ({
            index,
            visible: visible(modal),
            title: modal.querySelector('.ant-modal-title')?.innerText || '',
            text: (modal.innerText || '').slice(0, 1500),
            rows: [...modal.querySelectorAll('tbody tr')].map(row => ({
              visible: visible(row),
              text: (row.innerText || '').trim(),
              checked: row.querySelector('input[type=checkbox]')?.checked ?? null,
              checkboxClass: row.querySelector('.ant-checkbox')?.className || '',
            })),
          }));
        """)

    def _confirm_button_diagnostics(self):
        return self.driver.execute_script("""
          const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
          return [...document.querySelectorAll('button, a, [role=button]')]
            .filter(e => (e.innerText || '').replace(/\s+/g, '').includes('确认'))
            .map(e => ({
              tag: e.tagName,
              text: e.innerText || '',
              className: String(e.className || ''),
              visible: visible(e),
              disabled: !!e.disabled,
              html: e.outerHTML.slice(0, 2500),
              modalTitle: e.closest('.ant-modal-content')?.querySelector('.ant-modal-title')?.innerText || '',
            }));
        """)

    def _designated_user_dialog_visible(self):
        return bool(self.driver.execute_script("""
          const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
          return [...document.querySelectorAll('.ant-modal-content')].filter(visible)
            .some(e => (e.innerText || '').includes('最大支持5个用户单独录制'));
        """))

    def _confirm_authorized_user_panel(self):
        return bool(self.driver.execute_script("""
          const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
          const modal = [...document.querySelectorAll('.ant-modal-content')].filter(visible).at(-1);
          if (!modal || (modal.querySelector('.ant-modal-title')?.innerText || '').trim() !== '授权用户') return false;
          const button = [...modal.querySelectorAll('button')]
            .find(e => !e.disabled && (e.innerText || '').replace(/\s+/g, '') === '确认');
          if (!button) return false;
          button.click();
          return true;
        """))

    def _authorized_user_panel_contains(self, username):
        panel = self._visible_authorized_user_panel()
        if panel is False:
            return False
        try:
            return username in (panel.text or "")
        except Exception:
            return False

    def _close_authorized_user_panel(self):
        panel = self._visible_authorized_user_panel()
        if panel is False:
            return False
        try:
            close_button = panel.find_element(by.CSS_SELECTOR, "button.ant-modal-close")
            close_button.click()
            return True
        except Exception:
            return False

    def _top_visible_modal_title(self):
        return self.driver.execute_script("""
          const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
          const modal = [...document.querySelectorAll('.ant-modal-content')].filter(visible).at(-1);
          return (modal?.querySelector('.ant-modal-title')?.innerText || '').trim();
        """)

    def _visible_authorized_user_panel(self):
        modals = self.driver.find_elements(
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            "[.//div[contains(@class,'ant-modal-title') and normalize-space()='授权用户']]",
        )
        for modal in reversed(modals):
            try:
                if modal.is_displayed():
                    return modal
            except Exception:
                continue
        return False

    def _visible_element(self, locator):
        for element in self.driver.find_elements(*locator):
            try:
                if element.is_displayed():
                    return element
            except Exception:
                continue
        return False

    @staticmethod
    def _visible_descendant(parent, strategy, selector):
        try:
            for element in parent.find_elements(strategy, selector):
                if element.is_displayed():
                    return element
        except Exception:
            return False
        return False

    def _designated_user_checked(self, username):
        rows = self.driver.find_elements(
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            "[.//div[contains(@class,'ant-modal-title') and contains(normalize-space(),'指定用户录制')]]"
            f"//tbody//tr[contains(normalize-space(),'{username}')]",
        )
        for row in rows:
            try:
                checkbox = row.find_element(by.CSS_SELECTOR, "input[type='checkbox']")
                if checkbox.is_selected():
                    return True
                wrapper_class = checkbox.find_element(by.XPATH, "ancestor::label[1]").get_attribute("class") or ""
                if "checked" in wrapper_class:
                    return True
            except Exception:
                continue
        return False

    def designated_recording_user_is_listed(self, username):
        return bool(self.driver.execute_script("""
          const username = arguments[0]; const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
          const modal = [...document.querySelectorAll('.ant-modal-content')].filter(visible).at(-1);
          return !!modal && (modal.innerText || '').includes(username);
        """, username))

    def _recording_section_html(self):
        return self.driver.execute_script("""
          const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
          const modal = [...document.querySelectorAll('.ant-modal-content')].filter(visible).at(-1);
          const header = modal && [...modal.querySelectorAll('.item-header')].find(e => (e.innerText || '').includes('录制设置'));
          return header?.closest('form')?.outerHTML || '';
        """)

    def _open_advanced_section(self, title):
        return bool(self.driver.execute_script("""
          const title = arguments[0]; const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
          const modal = [...document.querySelectorAll('.ant-modal-content')].filter(visible).at(-1);
          const header = [...modal.querySelectorAll('.item-header')].find(e => (e.innerText || '').includes(title));
          if (!header) return false;
          header.scrollIntoView({block:'center'});
          const content = header.nextElementSibling;
          const isOpen = content && [...content.querySelectorAll('input, button, [role=switch], .ant-select-selection')].some(visible);
          if (!isOpen) header.querySelector('p')?.click();
          return true;
        """, title))

    def set_auto_recording(self, enabled=True):
        self._open_advanced_section("录制设置")
        changed = bool(self.driver.execute_script("""
          const enabled = arguments[0];
          const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
          const modal = [...document.querySelectorAll('.ant-modal-content')].filter(visible).at(-1);
          const header = [...modal.querySelectorAll('.item-header')].find(e => (e.innerText || '').includes('录制设置'));
          const form = header && header.closest('form');
          const label = form && [...form.querySelectorAll('*')].find(e =>
            e.children.length === 0 && (e.innerText || '').replace(/\s+/g, '').includes('入会自动录制')
          );
          let row = label;
          let button = null;
          while (row && row !== form && !button) {
            button = row.querySelector('[role=switch], .ant-switch, button[aria-checked], input[type=checkbox]');
            row = row.parentElement;
          }
          if (!button || (button.getAttribute('aria-checked') === 'true') === enabled) return !!button;
          button.click(); return true;
        """, enabled))
        if changed:
            time.sleep(0.25)
        return changed

    def auto_recording_enabled(self):
        self._open_advanced_section("录制设置")
        return bool(self.driver.execute_script("""
          const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
          const modal = [...document.querySelectorAll('.ant-modal-content')].filter(visible).at(-1);
          const header = modal && [...modal.querySelectorAll('.item-header')].find(e => (e.innerText || '').includes('录制设置'));
          const form = header && header.closest('form');
          const label = form && [...form.querySelectorAll('*')].find(e =>
            e.children.length === 0 && (e.innerText || '').replace(/\s+/g, '').includes('入会自动录制')
          );
          let row = label;
          while (row && row !== form) {
            const button = row.querySelector('[role=switch], .ant-switch, button[aria-checked], input[type=checkbox]');
            if (button) return button.getAttribute('aria-checked') === 'true' || button.checked === true;
            row = row.parentElement;
          }
          return false;
        """))

    def _click_modal_text(self, text):
        clicked = bool(self.driver.execute_script("""
          const text = arguments[0]; const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
          const modal = [...document.querySelectorAll('.ant-modal-content')].filter(visible).at(-1);
          const node = [...modal.querySelectorAll('label,span')].find(e => visible(e) && (e.innerText || '').trim() === text);
          if (!node) return false;
          node.scrollIntoView({block: 'center'});
          (node.closest('label') || node).click(); return true;
        """, text))
        if clicked:
            time.sleep(0.25)
        return clicked

    def open_meeting_for_modify(self, meeting_name):
        """Open the exact meeting room's edit modal without changing its data."""
        self._ensure_meeting_page_ready()
        if not self._find_exact_meeting_row_via_search(meeting_name):
            self._restore_list_state()
            return False
        if not self._click_first_available_safe(
            [self._exact_meeting_modify_button_locator(meeting_name)], timeout=10
        ):
            self._restore_list_state()
            return False
        if self.wait_visible(self._meeting_name_input_locator(self.modify_modal_title), timeout=10) is False:
            return False
        opened = self.wait_until(
            lambda: self._meeting_modal_name_value() == meeting_name,
            timeout=5,
        ) is not False
        if opened:
            self._active_meeting_name = meeting_name
        return opened

    def _ensure_active_meeting_name(self):
        meeting_name = getattr(self, "_active_meeting_name", "")
        if not meeting_name:
            return True
        modals = self.driver.find_elements(
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{self.modify_modal_title}']]",
        )
        for modal in reversed(modals):
            try:
                if not modal.is_displayed():
                    continue
                input_element = modal.find_element(
                    by.XPATH,
                    ".//label[normalize-space()='会议室名称']"
                    "/ancestor::div[contains(@class,'ant-form-item')]//input[not(@disabled)]",
                )
                if (input_element.get_attribute("value") or "") == meeting_name:
                    return True
                input_element.click()
                input_element.send_keys(Keys.CONTROL, "a")
                input_element.send_keys(Keys.DELETE)
                input_element.send_keys(meeting_name)
                return (input_element.get_attribute("value") or "") == meeting_name
            except Exception:
                continue
        return False

    def _meeting_modal_name_value(self):
        return self.driver.execute_script("""
          const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
          const modal = [...document.querySelectorAll('.ant-modal-content')].filter(visible).at(-1);
          const label = modal && [...modal.querySelectorAll('label')].find(e => (e.innerText || '').trim() === '会议室名称');
          return label?.closest('.ant-form-item')?.querySelector('input')?.value || '';
        """)

    def get_wrong_meeting_name_msg(self):
        return self.get_element_text(
            self._meeting_name_validation_locator(self.add_modal_title), timeout=10
        )

    def add_meeting(self, meeting_name, result="新增成功"):
        self._ensure_meeting_page_ready()
        self.click_new_add()
        self.send_meeting_name(meeting_name)
        self.click_save_button()
        if not self.wait_meeting_saved(timeout=8):
            self._capture_add_meeting_failure_state(meeting_name)
            return False
        added = self._find_exact_meeting_row_via_search(meeting_name)
        if not added:
            self._capture_add_meeting_failure_state(meeting_name)
        self._restore_list_state()
        return added

    def search_meeting(self, meeting_name):
        self._ensure_meeting_page_ready()
        found = self._find_exact_meeting_row_via_search(meeting_name)
        self._restore_list_state()
        return found

    def cancel_modify_meeting(self, old_name, new_name):
        self._ensure_meeting_page_ready()
        if not self._find_exact_meeting_row_via_search(old_name):
            return False
        if not self._click_first_available_safe(
            [self._exact_meeting_modify_button_locator(old_name)], timeout=10
        ):
            self._restore_list_state()
            return False
        if self.wait_visible(self._meeting_name_input_locator(self.modify_modal_title), timeout=10) is False:
            self._restore_list_state()
            return False
        if not self._replace_input_value(
            self._meeting_name_input_locator(self.modify_modal_title), new_name, timeout=10
        ):
            self._restore_list_state()
            return False
        if not self._click_first_available_safe(
            [self._modal_action_button_locator(self.modify_modal_title, self.close_button_text)],
            timeout=2,
        ):
            if not self._click_visible_modal_button(primary=False, timeout=2):
                self._restore_list_state()
                return False
        result = self.wait_until(
            lambda: self._find_exact_meeting_row_via_search(old_name),
            timeout=3,
        )
        self._restore_list_state()
        return result is not False

    def modify_meeting(self, old_name, new_name, result="修改成功"):
        self._ensure_meeting_page_ready()
        if old_name != new_name and not self.ensure_meeting_absent(new_name):
            return False
        if not self._find_exact_meeting_row_via_search(old_name):
            return False
        if not self._click_first_available_safe(
            [self._exact_meeting_modify_button_locator(old_name)], timeout=10
        ):
            self._restore_list_state()
            return False
        if self.wait_visible(self._meeting_name_input_locator(self.modify_modal_title), timeout=10) is False:
            self._restore_list_state()
            return False
        if not self._replace_input_value(
            self._meeting_name_input_locator(self.modify_modal_title), new_name, timeout=10
        ):
            self._restore_list_state()
            return False
        self.click_save_button()
        if not self.wait_meeting_saved(timeout=30):
            return False
        return self.search_meeting(new_name)

    def delete_meeting(self, meeting_name, result="删除成功"):
        self._ensure_meeting_page_ready()
        row_locator = self._exact_meeting_row_locator(meeting_name)
        if self.find_visible_now(row_locator) is False:
            if not self._find_exact_meeting_row_via_search(meeting_name):
                return False

        before_count = self.get_total_record_count()
        if not self._click_first_available_safe(
            [self._exact_meeting_delete_button_locator(meeting_name)], timeout=10
        ):
            self._restore_list_state()
            return False
        started=self.driver.execute_script('return performance.now()')
        if not self._click_first_available_safe(
            [self.delete_sure_button_text], timeout=10
        ):
            self._restore_list_state()
            return False
        if not wait_query_finished(self,started,timeout=10,request_path='/meeting/v1/roominfo/delete'):
            raise AssertionError('会议室删除请求未完成')
        absent=not self._find_exact_meeting_row_via_search(meeting_name)
        self._restore_list_state()
        return absent

    def add_meeting_with_passwords(
        self,
        meeting_name,
        admin_password,
        meeting_password,
        result="新增成功",
    ):
        self._ensure_meeting_page_ready()
        self.click_new_add()
        self.send_meeting_name(meeting_name)
        if not self._configure_meeting_password_fields(
            admin_password=admin_password,
            meeting_password=meeting_password,
            login_type=self.meeting_password_verify_option,
        ):
            self._close_add_meeting_modal()
            return False
        self.click_save_button()
        if self.wait_for_operation_result(result, timeout=2):
            return True
        if self._wait_for_visible_modal_closed(timeout=2):
            return True
        return self.is_meeting_visible_on_current_page(meeting_name, timeout=5)

    def is_meeting_visible_on_current_page(self, meeting_name, timeout=5):
        self._ensure_meeting_page_ready()
        row_locator = self._exact_meeting_row_locator(meeting_name)
        return self._visible_in_any([row_locator], timeout=timeout)

    def enable_admin_password_and_select_meeting_password(self):
        self.click_new_add()
        return self._configure_meeting_password_fields(
            admin_password=None,
            meeting_password=None,
            login_type=self.meeting_password_verify_option,
            fill_passwords=False,
        )

    def send_admin_password_and_meeting_password(self, admin_password, meeting_password):
        admin_locator = self._meeting_setting_password_input_locator(self.admin_password_label)
        meeting_locator = self._meeting_setting_password_input_locator(
            self.meeting_password_label
        )
        if not self._replace_input_value(admin_locator, admin_password, timeout=10):
            return False
        if not self._replace_input_value(meeting_locator, meeting_password, timeout=10):
            return False
        return True

    def get_admin_password_msg(self):
        return self.get_element_text(
            self._meeting_setting_password_msg_locator(self.admin_password_label), timeout=10
        )

    def get_meeting_password_msg(self):
        return self.get_element_text(
            self._meeting_setting_password_msg_locator(self.meeting_password_label), timeout=10
        )

    def authorize_first_available_user(self, meeting_name, result="操作成功"):
        self._ensure_meeting_page_ready()
        if not self._find_exact_meeting_row_via_search(meeting_name):
            return None

        for _ in range(2):
            if not self._click_first_available_safe(
                [self._exact_meeting_authorize_button_locator(meeting_name)], timeout=10
            ):
                self._restore_list_state()
                return None
            if self.wait_visible(self._authorize_modal_locator(), timeout=10) is False:
                self._restore_list_state()
                return None

            username = self._move_first_available_authorize_user_native()
            if not username:
                allure.attach(
                    json.dumps(self._authorize_modal_diagnostics(), ensure_ascii=False, indent=2),
                    "会议室授权用户移动诊断",
                    allure.attachment_type.TEXT,
                )
                self._close_authorize_modal()
                self._restore_list_state()
                continue

            if not self._set_authorized_user_role("参会者"):
                self._close_authorize_modal()
                self._restore_list_state()
                continue

            if not self._click_first_available_safe(
                [self._modal_action_button_locator(self.authorize_modal_title, self.save_button_text)],
                timeout=5,
            ):
                self._restore_list_state()
                continue
            if not self.wait_for_operation_result(result, timeout=8):
                self._restore_list_state()
                continue

            if not self._click_first_available_safe(
                [self._exact_meeting_authorize_button_locator(meeting_name)], timeout=10
            ):
                self._restore_list_state()
                continue
            if self.wait_visible(self._authorize_modal_locator(), timeout=10) is False:
                self._restore_list_state()
                continue

            authorized = self._authorize_modal_contains_username(username)
            self._close_authorize_modal()
            self._restore_list_state()
            if authorized:
                return username

        return None

    def _move_first_available_authorize_user_native(self):
        """Move one real row from the available-user table to the authorized table."""
        selected = self.driver.execute_script("""
          const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
          const modal = [...document.querySelectorAll('.ant-modal-content')].filter(visible)
            .find(e => (e.querySelector('.ant-modal-title')?.innerText || '').trim() === '会议室授权用户');
          const left = modal?.querySelector('.right-box-left');
          const row = left && [...left.querySelectorAll('tbody tr')]
            .find(e => visible(e) && !e.classList.contains('ant-table-measure-row') && e.querySelector('input[type=checkbox]'));
          const username = (row?.querySelector('td:nth-child(3)')?.innerText || '').trim();
          const input = row?.querySelector('input[type=checkbox]');
          if (!username || !input) return '';
          if (!input.checked) (input.closest('label') || input).click();
          return username;
        """)
        if not selected:
            return None
        enabled = self.wait_until(
            lambda: self.driver.execute_script("""
              const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
              const modal = [...document.querySelectorAll('.ant-modal-content')].filter(visible)
                .find(e => (e.querySelector('.ant-modal-title')?.innerText || '').trim() === '会议室授权用户');
              const button = modal && [...modal.querySelectorAll('button')].find(e =>
                !e.disabled && e.querySelector('[aria-label=right], .anticon-right'));
              if (!button) return false;
              button.click();
              return true;
            """),
            timeout=5,
        )
        if enabled is False:
            return None
        moved = self.wait_until(
            lambda: self._authorize_modal_contains_username(selected), timeout=5
        )
        return selected if moved is not False else None

    def _authorize_modal_diagnostics(self):
        return self.driver.execute_script("""
          const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
          const modal = [...document.querySelectorAll('.ant-modal-content')].filter(visible)
            .find(e => (e.querySelector('.ant-modal-title')?.innerText || '').trim() === '会议室授权用户');
          if (!modal) return {modal: false};
          const rows = box => [...(box?.querySelectorAll('tbody tr') || [])]
            .filter(e => visible(e) && !e.classList.contains('ant-table-measure-row'))
            .slice(0, 3).map(e => ({text:(e.innerText || '').trim(), checked:!!e.querySelector('input:checked')}));
          return {
            modal: true,
            leftRows: rows(modal.querySelector('.right-box-left')),
            rightRows: rows(modal.querySelector('.right-box-right')),
            arrows: [...modal.querySelectorAll('button')].filter(e => e.querySelector('[aria-label=right], .anticon-right'))
              .map(e => ({disabled:!!e.disabled, html:e.outerHTML.slice(0, 500)})),
            messages: [...document.querySelectorAll('.ant-message-notice-content')].filter(visible)
              .map(e => (e.innerText || '').trim()),
          };
        """)

    def authorize_user_for_recording(self, meeting_name, username, result="操作成功"):
        """Authorize one known user before assigning it to a designated recording mode."""
        self._ensure_meeting_page_ready()
        if not self._find_exact_meeting_row_via_search(meeting_name):
            return False
        if not self._click_first_available_safe(
            [self._exact_meeting_authorize_button_locator(meeting_name)], timeout=10
        ):
            self._restore_list_state()
            return False
        if self.wait_visible(self._authorize_modal_locator(), timeout=10) is False:
            self._restore_list_state()
            return False
        allure.attach(
            self._visible_modal_text(),
            "会议室授权用户初始内容",
            allure.attachment_type.TEXT,
        )
        row = self._authorize_left_row_by_username(username)
        if row is None:
            row = self._search_authorize_left_user(username)
        if row is None:
            # The user may already be authorized from an interrupted prior run.
            already_authorized = self._authorize_modal_contains_username(username)
            self._close_authorize_modal()
            self._restore_list_state()
            return already_authorized
        if not self._click_authorize_left_row_checkbox(row):
            self._close_authorize_modal()
            self._restore_list_state()
            return False
        if not self._click_first_available_safe(
            [self._authorize_move_right_button_locator()], timeout=5
        ):
            self._close_authorize_modal()
            self._restore_list_state()
            return False
        time.sleep(0.3)
        allure.attach(
            self._visible_modal_text(),
            "会议室授权用户移动后内容",
            allure.attachment_type.TEXT,
        )
        if self.wait_until(
            lambda: self._authorize_modal_contains_username(username), timeout=5
        ) is False:
            self._close_authorize_modal()
            self._restore_list_state()
            return False
        allure.attach(
            self._visible_modal_text(),
            "授权用户保存前页面内容",
            allure.attachment_type.TEXT,
        )
        if not self._click_first_available_safe(
            [self._modal_action_button_locator(self.authorize_modal_title, self.save_button_text)],
            timeout=5,
        ):
            self._restore_list_state()
            return False
        saved = self.wait_for_operation_result(result, timeout=3) or self._wait_for_visible_modal_closed(timeout=5)
        if not saved or not self._wait_for_visible_modal_closed(timeout=5):
            allure.attach(
                self._visible_modal_text(),
                "授权用户保存失败页面内容",
                allure.attachment_type.TEXT,
            )
            self._restore_list_state()
            return False
        if not self._find_exact_meeting_row_via_search(meeting_name):
            raise AssertionError("授权保存后会议室不可查询，禁止使用旧行验证持久化")
        if not self._click_first_available_safe(
            [self._exact_meeting_authorize_button_locator(meeting_name)], timeout=10
        ):
            self._restore_list_state()
            return False
        if self.wait_visible(self._authorize_modal_locator(), timeout=10) is False:
            self._restore_list_state()
            return False
        persisted = self.wait_until(lambda: self._authorize_modal_contains_username(username), timeout=5) is not False
        if not self._close_authorize_modal():
            raise AssertionError("授权用户弹窗关闭后遮罩未消失，禁止操作会议室列表")
        self._restore_list_state()
        return persisted

    def authorize_user_with_role(
        self, meeting_name, username, role="管理员", result="操作成功"
    ):
        """Authorize one exact user and persist an explicit meeting role."""
        self.last_authorization_error = ""

        def failed(stage):
            self.last_authorization_error = stage
            allure.attach(
                json.dumps(
                    {
                        "失败阶段": stage,
                        "目标会议室": meeting_name,
                        "目标用户": username,
                        "目标角色": role,
                        "搜索统计": getattr(self, "last_authorize_search", {}),
                        "弹窗文本": self._visible_modal_text(),
                        "弹窗诊断": self._authorize_modal_diagnostics(),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                "会议室用户授权失败诊断",
                allure.attachment_type.JSON,
            )
            return False

        if role not in {"管理员", "参会者"}:
            raise ValueError(f"不支持的会议室授权角色：{role}")
        self._ensure_meeting_page_ready()
        if not self._find_exact_meeting_row_via_search(meeting_name):
            return failed("未检索到目标会议室")
        if not self._click_first_available_safe(
            [self._exact_meeting_authorize_button_locator(meeting_name)], timeout=10
        ):
            self._restore_list_state()
            return failed("未点击到权限管理按钮")
        if self.wait_visible(self._authorize_modal_locator(), timeout=10) is False:
            self._restore_list_state()
            return failed("会议室授权用户弹窗未出现")

        row = self._authorize_left_row_by_username(username)
        if row is None:
            row = self._search_authorize_left_user(username)
        if row is not None:
            if not self._click_authorize_left_row_checkbox(row):
                self._close_authorize_modal()
                self._restore_list_state()
                return failed("未勾选左侧目标用户")
            moved = self.wait_until(
                lambda: self.driver.execute_script(
                    r"""
                    const visible = element => !!(element && element.offsetParent !== null);
                    const modal = [...document.querySelectorAll('.ant-modal-content')].filter(visible)
                      .find(element => (element.querySelector('.ant-modal-title')?.innerText || '').trim() === '会议室授权用户');
                    const button = modal && [...modal.querySelectorAll('button')].find(element =>
                      visible(element) && !element.disabled &&
                      element.querySelector('[aria-label=right],.anticon-right'));
                    if (!button) return false;
                    button.click(); return true;
                    """
                ),
                timeout=5,
                poll_frequency=0.2,
            )
            if moved is False:
                self._close_authorize_modal()
                self._restore_list_state()
                return failed("目标用户勾选后右移按钮仍不可用")
            if self.wait_until(
                lambda: self._authorize_modal_contains_username(username), timeout=5
            ) is False:
                self._close_authorize_modal()
                self._restore_list_state()
                return failed("右移后待授权列表未出现目标用户")
        elif not self._authorize_modal_contains_username(username):
            failure = failed("左侧搜索和右侧列表均无目标用户")
            self._close_authorize_modal()
            self._restore_list_state()
            return failure

        if not self._set_authorized_user_role(role):
            self._close_authorize_modal()
            self._restore_list_state()
            return failed(f"未选中授权角色：{role}")
        if not self._click_first_available_safe(
            [self._modal_action_button_locator(self.authorize_modal_title, self.save_button_text)],
            timeout=5,
        ):
            self._restore_list_state()
            return failed("未点击到授权保存按钮")
        saved = self.wait_for_operation_result(result, timeout=8) or self._wait_for_visible_modal_closed(timeout=5)
        self._restore_list_state()
        return bool(saved) if saved else failed("保存授权后未出现成功提示且弹窗未关闭")

    def _search_authorize_left_user(self, username, timeout=8):
        """Search the available-user table instead of assuming page one."""
        started = time.time()
        attempts = 0
        self.last_authorize_search = {"目标用户": username, "尝试次数": 0}
        deadline = started + 60
        while time.time() < deadline:
            attempts += 1
            self.last_authorize_search.update(
                {"尝试次数": attempts, "耗时秒": round(time.time() - started, 2)}
            )
            modal = self.wait_visible(self._authorize_modal_locator(), timeout=2)
            if modal is False:
                time.sleep(0.5)
                continue
            inputs = [
                element
                for element in modal.find_elements(
                    by.CSS_SELECTOR, "input[placeholder*='搜索']"
                )
                if element.is_displayed() and element.is_enabled()
            ]
            buttons = [
                element
                for element in modal.find_elements(
                    by.CSS_SELECTOR,
                    "button:has([aria-label='search']), button:has(.anticon-search)",
                )
                if element.is_displayed() and element.is_enabled()
            ]
            if not inputs or not buttons:
                self.last_authorize_search.update(
                    {"可见搜索框": len(inputs), "可用搜索按钮": len(buttons)}
                )
                time.sleep(0.5)
                continue
            search_input = inputs[0]
            search_input.click()
            search_input.send_keys(Keys.CONTROL, "a")
            search_input.send_keys(Keys.DELETE)
            search_input.send_keys(username)
            self.last_authorize_search.update(
                {
                    "可见搜索框": len(inputs),
                    "可用搜索按钮": len(buttons),
                    "输入框值": search_input.get_attribute("value") or "",
                }
            )
            buttons[0].click()
            row = self.wait_until(
                lambda: self._authorize_left_row_by_username(username) or False,
                timeout=min(timeout, 5),
                poll_frequency=0.2,
            )
            if row is not False:
                self.last_authorize_search["找到目标用户"] = True
                return row
            time.sleep(1)
        self.last_authorize_search.update(
            {"找到目标用户": False, "耗时秒": round(time.time() - started, 2)}
        )
        return None

    def _click_meeting_row_action(self, meeting_name, action_text, timeout=8):
        return self.wait_until(
            lambda: self.driver.execute_script(
                r"""
                const name = arguments[0];
                const action = arguments[1].replace(/\s+/g, '');
                const visible = element => !!(element && element.offsetParent !== null);
                const rows = [...document.querySelectorAll('main tbody tr')]
                  .filter(row => visible(row) && !row.classList.contains('ant-table-measure-row'));
                const row = rows.find(item =>
                  (item.querySelector('td:nth-child(3)')?.innerText || '').trim() === name);
                const target = row && [...row.querySelectorAll('button,a')].find(element =>
                  visible(element) && (element.innerText || '').replace(/\s+/g, '') === action);
                if (!target) return false;
                target.click(); return true;
                """,
                meeting_name,
                action_text,
            ),
            timeout=timeout,
            poll_frequency=0.2,
        ) is not False

    def _notification_field(self, selector):
        return self.driver.execute_script(
            r"""
            const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
            const modal=[...document.querySelectorAll('.ant-modal-content')].filter(visible)
              .find(e=>(e.querySelector('.ant-modal-title')?.innerText||'').replace(/\s/g,'')==='会议通知');
            return [...(modal?.querySelectorAll(arguments[0])||[])].find(visible)||null;
            """,selector,
        )

    def _notification_time_value(self):
        field=self._notification_field('#form_item_startTime,input[placeholder="开始时间"]')
        if field is None:return ''
        return field.get_attribute('value') or ''

    def _notification_picker(self):
        return next((e for e in self.driver.find_elements(by.CSS_SELECTOR,'.ant-picker-dropdown,.ant-calendar-picker-container') if e.is_displayed()),False)

    def _ready_notification_picker(self):
        panel=self._notification_picker()
        return panel if panel is not False and not re.search(r'(enter|appear|leave)-(active|to|from)',panel.get_attribute('class') or '') else False

    def _reopen_notification_picker_if_closed(self):
        def settled():
            panel=self._notification_picker()
            if panel is False:return {'closed':True}
            return {'panel':panel} if self._ready_notification_picker() is not False else False
        state=self.wait_until(settled,timeout=3)
        if state is False:return False
        if state.get('closed'):
            self._notification_field('#form_item_startTime,input[placeholder="开始时间"]').click()
            return self.wait_until(self._ready_notification_picker,timeout=3)
        return state['panel']

    def _set_notification_start_time(self, value):
        self.last_notification_start_time=value
        def ready():
            field=self._notification_field('#form_item_startTime,input[placeholder="开始时间"]')
            return field if field is not None and field.is_displayed() and field.is_enabled() else False
        input_element=self.wait_until(ready,timeout=8,poll_frequency=0.1)
        if input_element is False:return False
        input_element.click()
        panel=self.wait_until(self._ready_notification_picker,timeout=5)
        if panel is False:return False
        if 'ant-calendar-picker-container' in (panel.get_attribute('class') or ''):
            return self._set_legacy_notification_start_time(input_element,value)
        target=datetime.strptime(value,'%Y-%m-%d %H:%M:%S')
        if target.date()==datetime.now().date():
            now_button=next((e for e in panel.find_elements(by.CSS_SELECTOR,'.ant-picker-now-btn') if e.is_displayed()),None)
            if now_button is None:return False
            now_button.click()
            panel=self._reopen_notification_picker_if_closed()
            if panel is False:return False
        else:
            day=next((e for e in panel.find_elements(by.CSS_SELECTOR,'td[title]')
                if e.get_attribute('title')==value[:10] and 'disabled' not in (e.get_attribute('class') or '')),None)
            if day is None:return False
            day.click()
        # Time-picker columns have a fixed hour/minute/second schema; these
        # are scoped widget options, not global form input indexes.
        for column,expected in enumerate((target.hour,target.minute,target.second)):
            def option():
                current=self._notification_picker()
                if current is False:return False
                columns=current.find_elements(by.CSS_SELECTOR,'.ant-picker-time-panel-column')
                if len(columns)!=3:return False
                return next((e for e in columns[column].find_elements(by.TAG_NAME,'li')
                    if (e.get_attribute('textContent') or '').strip()==f'{expected:02d}' and 'disabled' not in (e.get_attribute('class') or '')),False)
            item=self.wait_until(option,timeout=3)
            if item is False:return False
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'})",item)
            item.click()
        panel=self._notification_picker()
        if panel is not False:
            button=next((e for e in panel.find_elements(by.CSS_SELECTOR,'button')
                if e.is_displayed() and e.is_enabled() and (e.text or '').replace(' ','')=='确定'),None)
            if button is None:return False
            button.click()
        actual=self.wait_until(lambda:self._notification_time_value() if self._notification_time_value()==value else False,timeout=5)
        allure.attach(
            json.dumps(
                {"期望开始时间": value, "控件实际值": actual or ""},
                ensure_ascii=False,
                indent=2,
            ),
            "会议通知开始时间控件值",
            allure.attachment_type.JSON,
        )
        return actual is not False

    def _set_legacy_notification_start_time(self, input_element, value):
        editable=next((e for e in self.driver.find_elements(by.CSS_SELECTOR,'.ant-calendar-picker-container input.ant-calendar-input')
            if e.is_displayed() and e.is_enabled() and not e.get_property('readOnly')),None)
        if editable is not None:
            editable.click();editable.send_keys(Keys.CONTROL,'a');editable.send_keys(Keys.DELETE)
            editable.send_keys(value);editable.send_keys(Keys.ENTER)
            def committed():
                panel=self._notification_picker()
                if panel is False:return self._notification_time_value()==value
                button=next((e for e in panel.find_elements(by.CSS_SELECTOR,'.ant-calendar-ok-btn')
                    if e.is_displayed() and 'disabled' not in (e.get_attribute('class') or '')),None)
                if button is not None:button.click()
                return False
            success=self.wait_until(committed,timeout=5)
            allure.attach(json.dumps({'期望开始时间':value,'控件实际值':self._notification_time_value()},ensure_ascii=False),
                '会议通知旧版日期控件值',allure.attachment_type.JSON)
            return success is not False
        target = time.strptime(value, "%Y-%m-%d %H:%M:%S")
        date_title = f"{target.tm_year}年{target.tm_mon}月{target.tm_mday}日"
        date_selected=False
        if value[:10]==datetime.now().strftime('%Y-%m-%d'):
            now_button=self.wait_until(lambda:next((e for e in self.driver.find_elements(by.CSS_SELECTOR,'.ant-calendar-picker-container .ant-calendar-today-btn')
                if e.is_displayed() and 'disabled' not in (e.get_attribute('class') or '')),False),timeout=3)
            if now_button is not False:
                now_button.click()
                if self._reopen_notification_picker_if_closed() is False:return False
                date_selected=True
        if not date_selected:date_selected = self.wait_until(
            lambda: self.driver.execute_script(
                r"""
                const title = arguments[0];
                const visible = element => !!(element && element.offsetParent !== null);
                const cell = [...document.querySelectorAll('.ant-calendar-picker-container td[title]')]
                  .find(element => visible(element) && element.title === title
                    && !element.classList.contains('ant-calendar-disabled-cell'));
                if (!cell) return false;
                cell.click(); return true;
                """,
                date_title,
            ),
            timeout=5,
            poll_frequency=0.2,
        )
        if date_selected is False:
            return False
        opened_time = self.wait_until(
            lambda: self.driver.execute_script(
                r"""
                const visible = element => !!(element && element.offsetParent !== null);
                const button = [...document.querySelectorAll('.ant-calendar-time-picker-btn')]
                  .find(visible);
                if (!button) return false;
                button.click(); return true;
                """
            ),
            timeout=5,
            poll_frequency=0.2,
        )
        if opened_time is False:
            return False
        for column, expected in enumerate(
            (target.tm_hour, target.tm_min, target.tm_sec)
        ):
            selected = self.wait_until(
                lambda column=column, expected=expected: self.driver.execute_script(
                    r"""
                    const column = arguments[0];
                    const expected = String(arguments[1]).padStart(2, '0');
                    const visible = element => !!(element && element.offsetParent !== null);
                    const lists = [...document.querySelectorAll('.ant-calendar-time-picker-select')]
                      .filter(visible);
                    const item = lists[column] && [...lists[column].querySelectorAll('li')]
                      .find(element => (element.innerText || '').trim() === expected
                        && !element.classList.contains('ant-calendar-time-picker-select-option-disabled'));
                    if (!item) return false;
                    item.scrollIntoView({block:'center'}); item.click(); return true;
                    """,
                    column,
                    expected,
                ),
                timeout=5,
                poll_frequency=0.2,
            )
            if selected is False:
                return False
        confirmed = self.wait_until(
            lambda: self.driver.execute_script(
                r"""
                const visible = element => !!(element && element.offsetParent !== null);
                const button = [...document.querySelectorAll('.ant-calendar-ok-btn')]
                  .find(element => visible(element)
                    && !element.classList.contains('ant-calendar-ok-btn-disabled'));
                if (!button) return false;
                button.click(); return true;
                """
            ),
            timeout=5,
            poll_frequency=0.2,
        )
        actual = self.wait_until(lambda:self._notification_time_value() if self._notification_time_value()==value else False,timeout=5)
        allure.attach(
            json.dumps(
                {"期望开始时间": value, "旧版日期控件实际值": actual},
                ensure_ascii=False,
                indent=2,
            ),
            "会议通知旧版日期控件值",
            allure.attachment_type.JSON,
        )
        return confirmed is not False and actual is not False

    def send_email_notification(
        self, meeting_name, username, subject, start_time, result="操作成功"
    ):
        """Schedule a real email notification for one retained test meeting."""
        self.last_notification_error = ""
        self.last_notification_start_time=''

        def failed(stage):
            self.last_notification_error = stage
            allure.attach(
                json.dumps(
                    {
                        "失败阶段": stage,
                        "当前路由": self.driver.current_url,
                        "弹窗内容": self._visible_modal_text(),
                        '期望开始时间':self.last_notification_start_time,
                        '实际开始时间':self._notification_time_value(),
                        '当前时间':datetime.now().isoformat(),
                        '日期弹层':self.driver.execute_script("return [...document.querySelectorAll('.ant-picker-dropdown,.ant-calendar-picker-container')].filter(e=>e.offsetParent!==null).map(e=>(e.innerText||'').slice(-900))"),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                "会议邮件通知失败诊断",
                allure.attachment_type.JSON,
            )
            from common.privacy import masked_screenshot
            with masked_screenshot(self.driver):
                allure.attach(self.driver.get_screenshot_as_png(),'会议通知失败时的活动表单',allure.attachment_type.PNG)
            return False

        self._ensure_meeting_page_ready()
        if not self._find_exact_meeting_row_via_search(meeting_name):
            return failed("未检索到目标会议室")
        if not self._click_meeting_row_action(meeting_name, "通知"):
            self._restore_list_state()
            return failed("未点击到目标会议室的通知按钮")
        if self.wait_until(
            lambda: self._top_visible_modal_title() == "会议通知", timeout=8
        ) is False:
            self._restore_list_state()
            return failed("会议通知弹窗未出现")

        email_label=self.wait_until(lambda:self.driver.execute_script(
            "const m=[...document.querySelectorAll('.ant-modal-content')].filter(e=>e.offsetParent!==null).find(e=>(e.querySelector('.ant-modal-title')?.innerText||'').replace(/\\s/g,'')==='会议通知');const input=m?.querySelector('input[type=radio][value=email]');return input&&!input.disabled?input.closest('label'):null;"
        ),timeout=8)
        if email_label is False:return failed('邮件通知方式尚未就绪')
        email_label.click()
        recipient_visible=self.wait_until(lambda:username in self._visible_modal_text(),timeout=20,poll_frequency=0.2)
        if recipient_visible is False:return failed('默认授权收件人尚未加载')

        subject_input = self.wait_until(
            lambda: next(
                (
                    element
                    for element in self.driver.find_elements(
                        by.CSS_SELECTOR,
                        "#form_item_subject, .ant-modal-content input[placeholder='会议主题']",
                    )
                    if element.is_displayed() and element.is_enabled()
                ),
                False,
            ),
            timeout=8,
            poll_frequency=0.2,
        )
        if subject_input is False:
            self._click_visible_modal_button(primary=False, timeout=2)
            self._restore_list_state()
            return failed("会议主题输入框不可用")
        subject_input.click()
        subject_input.send_keys(Keys.CONTROL, "a")
        subject_input.send_keys(Keys.DELETE)
        subject_input.send_keys(subject)
        subject_input.send_keys(Keys.TAB)
        actual_subject = subject_input.get_attribute("value") or ""
        allure.attach(
            json.dumps(
                {"期望会议主题": subject, "控件实际值": actual_subject},
                ensure_ascii=False,
                indent=2,
            ),
            "会议通知主题控件值",
            allure.attachment_type.JSON,
        )
        subject_ok = actual_subject==subject
        start_time=start_time() if callable(start_time) else start_time
        self.last_notification_start_time=start_time
        if not subject_ok or not self._set_notification_start_time(start_time):
            return failed("会议主题或开始时间未写入控件")
        email_input=self._notification_field('input[type=radio][value=email]')
        email_selected=email_input is not None and email_input.is_selected()
        recipient_visible=username in self._visible_modal_text()
        allure.attach(
            json.dumps(
                {
                    "会议室": meeting_name,
                    "会议主题": subject,
                    "开始时间": start_time,
                    "通知方式": "邮件通知",
                    "授权用户": username,
                    "授权用户已显示": recipient_visible is not False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            "会议邮件通知输入数据",
            allure.attachment_type.JSON,
        )
        if not email_selected or not recipient_visible:
            return failed("邮件通知未选中或授权收件人未显示")
        subject_now=self._notification_field('#form_item_subject,input[placeholder="会议主题"]')
        if subject_now is None or subject_now.get_attribute('value')!=subject or self._notification_time_value()!=start_time:
            return failed('保存前主题或开始时间被重绘覆盖')
        if datetime.strptime(start_time,'%Y-%m-%d %H:%M:%S')<=datetime.now():
            return failed('保存前开始时间已过期')
        if self.wait_until(lambda:self._notification_picker() is False,timeout=3) is False:
            return failed('日期弹层确认后未关闭')
        if not self._click_visible_modal_button(primary=True, timeout=5):
            self._restore_list_state()
            return failed("未点击到会议通知保存按钮")
        saved = self.wait_until(
            lambda: self._top_visible_modal_title() != "会议通知",
            timeout=10,
            poll_frequency=0.2,
        )
        if saved is False:
            return failed("保存后会议通知编辑弹窗未关闭")
        self._restore_list_state()
        deadline = time.time() + 20
        persisted = ""
        valid = False
        while time.time() < deadline:
            if not self._find_exact_meeting_row_via_search(meeting_name):
                time.sleep(1)
                continue
            if not self._click_meeting_row_action(meeting_name, "查看", timeout=4):
                self._restore_list_state()
                time.sleep(1)
                continue
            if self.wait_until(
                lambda: self._top_visible_modal_title() == "会议通知", timeout=4
            ) is False:
                self._restore_list_state()
                time.sleep(1)
                continue
            hydrated = self.wait_until(
                lambda: (
                    text
                    if subject in text
                    and start_time in text
                    and "邮件" in text
                    and username in text
                    else False
                )
                if (text := self._visible_modal_text())
                else False,
                timeout=6,
                poll_frequency=0.2,
            )
            persisted = (
                hydrated
                if isinstance(hydrated, str)
                else self._visible_modal_text()
            )
            valid = hydrated is not False
            self._click_visible_modal_button(primary=False, timeout=2)
            self._restore_list_state()
            if valid:
                break
            time.sleep(1)
        allure.attach(persisted, "会议邮件通知保存后详情", allure.attachment_type.TEXT)
        return valid if valid else failed("通知详情未持久化主题、时间、方式或收件人")

    def wait_email_notification_success(self, meeting_name, timeout=90):
        """Poll the notification detail until the backend records email success."""
        deadline = time.time() + timeout
        latest = ""
        while time.time() < deadline:
            self._ensure_meeting_page_ready()
            if not self._find_exact_meeting_row_via_search(meeting_name):
                time.sleep(1)
                continue
            if not self._click_meeting_row_action(meeting_name, "查看", timeout=4):
                self._restore_list_state()
                time.sleep(1)
                continue
            if self.wait_until(
                lambda: self._top_visible_modal_title() == "会议通知", timeout=5
            ) is False:
                self._restore_list_state()
                time.sleep(1)
                continue
            latest = self._visible_modal_text()
            if "邮件全部发送成功" in latest:
                allure.attach(latest, "会议通知发送结果", allure.attachment_type.TEXT)
                self._click_visible_modal_button(primary=False, timeout=2)
                self._restore_list_state()
                return latest
            self._click_visible_modal_button(primary=False, timeout=2)
            self._restore_list_state()
            time.sleep(2)
        allure.attach(latest or "未获取到通知结果", "会议通知发送超时结果", allure.attachment_type.TEXT)
        return ""

    def sort_first_authorized_user(self, meeting_name, sort_value="1"):
        self.last_sort_error = ""

        def failed(stage):
            self.last_sort_error = stage
            allure.attach(stage, "用户排序失败阶段", allure.attachment_type.TEXT)
            return None

        self._ensure_meeting_page_ready()
        if not self._find_exact_meeting_row_via_search(meeting_name):
            return failed("未检索到目标会议室")

        if not self._click_first_available_safe(
            [self._exact_meeting_sort_button_locator(meeting_name)], timeout=10
        ):
            self._restore_list_state()
            return failed("未点击到用户排序操作")
        if self.wait_visible(self._sort_modal_locator(), timeout=10) is False:
            self._restore_list_state()
            return failed("用户排序弹窗未出现")

        username = ""
        end = time.time() + 8
        while time.time() < end and not username:
            username = str(self.driver.execute_script(
                """
                const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                const modal=[...document.querySelectorAll('.ant-modal-content')].filter(visible)
                  .find(e=>(e.querySelector('.ant-modal-title')?.innerText||'').trim()==='用户排序');
                const row=modal&&[...modal.querySelectorAll('tbody tr')]
                  .find(e=>visible(e)&&!e.classList.contains('ant-table-measure-row'));
                return (row?.querySelector('td:nth-child(2)')?.innerText||'').trim();
                """
            ) or "").strip()
            if not username:
                time.sleep(0.2)
        if not username:
            self._close_sort_modal()
            self._restore_list_state()
            return failed("用户排序弹窗没有已授权用户")

        if not self._click_first_available_safe([self._sort_first_row_edit_button_locator()], timeout=5):
            self._close_sort_modal()
            self._restore_list_state()
            return failed("未点击到首行排序编辑按钮")
        if not self._replace_input_value(self._sort_edit_input_locator(), sort_value, timeout=10):
            self._close_sort_modal()
            self._restore_list_state()
            return failed("未写入排序值")

        try:
            edit_input = self.wait_visible(self._sort_edit_input_locator(), timeout=5)
            if edit_input is False:
                self._close_sort_modal()
                self._restore_list_state()
                return failed("排序输入框在提交前消失")
            edit_input.send_keys(Keys.ENTER)
        except Exception:
            self._close_sort_modal()
            self._restore_list_state()
            return failed("按回车提交排序值失败")

        if not self._wait_sort_value_present(sort_value, timeout=5):
            self._close_sort_modal()
            self._restore_list_state()
            return failed("提交后列表未显示排序值")

        self._close_sort_modal()

        if not self._click_first_available_safe(
            [self._exact_meeting_sort_button_locator(meeting_name)], timeout=10
        ):
            self._restore_list_state()
            return failed("未能再次打开用户排序弹窗")
        if self.wait_visible(self._sort_modal_locator(), timeout=10) is False:
            self._restore_list_state()
            return failed("第二次用户排序弹窗未出现")

        persisted = self._sort_modal_value_for_username(username) == str(sort_value)
        self._close_sort_modal()
        self._restore_list_state()
        if not persisted:
            return failed("刷新弹窗后排序值未持久化")
        return username

    def ensure_meeting_absent(self, meeting_name):
        self._ensure_meeting_page_ready()
        if self._ensure_meeting_absent_via_search(meeting_name, max_attempts=5):
            self._restore_list_state()
            return True

        absent = self._ensure_meeting_absent_globally(meeting_name, max_attempts=10)
        self._restore_list_state()
        return absent

    def get_total_record_count(self):
        self._ensure_meeting_page_ready()
        text = self._first_visible_text(self.data_num)
        if text:
            numbers = re.findall(r"\d+", text)
            if numbers:
                return int(numbers[-1])
        # Vue3 removed the summary text on this page. A pagination-derived
        # lower bound is sufficient for minimum-record preconditions.
        return self.driver.execute_script(
            """
            const rows=[...document.querySelectorAll('main tbody tr')]
              .filter(e=>e.offsetParent!==null&&!e.classList.contains('ant-table-measure-row'));
            const pages=[...document.querySelectorAll('main .ant-pagination-item')]
              .map(e=>Number((e.innerText||'').trim())).filter(Number.isFinite);
            const selected=document.querySelector(
              'main .ant-pagination-options-size-changer .ant-select-selection-item, '
              + 'main .ant-pagination-options-size-changer .ant-select-selection-selected-value');
            const size=Number(((selected?.innerText||'').match(/\d+/)||['0'])[0]);
            const last=pages.length?Math.max(...pages):1;
            return last>1&&size ? (last-1)*size+1 : rows.length;
            """
        )

    def wait_for_record_count_change(self, previous_count, timeout=20):
        end = time.time() + timeout
        while time.time() < end:
            current_count = self.get_total_record_count()
            if current_count is not None and current_count != previous_count:
                return current_count
            time.sleep(0.2)
        return None

    def get_current_page_text(self):
        return self._get_visible_active_page_text()

    def get_pagination_summary_text(self):
        summary = self._first_visible_text(self.data_num) or ""
        if summary:
            return summary
        return self.driver.execute_script(
            """
            const page=(document.querySelector('main .ant-pagination-item-active')?.innerText||'').trim();
            const row=[...document.querySelectorAll('main tbody tr')]
              .find(e=>e.offsetParent!==null&&!e.classList.contains('ant-table-measure-row'));
            return page && row ? `page=${page};row=${(row.innerText||'').replace(/\s+/g,' ').trim()}` : '';
            """
        )

    def get_current_page_size_text(self):
        return self._first_visible_text(self.page_size_value) or ""

    def set_result_page_size(self, page_size, timeout=4):
        self._ensure_meeting_page_ready()
        target_text = str(page_size)
        if self._extract_first_number(self.get_current_page_size_text()) == target_text:
            return True

        if not self._click_first_available_safe([
            self.page_size_changer,
            (by.CSS_SELECTOR, ".ant-pagination-options-size-changer .ant-select-selector"),
        ], timeout=5):
            return False

        option_locator = (
            by.XPATH,
            "//div[contains(@class,'ant-select-dropdown') and not(contains(@style,'display: none'))]"
            f"//*[self::li or contains(@class,'ant-select-item-option')]"
            f"[starts-with(normalize-space(),'{target_text}')]",
        )
        if not self._click_first_available_safe([option_locator], timeout=timeout):
            return False

        end = time.time() + timeout
        while time.time() < end:
            if self._extract_first_number(self.get_current_page_size_text()) == target_text:
                return True
            time.sleep(0.2)
        return False

    def jump_to_result_page(self, page_num, timeout=4):
        self._ensure_meeting_page_ready()
        target_page = str(page_num)
        if self.get_current_page_text() == target_page:
            return True

        input_element = self.wait_visible(self.quick_jump_input, timeout=timeout)
        if input_element is False:
            return False

        try:
            input_element.click()
            input_element.send_keys(Keys.CONTROL, "a")
            input_element.send_keys(Keys.DELETE)
            time.sleep(0.1)
            input_element.send_keys(target_page)
            input_element.send_keys(Keys.ENTER)
        except Exception:
            self.send_keys_enter_after_input_by_js(self.quick_jump_input, target_page)

        end = time.time() + timeout
        while time.time() < end:
            if self.get_current_page_text() == target_page:
                return True
            time.sleep(0.2)
        return False

    def submit_search(self):
        search=self.wait_visible(self.locate_search,timeout=5)
        if search is False:
            raise AssertionError('会议室查询输入框不存在')
        started=self.driver.execute_script('return performance.now()')
        if not click_toolbar_search(self.driver,search) or not wait_query_finished(self,started,timeout=10,request_path='/meeting/v1/roominfo/page'):
            raise AssertionError('会议室查询请求未完成')
        return True

    def reset_search(self):
        return self._search_keyword('')

    def delete_meetings_by_names(self, meeting_names, result="删除成功"):
        names = list(dict.fromkeys(meeting_names))
        recording_names = [name for name in names if name.startswith("meeting_recording_")]
        if len(recording_names) > 1 and self._batch_delete_meetings(
            recording_names, "meeting_recording_"
        ):
            names = [name for name in names if name not in recording_names]
        ok = True
        for meeting_name in names:
            ok = self.ensure_meeting_absent(meeting_name) and ok
        return ok

    def _batch_delete_meetings(self, meeting_names, search_prefix):
        """Delete only the exact temporary rows selected from one prefix search."""
        self._ensure_meeting_page_ready()
        self._restore_list_state()
        self._search_keyword(search_prefix)
        expected = list(dict.fromkeys(meeting_names))
        selected = self.wait_until(
            lambda: self.driver.execute_script(
                """
                const names=new Set(arguments[0]);
                const rows=[...document.querySelectorAll('main tbody tr')]
                  .filter(row=>row.offsetParent!==null&&!row.classList.contains('ant-table-measure-row'));
                const targets=rows.filter(row=>names.has((row.querySelector('td:nth-child(3)')?.innerText||'').trim()));
                if (targets.length!==names.size) return false;
                for (const row of targets) {
                  const input=row.querySelector('input[type=checkbox]');
                  if (!input) return false;
                  if (!input.checked) input.click();
                }
                return targets.every(row=>row.querySelector('input[type=checkbox]')?.checked);
                """,
                expected,
            ),
            timeout=6,
            poll_frequency=.2,
        )
        if selected is False:
            self._restore_list_state()
            return False
        clicked = self.driver.execute_script(
            """
            const clean=s=>(s||'').replace(/\s/g,'');
            const button=[...document.querySelectorAll('main button')]
              .find(e=>e.offsetParent!==null&&!e.closest('td')&&clean(e.innerText)==='删除');
            if (!button||button.disabled) return false;
            button.click(); return true;
            """
        )
        if not clicked or not self._click_first_available_safe(
            [self.delete_sure_button_text], timeout=5
        ):
            self._restore_list_state()
            return False
        removed = self.wait_until(
            lambda: self.driver.execute_script(
                """
                const names=new Set(arguments[0]);
                return ![...document.querySelectorAll('main tbody tr')].some(row=>
                  row.offsetParent!==null && names.has((row.querySelector('td:nth-child(3)')?.innerText||'').trim()));
                """,
                expected,
            ),
            timeout=8,
            poll_frequency=.2,
        )
        self._restore_list_state()
        return removed is not False

    def _meeting_name_input_locator(self, modal_title):
        return (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{modal_title}']]"
            f"//label[normalize-space()='{self.meeting_name_label}']"
            "/ancestor::div[contains(concat(' ',normalize-space(@class),' '),' ant-form-item ')][1]//input[not(@disabled)]",
        )

    def _meeting_name_validation_locator(self, modal_title):
        return (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{modal_title}']]"
            f"//label[normalize-space()='{self.meeting_name_label}']"
            "/ancestor::div[contains(concat(' ',normalize-space(@class),' '),' ant-form-item ')][1]"
            "//*[contains(@class,'ant-form-explain') or contains(@class,'ant-form-explain-connected') "
            "or contains(@class,'ant-form-item-explain-error')]",
        )

    def _modal_action_button_locator(self, modal_title, button_text):
        return (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{modal_title}']]"
            f"//button[normalize-space()='{button_text}' or .//span[normalize-space()='{button_text}']]",
        )

    def _visible_modal_title_contains(self, title_text):
        return bool(self.driver.execute_script("""
          const text = arguments[0];
          const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
          return [...document.querySelectorAll('.ant-modal-content')].some(modal =>
            visible(modal) && (modal.querySelector('.ant-modal-title')?.innerText || '').includes(text)
          );
        """, title_text))

    def _visible_overlay_text_contains(self, text):
        return bool(self.driver.execute_script("""
          const text = arguments[0];
          const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
          return [...document.querySelectorAll('.ant-modal-content, .ant-popover, .ant-popover-content')].some(overlay =>
            visible(overlay) && (overlay.innerText || '').includes(text)
          );
        """, text))

    def _visible_modal_text(self):
        return self.driver.execute_script("""
          const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
          const modals = [...document.querySelectorAll('.ant-modal-content')].filter(visible);
          return modals.at(-1)?.innerText || '';
        """)

    def _visible_overlay_diagnostics(self):
        return self.driver.execute_script("""
          const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
          return [...document.querySelectorAll('body *')]
            .filter(e => visible(e) && (e.innerText || '').includes('授权用户'))
            .slice(0, 12)
            .map(e => ({tag: e.tagName, className: String(e.className || ''), text: (e.innerText || '').slice(0, 500), html: e.outerHTML.slice(0, 2000)}));
        """)

    def _click_visible_modal_text_button(self, button_text):
        return bool(self.driver.execute_script("""
          const text = arguments[0];
          const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
          const modals = [...document.querySelectorAll('.ant-modal-content')].filter(visible);
          const modal = modals.at(-1);
          const button = modal && [...modal.querySelectorAll('button')].find(e =>
            visible(e) && !e.disabled && (e.innerText || '').replace(/\s+/g, '').trim() === text
          );
          if (!button) return false;
          button.scrollIntoView({block: 'center'}); button.click(); return true;
        """, button_text))

    def _click_visible_overlay_text_button(self, button_text):
        return bool(self.driver.execute_script("""
          const text = arguments[0];
          const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
          const overlays = [...document.querySelectorAll('.ant-modal-content, .ant-popover, .ant-popover-content')].filter(visible);
          const button = overlays.flatMap(e => [...e.querySelectorAll('button')]).find(e =>
            visible(e) && !e.disabled && (e.innerText || '').replace(/\s+/g, '').trim() === text
          );
          if (!button) return false;
          button.scrollIntoView({block: 'center'}); button.click(); return true;
        """, button_text))

    def _click_visible_text(self, text):
        return bool(self.driver.execute_script("""
          const text = arguments[0];
          const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
          const node = [...document.querySelectorAll('button, a, span, div')].find(e =>
            visible(e) && e.children.length === 0 && (e.innerText || '').replace(/\s+/g, '').trim() === text
          );
          if (!node) return false;
          node.scrollIntoView({block: 'center'}); (node.closest('button, a') || node).click(); return true;
        """, text))

    def _click_visible_modal_button(self, primary=True, timeout=5):
        script = """
        const wantPrimary = arguments[0];
        const normalize = (value) => String(value || '').replace(/\\s+/g, '').trim();
        const isVisible = (el) => {
            if (!el) return false;
            const style = window.getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            return style.display !== 'none'
                && style.visibility !== 'hidden'
                && rect.width > 0
                && rect.height > 0;
        };
        const modals = Array.from(document.querySelectorAll('.ant-modal-content')).filter(isVisible);
        if (!modals.length) return false;
        const modal = modals[modals.length - 1];
        const footer = modal.querySelector('.ant-modal-footer') || modal;
        const buttons = Array.from(footer.querySelectorAll('button'))
            .filter((button) => isVisible(button) && !button.disabled);
        const hasPrimaryClass = (button) => String(button.className || '').includes('ant-btn-primary');
        const textOf = (button) => normalize(button.innerText || button.textContent);
        let button = null;
        if (wantPrimary) {
            button = buttons.find((item) => ['保存', '确定', '确认'].includes(textOf(item)))
                || buttons.find((item) => hasPrimaryClass(item))
                || buttons[0];
        } else {
            button = buttons.find((item) => ['关闭', '取消'].some((text) => textOf(item).includes(text)))
                || buttons.slice().reverse().find((item) => !hasPrimaryClass(item))
                || modal.querySelector('button.ant-modal-close');
        }
        if (!button || !isVisible(button)) return false;
        button.scrollIntoView({block: 'center'});
        button.click();
        return true;
        """
        end = time.time() + timeout
        while time.time() < end:
            try:
                if self.driver.execute_script(script, primary):
                    return True
            except Exception:
                pass
            time.sleep(0.2)
        return False

    def _wait_for_visible_modal_closed(self, timeout=2):
        script = """
        const isVisible = (el) => {
            if (!el) return false;
            const style = window.getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            return style.display !== 'none'
                && style.visibility !== 'hidden'
                && rect.width > 0
                && rect.height > 0;
        };
        return !Array.from(document.querySelectorAll('.ant-modal-content,.ant-modal-wrap,.ant-modal-mask')).some(isVisible);
        """
        end = time.time() + timeout
        while time.time() < end:
            try:
                if self.driver.execute_script(script):
                    return True
            except Exception:
                pass
            time.sleep(0.2)
        return False

    def _first_visible_text(self, locator):
        for element in self.driver.find_elements(*locator):
            try:
                if element.is_displayed():
                    return (element.text or "").strip()
            except Exception:
                continue
        return ""

    def _meeting_setting_section_locator(self):
        return (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{self.add_modal_title}']]"
            "//form[.//div[contains(@class,'item-header')]//*[normalize-space()='会议室设置']]"
            "//div[contains(@class,'item-header')]//p",
        )

    def _meeting_setting_switch_locator(self, label_text):
        return (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{self.add_modal_title}']]"
            "//form[.//div[contains(@class,'item-header')]//*[normalize-space()='会议室设置']]"
            f"//label[contains(@title,'{label_text}') or contains(normalize-space(),'{label_text}')]"
            "/ancestor::*[contains(@class,'ant-row') or contains(@class,'ant-form-item')][1]"
            "//button[@role='switch']",
        )

    def _meeting_setting_select_locator(self, label_text):
        label_match = (
            "contains(normalize-space(),'登录') and "
            "(contains(normalize-space(),'类型') or contains(normalize-space(),'校验'))"
            if label_text == self.login_type_label
            else f"(@title='{label_text}' or normalize-space()='{label_text}')"
        )
        return (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{self.add_modal_title}']]"
            "//form[.//div[contains(@class,'item-header')]//*[normalize-space()='会议室设置']]"
            f"//label[{label_match}]"
            "/ancestor::*[contains(@class,'ant-row') or contains(@class,'ant-form-item')][1]"
            "//div[contains(@class,'ant-select-selection') or contains(@class,'ant-select-selector')]",
        )

    def _meeting_setting_password_input_locator(self, label_text):
        return (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{self.add_modal_title}']]"
            "//form[.//div[contains(@class,'item-header')]//*[normalize-space()='会议室设置']]"
            f"//input[@placeholder='{label_text}']",
        )

    def _meeting_setting_password_msg_locator(self, label_text):
        item_class = ""
        if label_text == self.admin_password_label:
            item_class = "manage-password"
        elif label_text == self.meeting_password_label:
            item_class = "meeting-login"

        if item_class:
            return (
                by.XPATH,
                "//div[contains(@class,'ant-modal-content')]"
                f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{self.add_modal_title}']]"
                "//form[.//div[contains(@class,'item-header')]//*[normalize-space()='会议室设置']]"
                f"//div[contains(@class,'{item_class}')]"
                "//div[contains(@class,'ant-form-explain') or contains(@class,'ant-form-item-explain-error')]",
            )
        return (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{self.add_modal_title}']]"
            "//form[.//div[contains(@class,'item-header')]//*[normalize-space()='会议室设置']]"
            f"//label[@title='{label_text}' or normalize-space()='{label_text}']"
            "/ancestor::div[contains(@class,'ant-form-item')][1]"
            "//div[contains(@class,'ant-form-explain') or contains(@class,'ant-form-item-explain-error')]",
        )

    def _capture_add_meeting_failure_state(self, meeting_name):
        state = self.driver.execute_script(r"""
            const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
            const modal=[...document.querySelectorAll('.ant-modal-content')].filter(visible).at(-1);
            const label=modal&&[...modal.querySelectorAll('label')].find(e=>(e.innerText||'').trim()==='会议室名称');
            const field=label?.closest('.ant-form-item')?.querySelector('input');
            return {弹窗标题:modal?.querySelector('.ant-modal-title')?.innerText||'',
              实际名称:field?.value??null,字段ID:field?.id||'',当前路由:location.hash,
              字段错误:[...(modal?.querySelectorAll('.ant-form-explain,.ant-form-item-explain-error,[role=alert]')||[])].filter(visible).map(e=>(e.innerText||'').trim()),
              页面提示:[...document.querySelectorAll('.ant-message-notice-content')].filter(visible).map(e=>(e.innerText||'').trim())};
        """)
        state.update({"预期名称": str(meeting_name), "输入过程": getattr(self, 'last_meeting_name_input', {})})
        self.last_add_meeting_debug = state
        allure.attach(json.dumps(state, ensure_ascii=False, indent=2), "新增会议室失败诊断", allure.attachment_type.JSON)
        with masked_screenshot(self.driver):
            allure.attach(self.driver.get_screenshot_as_png(), "新增会议室清理前现场", allure.attachment_type.PNG)

    def _exact_meeting_row_locator(self, meeting_name):
        return (
            by.XPATH,
            f"//table//tbody//tr[td[3][normalize-space()='{meeting_name}']]",
        )

    def _exact_meeting_modify_button_locator(self, meeting_name):
        return action_locator(self, '会议室名称', meeting_name, '修改')

    def _exact_meeting_delete_button_locator(self, meeting_name):
        return action_locator(self, '会议室名称', meeting_name, '删除')

    def _exact_meeting_authorize_button_locator(self, meeting_name):
        return action_locator(self, '会议室名称', meeting_name, '授权')

    def _exact_meeting_sort_button_locator(self, meeting_name):
        return action_locator(self, '会议室名称', meeting_name, '排序')

    def _authorize_modal_locator(self):
        return (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{self.authorize_modal_title}']]",
        )

    def _authorize_move_right_button_locator(self):
        return (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{self.authorize_modal_title}']]"
            "//div[contains(@class,'main_box')]//button["
            ".//*[contains(@class,'anticon-right') or @aria-label='right']][1]",
        )

    def _authorize_left_user_rows_locator(self):
        return (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{self.authorize_modal_title}']]"
            "//div[contains(@class,'right-box-left')]//table//tbody//tr",
        )

    def _authorize_right_user_rows_locator(self):
        return (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{self.authorize_modal_title}']]"
            "//div[contains(@class,'right-box-right')]//table//tbody//tr",
        )

    def _sort_modal_locator(self):
        return (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{self.sort_modal_title}']]",
        )

    def _sort_modal_rows_locator(self):
        return (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{self.sort_modal_title}']]"
            "//table//tbody//tr",
        )

    def _sort_first_row_edit_button_locator(self):
        return (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{self.sort_modal_title}']]"
            "//table//tbody//tr[not(contains(@class,'ant-table-measure-row'))][1]"
            "//td[last()]//button[1]",
        )

    def _sort_edit_input_locator(self):
        return (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{self.sort_modal_title}']]"
            "//table//tbody//tr[not(contains(@class,'ant-table-measure-row'))][1]"
            "//td[last()]//input[not(@disabled)]",
        )

    def _search_keyword(self, keyword):
        search=wait_control_unobscured(self,self.locate_search,timeout=5)
        if search is False:
            raise AssertionError('会议室搜索字段未就绪或仍被弹窗遮罩阻挡')
        search.click();search.send_keys(Keys.CONTROL,'a');search.send_keys(Keys.DELETE)
        if keyword:search.send_keys(str(keyword))
        self.submit_search()
        current=self.wait_visible(self.locate_search,timeout=2)
        if current is False or current.get_attribute('value')!=str(keyword):
            raise AssertionError('会议室查询条件在提交后被重绘覆盖')
        return True

    def _configure_meeting_password_fields(
        self,
        admin_password,
        meeting_password,
        login_type,
        fill_passwords=True,
    ):
        if not self._ensure_meeting_setting_expanded(timeout=8):
            return False
        switch = self._meeting_setting_semantic_control("switch", self.admin_password_label)
        if switch is None or not self._ensure_switch_element_checked(switch, timeout=5):
            return False
        select = self._meeting_setting_semantic_control("select", "登录")
        if select is None or not self._select_dropdown_element_option(select, login_type, timeout=8):
            return False
        if not fill_passwords:
            return True
        return self.send_admin_password_and_meeting_password(
            admin_password, meeting_password
        )

    def _ensure_meeting_setting_expanded(self, timeout=8):
        self.driver.execute_script(
            """
            const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
            const modal = [...document.querySelectorAll('.ant-modal-content')].filter(visible)
              .find(e => (e.querySelector('.ant-modal-title')?.innerText || '').trim() === arguments[0]);
            const body = modal?.querySelector('.ant-modal-body');
            if (body) body.scrollTop = 0;
            """,
            self.add_modal_title,
        )
        content_locators = [
            self._meeting_setting_switch_locator(self.admin_password_label),
            self._meeting_setting_select_locator(self.login_type_label),
            self._meeting_setting_password_input_locator(self.admin_password_label),
        ]
        if self._meeting_setting_semantic_control("switch", self.admin_password_label) is not None:
            return True

        if not self._click_first_available_safe([self._meeting_setting_section_locator()], timeout=5):
            return False

        end = time.time() + timeout
        while time.time() < end:
            if self._meeting_setting_semantic_control("switch", self.admin_password_label) is not None:
                return True
            time.sleep(0.2)
        return False

    def _meeting_setting_semantic_control(self, control_type, label_text):
        selector = (
            "button.ant-switch, .ant-switch" if control_type == "switch"
            else ".ant-select-selector, .ant-select-selection"
        )
        return self.driver.execute_script(
            """
            const [title, label, selector] = arguments;
            const clean = text => (text || '').replace(/[\s：:*]/g, '');
            const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
            const modal = [...document.querySelectorAll('.ant-modal-content')].filter(visible)
              .find(e => clean(e.querySelector('.ant-modal-title')?.innerText) === clean(title));
            if (!modal) return null;
            const nodes = [...modal.querySelectorAll('label, .ant-form-item-label, span, div')]
              .filter(e => visible(e) && clean(e.innerText).includes(clean(label)));
            nodes.sort((a, b) => a.querySelectorAll('*').length - b.querySelectorAll('*').length);
            for (const node of nodes) {
              let scope = node.closest('.ant-form-item, .ant-row, [class*=password], [class*=login]');
              for (let depth = 0; scope && depth < 4; depth++, scope = scope.parentElement) {
                const control = [...scope.querySelectorAll(selector)].find(visible);
                if (control) return control;
              }
            }
            return null;
            """,
            self.add_modal_title,
            label_text,
            selector,
        )

    def _ensure_switch_element_checked(self, element, timeout=5):
        def checked():
            try:
                return element.get_attribute("aria-checked") == "true" or "checked" in (
                    element.get_attribute("class") or ""
                )
            except Exception:
                return False

        if checked():
            return True
        self.driver.execute_script("arguments[0].click();", element)
        return bool(self.wait_until(checked, timeout=timeout, poll_frequency=.2))

    def _select_dropdown_element_option(self, element, option_text, timeout=8):
        self.driver.execute_script("arguments[0].click();", element)
        option = self.wait_until(
            lambda: self.driver.execute_script(
                """
                const expected = arguments[0].replace(/\s/g, '');
                const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
                return [...document.querySelectorAll(
                  '.ant-select-dropdown li, .ant-select-dropdown .ant-select-item-option, .ant-select-dropdown [role=option]'
                )].filter(visible).find(e => (e.innerText || '').replace(/\s/g, '') === expected) || null;
                """,
                option_text,
            ),
            timeout=timeout,
            poll_frequency=.2,
        )
        if option is False or option is None:
            return False
        self.driver.execute_script("arguments[0].click();", option)
        return True

    def _restore_list_state(self):
        self.reset_search()
        self._go_to_first_result_page(timeout=3)
        return True

    def _extract_first_number(self, text):
        numbers = re.findall(r"\d+", text or "")
        if not numbers:
            return ""
        return numbers[0]

    def _get_visible_active_page_text(self):
        for element in self.driver.find_elements(*self.active_page_num):
            try:
                if element.is_displayed():
                    return (element.text or "").strip()
            except Exception:
                continue
        return None

    def _replace_input_value(self, locator, value, timeout=10):
        element = self.wait_visible(locator, timeout)
        if element is False:
            return False
        try:
            element.click()
            element.send_keys(Keys.CONTROL, "a")
            element.send_keys(Keys.DELETE)
            time.sleep(0.1)
            element.send_keys(str(value))
        except Exception:
            self.clear_by_javascript(locator)
            self.send_keys(locator, value)
            element = self.wait_visible(locator, timeout)
            if element is False:
                return False
        time.sleep(0.1)
        current_value = element.get_attribute("value") or ""
        return current_value == str(value)

    def _ensure_switch_checked(self, locator, timeout=5):
        element = self.wait_visible(locator, timeout)
        if element is False:
            return False
        aria_checked = element.get_attribute("aria-checked")
        class_name = element.get_attribute("class") or ""
        if aria_checked == "true" or "checked" in class_name:
            return True
        try:
            element.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", element)
        end = time.time() + timeout
        while time.time() < end:
            element = self.wait_visible(locator, timeout=1)
            if element is not False:
                aria_checked = element.get_attribute("aria-checked")
                class_name = element.get_attribute("class") or ""
                if aria_checked == "true" or "checked" in class_name:
                    return True
            time.sleep(0.2)
        return False

    def _select_dropdown_option(self, select_locator, option_text, timeout=8):
        if not self._click_first_available_safe([select_locator], timeout=timeout):
            return False
        option = self.wait_until(
            lambda: self.driver.execute_script(
                """
                const expected = arguments[0].replace(/\s/g, '');
                const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
                const dropdowns = [...document.querySelectorAll('.ant-select-dropdown')].filter(visible);
                for (const dropdown of dropdowns.reverse()) {
                  const candidates = [...dropdown.querySelectorAll(
                    'li.ant-select-dropdown-menu-item, .ant-select-item-option, [role=option]'
                  )].filter(visible);
                  const exact = candidates.find(e => (e.innerText || '').replace(/\s/g, '') === expected);
                  if (exact) return exact;
                }
                return null;
                """,
                option_text,
            ),
            timeout=timeout,
            poll_frequency=.2,
        )
        if option is False or option is None:
            return False
        self.driver.execute_script("arguments[0].click();", option)
        time.sleep(0.2)
        return True

    def _set_authorized_user_role(self, role):
        """Assign the moved user to an explicit meeting role before saving."""
        value = "3" if role == "管理员" else "2"
        locator = (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{self.authorize_modal_title}']]"
            f"//div[contains(@class,'right-box-right')]//input[@type='radio' and @value='{value}']",
        )
        input_elements = self.driver.find_elements(*locator)
        input_element = input_elements[0] if input_elements else None
        if input_element is not None:
            try:
                if not input_element.is_selected():
                    label = input_element.find_element(by.XPATH, "ancestor::label[1]")
                    self.driver.execute_script("arguments[0].click();", label)
            except Exception:
                try:
                    self.driver.execute_script("arguments[0].click();", input_element)
                except Exception:
                    pass

        selected = bool(self.wait_until(lambda: self._authorized_user_role_selected(value), timeout=3))
        if not selected:
            diagnostics = self.driver.execute_script("""
              const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
              const modal = [...document.querySelectorAll('.ant-modal-content')].filter(visible)
                .find(e => (e.innerText || '').includes('会议室授权用户'));
              if (!modal) return [];
              return [...modal.querySelectorAll('*')]
                .filter(e => visible(e) && /管理员|参会者/.test(e.innerText || ''))
                .slice(-20)
                .map(e => ({tag: e.tagName, className: String(e.className || ''), text: (e.innerText || '').trim(), html: e.outerHTML.slice(0, 2000)}));
            """)
            allure.attach(
                json.dumps(diagnostics, ensure_ascii=False, indent=2),
                "授权角色控件诊断",
                allure.attachment_type.TEXT,
            )
        return selected

    def _authorized_user_role_selected(self, value):
        locator = (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{self.authorize_modal_title}']]"
            f"//div[contains(@class,'right-box-right')]//input[@type='radio' and @value='{value}']",
        )
        elements = self.driver.find_elements(*locator)
        for element in elements:
            try:
                if element.is_selected():
                    return True
                label_class = element.find_element(by.XPATH, "ancestor::label[1]").get_attribute("class") or ""
                if "checked" in label_class:
                    return True
            except Exception:
                continue
        return False

    def _authorize_left_user_rows(self):
        rows = self.driver.find_elements(*self._authorize_left_user_rows_locator())
        result = []
        for row in rows:
            try:
                if row.is_displayed() and "ant-table-measure-row" not in (
                    row.get_attribute("class") or ""
                ):
                    result.append(row)
            except Exception:
                continue
        return result

    def _authorize_left_row_by_username(self, username):
        for row in self._authorize_left_user_rows():
            if self._authorize_left_row_username(row) == username:
                return row
        return None

    def _authorize_left_row_username(self, row):
        try:
            username = self.driver.execute_script(
                "return arguments[0].querySelector('td:nth-child(3)')?.innerText || '';",
                row,
            )
        except Exception:
            return ""
        return str(username).strip()

    def _click_authorize_left_row_checkbox(self, row):
        try:
            checkbox = row.find_element(by.XPATH, ".//td[1]//input[@type='checkbox']")
            self.driver.execute_script("arguments[0].click();", checkbox)
            return True
        except Exception:
            return False

    def _authorize_modal_contains_username(self, username):
        rows = self.driver.find_elements(*self._authorize_right_user_rows_locator())
        for row in rows:
            try:
                if not row.is_displayed():
                    continue
                text = row.text or ""
                if username in text:
                    return True
            except Exception:
                continue
        return False

    def _close_authorize_modal(self):
        clicked = self._click_first_available_safe(
            [self._modal_action_button_locator(self.authorize_modal_title, self.close_button_text)],
            timeout=5,
        )
        return clicked and self._wait_for_visible_modal_closed(timeout=5)

    def _close_add_meeting_modal(self):
        return self._click_first_available_safe(
            [self._modal_action_button_locator(self.add_modal_title, self.close_button_text)],
            timeout=5,
        )

    def _sort_modal_rows(self):
        rows = self.driver.find_elements(*self._sort_modal_rows_locator())
        result = []
        for row in rows:
            try:
                if row.is_displayed():
                    result.append(row)
            except Exception:
                continue
        return result

    def _sort_row_username(self, row):
        try:
            username = self.driver.execute_script(
                "return arguments[0].querySelector('td:nth-child(2)')?.innerText || '';",
                row,
            )
        except Exception:
            return ""
        return str(username).strip()

    def _wait_sort_value_present(self, sort_value, timeout=5):
        end = time.time() + timeout
        while time.time() < end:
            rows = self._sort_modal_rows()
            for row in rows:
                try:
                    last_text = self.driver.execute_script(
                        "return arguments[0].querySelector('td:last-child')?.innerText || '';",
                        row,
                    )
                    if str(last_text).strip() == str(sort_value):
                        return True
                except Exception:
                    continue
            time.sleep(0.2)
        return False

    def _sort_modal_value_for_username(self, username):
        rows = []
        end = time.time() + 8
        while time.time() < end and not rows:
            rows = [row for row in self._sort_modal_rows() if self._sort_row_username(row)]
            if not rows:
                time.sleep(0.2)
        for row in rows:
            try:
                current_username = self._sort_row_username(row)
                if current_username != username:
                    continue
                value = self.driver.execute_script(
                    "return arguments[0].querySelector('td:last-child')?.innerText || '';",
                    row,
                )
                return str(value).strip()
            except Exception:
                continue
        return ""

    def _close_sort_modal(self):
        close_locator = (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            f"[.//div[contains(@class,'ant-modal-title') and normalize-space()='{self.sort_modal_title}']]"
            "//button[contains(@class,'ant-modal-close')]",
        )
        return self._click_first_available_safe([close_locator], timeout=5)

    def _go_to_next_result_page(self, timeout=5):
        buttons = self.driver.find_elements(*self.next_page_button)
        for button in buttons:
            try:
                if not button.is_displayed():
                    continue
                class_name = button.get_attribute("class") or ""
                if "disabled" in class_name:
                    return False
                current_page = self._get_visible_active_page_text()
                try:
                    button.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", button)
                end = time.time() + timeout
                while time.time() < end:
                    next_page = self._get_visible_active_page_text()
                    if next_page and next_page != current_page:
                        return True
                    time.sleep(0.2)
                return False
            except Exception:
                continue
        return False

    def _go_to_first_result_page(self, timeout=5):
        current_page = self._get_visible_active_page_text()
        if current_page in (None, "", "1"):
            return True

        buttons = self.driver.find_elements(*self.first_result_page_button)
        for button in buttons:
            try:
                if not button.is_displayed():
                    continue
                class_name = button.get_attribute("class") or ""
                if "active" in class_name:
                    return True
                try:
                    button.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", button)

                end = time.time() + timeout
                while time.time() < end:
                    active_page = self._get_visible_active_page_text()
                    if active_page == "1":
                        return True
                    time.sleep(0.2)
            except Exception:
                continue

        return self._get_visible_active_page_text() in (None, "", "1")

    def _find_exact_meeting_row_on_results_pages(self, meeting_name, max_pages=20):
        row_locator = self._exact_meeting_row_locator(meeting_name)
        for _ in range(max_pages):
            rows = self.driver.find_elements(*row_locator)
            for row in rows:
                try:
                    if row.is_displayed():
                        return True
                except Exception:
                    continue
            if not self._go_to_next_result_page(timeout=5):
                return False
        return False

    def _find_exact_meeting_row_globally(self, meeting_name, max_pages=20):
        self.reset_search()
        self._go_to_first_result_page(timeout=3)
        return self._find_exact_meeting_row_on_results_pages(
            meeting_name, max_pages=max_pages
        )

    def _find_exact_meeting_row_via_search(self, meeting_name):
        self._ensure_meeting_page_ready()
        self._search_keyword(meeting_name)
        if self.get_current_page_text() not in (None,'','1'):
            assert self._go_to_first_result_page(timeout=3), '会议室准确查询未恢复到第一页'
            self._search_keyword(meeting_name)
        # The query completion and stable render were already verified above.
        return self.find_visible_now(self._exact_meeting_row_locator(meeting_name)) is not False

    def _delete_visible_meeting_row(self, meeting_name):
        before_count = self.get_total_record_count()
        if not self._click_first_available_safe(
            [self._exact_meeting_delete_button_locator(meeting_name)], timeout=10
        ):
            return False
        if not self._click_first_available_safe([self.delete_sure_button_text], timeout=10):
            return False

        row_locator = self._exact_meeting_row_locator(meeting_name)
        evidence = self.wait_operation_evidence(
            [
                (
                    "row_absent",
                    lambda: self.wait_loading_finished(timeout=0.2)
                    and self.find_visible_now(row_locator) is False,
                ),
                (
                    "count_changed",
                    lambda: before_count is not None
                    and self.get_total_record_count() < before_count,
                ),
                ("toast", lambda: bool(self._first_visible_text(self.save_result))),
            ],
            timeout=6,
        )
        return evidence is not False

    def _ensure_meeting_absent_via_search(self, meeting_name, max_attempts=5):
        for _ in range(max_attempts):
            if not self._find_exact_meeting_row_via_search(meeting_name):
                return True
            if not self._delete_visible_meeting_row(meeting_name):
                return False
        return not self._find_exact_meeting_row_via_search(meeting_name)

    def _ensure_meeting_absent_globally(self, meeting_name, max_attempts=10):
        for _ in range(max_attempts):
            if not self._find_exact_meeting_row_globally(meeting_name):
                return True
            if not self._delete_visible_meeting_row(meeting_name):
                return False
        return not self._find_exact_meeting_row_globally(meeting_name)

    def _click_first_available_safe(self, locators, timeout=4):
        end = time.time() + timeout
        while time.time() < end:
            for locator in locators:
                elements = self.driver.find_elements(*locator)
                for element in elements:
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

    def _visible_in_any(self, locators, timeout=4):
        end = time.time() + timeout
        while time.time() < end:
            for locator in locators:
                elements = self.driver.find_elements(*locator)
                for element in elements:
                    try:
                        if element.is_displayed():
                            return True
                    except Exception:
                        continue
            time.sleep(0.2)
        return False

    def _dismiss_blocking_layers(self):
        self.dismiss_intro_if_present()
        for _ in range(5):
            modal = self.driver.execute_script(
                """
                const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
                return [...document.querySelectorAll('.ant-modal-content,.ant-drawer-content')]
                  .filter(visible).at(-1) || null;
                """
            )
            if modal is None:
                return True
            clicked = self.driver.execute_script(
                r"""
                const modal = arguments[0];
                const close = modal.querySelector('.ant-modal-close,.ant-drawer-close') ||
                  [...modal.querySelectorAll('button')].find(e =>
                    ['关闭','取消'].includes((e.innerText || '').replace(/\s+/g, '')));
                if (!close) return false;
                close.click(); return true;
                """,
                modal,
            )
            if not clicked:
                break
            self.wait_until(
                lambda: self.driver.execute_script(
                    "return !arguments[0].isConnected || getComputedStyle(arguments[0]).display === 'none' || "
                    "arguments[0].getBoundingClientRect().width === 0;",
                    modal,
                ),
                timeout=2,
                poll_frequency=0.1,
            )
        return self._wait_for_visible_modal_closed(timeout=2)

    def _is_sidebar_collapsed(self):
        menus = self.driver.find_elements(*self.sidebar_menu_root)
        for menu in menus:
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

    def _ensure_meeting_page_ready(self):
        ready_locators = [self.new_add_text, self.new_add]
        current_url = self.driver.current_url or ""
        if self.meeting_info_route.lstrip("#") in current_url and self._visible_in_any(
            ready_locators, timeout=2
        ):
            return self._wait_meeting_list_loaded(allow_cached=True)
        self._enter_meeting_info_via_route()
        if self._visible_in_any([self.new_add_text, self.new_add], timeout=8):
            return self._wait_meeting_list_loaded(allow_cached=True)
        return self.common_enter_meeting_info() and self._wait_meeting_list_loaded(allow_cached=True)

    def _wait_meeting_list_loaded(self, timeout=12,allow_cached=False):
        return wait_page_layout(self,self.meeting_info_route,[['会议室名称']],
            '.ant-tree-title,.ant-tree-node-content-wrapper,.el-tree-node__content,.custom-tree-node',
            timeout=timeout,allow_cached=allow_cached)
