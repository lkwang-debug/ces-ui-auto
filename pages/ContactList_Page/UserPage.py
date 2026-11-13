# -*- coding:utf-8 -*-
from pages.Index_Page.index import LoginPage
from selenium.webdriver.common.by import By as by
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import StaleElementReferenceException,ElementNotInteractableException,ElementClickInterceptedException,InvalidElementStateException
import re
import time
import json
import allure
from pathlib import Path

from common.runtime_artifacts import clean_directory, wait_for_download, prepare_download
from conf.conf import ConfigManager
from common.ui_state import wait_stable_state, wait_query_finished,wait_page_layout,wait_control_unobscured
from common.operation_metrics import timed_operation

class UserManagerPage(LoginPage):
    user_route = "#/ui/organizational-management/user-management"
    # 表现层
    # 閫氳褰?
    contactlist_button = (by.XPATH,"/html/body/div[1]/section/div/aside/div/ul/li[2]/div")
    contactlist_button_text = (
        by.XPATH,
        "//aside//li[contains(@class,'ant-menu-submenu')]"
        "//div[contains(@class,'ant-menu-submenu-title')]"
        "[.//span[normalize-space()='\u901a\u8baf\u5f55']]",
    )
    sidebar_menu_root = (by.CSS_SELECTOR, "aside ul.ant-menu, .ant-layout-sider ul.ant-menu")
    sidebar_expand_button = (
        by.CSS_SELECTOR,
        "aside .trigger.anticon-menu-unfold, .ant-layout-sider .trigger.anticon-menu-unfold, "
        ".ant-layout-sider [aria-label='menu-unfold']",
    )

    # 鐢ㄦ埛绠＄悊
    user_button = (by.XPATH,"/html/body/div/section/div/aside/div/ul/li[2]/ul/li[2]")
    user_button_alt = (by.XPATH,"/html/body/div[1]/section/div/aside/div/ul/li[2]/ul/li[2]")
    user_button_text = (
        by.XPATH,
        "//aside//li[contains(@class,'ant-menu-item')]"
        "[.//span[normalize-space()='\u7528\u6237\u7ba1\u7406']]",
    )

    # 瀹氫綅鏂板鐨勬寜閽?
    new_add = (by.XPATH,"/html/body/div[1]/section/section/main/div/div[2]/div/div[2]/div[2]/div[1]/button[1]")
    new_add_text = (
        by.XPATH,
        "//main//button[normalize-space(.)='新增' or contains(normalize-space(.),'新增')]",
    )

    # 瀹氫綅鏂板鍐呯殑鐢ㄦ埛濮撳悕
    user_name = (
        by.CSS_SELECTOR,
        ".ant-modal:not([style*='display: none']) .ant-modal-content input:nth-of-type(1), .ant-modal:not([style*='display: none']) .ant-modal-content input",
    )

    # 新增弹窗密码输入框
    code = (
        by.XPATH,
        "//div[contains(@class,'ant-modal') and not(contains(@style,'display: none'))]"
        "//div[contains(@class,'ant-modal-content')]"
        "//input[@type='password' or @type='Password' or @placeholder='密码']",
    )

    #鏂板鍐呰緭鍏ラ敊璇鍚嶇殑鎻愮ず娑堟伅
    wrong_user_name_msg = (
        by.CSS_SELECTOR,
        ".ant-modal:not([style*='display: none']) .ant-form-explain, .ant-modal:not([style*='display: none']) .ant-form-item-explain",
    )

    # 新增弹窗密码错误提示
    wrong_password_msg = (
        by.XPATH,
        "(//div[contains(@class,'ant-modal-content') and not(ancestor::*[contains(@style,'display: none')])]//*[contains(@class,'ant-form-explain') or contains(@class,'ant-form-item-explain')])[2]",
    )

    # 瀹氫綅鎵嬫満鍙风爜
    phone_number = (
        by.XPATH,
        "(//div[contains(@class,'ant-modal-content') and not(ancestor::*[contains(@style,'display: none')])]//input)[3]",
    )

    # 新增弹窗关闭按钮
    skip_button = (
        by.CSS_SELECTOR,
        ".ant-modal:not([style*='display: none']) .ant-modal-content "
        ".ant-modal-footer button.ant-btn:not(.ant-btn-primary), "
        ".ant-modal:not([style*='display: none']) .ant-modal-content button.ant-modal-close",
    )

    # 新增弹窗保存按钮
    save_button = (
        by.CSS_SELECTOR,
        ".ant-modal:not([style*='display: none']) .ant-modal-content "
        ".ant-modal-footer button.ant-btn-primary",
    )

    #淇濆瓨鍚庣殑缁撴灉
    save_result = (
        by.XPATH,
        "//div[contains(@class,'ant-message-notice-content')]"
        "//div[contains(@class,'ant-message-custom-content')]//span[normalize-space()]",
    )

    #瀹氫綅鐢ㄦ埛瀵煎嚭鎸夐挳
    export_user_button = (by.XPATH,"/html/body/div[1]/section/section/main/div/div[2]/div/div[2]/div[2]/div[1]/button[6]")
    export_user_button_text = (
        by.XPATH,
        "//main//button[normalize-space(.)='\u7528\u6237\u5bfc\u51fa']",
    )
    export_user_button_modern = (by.CSS_SELECTOR, "main button.left_userExport")
    export_user_modal = (
        by.XPATH,
        "//div[contains(@class,'ant-modal-content')]"
        "[.//div[contains(@class,'ant-modal-title') and normalize-space()='\u7528\u6237\u5bfc\u51fa']]",
    )
    export_first_organization_checkbox = (
        by.XPATH,
        "//div[contains(@class,'ant-modal-content')]"
        "[.//div[contains(@class,'ant-modal-title') and normalize-space()='\u7528\u6237\u5bfc\u51fa']]"
        "//ul[contains(@class,'ant-tree')]//span[contains(@class,'ant-tree-checkbox')][1]",
    )
    export_user_list_items = (
        by.XPATH,
        "//div[contains(@class,'ant-modal-content')]"
        "[.//div[contains(@class,'ant-modal-title') and normalize-space()='\u7528\u6237\u5bfc\u51fa']]"
        "//div[contains(@class,'user-export-right')]//ul/*[normalize-space()]",
    )
    export_confirm_button = (
        by.XPATH,
        "//div[contains(@class,'ant-modal-content')]"
        "[.//div[contains(@class,'ant-modal-title') and normalize-space()='\u7528\u6237\u5bfc\u51fa']]"
        "//button[normalize-space()='\u7528\u6237\u5bfc\u51fa']",
    )
    export_close_button = (
        by.XPATH,
        "//div[contains(@class,'ant-modal-content')]"
        "[.//div[contains(@class,'ant-modal-title') and normalize-space()='\u7528\u6237\u5bfc\u51fa']]"
        "//button[normalize-space()='\u5173 \u95ed' or normalize-space()='\u5173\u95ed']",
    )
    export_modal_close_icon = (
        by.XPATH,
        "//div[contains(@class,'ant-modal-content')]"
        "[.//div[contains(@class,'ant-modal-title') and normalize-space()='\u7528\u6237\u5bfc\u51fa']]"
        "//button[contains(@class,'ant-modal-close')]",
    )

    #瀹氫綅鐐瑰嚮鐢ㄦ埛瀵煎嚭鍚庡叏閮ㄩ儴闂ㄦ寜閽?
    select_all_organization = (by.XPATH,"/html/body/div[5]/div/div[2]/div/div[2]/div[2]/div/div[1]/ul/li/span[2]/span")


    #瀹氫綅鍕鹃€夊叏閮ㄩ儴闂ㄥ悗鐨勭敤鎴峰鍑烘寜閽?
    new_export_user_button = (by.XPATH,"/html/body/div[5]/div/div[2]/div/div[2]/div[2]/p/button[1]")

    #瀹氫綅鍏抽棴鐢ㄦ埛瀵煎嚭椤甸潰鐨勬寜閽?
    close_export_user_page = (by.XPATH,"/html/body/div[5]/div/div[2]/div/div[2]/button")

    #瀹氫綅鎼滅储鍐呭
    locate_search = (
        by.CSS_SELECTOR,
        "main input.ant-input",
    )

    # 搜索按钮
    search_button = (
        by.XPATH,
        "//main//input[contains(@class,'ant-input')]"
        "/ancestor::div[contains(@class,'ant-input-search') or contains(@class,'search')][1]"
        "//button | //main//input[contains(@class,'ant-input')]/following::button[1]",
    )

    #淇敼鐢ㄦ埛鏄电О
    modify_user_nickname = (
        by.XPATH,
        "//div[contains(@class,'ant-modal-content')]"
        "[.//div[contains(@class,'ant-modal-title') and normalize-space()='淇敼']]"
        "//input[@placeholder='鐢ㄦ埛鏄电О']",
    )

    # 修改弹窗保存按钮
    modify_save_button = (
        by.XPATH,
        "//div[contains(@class,'ant-modal-content')]"
        "[.//div[contains(@class,'ant-modal-title') and normalize-space()='淇敼']]"
        "//button[contains(., '淇濆瓨') or contains(., '淇?瀛?)]",
    )

    # 修改弹窗取消按钮
    modify_cancel_button = (
        by.XPATH,
        "//div[contains(@class,'ant-modal-content')]"
        "[.//div[contains(@class,'ant-modal-title') and normalize-space()='淇敼']]"
        "//button[contains(., '鍏抽棴') or contains(., '鍏?闂?)]",
    )

    #鐐瑰嚮鍒犻櫎鍚庣殑纭畾鎸夐挳
    delete_sure_button = (by.XPATH,"/html/body/div[8]/div/div[2]/div/div[2]/div/div/div[2]/button[2]")
    delete_sure_button_text = (
        by.CSS_SELECTOR,
        ".ant-modal-confirm .ant-modal-confirm-btns .ant-btn-primary,"
        ".ant-confirm .ant-modal-confirm-btns .ant-btn-primary,"
        ".ant-popover:not(.ant-popover-hidden) .ant-popover-buttons .ant-btn-primary",
    )
    delete_confirm_button_text = (
        by.CSS_SELECTOR,
        ".ant-popover:not(.ant-popover-hidden) .ant-popover-buttons button.ant-btn-primary,"
        ".ant-modal-confirm .ant-modal-confirm-btns button.ant-btn-primary,"
        ".ant-confirm .ant-modal-confirm-btns button.ant-btn-primary",
    )
    delete_confirm_button_css = (
        by.CSS_SELECTOR,
        ".ant-popover:not(.ant-popover-hidden) .ant-popover-buttons button.ant-btn-primary,"
        ".ant-modal-confirm .ant-modal-confirm-btns button.ant-btn-primary,"
        ".ant-confirm .ant-modal-confirm-btns button.ant-btn-primary",
    )

    #瀹氫綅鎵归噺鏂板鎸夐挳
    add_in_batches = (by.XPATH,"/html/body/div[1]/section/section/main/div/div[2]/div/div[2]/div[2]/div[1]/button[3]")
    add_in_batches_text = (
        by.XPATH,
        "//main//button[contains(normalize-space(.), '\u6279\u91cf\u65b0\u589e')]",
    )
    add_in_batches_modern = (by.CSS_SELECTOR, "main button.left_batchAdd")

    #瀹氫綅鎵归噺鏂板鍐呯敤鎴峰墠缂€
    user_prefix = (
        by.XPATH,
        "//div[contains(@class,'ant-modal-content')]"
        "[.//div[contains(@class,'ant-modal-title') and normalize-space()='鎵归噺鏂板']]"
        "//input[@placeholder='鐢ㄦ埛鍓嶇紑']",
    )

    #瀹氫綅鎵归噺鏂板鍐呯敤鎴锋暟閲?
    user_number = (
        by.XPATH,
        "//div[contains(@class,'ant-modal-content')]"
        "[.//div[contains(@class,'ant-modal-title') and normalize-space()='鎵归噺鏂板']]"
        "//input[@placeholder='鐢ㄦ埛鏁伴噺']",
    )

    #瀹氫綅鎵归噺鏂板鍐呯敤鎴峰瘑鐮?
    user_password = (
        by.XPATH,
        "//div[contains(@class,'ant-modal-content')]"
        "[.//div[contains(@class,'ant-modal-title') and normalize-space()='鎵归噺鏂板']]"
        "//input[@placeholder='瀵嗙爜']",
    )

    #瀹氫綅鎵归噺鏂板鍐呯‘璁ょ敤鎴峰瘑鐮?
    sure_user_password = (
        by.XPATH,
        "//div[contains(@class,'ant-modal-content')]"
        "[.//div[contains(@class,'ant-modal-title') and normalize-space()='鎵归噺鏂板']]"
        "//input[@placeholder='纭瀵嗙爜']",
    )

    #瀹氫綅鎵归噺鏂板鍐呯殑淇濆瓨鎸夐挳
    save_button_2 = (
        by.XPATH,
        "//div[contains(@class,'ant-modal-content')]"
        "[.//div[contains(@class,'ant-modal-title') and normalize-space()='鎵归噺鏂板']]"
        "//button[contains(., '淇濆瓨') or contains(., '淇?瀛?)]",
    )

    #瀹氫綅鍕鹃€夊叏閮ㄧ敤鎴风殑鎸夐挳
    select_all_user = (
        by.XPATH,
        "//table//thead//th[1]//span[contains(@class,'ant-checkbox')]",
    )

    #瀹氫綅鍒犻櫎鎸夐挳
    delete_button = (by.XPATH,"/html/body/div[1]/section/section/main/div/div[2]/div/div[2]/div[2]/div[1]/button[2]")
    delete_button_modern = (by.CSS_SELECTOR, "main button.left_delete")
    delete_button_text = (
        by.XPATH,
        "//main//button[normalize-space(.)='鍒犻櫎' or normalize-space(.)='鍒?闄?]",
    )

    #绗簩椤垫寜閽?
    second_page_button = (by.CSS_SELECTOR,".ant-pagination>li:nth-child(4)")

    #绗竴椤垫寜閽?
    first_page_button = (by.CSS_SELECTOR,".ant-pagination>li:nth-child(3)")

    data_num = (by.CSS_SELECTOR,".pagination-box>div:nth-child(2)>span")

    #椤垫暟鎸夐挳
    page_num_button = (by.CSS_SELECTOR,".ant-pagination-options>div>div>div>div")
    page_size_changer = (by.CSS_SELECTOR, ".ant-pagination-options-size-changer")
    page_size_value = (
        by.CSS_SELECTOR,
        ".ant-pagination-options-size-changer .ant-select-selection-selected-value,"
        ".ant-pagination-options-size-changer .ant-select-selection-item",
    )
    quick_jump_input = (by.CSS_SELECTOR, ".ant-pagination-options-quick-jumper input")
    active_page_num = (by.CSS_SELECTOR, ".ant-pagination-item-active")
    first_result_page_button = (by.CSS_SELECTOR, ".ant-pagination-item-1")
    next_page_button = (by.CSS_SELECTOR, ".ant-pagination-next")

    #10椤垫寜閽?
    ten_num = (by.CSS_SELECTOR,'.ant-select-dropdown-content>ul>li')

    fifteen_num = (by.CSS_SELECTOR,'.ant-select-dropdown-content>ul>li:nth-child(2)')

    twenty_num = (by.CSS_SELECTOR,'.ant-select-dropdown-content>ul>li:nth-child(3)')

    fifty_num = (by.CSS_SELECTOR, '.ant-select-dropdown-content>ul>li:nth-child(4)')


    # 操作层
    def wait_for_operation_result(self, expected_text=None, timeout=20):
        """
        Wait for toast style operation result.
        """
        if expected_text:
            return self.wait_text_contains(self.save_result, expected_text, timeout=timeout)
        return self.wait_visible(self.save_result, timeout=timeout) is not False

    @timed_operation
    def add_user(self, username, password, result, phone_number=None):
        self._dismiss_blocking_layers()
        self._ensure_user_page_ready()
        if not self._wait_user_list_loaded():
            raise AssertionError("用户列表和组织数据尚未加载完成")
        before_table = self.table_snapshot()
        dialog_ready = False
        for _ in range(2):
            if not self._click_first_available_safe([self.new_add_text, self.new_add], timeout=3):
                continue
            if self.wait_modal_state(True, timeout=5) and self.wait_until(
                lambda: self._visible_modal_field(
                    labels=('用户姓名', '用户名', '用户名称'),
                    field_ids=('form_item_username', 'form_item_userName'),
                    placeholders=('用户姓名', '用户名', '用户名称'),
                ),
                timeout=3,
                poll_frequency=0.1,
            ) is not False:
                dialog_ready = True
                break
            self._hard_reload_user_page()
        if not dialog_ready:
            raise AssertionError("Add user dialog did not appear")
        if not self._replace_visible_modal_field(
            labels=('用户姓名', '用户名', '用户名称'), value=username,
            field_ids=('form_item_username', 'form_item_userName'),
            placeholders=('用户姓名', '用户名', '用户名称'), timeout=3,
        ):
            raise AssertionError("Failed to fill username in add user dialog")
        if not self._replace_visible_modal_field(
            labels=('密码', '用户密码'), value=password,
            field_ids=('form_item_password',), placeholders=('密码', '请输入密码'), timeout=3,
        ):
            raise AssertionError("Failed to fill password in add user dialog")
        if phone_number is not None and not self._replace_visible_modal_field(
            labels=("手机号码", "手机号"),
            value=str(phone_number),
            field_ids=("form_item_phone", "form_item_mobile", "form_item_phoneNumber"),
            placeholders=("手机号码", "手机号", "请输入手机号码", "请输入手机号"),
            timeout=3,
        ):
            raise AssertionError("Failed to fill phone number in add user dialog")
        if not self.click_save_button():
            raise AssertionError("Failed to click save button in add user dialog")
        evidence = self.wait_operation_evidence(
            [
                ("toast", lambda: result in " ".join(self._visible_notice_texts())),
                ("modal_closed", lambda: not self._has_visible_modal_content()),
                ("table_changed", lambda: self.table_snapshot() != before_table),
            ],
            timeout=4,
        )
        if not evidence:
            self.click_cancel_button()
        found = self._find_exact_user_row_by_search(username, timeout=4)
        if not found:
            self.driver.refresh()
            self.wait_for_document_ready(timeout=5)
            self.wait_loading_finished(timeout=5)
            self._ensure_user_page_ready()
            found = self._find_exact_user_row_by_search(username, timeout=3)
        self._restore_list_state()
        return found

    def add_user_with_email(self, username, password, email, result="添加成功"):
        """Create a user with an email address for meeting notification tests."""
        self._dismiss_blocking_layers()
        self._ensure_user_page_ready()
        self.click_add_button()
        fields = (
            ("form_item_username", ("用户名", "用户名称", "用户姓名"), username),
            ("form_item_password", ("密码", "用户密码"), password),
            ("form_item_email", ("电子邮箱", "邮箱", "邮箱地址"), email),
        )
        populated = True
        for field_id, labels, value in fields:
            element = self.wait_until(
                lambda field_id=field_id, labels=labels: self.driver.execute_script(
                    r"""
                    const id = arguments[0];
                    const labels = arguments[1].map(value => String(value).replace(/\s+/g, ''));
                    const visible = node => !!(node && node.offsetParent !== null);
                    const direct = document.getElementById(id);
                    if (direct && visible(direct)) return direct;
                    const modal = [...document.querySelectorAll('.ant-modal-content')]
                      .filter(visible).at(-1);
                    const label = modal && [...modal.querySelectorAll('label')].find(node =>
                      visible(node) && labels.includes((node.innerText || '').replace(/\s+/g, '')));
                    return label?.closest('.ant-form-item')?.querySelector('input') || null;
                    """,
                    field_id,
                    list(labels),
                )
                or False,
                timeout=6,
                poll_frequency=0.2,
            )
            if element is False:
                populated = False
                break
            element.click()
            element.send_keys(Keys.CONTROL, "a")
            element.send_keys(Keys.DELETE)
            element.send_keys(str(value))
            element.send_keys(Keys.TAB)
            if (element.get_attribute("value") or "") != str(value):
                populated = False
                break
        if not populated or not self.click_save_button():
            self.click_cancel_button()
            return False
        if self.wait_for_operation_result(result, timeout=6):
            return True
        self.click_cancel_button()
        found = self._find_exact_user_row_by_search(username, timeout=4)
        self._restore_list_state()
        return found

    def _visible_notice_texts(self):
        try:
            return self.driver.execute_script("""
            const isVisible = (el) => {
                if (!el) return false;
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return style.display !== 'none'
                    && style.visibility !== 'hidden'
                    && rect.width > 0
                    && rect.height > 0;
            };
            return Array.from(document.querySelectorAll(
                '.ant-message-notice-content .ant-message-custom-content span,.layer_body'
            ))
                .filter(isVisible)
                .map(el => (el.innerText || el.textContent || '').trim())
                .filter(Boolean);
            """) or []
        except Exception:
            return []

    def _latest_operation_message(self, timeout=8, previous_messages=None):
        end = time.time() + timeout
        latest_text = ""
        previous_messages = set(previous_messages or [])
        while time.time() < end:
            for text in self._visible_notice_texts():
                latest_text = text
                if text not in previous_messages:
                    return text
            time.sleep(0.2)
        return "" if latest_text in previous_messages else latest_text

    def _visible_modal_text(self):
        try:
            return self.driver.execute_script("""
            const isVisible = (el) => {
                if (!el) return false;
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return style.display !== 'none'
                    && style.visibility !== 'hidden'
                    && rect.width > 0
                    && rect.height > 0;
            };
            const modals = Array.from(document.querySelectorAll('.ant-modal-content,.layer_body')).filter(isVisible);
            if (!modals.length) return '';
            return modals[modals.length - 1].innerText || '';
            """) or ""
        except Exception:
            return ""
    def add_duplicate_user_expect_failed(self, username, password):
        self._ensure_user_page_ready()
        self.reset_search()
        before_count = 1 if self._find_exact_user_row_by_search(username, timeout=1) else 0
        self.click_add_button()
        self.clear_by_javascript(self.user_name)
        self.clear_by_javascript(self.code)
        self.send_user_name(username)
        self.send_password(password)
        before_messages = self._visible_notice_texts()
        if not self.click_save_button():
            raise AssertionError("Failed to click save button in add user dialog")
        message_source = ""
        message = self._latest_operation_message(timeout=2, previous_messages=before_messages) or ""
        if message:
            message_source = "toast"
        if not message:
            form_message = self.get_element_text(self.wrong_user_name_msg, timeout=1) or ""
            message = form_message
            if message:
                message_source = "form"
        self.click_cancel_button()
        after_count = 1 if self._find_exact_user_row_by_search(username, timeout=1) else 0
        self._restore_list_state()
        count_unchanged = after_count == before_count
        return {
            "blocked": count_unchanged,
            "message": message,
            "message_source": message_source,
            "before_count": before_count,
            "after_count": after_count,
        }

    def get_wrong_user_name_msg(self):
        return self._visible_form_field_error("form_item_username") or self.get_element_text(
            self.wrong_user_name_msg, timeout=2
        )

    def get_wrong_password_msg(self):
        return self._visible_form_field_error("form_item_password") or self.get_element_text(
            self.wrong_password_msg, timeout=2
        )

    def visible_add_user_validation_errors(self):
        return self.driver.execute_script(
            """
            const visible=element=>!!(element&&(element.offsetWidth||element.offsetHeight||element.getClientRects().length));
            const result={};
            for (const item of [...document.querySelectorAll('.ant-modal-content .ant-form-item')].filter(visible)) {
              const label=(item.querySelector('label')?.innerText||'').replace(/[\s*：:]/g,'');
              const error=item.querySelector('.ant-form-item-explain-error,.ant-form-explain,[role=alert]');
              if (label && visible(error)) result[label]=(error.innerText||'').trim();
            }
            return result;
            """
        ) or {}

    def _visible_form_label_error(self, labels, timeout=2):
        end = time.time() + timeout
        while time.time() < end:
            text = self.driver.execute_script(
                """
                const expected=arguments[0];
                const visible=element=>!!(element&&(element.offsetWidth||element.offsetHeight||element.getClientRects().length));
                const labels=[...document.querySelectorAll('.ant-modal-content label')]
                  .filter(visible);
                const label=labels.find(item=>expected.includes((item.innerText||'').replace(/[\s*：:]/g,'')));
                const formItem=label?.closest('.ant-form-item');
                const error=formItem?.querySelector(
                  '.ant-form-item-explain-error,.ant-form-explain,[role=alert]');
                return visible(error) ? (error.innerText||'').trim() : '';
                """,
                [str(value).replace(" ", "") for value in labels],
            ) or ""
            if text:
                return text
            time.sleep(0.1)
        return ""

    def _visible_form_field_error(self, field_id, timeout=5):
        """Read the validation message owned by one field in Vue 2 or Vue 3 forms."""
        end = time.time() + timeout
        while time.time() < end:
            text = self.driver.execute_script(
                """
                const visible = element => !!(element && (
                  element.offsetWidth || element.offsetHeight || element.getClientRects().length));
                const field = [...document.querySelectorAll('#' + CSS.escape(arguments[0]))]
                  .filter(visible).at(-1);
                const item = field?.closest('.ant-form-item');
                if (!item) return '';
                const error = item.querySelector(
                  '.ant-form-item-explain-error,.ant-form-explain,.ant-form-item-explain,[role="alert"]'
                );
                return (error?.innerText || error?.textContent || '').trim();
                """,
                field_id,
            ) or ""
            if text:
                return text
            time.sleep(0.2)
        return ""

    def current_import_organization_path(self):
        """Return the current environment's root organization shown by the page."""
        self._ensure_user_page_ready()
        value = self.driver.execute_script(
            """
            const visible = el => !!(el && (el.offsetWidth || el.offsetHeight || el.getClientRects().length));
            const selectors = [
              'main .ant-tree-title', 'main .ant-tree-node-content-wrapper',
              'main .el-tree-node__content', 'main .custom-tree-node',
              '.organization-tree .el-tree-node__label',
              'main .department .name', 'main [class*="organization"] .name'
            ];
            for (const selector of selectors) {
              const candidates = [...document.querySelectorAll(selector)].filter(visible);
              for (const candidate of candidates) {
                const text = (candidate.innerText || candidate.textContent || '').trim();
                if (text && !['\u7ec4\u7ec7\u67b6\u6784', '\u7fa4\u7ec4'].includes(text)) return text;
              }
            }
            return '';
            """
        ) or ""
        return value or ConfigManager.IMPORT_ORGANIZATION_PATH

    def _select_export_organization(self, timeout=8):
        """Select the first visible organization in either export dialog implementation."""
        end = time.time() + timeout
        while time.time() < end:
            selected = self.driver.execute_script(
                """
                const visible = el => !!(el && (el.offsetWidth || el.offsetHeight || el.getClientRects().length));
                const dialogs = [...document.querySelectorAll('.ant-modal-content')].filter(visible);
                const modal = dialogs.find(el => (el.innerText || '').includes('\u7528\u6237\u5bfc\u51fa'));
                if (!modal) return false;
                const checkbox = [...modal.querySelectorAll('.ant-tree-checkbox,input[type="checkbox"]')].find(visible);
                if (!checkbox) return false;
                const wrapper = checkbox.classList?.contains('ant-tree-checkbox')
                  ? checkbox : checkbox.closest('.ant-tree-checkbox,.ant-checkbox');
                if (!(wrapper?.className || '').includes('checked') && !checkbox.checked) checkbox.click();
                return true;
                """
            )
            if selected:
                return True
            time.sleep(0.2)
        return False

    def click_add_button(self):
        self._ensure_user_page_ready()
        if not self._click_first_available_safe([self.new_add_text, self.new_add], timeout=5):
            raise AssertionError("Failed to open add user dialog")
        if self.wait_modal_state(True, timeout=3) is False:
            raise AssertionError("Add user dialog did not appear")

    def send_user_name(self,username):
        if not self._replace_visible_modal_field(labels=('用户姓名','用户名','用户名称'),field_ids=('form_item_username','form_item_userName'),
            placeholders=('用户姓名','用户名','请输入用户名'),value=username,timeout=5):
            raise AssertionError('用户名字段未保持目标输入')

    def send_password(self,password):
        if not self._replace_visible_modal_field(labels=('密码','用户密码'),field_ids=('form_item_password','form_item_userPassword'),
            placeholders=('密码','用户密码','请输入密码'),value=password,timeout=5):
            raise AssertionError('密码字段未保持目标输入')

    def send_phone_number(self,phone_number):
        if not self._replace_visible_modal_field(labels=('手机号码','手机号'),field_ids=('form_item_phone','form_item_mobile','form_item_phoneNumber'),
            placeholders=('手机号码','手机号','请输入手机号'),value=phone_number,timeout=5):
            raise AssertionError('手机号字段未保持目标输入')

    def click_save_button(self):
        # Scope the primary action to the open dialog first.  The page-level
        # locator is retained only for version-specific markup fallback.
        return self._click_visible_modal_button(primary=True, timeout=2) or self._click_first_available_safe([self.save_button], timeout=2)

    def click_cancel_button(self):
        clicked = self._click_visible_modal_button(
            primary=False, timeout=2
        ) or self._click_first_available_safe([self.skip_button], timeout=2)
        return bool(clicked and self.wait_modal_state(False, timeout=3))

    def export_user(self):
        self._ensure_user_page_ready()
        if not self._click_first_available_safe(
            [self.export_user_button_modern, self.export_user_button_text, self.export_user_button], timeout=5
        ):
            return False
        if self.wait_visible(self.export_user_modal, timeout=10) is False:
            return False
        if not self._select_export_organization(timeout=5):
            return False
        self._click_first_available_safe(
            [self.export_close_button, self.export_modal_close_icon], timeout=2
        ) or self._click_visible_modal_button(primary=False, timeout=2)
        self.wait_modal_state(False, timeout=3)
        if self._has_visible_modal_content():
            self._hard_reload_user_page()
        return self._visible_in_any(
            [
                self.new_add,
                self.new_add_text,
                self.add_in_batches,
                self.add_in_batches_text,
                self.locate_search,
            ],
            timeout=10,
        )

    def _active_user_modal(self):
        try:
            modal = self.driver.execute_script(
                r"""
                const visible = element => !!(element && (
                  element.offsetWidth || element.offsetHeight ||
                  element.getClientRects().length));
                return [...document.querySelectorAll('.ant-modal-content')]
                  .filter(visible).at(-1) || null;
                """
            )
            return modal if modal else False
        except Exception:
            return False

    def _wait_user_import_modal_ready(self, timeout=8):
        return self.wait_until(
            lambda: (
                (modal := self._active_user_modal()) is not False
                and bool(modal.find_elements(by.CSS_SELECTOR, "input[type='file']"))
                and (
                    "\u8986\u76d6" in (modal.text or "")
                    or bool(modal.find_elements(by.CSS_SELECTOR, ".ant-select"))
                )
                and modal
            ),
            timeout=timeout,
            poll_frequency=0.1,
        )

    def _prepare_user_modal_operation(self):
        """Restore a clean list before starting an independent modal flow."""
        if self._has_visible_modal_content():
            self._click_visible_modal_button(primary=False, timeout=2)
            self.wait_modal_state(False, timeout=2)
        if self._has_visible_modal_content():
            self._dismiss_blocking_layers()
        if self._has_visible_modal_content():
            self._hard_reload_user_page()
        if not self._ensure_user_page_ready():
            return False
        return self.wait_until(
            lambda: bool(self.driver.execute_script(
                r"""
                const visible = element => !!(element && (
                  element.offsetWidth || element.offsetHeight ||
                  element.getClientRects().length));
                return [...document.querySelectorAll('main tbody tr')].some(row =>
                  visible(row) && !row.classList.contains('ant-table-measure-row'));
                """
            )),
            timeout=10,
            poll_frequency=0.1,
        ) is not False

    # Support both Ant Design DOM generations with one implementation.
    def inspect_user_import_dialog(self):
        if not self._prepare_user_modal_operation():
            return None
        button = (
            by.XPATH,
            "//main//button[contains(normalize-space(.),'\u7528\u6237\u5bfc\u5165')]",
        )
        if not self._click_first_available_safe([button], timeout=5):
            return None
        if not self.wait_modal_state(True, timeout=8):
            return None
        modal = self._wait_user_import_modal_ready(timeout=8)
        if modal is False:
            return None
        modal_text = self.driver.execute_script(
            "return (arguments[0].innerText || arguments[0].textContent || '').trim();",
            modal,
        ) or ""
        result = {
            "text": " ".join(modal_text.split()),
            "accept": ",".join(
                element.get_attribute("accept") or ""
                for element in modal.find_elements(by.CSS_SELECTOR, "input[type='file']")
            ),
        }
        self._click_visible_modal_button(primary=False, timeout=3)
        self.wait_modal_state(False, timeout=3)
        return result

    @timed_operation
    def download_user_import_template(self):
        if not self._prepare_user_modal_operation():
            return None
        directory = prepare_download(self.driver)
        button = (
            by.XPATH,
            "//main//button[contains(normalize-space(.),'\u7528\u6237\u5bfc\u5165')]",
        )
        if not self._click_first_available_safe([button], timeout=5):
            return None
        if not self.wait_modal_state(True, timeout=8):
            return None
        modal = self._wait_user_import_modal_ready(timeout=8)
        if modal is False:
            return None
        link = (
            by.XPATH,
            "//div[contains(@class,'ant-modal-content')]"
            "//*[normalize-space()='\u4e0b\u8f7d\u6a21\u677f']",
        )
        if not self._click_first_available_safe([link], timeout=5):
            self._click_visible_modal_button(primary=False, timeout=2)
            return None
        downloaded = wait_for_download(directory, extensions={".xlsx", ".xls"}, driver=self.driver)
        self._click_visible_modal_button(primary=False, timeout=3)
        self.wait_modal_state(False, timeout=3)
        if downloaded is None:
            return None
        target_dir = Path(ConfigManager.IMPORT_TEMPLATE_DIR)/'user'
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / downloaded.name
        downloaded.replace(target)
        return target

    @timed_operation
    def import_user_workbook(self, workbook, overwrite=False, timeout=10):
        """Upload a generated workbook and wait for the import dialog to close."""
        self.last_import_error = ""
        if not self._prepare_user_modal_operation():
            self.last_import_error = "\u7528\u6237\u5217\u8868\u72b6\u6001\u672a\u6062\u590d"
            return False
        button = (
            by.XPATH,
            "//main//button[contains(normalize-space(.),'\u7528\u6237\u5bfc\u5165')]",
        )
        if not self._click_first_available_safe([button], timeout=5):
            self.last_import_error = "未找到用户导入按钮"
            return False
        modal_locator = (by.CSS_SELECTOR, ".ant-modal-content")
        modal = self._wait_user_import_modal_ready(timeout=12)
        if modal is False:
            self.last_import_error = "用户导入弹窗不可见"
            return False
        file_input = modal.find_element(by.CSS_SELECTOR, "input[type='file']")
        file_input.send_keys(str(Path(workbook).resolve()))
        # Selecting a file causes the upload component to re-render. Reacquire
        # the modal instead of retaining a stale Selenium element reference.
        filename = Path(workbook).name
        selected_file = wait_stable_state(
            self,
            lambda: self.driver.execute_script(
                """
                const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                const modal=[...document.querySelectorAll('.ant-modal-content')].filter(visible).at(-1);
                const input=modal?.querySelector('input[type=file]');
                // Ant Upload clears the native input after accepting a file;
                // its filename stays in the rendered upload list instead.
                const accepted=input?.files?.[0]?.name===arguments[0] ||
                  (modal?.innerText||'').includes(arguments[0]) ||
                  [...(modal?.querySelectorAll('[title],[data-file-name]')||[])].some(e=>
                    e.getAttribute('title')===arguments[0]||e.getAttribute('data-file-name')===arguments[0]);
                return accepted ? {file:arguments[0]} : null;
                """, filename,
            ), timeout=6,
        )
        if selected_file is False:
            self.last_import_error = "选择文件后表单未保留目标文件"
            return False
        # 4.39.7 renders this as an Ant select and defaults to “是”. Choose
        # the requested value explicitly so the non-overwrite case is real.
        option_text = "是" if overwrite else "否"
        def visible_option():
            return self.driver.execute_script(
                r"""
                const expected = String(arguments[0]).trim();
                const visible = element => !!(element && (
                  element.offsetWidth || element.offsetHeight ||
                  element.getClientRects().length));
                const dropdowns = [...document.querySelectorAll(
                  '.ant-select-dropdown,.ant-select-dropdown-menu')].filter(visible);
                const candidates = dropdowns.flatMap(dropdown =>
                  [...dropdown.querySelectorAll(
                    'li,.ant-select-item-option,.ant-select-dropdown-menu-item')]);
                return candidates.find(element => visible(element)
                  && (element.innerText || '').trim() === expected) || null;
                """,
                option_text,
            )

        option_element = False
        for _ in range(3):
            option_element = visible_option()
            if option_element:
                break
            modal = self._active_user_modal()
            if modal is None or modal is False:
                break
            select = modal.find_element(by.CSS_SELECTOR, ".ant-select")
            trigger = select.find_element(by.CSS_SELECTOR, ".ant-select-selection, .ant-select-selector")
            try:
                trigger.click()
            except Exception:
                self.driver.execute_script("arguments[0].click()", trigger)
            option_element = self.wait_until(visible_option, timeout=2, poll_frequency=0.1)
            if option_element is not False:
                break
        if not option_element:
            self.last_import_error = f"覆盖选项未找到: {option_text}"
            return False
        self.driver.execute_script("arguments[0].click()", option_element)
        selected = self.wait_until(
            lambda: self.driver.execute_script(
                """
                const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                const modal=[...document.querySelectorAll('.ant-modal-content')].filter(visible).at(-1);
                const value=modal?.querySelector('.ant-select-selection-selected-value,.ant-select-selection-item');
                return (value?.innerText||'').trim()===arguments[0];
                """, option_text,
            ), timeout=3,
        )
        if selected is False:
            self.last_import_error = f"覆盖选项未生效: {option_text}"
            return False
        self.driver.find_element(by.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        modal = self.wait_until(
            lambda: self._active_user_modal(),
            timeout=4,
            poll_frequency=0.1,
        )
        if modal is False:
            self.last_import_error = "选择覆盖选项后导入弹窗消失"
            return False
        before_messages = self._visible_notice_texts()
        started=self.driver.execute_script('return performance.now()')
        if not self._click_visible_modal_button(primary=True, timeout=5):
            self.last_import_error = "未找到导入确认按钮"
            return False
        result_text = self.wait_until(
            lambda: next(
                (
                    text for text in self._visible_notice_texts()
                    if text not in before_messages
                    and any(word in text for word in ("\u6210\u529f", "\u5931\u8d25", "\u9519\u8bef"))
                ),
                False,
            )
            or (
                self._visible_modal_text()
                if any(
                    word in self._visible_modal_text()
                    for word in ("\u6210\u529f", "\u5931\u8d25", "\u9519\u8bef")
                )
                else False
            ),
            timeout=timeout,
            poll_frequency=.2,
        )
        import allure
        allure.attach(str({'文件':filename,'覆盖选项':option_text,'导入结果':result_text or '提示未保留，继续校验本次请求和持久化数据'}),
            '用户实际导入结果',allure.attachment_type.TEXT)
        if result_text is False:
            completed_without_toast = (
                not self._has_visible_modal_content()
                and wait_query_finished(self,started,timeout=5)
            )
            if not completed_without_toast:
                self.last_import_error = (
                    "\u5bfc\u5165\u540e\u672a\u51fa\u73b0\u660e\u786e\u7ed3\u679c\u63d0\u793a\uff0c"
                    f"\u5f39\u7a97\u5185\u5bb9: {self._visible_modal_text()!r}"
                )
                return False
            return True
        if "\u5931\u8d25" in result_text or "\u9519\u8bef" in result_text:
            self.last_import_error = result_text
            self._dismiss_import_result()
            return False
        return self._dismiss_import_result()

    def _dismiss_import_result(self):
        self.driver.execute_script(
            """
            const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
            for(const layer of [...document.querySelectorAll('.layer_body,.ant-modal-content')].filter(visible).reverse()){
              if(layer.querySelector('input,select,textarea')||!(/导入/.test(layer.innerText||'')))continue;
              const button=[...layer.querySelectorAll('button')].find(e=>visible(e)&&!e.disabled&&
                ['知道了','确定','关闭'].includes((e.innerText||'').replace(/\s/g,'')));
              button?.click();
            }
            """
        )
        return self.wait_until(lambda:not self._has_visible_modal_content(),timeout=4) is not False

    @timed_operation
    def download_user_export(self):
        self._ensure_user_page_ready()
        directory = prepare_download(self.driver)
        existing = {path.name for path in directory.iterdir()}
        if not self._click_first_available_safe(
            [self.export_user_button_modern, self.export_user_button_text, self.export_user_button], timeout=5
        ):
            return None
        if self.wait_visible(self.export_user_modal, timeout=8) is False:
            return None
        if not self._select_export_organization(timeout=5):
            return None
        if not self._click_first_available_safe([self.export_confirm_button], timeout=5):
            return None
        downloaded = wait_for_download(directory, existing, {".xlsx", ".xls", ".csv"}, driver=self.driver)

        # The export dialog remains open in 4.39.7 after the file is generated.
        # Close it before the next test operates on the user list.
        self._dismiss_blocking_layers()
        if self._visible_in_any([self.export_user_modal], timeout=1):
            self._hard_reload_user_page()
        return downloaded

    def _exact_user_row_locator(self, username):
        return (
            by.XPATH,
            "//table//tbody//tr["
            f"td[3][normalize-space()='{username}'] or "
            f"td[6][normalize-space()='{username}']"
            "]",
        )

    def _exact_user_delete_button_locator(self, username):
        return (
            by.XPATH,
            "//table//tbody//tr["
            f"td[3][normalize-space()='{username}'] or "
            f"td[6][normalize-space()='{username}']"
            "]//td[last()]//button[3]",
        )

    def _exact_user_modify_button_locator(self, username):
        return (
            by.XPATH,
            "//table//tbody//tr["
            f"td[3][normalize-space()='{username}'] or "
            f"td[6][normalize-space()='{username}']"
            "]//td[last()]//button[2]",
        )

    def _exact_user_nickname_cell_locator(self, username):
        return (
            by.XPATH,
            "//table//tbody//tr["
            f"td[3][normalize-space()='{username}'] or "
            f"td[6][normalize-space()='{username}']"
            "]/td[6]",
        )

    def _keyword_user_row_locator(self, keyword):
        return (
            by.XPATH,
            f"//table//tbody//tr[.//td[contains(normalize-space(),'{keyword}')]]",
        )

    def _search_keyword(self, keyword):
        # Readiness includes headers, organization tree, loading and a stable
        # table snapshot. A completed empty result is also a valid start state.
        if not self._ensure_user_page_ready():
            return False
        search_input = wait_control_unobscured(self,
            lambda: self.driver.execute_script(
                r"""
                const visible = element => !!(element && (
                  element.offsetWidth || element.offsetHeight ||
                  element.getClientRects().length));
                const inputs = [...document.querySelectorAll('main input.ant-input')]
                  .filter(visible);
                return inputs.find(input =>
                  /\u641c\u7d22|\u8bf7\u8f93\u5165/.test(input.placeholder || ''))
                  || inputs.at(-1) || null;
                """
            ),
            timeout=8,
            poll_frequency=0.1,
        )
        if search_input is False:
            self._hard_reload_user_page()
            return False
        before_table = self.table_snapshot()
        self.last_user_search_debug = {
            "keyword": str(keyword),
            "input_placeholder": search_input.get_attribute("placeholder") or "",
            "before_table": before_table,
        }
        try:
            search_input.click()
            search_input.send_keys(Keys.CONTROL, "a")
            search_input.send_keys(Keys.DELETE)
            search_input.send_keys(str(keyword))
            started = self.driver.execute_script('return performance.now()')
            clicked = self.driver.execute_script(
                r"""
                const input = arguments[0];
                const visible = element => !!(element && (
                  element.offsetWidth || element.offsetHeight ||
                  element.getClientRects().length));
                let scope = input;
                let button = null;
                for (let depth = 0; depth < 6 && scope && !button; depth += 1) {
                  scope = scope.parentElement;
                  button = [...(scope?.querySelectorAll('button') || [])]
                    .find(visible) || null;
                }
                if (!button) {
                  const inputRect = input.getBoundingClientRect();
                  button = [...document.querySelectorAll('main button')]
                    .filter(visible)
                    .map(element => ({element, rect: element.getBoundingClientRect()}))
                    .filter(item => Math.abs(item.rect.top - inputRect.top) < 20
                      && item.rect.left >= inputRect.right - 5
                      && item.rect.left - inputRect.right < 100)
                    .sort((left, right) => left.rect.left - right.rect.left)[0]?.element || null;
                }
                if (!button) return false;
                button.click();
                return true;
                """,
                search_input,
            )
            if not clicked:
                search_input.send_keys(Keys.ENTER)
            self.last_user_search_debug["trigger_clicked"] = bool(clicked)
        except Exception:
            self.last_user_search_debug["trigger_clicked"] = False
            return False

        query_completed = wait_query_finished(self, started, timeout=8, request_path='/basis/v1/userInfo/queryUserPage')
        current_value = self.driver.execute_script(
            r"""
            const visible = element => !!(element && (
              element.offsetWidth || element.offsetHeight ||
              element.getClientRects().length));
            const inputs = [...document.querySelectorAll('main input.ant-input')]
              .filter(visible);
            const input = inputs.find(item =>
              /\u641c\u7d22|\u8bf7\u8f93\u5165/.test(item.placeholder || ''))
              || inputs.at(-1);
            return input?.value || '';
            """
        ) or ""
        self.last_user_search_debug.update({
            "input_value": current_value,
            "after_table": self.table_snapshot(),
            "query_completed": query_completed,
        })
        return query_completed and self.last_user_search_debug["input_value"] == str(keyword)

    def _ensure_select_all_checked(self, timeout=5):
        checkbox = self.wait_visible(self.select_all_user, timeout=timeout)
        if checkbox is False:
            return False
        class_name = checkbox.get_attribute("class") or ""
        if "checked" in class_name:
            return True
        if not self._click_first_available_safe([self.select_all_user], timeout=timeout):
            return False
        time.sleep(0.5)
        checkbox = self.wait_visible(self.select_all_user, timeout=timeout)
        if checkbox is False:
            return False
        class_name = checkbox.get_attribute("class") or ""
        return "checked" in class_name

    def _replace_input_value(self, locator, value, timeout=10):
        element = self.wait_visible(locator, timeout)
        if element is False:
            return False
        try:
            element.click()
            element.send_keys(Keys.CONTROL, "a")
            element.send_keys(Keys.DELETE)
            time.sleep(0.2)
            element.send_keys(str(value))
        except Exception:
            self.clear_by_javascript(locator)
            self.send_keys(locator, value)
            element = self.wait_visible(locator, timeout)
            if element is False:
                return False
        time.sleep(0.2)
        current_value = element.get_attribute("value") or ""
        return current_value == str(value)

    def _visible_modal_input(self, placeholder=None, index=0):
        script = """
        const placeholder = arguments[0];
        const index = arguments[1];
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
        if (!modals.length) return null;
        const modal = modals[modals.length - 1];
        const inputs = Array.from(modal.querySelectorAll('input')).filter(isVisible);
        if (placeholder) {
            const exact = inputs.find((input) => input.getAttribute('placeholder') === placeholder);
            if (exact) return exact;
            const partial = inputs.find((input) => String(input.getAttribute('placeholder') || '').includes(placeholder));
            if (partial) return partial;
        }
        return inputs[index] || null;
        """
        try:
            element = self.driver.execute_script(script, placeholder, index)
            return element if element else False
        except Exception:
            return False

    def _visible_modal_field(self, labels=(), field_ids=(), placeholders=()):
        """Find one field semantically inside the topmost visible modal."""
        try:
            element = self.driver.execute_script(
                r"""
                const expectedLabels = arguments[0].map(value =>
                  String(value).replace(/[\s*：:]/g, ''));
                const fieldIds = arguments[1];
                const placeholders = arguments[2].map(value => String(value));
                const visible = element => !!(element && (
                  element.offsetWidth || element.offsetHeight || element.getClientRects().length));
                const modal = [...document.querySelectorAll('.ant-modal-content')]
                  .filter(visible).at(-1);
                if (!modal) return null;
                for (const fieldId of fieldIds) {
                  const field = modal.querySelector('#' + CSS.escape(fieldId));
                  if (visible(field)) return field;
                }
                for (const item of [...modal.querySelectorAll('.ant-form-item')].filter(visible)) {
                  const label = (item.querySelector('label')?.innerText || '')
                    .replace(/[\s*：:]/g, '');
                  if (!expectedLabels.includes(label)) continue;
                  const field = [...item.querySelectorAll('input,textarea')].find(visible);
                  if (field) return field;
                }
                const inputs = [...modal.querySelectorAll('input,textarea')].filter(visible);
                return inputs.find(field => {
                  const placeholder = field.getAttribute('placeholder') || '';
                  return placeholders.some(value =>
                    placeholder === value || placeholder.includes(value));
                }) || null;
                """,
                list(labels),
                list(field_ids),
                list(placeholders),
            )
            return element if element else False
        except Exception:
            return False

    def _replace_visible_modal_field(
        self, labels, value, field_ids=(), placeholders=(), timeout=5
    ):
        end = time.time() + timeout
        self.last_field_input_debug={'字段':list(labels),'期望长度':len(str(value)),'尝试次数':0}
        while time.time() < end:
            element = self._visible_modal_field(
                labels=labels, field_ids=field_ids, placeholders=placeholders
            )
            try:
                if element is False or not element.is_displayed() or not element.is_enabled() or element.get_property('readOnly'):
                    time.sleep(0.1)
                    continue
                self.last_field_input_debug.update(控件ID=element.get_attribute('id'),控件类型=element.get_attribute('type'))
                self.last_field_input_debug['尝试次数']+=1
                element.click()
                element.send_keys(Keys.CONTROL, "a")
                element.send_keys(Keys.DELETE)
                element.send_keys(str(value))
                element.send_keys(Keys.TAB)
            except (StaleElementReferenceException,ElementNotInteractableException,ElementClickInterceptedException,InvalidElementStateException) as error:
                self.last_field_input_debug['重绘异常']=type(error).__name__
                time.sleep(0.05)
                continue
            def committed():
                current=self._visible_modal_field(labels=labels,field_ids=field_ids,placeholders=placeholders)
                if current is False:return False
                actual=current.get_attribute('value') or ''
                self.last_field_input_debug['实际长度']=len(actual)
                return {'committed':True} if actual==str(value) else False
            matched=wait_stable_state(self,committed,timeout=min(1,max(0.1,end-time.time())),stable_for=0.2)
            if matched is not False:
                return True
        allure.attach(json.dumps(self.last_field_input_debug,ensure_ascii=False),'字段输入失败诊断（仅长度与控件信息）',allure.attachment_type.JSON)
        return False

    def _read_visible_modal_field(
        self, labels, field_ids=(), placeholders=(), timeout=4
    ):
        element = self.wait_until(
            lambda: self._visible_modal_field(
                labels=labels, field_ids=field_ids, placeholders=placeholders
            ),
            timeout=timeout,
            poll_frequency=0.1,
        )
        if element is False:
            return None
        return element.get_attribute("value") or ""

    def _replace_visible_modal_input(self, placeholder, value, timeout=5, index=0):
        end = time.time() + timeout
        element = False
        while time.time() < end:
            element = self._visible_modal_input(placeholder=placeholder, index=index)
            if element is not False:
                break
            time.sleep(0.2)
        if element is False:
            return False
        try:
            element.click()
            element.send_keys(Keys.CONTROL, "a")
            element.send_keys(Keys.DELETE)
            time.sleep(0.1)
            element.send_keys(str(value))
            element.send_keys(Keys.TAB)
        except Exception:
            try:
                self.driver.execute_script(
                    """
                    arguments[0].value = arguments[1];
                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                    """,
                    element,
                    str(value),
                )
            except Exception:
                return False
        time.sleep(0.1)
        return (element.get_attribute("value") or "") == str(value)

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
                        time.sleep(0.5)
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
                        time.sleep(0.5)
                        return True
                    time.sleep(0.2)
            except Exception:
                continue

        return self._get_visible_active_page_text() in (None, "", "1")

    def _find_exact_user_row_on_results_pages(self, username, max_pages=20):
        row_locator = self._exact_user_row_locator(username)
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

    def _find_exact_user_row_on_current_page(self, username):
        row_locator = self._exact_user_row_locator(username)
        rows = self.driver.find_elements(*row_locator)
        for row in rows:
            try:
                if row.is_displayed():
                    return True
            except Exception:
                continue
        return False

    def _wait_for_exact_user_row_on_current_page(self, username, timeout=3):
        end = time.time() + timeout
        while time.time() < end:
            if self._find_exact_user_row_on_current_page(username):
                return True
            time.sleep(0.2)
        return False

    def _find_exact_user_row_element_on_results_pages(self, username, max_pages=20):
        row_locator = self._exact_user_row_locator(username)
        for _ in range(max_pages):
            rows = self.driver.find_elements(*row_locator)
            for row in rows:
                try:
                    if row.is_displayed():
                        return row
                except Exception:
                    continue
            if not self._go_to_next_result_page(timeout=5):
                return None
        return None

    def _find_exact_user_row_element_on_current_page(self, username):
        # Column positions differ between the legacy and modern user tables.
        # Match the exact cell value rather than binding row lookup to td[3].
        try:
            row = self.driver.execute_script(
                r"""
                const expected = String(arguments[0]).trim();
                const visible = element => !!(element && (
                  element.offsetWidth || element.offsetHeight ||
                  element.getClientRects().length));
                for (const table of [...document.querySelectorAll('main table')].filter(visible)) {
                  const rows = [...table.querySelectorAll('tbody tr')].filter(visible);
                  if (!rows.length) continue;
                  let headers = [...table.querySelectorAll('thead th')];
                  if (!headers.length) {
                    // Ant Design can render fixed headers in a separate table.
                    const wrapper = table.closest('.ant-table-wrapper') || document.querySelector('main');
                    const count = rows[0].querySelectorAll('td').length;
                    headers = [...wrapper.querySelectorAll('table')].filter(visible)
                      .map(header => [...header.querySelectorAll('thead th')])
                      .find(items => items.length === count) || [];
                  }
                  const column = headers.findIndex(th =>
                    ['用户名','用户姓名','用户名称'].includes((th.innerText || '').trim()));
                  if (column < 0) continue;
                  const row = rows.find(tr =>
                    (tr.querySelectorAll('td')[column]?.innerText || '').trim() === expected);
                  if (row) return row;
                }
                return null;
                """,
                str(username),
            )
            return row if row else None
        except Exception:
            row_locator = self._exact_user_row_locator(username)
            for row in self.driver.find_elements(*row_locator):
                try:
                    if row.is_displayed():
                        return row
                except Exception:
                    continue
            return None

    def _click_user_row_action(self, username, action, timeout=5):
        """Click an operation in an exact user's row across UI versions."""
        end = time.time() + timeout
        while time.time() < end:
            row = self._find_exact_user_row_element_on_current_page(username)
            if row is None:
                time.sleep(0.1)
                continue
            try:
                buttons = [
                    item for item in row.find_elements(
                        by.CSS_SELECTOR, "td:last-child button,td:last-child a"
                    ) if item.is_displayed()
                ]
                keywords = {
                    "modify": ("\u4fee\u6539", "edit"),
                    "delete": ("\u5220\u9664", "delete"),
                }[action]
                candidate = None
                for item in buttons:
                    evidence = " ".join(filter(None, [
                        item.text,
                        item.get_attribute("title"),
                        item.get_attribute("aria-label"),
                        item.get_attribute("class"),
                    ])).lower()
                    if any(keyword.lower() in evidence for keyword in keywords):
                        candidate = item
                        break
                if candidate is None:
                    fallback_index = 1 if action == "modify" else 2
                    if len(buttons) > fallback_index:
                        candidate = buttons[fallback_index]
                if candidate is not None:
                    self.driver.execute_script("arguments[0].click()", candidate)
                    return True
            except Exception:
                pass
            time.sleep(0.1)
        return False

    def _wait_for_exact_user_row_element_on_current_page(self, username, timeout=3):
        end = time.time() + timeout
        while time.time() < end:
            row = self._find_exact_user_row_element_on_current_page(username)
            if row is not None:
                return row
            time.sleep(0.2)
        return None

    def _wait_for_exact_user_row_absent_on_current_page(self, username, timeout=5):
        end = time.time() + timeout
        while time.time() < end:
            if not self._find_exact_user_row_on_current_page(username):
                return True
            time.sleep(0.2)
        return False

    def _get_row_cell_texts(self, row):
        try:
            cells = row.find_elements(by.XPATH, "./td")
        except Exception:
            return []
        values = []
        for cell in cells:
            try:
                values.append((cell.text or "").strip())
            except Exception:
                values.append("")
        return values

    def _get_exact_user_row_cells_globally(self, username, max_pages=30):
        row = self._find_exact_user_row_element_with_search_priority(
            username,
            short_scan_pages=min(2, max_pages),
            allow_global_fallback=True,
            max_pages=max_pages,
        )
        if row is None:
            return []
        return self._get_row_cell_texts(row)

    def _restore_list_state(self):
        self.reset_search()
        self._go_to_first_result_page(timeout=3)
        return True

    def _get_visible_active_page_text(self):
        for element in self.driver.find_elements(*self.active_page_num):
            try:
                if element.is_displayed():
                    return (element.text or "").strip()
            except Exception:
                continue
        return None

    def _find_exact_user_row_globally(self, username, max_pages=30):
        return self._find_exact_user_row_with_search_priority(
            username,
            short_scan_pages=min(2, max_pages),
            allow_global_fallback=True,
            max_pages=max_pages,
        )

    def _find_exact_user_row_element_with_search_priority(
        self, username, short_scan_pages=1, allow_global_fallback=False, max_pages=30
    ):
        self._ensure_user_page_ready()
        row = self._find_exact_user_row_element_on_current_page(username)
        if row is not None:
            return row

        if self._search_keyword(username):
            row = self._find_exact_user_row_element_on_current_page(username)
            if row is not None:
                return row

            if self._get_visible_active_page_text() not in (None,'','1'):
                assert self._go_to_first_result_page(timeout=3), '用户准确查询未恢复到第一页'
                assert self._search_keyword(username), '用户准确查询请求未完成'
                row = self._find_exact_user_row_element_on_current_page(username)
                if row is not None:return row

            if short_scan_pages > 1:
                row = self._find_exact_user_row_element_on_results_pages(
                    username, max_pages=short_scan_pages
                )
                if row is not None:
                    return row

        if not allow_global_fallback:
            return None

        self.reset_search()
        self._go_to_first_result_page(timeout=3)
        row = self._wait_for_exact_user_row_element_on_current_page(username, timeout=1.5)
        if row is not None:
            return row
        return self._find_exact_user_row_element_on_results_pages(
            username, max_pages=max_pages
        )

    def _find_exact_user_row_with_search_priority(
        self, username, short_scan_pages=1, allow_global_fallback=False, max_pages=30
    ):
        row = self._find_exact_user_row_element_with_search_priority(
            username,
            short_scan_pages=short_scan_pages,
            allow_global_fallback=allow_global_fallback,
            max_pages=max_pages,
        )
        return row is not None

    def _find_exact_user_row_element_by_search(self, username, timeout=2):
        self._ensure_user_page_ready()
        if not self._search_keyword(username):
            raise AssertionError('用户准确查询请求未完成，禁止判定不存在')
        if self._get_visible_active_page_text() not in (None,'','1'):
            assert self._go_to_first_result_page(timeout=2), '用户查询未到第一页'
            assert self._search_keyword(username), '用户查询请求未完成'
        return self._find_exact_user_row_element_on_current_page(username)

    def _find_exact_user_row_by_search(self, username, timeout=2):
        return self._find_exact_user_row_element_by_search(
            username, timeout=timeout
        ) is not None

    @timed_operation
    def search_user(self, search_text):
        self._ensure_user_page_ready()
        found = self._find_exact_user_row_by_search(search_text, timeout=3)
        self._restore_list_state()
        return found

    def search_users_by_keyword(self, keyword):
        """Return whether a prefix search displays only rows created for it."""
        self._ensure_user_page_ready()
        if not self._search_keyword(keyword):
            return False
        row_locator = self._keyword_user_row_locator(keyword)
        found = self._visible_in_any([row_locator], timeout=5)
        self.reset_search()
        return found

    def _open_modify_user_dialog(self, username):
        self.last_open_profile_debug = {"username": username, "stage": "page_ready"}
        self._ensure_user_page_ready()
        if not self._find_exact_user_row_by_search(username, timeout=8):
            self.last_open_profile_debug.update({
                "stage": "row_search",
                "table": self.table_snapshot(),
                "search": getattr(self, "last_user_search_debug", None),
            })
            self._restore_list_state()
            return False
        self.last_open_profile_debug["stage"] = "row_found"
        started=self.driver.execute_script('return performance.now()')
        if not self._click_user_row_action(username, "modify", timeout=6):
            self.last_open_profile_debug["stage"] = "modify_action"
            self._restore_list_state()
            return False
        self.last_open_profile_debug["stage"] = "modify_clicked"
        if not self.wait_modal_state(True, timeout=4):
            self.last_open_profile_debug["stage"] = "modal_not_visible"
            return False
        self.last_open_profile_debug["stage"] = "modal_visible"
        if not wait_query_finished(self,started,timeout=8,request_path='/basis/v1/userInfo/userEdit'):
            self.last_open_profile_debug['stage']='edit_request_not_completed'
            self.last_open_profile_debug['request_paths']=self.driver.execute_script(
                "return performance.getEntriesByType('resource').filter(e=>e.startTime>=arguments[0]&&['fetch','xmlhttprequest'].includes(e.initiatorType)).map(e=>new URL(e.name,location.href).pathname)",started)
            return False
        def hydrated_fields():
            actual=self._read_visible_modal_field(
                labels=("用户姓名", "用户名", "用户名称"),
                field_ids=("form_item_username", "form_item_userName"),
                placeholders=("用户姓名", "用户名", "请输入用户名"),
                timeout=0.2,
            )
            if actual!=username:return False
            return {'username':actual,'nickname':self._read_visible_modal_field(labels=('用户昵称','昵称'),
                field_ids=('form_item_nickname','form_item_userNickname'),placeholders=('用户昵称','昵称','请输入用户昵称','请输入昵称'),timeout=0.2),
                'phone':self._read_visible_modal_field(labels=('手机号码','手机号'),
                field_ids=('form_item_phone','form_item_mobile','form_item_phoneNumber'),placeholders=('手机号码','手机号','请输入手机号'),timeout=0.2)}
        hydrated = wait_stable_state(self,hydrated_fields,timeout=5,stable_for=0.2)
        if hydrated is False:
            self.last_open_profile_debug.update({
                "stage": "username_not_hydrated",
                "modal_text": self._visible_modal_text(),
            })
            self._click_visible_modal_button(primary=False, timeout=1)
            self.wait_modal_state(False, timeout=2)
            return False
        self.last_open_profile_debug["stage"] = "ready"
        return True

    def _replace_modify_nickname(self, nickname):
        return self._replace_visible_modal_field(
            labels=("用户昵称", "昵称"),
            value=nickname,
            field_ids=("form_item_nickname", "form_item_userNickname"),
            placeholders=("用户昵称", "昵称", "请输入用户昵称", "请输入昵称"),
            timeout=5,
        )

    def _replace_modify_phone(self, phone_number):
        return self._replace_visible_modal_field(
            labels=("手机号码", "手机号"),
            value=str(phone_number),
            field_ids=("form_item_phone", "form_item_mobile", "form_item_phoneNumber"),
            placeholders=("手机号码", "手机号", "请输入手机号码", "请输入手机号"),
            timeout=5,
        )

    def read_user_profile(
        self, username, refresh=False, expected_phone=None, expected_nickname=None
    ):
        """Read persisted nickname and phone from the real modify dialog."""
        if refresh:
            self.driver.refresh()
            self.wait_for_document_ready(timeout=5)
            self.wait_loading_finished(timeout=5)
        if not self._open_modify_user_dialog(username):
            return None
        try:
            def snapshot():
                profile = {
                    "nickname": self._read_visible_modal_field(
                        labels=("用户昵称", "昵称"),
                        field_ids=("form_item_nickname", "form_item_userNickname"),
                        placeholders=("用户昵称", "昵称", "请输入用户昵称", "请输入昵称"),
                        timeout=0.2,
                    ),
                    "phone_number": self._read_visible_modal_field(
                        labels=("手机号码", "手机号"),
                        field_ids=("form_item_phone", "form_item_mobile", "form_item_phoneNumber"),
                        placeholders=("手机号码", "手机号", "请输入手机号码", "请输入手机号"),
                        timeout=0.2,
                    ),
                    "errors": self.visible_add_user_validation_errors(),
                }
                if expected_phone is not None and profile["phone_number"] != str(
                    expected_phone
                ):
                    return False
                if expected_nickname is not None and profile["nickname"] != str(
                    expected_nickname
                ):
                    return False
                return profile

            matched = self.wait_until(
                snapshot, timeout=6, poll_frequency=0.15
            )
            if matched is not False:
                return matched
            return {
                "nickname": self._read_visible_modal_field(
                    labels=("用户昵称", "昵称"),
                    field_ids=("form_item_nickname", "form_item_userNickname"),
                    placeholders=("用户昵称", "昵称", "请输入用户昵称", "请输入昵称"),
                    timeout=0.5,
                ),
                "phone_number": self._read_visible_modal_field(
                    labels=("手机号码", "手机号"),
                    field_ids=("form_item_phone", "form_item_mobile", "form_item_phoneNumber"),
                    placeholders=("手机号码", "手机号", "请输入手机号码", "请输入手机号"),
                    timeout=0.5,
                ),
                "errors": self.visible_add_user_validation_errors(),
            }
        finally:
            self._click_visible_modal_button(primary=False, timeout=3)
            self.wait_modal_state(False, timeout=3)
            self._restore_list_state()

    def cancel_modify_user(self,old_user_name,new_user_name):
        if not self._open_modify_user_dialog(old_user_name):
            return False
        original=self._read_visible_modal_field(labels=('用户昵称','昵称'),field_ids=('form_item_nickname','form_item_userNickname'),
            placeholders=('用户昵称','昵称','请输入用户昵称','请输入昵称'),timeout=2)
        if not self._replace_modify_nickname(new_user_name):
            self._click_visible_modal_button(primary=False, timeout=2)
            self._restore_list_state()
            return False
        if not self._click_visible_modal_button(primary=False, timeout=3):
            self._restore_list_state()
            return False
        profile=self.read_user_profile(old_user_name,refresh=True,expected_nickname=original)
        self._restore_list_state()
        return bool(profile and profile['nickname']==original)

    @timed_operation
    def modify_user(self, old_user_name, user_nickname, phone_number=None):
        self.last_modify_debug = {
            "username": old_user_name,
            "nickname": user_nickname,
            "phone_number": str(phone_number) if phone_number is not None else None,
            "stage": "open_dialog",
        }
        if not self._open_modify_user_dialog(old_user_name):
            self.last_modify_debug["error"] = "修改弹窗未打开"
            return False
        if not self._replace_modify_nickname(user_nickname):
            self.last_modify_debug["error"] = "昵称字段未写入目标值"
            self._click_visible_modal_button(primary=False, timeout=2)
            self._restore_list_state()
            return False
        if phone_number is not None and not self._replace_modify_phone(phone_number):
            self.last_modify_debug["error"] = "手机号字段未写入目标值"
            self._click_visible_modal_button(primary=False, timeout=2)
            self._restore_list_state()
            return False
        errors = self.visible_add_user_validation_errors()
        self.last_modify_debug.update(
            {
                "stage": "fields_populated",
                "visible_values": {
                    "nickname": self._read_visible_modal_field(
                        labels=("用户昵称", "昵称"),
                        field_ids=("form_item_nickname", "form_item_userNickname"),
                        placeholders=("用户昵称", "昵称", "请输入用户昵称", "请输入昵称"),
                        timeout=1,
                    ),
                    "phone_number": self._read_visible_modal_field(
                        labels=("手机号码", "手机号"),
                        field_ids=("form_item_phone", "form_item_mobile", "form_item_phoneNumber"),
                        placeholders=("手机号码", "手机号", "请输入手机号码", "请输入手机号"),
                        timeout=1,
                    ),
                },
                "validation_errors": errors,
            }
        )
        if any(
            errors.get(label)
            for label in ("用户昵称", "昵称", "手机号码", "手机号")
        ):
            self.last_modify_debug["error"] = "修改字段出现前端校验错误"
            self._click_visible_modal_button(primary=False, timeout=2)
            self._restore_list_state()
            return False
        before_table = self.table_snapshot()
        before_messages = self._visible_notice_texts()
        if not self._click_visible_modal_button(primary=True, timeout=3):
            self._click_visible_modal_button(primary=False, timeout=2)
            self._restore_list_state()
            return False
        def field_rejected():
            current=self.visible_add_user_validation_errors()
            return current if any(current.get(label) for label in ('用户昵称','昵称','手机号码','手机号')) else False
        evidence = self.wait_operation_evidence(
            [
                (
                    "new_toast",
                    lambda: any(
                        text not in before_messages
                        for text in self._visible_notice_texts()
                    ),
                ),
                ("modal_closed", lambda: not self._has_visible_modal_content()),
                ("table_changed", lambda: self.table_snapshot() != before_table),
                ('field_rejected',field_rejected),
            ],
            timeout=6,
            poll_frequency=0.2,
        )
        self.last_modify_debug["save_evidence"] = evidence or None
        rejected=self.visible_add_user_validation_errors()
        if any(rejected.get(label) for label in ('用户昵称','昵称','手机号码','手机号')):
            self.last_modify_debug.update(error='修改字段出现前端校验错误',validation_errors_after_save=rejected)
            self._click_visible_modal_button(primary=False,timeout=2)
            self._restore_list_state()
            return False
        if not evidence:
            self.last_modify_debug["error"] = "保存后没有可靠页面证据"
            if self._has_visible_modal_content():
                self.last_modify_debug["validation_errors_after_save"] = (
                    self.visible_add_user_validation_errors()
                )
                self._click_visible_modal_button(primary=False, timeout=2)
            self._restore_list_state()
            return False
        profile = self.read_user_profile(
            old_user_name,
            refresh=True,
            expected_phone=phone_number,
            expected_nickname=user_nickname,
        )
        self.last_modify_debug.update(
            {
                "stage": "persisted_profile",
                "persisted_profile": profile,
                "profile_open_debug": getattr(
                    self, "last_open_profile_debug", None
                ),
            }
        )
        if not profile or profile["nickname"] != user_nickname:
            self.last_modify_debug["error"] = "刷新后昵称未持久化"
            return False
        if phone_number is not None and profile["phone_number"] != str(phone_number):
            self.last_modify_debug["error"] = "刷新后手机号未持久化"
            return False
        return not any(
            profile["errors"].get(label)
            for label in ("用户昵称", "昵称", "手机号码", "手机号")
        )

    def reset_user_password(self, username, new_password):
        """Reset one exact user's password through the administrator edit dialog."""
        if not self._open_modify_user_dialog(username):
            return False
        if not self._replace_visible_modal_field(
            labels=("密码", "用户密码"),
            value=new_password,
            field_ids=("form_item_password",),
            placeholders=("密码", "用户密码", "请输入密码"),
            timeout=5,
        ):
            self._click_visible_modal_button(primary=False, timeout=2)
            self._restore_list_state()
            return False
        errors = self.visible_add_user_validation_errors()
        if errors.get("密码") or errors.get("用户密码"):
            self._click_visible_modal_button(primary=False, timeout=2)
            self._restore_list_state()
            return False
        previous_messages = self._visible_notice_texts()
        if not self._click_visible_modal_button(primary=True, timeout=3):
            self._click_visible_modal_button(primary=False, timeout=2)
            self._restore_list_state()
            return False
        evidence = self.wait_operation_evidence(
            [
                (
                    "success_toast",
                    lambda: any(
                        "成功" in text and text not in previous_messages
                        for text in self._visible_notice_texts()
                    ),
                ),
                ("modal_closed", lambda: not self._has_visible_modal_content()),
            ],
            timeout=8,
            poll_frequency=0.2,
        )
        self._restore_list_state()
        return bool(evidence)

    def batch_reset_user_password(self, username, new_password):
        """Reset one exact user through the dedicated batch-password dialog."""
        self.last_batch_password_debug = {"username": username, "stage": "open"}
        self._ensure_user_page_ready()
        button = (by.CSS_SELECTOR, "main button.left_batchEditPwd")
        if not self._click_first_available_safe([button], timeout=5):
            return False
        modal = self.wait_until(
            lambda: self.driver.execute_script(
                """
                const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                return [...document.querySelectorAll('.ant-modal-content')].filter(visible)
                  .find(e=>(e.innerText||'').includes('批量修改密码'))||null;
                """
            )
            or False,
            timeout=6,
            poll_frequency=0.1,
        )
        if modal is False:
            self.last_batch_password_debug["error"] = "批量修改密码弹窗未出现"
            return False
        organization_checkbox = self.wait_until(
            lambda: next(
                (
                    item
                    for item in modal.find_elements(
                        by.CSS_SELECTOR, ".ant-tree .ant-tree-checkbox"
                    )
                    if item.is_displayed()
                ),
                False,
            ),
            timeout=6,
            poll_frequency=0.2,
        )
        if organization_checkbox is False:
            self.last_batch_password_debug["error"] = "组织树复选框未出现"
            return False
        self.driver.execute_script("arguments[0].click();", organization_checkbox)

        selected = False
        deadline = time.time() + 8
        while time.time() < deadline and not selected:
            selected = bool(
                self.driver.execute_script(
                    """
                    const modal=arguments[0], expected=arguments[1];
                    const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                    const label=[...modal.querySelectorAll('.ant-checkbox-wrapper')]
                      .find(e=>visible(e)&&(e.innerText||'').trim()===expected);
                    if(label){label.click();return true;}
                    const scroll=modal.querySelector('.scroll-wrapper');
                    if(scroll){
                      scroll.scrollTop=Math.min(scroll.scrollTop+Math.max(80,scroll.clientHeight),scroll.scrollHeight);
                      scroll.dispatchEvent(new Event('scroll',{bubbles:true}));
                    }
                    return false;
                    """,
                    modal,
                    username,
                )
            )
            if not selected:
                time.sleep(0.2)
        if not selected:
            self.last_batch_password_debug.update(
                {
                    "error": "目标用户未出现在可选用户列表",
                    "modal_text": (modal.text or "")[:3000],
                    "visible_users": self.driver.execute_script(
                        """
                        return [...arguments[0].querySelectorAll('.ant-checkbox-wrapper')]
                          .filter(e=>e.offsetParent!==null).map(e=>(e.innerText||'').trim());
                        """,
                        modal,
                    ),
                }
            )
            return False
        self.last_batch_password_debug["stage"] = "user_selected"
        if not self._replace_visible_modal_field(
            labels=("修改密码",),
            value=new_password,
            placeholders=("修改密码",),
            timeout=4,
        ) or not self._replace_visible_modal_field(
            labels=("确认密码",),
            value=new_password,
            placeholders=("确认密码",),
            timeout=4,
        ):
            self.last_batch_password_debug["error"] = "密码或确认密码字段未写入"
            self.last_batch_password_debug["modal_text"] = (modal.text or "")[:3000]
            return False
        before_messages = self._visible_notice_texts()
        confirm = next(
            (
                item
                for item in modal.find_elements(by.CSS_SELECTOR, "button")
                if item.is_displayed()
                and "确定" in (item.text or "").replace(" ", "")
            ),
            None,
        )
        if confirm is None:
            confirm = next(
                (
                    item
                    for item in modal.find_elements(
                        by.CSS_SELECTOR, "button.ant-btn-primary"
                    )
                    if item.is_displayed()
                ),
                None,
            )
        if confirm is None:
            self.last_batch_password_debug["error"] = "确认按钮未找到"
            return False
        self.driver.execute_script("arguments[0].click();", confirm)
        success = self.wait_until(
            lambda: any(
                "成功" in text and text not in before_messages
                for text in self._visible_notice_texts()
            ),
            timeout=8,
            poll_frequency=0.2,
        )
        self._restore_list_state()
        if success is False:
            self.last_batch_password_debug["error"] = "提交后未出现成功提示"
            self.last_batch_password_debug["modal_text"] = (modal.text or "")[:3000]
        else:
            self.last_batch_password_debug["stage"] = "completed"
        return success is not False

    def _click_active_confirmation(self, timeout=5):
        """Click the primary action in the topmost genuinely visible confirm layer."""
        script = """
        const visible = item => {
          const rect = item.getBoundingClientRect();
          if (rect.width <= 0 || rect.height <= 0) return false;
          for (let node = item; node && node !== document.body; node = node.parentElement) {
            const style = getComputedStyle(node);
            if (style.display === 'none' || style.visibility === 'hidden') return false;
          }
          return true;
        };
        const layers = [...document.querySelectorAll(
          '.ant-modal-confirm,.ant-modal-content,.ant-popover:not(.ant-popover-hidden)'
        )].filter(visible);
        for (const layer of layers.reverse()) {
          const buttons = [...layer.querySelectorAll('button')]
            .filter(button => visible(button) && !button.disabled);
          const normalize = value => String(value || '').replace(/\\s+/g, '');
          const button = buttons.find(item => ['确定', '确认', '删除']
            .some(word => normalize(item.innerText).includes(word)))
            || buttons.find(item => item.classList.contains('ant-btn-primary'));
          if (button) { button.click(); return true; }
        }
        return false;
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

    def delete_user(self, username, result):
        # Unlike cleanup, this functional case must observe the user first.
        if not self._search_keyword(username):
            return False
        if self._wait_for_exact_user_row_element_on_current_page(username, timeout=3) is None:
            self.reset_search()
            return False
        return self.ensure_user_absent(username)

    def delete_all_user(self,result):
        self._ensure_user_page_ready()
        self.reset_search()
        self.set_result_page_size(15, timeout=5)
        self._go_to_first_result_page(timeout=3)
        before_count = self.get_total_record_count()
        if before_count in (None, 0):
            return True
        if not self._ensure_select_all_checked(timeout=5):
            return False
        if not self._click_first_available_safe(
            [self.delete_button_modern, self.delete_button], timeout=5
        ):
            return False
        delete_confirm_locators = [
            self.delete_confirm_button_css,
            self.delete_confirm_button_text,
            self.delete_sure_button_text,
            self.delete_sure_button,
        ]
        if not self._visible_in_any(delete_confirm_locators, timeout=3):
            if not self._ensure_select_all_checked(timeout=3):
                return False
            if not self._click_first_available_safe(
                [self.delete_button_modern, self.delete_button], timeout=3
            ):
                return False
        if not self._click_active_confirmation(timeout=5):
            return False
        after_count = self.wait_for_record_count_change(before_count, timeout=20)
        if after_count is not None and after_count < before_count:
            return True
        return self.wait_for_operation_result(timeout=5)

    def delete_users_by_keyword(self, keyword, result):
        self._ensure_user_page_ready()
        self._search_keyword(keyword)
        self._go_to_first_result_page(timeout=3)

        row_locator = self._keyword_user_row_locator(keyword)
        if not self._visible_in_any([row_locator], timeout=3):
            self.reset_search()
            return True

        before_count = self.get_total_record_count()
        if not self._ensure_select_all_checked(timeout=5):
            self.reset_search()
            return False
        if not self._click_first_available_safe(
            [self.delete_button_modern, self.delete_button], timeout=5
        ):
            self.reset_search()
            return False
        if not self._click_active_confirmation(timeout=5):
            self.reset_search()
            return False

        # The filtered rows disappearing is the authoritative deletion
        # result.  Some supported builds do not emit a readable toast and do
        # not refresh the total counter promptly; waiting for both first made
        # an already-complete deletion spend up to 30 seconds here.
        rows_removed = self.wait_operation_evidence(
            [
                (
                    "rows_absent",
                    lambda: self.wait_loading_finished(timeout=0.2)
                    and self.find_visible_now(row_locator) is False,
                ),
                ("toast", lambda: result in " ".join(self._visible_notice_texts())),
            ],
            timeout=4,
        )
        if rows_removed:
            self._search_keyword(keyword)
            self.wait_loading_finished(timeout=2)
            absent = self.find_visible_now(row_locator) is False
            self.reset_search()
            return absent

        self._search_keyword(keyword)
        self.wait_loading_finished(timeout=2)
        still_exists = self.find_visible_now(row_locator) is not False
        self.reset_search()
        return not still_exists

    def add_user_in_batches(self,user_prefix,user_number,user_password,result):
        if not self._prepare_user_modal_operation():
            return False
        before_count = self.get_total_record_count()
        if not self._click_first_available_safe(
            [self.add_in_batches_modern, self.add_in_batches_text, self.add_in_batches], timeout=5
        ):
            raise AssertionError("Failed to open batch add dialog")

        # 4.39.7 and 4.39.8 use the same four-field dialog but render the
        # title in different component trees. Scope interaction to the visible
        # modal instead of relying on an absolute XPath or title text.
        modal = self.wait_visible(
            (by.CSS_SELECTOR, ".ant-modal:not([style*='display: none'])"),
            timeout=8,
        )
        if modal is False:
            return False
        inputs = [
            element
            for element in modal.find_elements(by.CSS_SELECTOR, "input")
            if element.is_displayed()
        ]
        if len(inputs) < 4:
            return False
        before_messages = self._visible_notice_texts()
        try:
            # The dialog has prefix, count, department, password and confirm
            # password.  Department is a selector, therefore use the first
            # two and the last two editable fields rather than a positional
            # four-field assumption.
            field_values = [
                (inputs[0], user_prefix),
                (inputs[1], user_number),
                (inputs[-2], user_password),
                (inputs[-1], user_password),
            ]
            for input_element, value in field_values:
                input_element.click()
                input_element.send_keys(Keys.CONTROL, "a")
                input_element.send_keys(Keys.DELETE)
                input_element.send_keys(str(value))
            save_buttons = [
                button
                for button in modal.find_elements(by.CSS_SELECTOR, "button.ant-btn-primary")
                if button.is_displayed()
            ]
            if not save_buttons:
                return False
            self.driver.execute_script("arguments[0].click();", save_buttons[0])
        except Exception:
            return False
        message = self._latest_operation_message(
            timeout=3, previous_messages=before_messages
        )
        if "\u6210\u529f" in message:
            return True

        if before_count is None:
            return False

        try:
            expected_growth = int(user_number)
        except (TypeError, ValueError):
            expected_growth = 1

        after_count = self.wait_for_record_count_change(before_count, timeout=6)
        if after_count is not None and after_count >= before_count + expected_growth:
            return True

        # Use the data actually created by this batch as the final fallback.
        # This is more reliable than a stale pagination counter and still
        # proves the batch operation produced searchable user records.
        self._search_keyword(user_prefix)
        created = self._visible_in_any(
            [self._keyword_user_row_locator(user_prefix)], timeout=3
        )
        self.reset_search()
        return created

    def get_total_record_count(self):
        self._ensure_user_page_ready()
        text = self._first_visible_text(self.data_num)
        numbers = re.findall(r'\d+', text or "")
        if numbers:
            return int(numbers[-1])

        # Vue 3 does not render the old total-count label. The largest page
        # number still gives a reliable lower bound, which is sufficient for
        # pagination preconditions without pretending to know the exact total.
        estimate = self.driver.execute_script(
            """
            const visible = el => !!(el && (el.offsetWidth || el.offsetHeight || el.getClientRects().length));
            const pages = [...document.querySelectorAll('main .ant-pagination-item')]
              .filter(visible).map(el => Number((el.innerText || '').trim())).filter(Number.isFinite);
            if (!pages.length) return null;
            const sizeText = [...document.querySelectorAll('main .ant-pagination-options-size-changer')]
              .filter(visible).map(el => el.innerText || '').join(' ');
            const size = Number((sizeText.match(/\d+/) || ['15'])[0]);
            const maxPage = Math.max(...pages);
            return maxPage > 1 ? (maxPage - 1) * size + 1 : document.querySelectorAll('main tbody tr').length;
            """
        )
        return int(estimate) if estimate is not None else None

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
        summary = self._first_visible_text(self.data_num)
        if summary:
            return summary
        page = self.get_current_page_text() or "1"
        rows = len(
            [row for row in self.driver.find_elements(by.CSS_SELECTOR, "main tbody tr") if row.is_displayed()]
        )
        return f"page={page};rows={rows}"

    def get_current_page_size_text(self):
        return self._first_visible_text(self.page_size_value) or ""

    def set_result_page_size(self, page_size, timeout=4):
        self._ensure_user_page_ready()
        option_text = f"{page_size} \u6761/\u9875"
        if option_text in self.get_current_page_size_text():
            return True

        if not self._click_first_available_safe(
            [self.page_size_changer, self.page_num_button], timeout=5
        ):
            return False

        option_locator = (
            by.XPATH,
            "//div[contains(@class,'ant-select-dropdown') and not(contains(@style,'display: none'))]"
            f"//*[self::li or contains(@class,'ant-select-item-option')][normalize-space()='{option_text}']",
        )
        if not self._click_first_available_safe([option_locator], timeout=timeout):
            return False

        end = time.time() + timeout
        while time.time() < end:
            if option_text in self.get_current_page_size_text():
                return True
            time.sleep(0.2)
        return False

    def jump_to_result_page(self, page_num, timeout=4):
        self._ensure_user_page_ready()
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
        try:
            self.send_keys_enter(self.locate_search)
        except Exception:
            pass
        # Enter is the primary query action.  Click the explicit icon only as
        # a short compatibility fallback; it is already present whenever a
        # build requires it, so a long polling wait adds no test evidence.
        self._click_first_available_safe([self.search_button], timeout=0.8)
        time.sleep(0.1)

    def reset_search(self):
        return self._search_keyword("")

    def _first_visible_text(self, locator):
        for element in self.driver.find_elements(*locator):
            try:
                if element.is_displayed():
                    return (element.text or "").strip()
            except Exception:
                continue
        return ""

    def delete_users_by_names(self, usernames, result="删除成功"):
        ok = True
        for username in dict.fromkeys(usernames):
            ok = self.ensure_user_absent(username) and ok
        return ok

    @timed_operation
    def ensure_user_absent(self, username):
        if not self._ensure_user_page_ready():
            return False

        for _ in range(2):
            if not self._search_keyword(username):
                return False
            # _search_keyword has already proved this exact request completed
            # and the rendered table is stable; no extra absence timeout.
            if self._find_exact_user_row_element_on_current_page(username) is None:
                return self.reset_search()

            delete_locator = self._exact_user_delete_button_locator(username)
            started = self.driver.execute_script("return performance.now()")
            if not self._click_first_available_safe([delete_locator], timeout=4):
                self.reset_search()
                return False
            # Some builds delete immediately; others require confirmation.
            self._click_active_confirmation(timeout=2)
            if not wait_query_finished(self, started, timeout=8):
                self.reset_search()
                return False
            # Always issue a fresh exact query after deletion. Neither a toast
            # nor an old empty table is sufficient proof that cleanup succeeded.
            if not self._search_keyword(username):
                return False
            if self._find_exact_user_row_element_on_current_page(username) is None:
                return self.reset_search()

        if not self._search_keyword(username):
            return False
        absent = self._find_exact_user_row_element_on_current_page(username) is None
        self.reset_search()
        return absent


    def skip_to_second_page(self):
        self.click(self.second_page_button)
        text = self.get_element_text(self.data_num)
        text = text[3:]
        num = int(re.findall(r'\d+', text)[0])
        return num

    def skip_to_first_page(self):
        self.click(self.first_page_button)
        text = self.get_element_text(self.data_num)
        text = text[6:]
        num = int(re.findall(r'\d+', text)[0])
        return num

    def select_10_number(self):
        self.click(self.page_num_button)
        self.click(self.ten_num)
        text = self.get_element_text(self.data_num)
        text = text[6:]
        num = int(re.findall(r'\d+', text)[0])
        return num

    def select_15_number(self):
        self.click(self.page_num_button)
        self.click(self.fifteen_num)
        text = self.get_element_text(self.data_num)
        text = text[6:]
        num = int(re.findall(r'\d+', text)[0])
        return num

    def select_20_number(self):
        self.click(self.page_num_button)
        self.click(self.twenty_num)
        text = self.get_element_text(self.data_num)
        text = text[6:]
        num = int(re.findall(r'\d+', text)[0])
        return num

    def select_50_number(self):
        self.click(self.page_num_button)
        self.click(self.fifty_num)
        text = self.get_element_text(self.data_num)
        text = text[6:]
        num = int(re.findall(r'\d+', text)[0])
        return num

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
        const modalContents = Array.from(document.querySelectorAll('.ant-modal-content'))
            .filter(isVisible);
        if (!modalContents.length) return false;
        const modal = modalContents[modalContents.length - 1];
        const footer = modal.querySelector('.ant-modal-footer') || modal;
        const buttons = Array.from(footer.querySelectorAll('button'))
            .filter((button) => isVisible(button) && !button.disabled);
        const hasPrimaryClass = (button) => String(button.className || '').includes('ant-btn-primary');
        const textOf = (button) => normalize(button.innerText || button.textContent);
        let button = null;
        if (wantPrimary) {
            button = buttons.find((item) => hasPrimaryClass(item))
                || buttons.find((item) => ['保存', '确定'].some((text) => textOf(item).includes(text)))
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

    def _has_visible_modal_content(self):
        try:
            return bool(self.driver.execute_script("""
              const visible = el => !!(el && (el.offsetWidth || el.offsetHeight || el.getClientRects().length));
              return [...document.querySelectorAll('.ant-modal-content,.layer_body')].some(visible);
            """))
        except Exception:
            return False
    def _click_first_available_safe(self, locators, timeout=4):
        """
        Click first available locator and return True on success.
        """
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
        """
        Check whether any locator becomes visible.
        """
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
        """
        Best effort close optional overlays that may intercept sidebar clicks.
        """
        close_locators = [
            (by.CLASS_NAME, "introjs-skipbutton"),
            (by.CSS_SELECTOR, ".ant-modal-close"),
            (by.CSS_SELECTOR, ".ant-drawer-close"),
        ]
        for locator in close_locators:
            elements = self.driver.find_elements(*locator)
            for element in elements:
                if not element.is_displayed():
                    continue
                try:
                    element.click()
                except Exception:
                    try:
                        self.driver.execute_script("arguments[0].click();", element)
                    except Exception:
                        continue

    def _is_sidebar_collapsed(self):
        menus = self.driver.find_elements(*self.sidebar_menu_root)
        for menu in menus:
            class_name = menu.get_attribute("class") or ""
            if "ant-menu-inline-collapsed" in class_name:
                return True
        return False

    def _ensure_sidebar_expanded(self, timeout=8):
        """
        Expand collapsed sidebar before using text-based sidebar locators.
        """
        end = time.time() + timeout
        while time.time() < end:
            if not self._is_sidebar_collapsed():
                return True
            self._click_first_available_safe([self.sidebar_expand_button], timeout=1.5)
            time.sleep(0.3)
        return not self._is_sidebar_collapsed()

    def _ensure_user_page_ready(self):
        """
        Re-enter user management page when the current test starts elsewhere.
        """
        if self.find_visible_now(self.export_user_modal) is not False:
            self._dismiss_blocking_layers()
            if not self.wait_modal_state(False, timeout=1):
                self._hard_reload_user_page()
        ready_locators = [
            self.add_in_batches_modern,
            self.add_in_batches_text,
            self.export_user_button_modern,
            self.export_user_button_text,
        ]
        if self.ensure_page_ready_fast(self.user_route, ready_locators):
            return self._wait_user_list_loaded(allow_cached=True)
        return self.common_enter_user()

    def _wait_user_list_loaded(self, timeout=12,allow_cached=False):
        return wait_page_layout(self,self.user_route,[['用户名','用户姓名'],['昵称']],
            '.ant-tree-title,.ant-tree-node-content-wrapper,.el-tree-node__content,.custom-tree-node',
            timeout=timeout,allow_cached=allow_cached)

    @timed_operation
    def common_enter_user(self):
        """Robust enter flow for user management page."""
        self.common_login()
        self.dismiss_intro_if_present()
        self._dismiss_blocking_layers()
        new_add_locators = [
            self.add_in_batches_modern,
            self.add_in_batches_text,
            self.export_user_button_modern,
            self.export_user_button_text,
        ]
        self._enter_user_via_route()
        if self._visible_in_any(new_add_locators, timeout=10):
            return self._wait_user_list_loaded(allow_cached=True)
        self.driver.refresh()
        self.wait_for_document_ready(timeout=5)
        if self._visible_in_any(new_add_locators, timeout=10):
            return True
        if not self._ensure_sidebar_expanded(timeout=8):
            raise AssertionError("Sidebar is still collapsed after expand attempt")

        contactlist_locators = [self.contactlist_button_text, self.contactlist_button]
        user_menu_locators = [self.user_button_text, self.user_button, self.user_button_alt]
        if not self._visible_in_any(user_menu_locators, timeout=3):
            opened = False
            for _ in range(4):
                self._click_first_available_safe(contactlist_locators, timeout=5)
                if self._visible_in_any(user_menu_locators, timeout=4):
                    opened = True
                    break
            if not opened:
                self._enter_user_via_route()
                if self._visible_in_any(new_add_locators, timeout=10):
                    return True
                raise AssertionError("Failed to open contact list menu")

        if not self._click_first_available_safe(user_menu_locators, timeout=5):
            self._enter_user_via_route()
            if self._visible_in_any(new_add_locators, timeout=10):
                return True
            raise AssertionError("Failed to click user management menu")

        if not self._visible_in_any(new_add_locators, timeout=10):
            self._enter_user_via_route()
            if not self._visible_in_any(new_add_locators, timeout=10):
                raise AssertionError("Failed to enter user management page")
        return True

    def _enter_user_via_route(self):
        current_url = self.driver.current_url or ""
        if "#" in current_url:
            base_url = current_url.split("#", 1)[0]
        else:
            base_url = current_url.rstrip("/") + "/"
        if not base_url:
            base_url = self.url
        self.open_spa_route(self.user_route, timeout=5)

    def _hard_reload_user_page(self):
        self._enter_user_via_route()
        self.driver.refresh()
        self.wait_for_document_ready(timeout=5)
        return True






