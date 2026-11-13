# -*- coding:utf-8 -*-
import math
import re
import time

from selenium.webdriver.common.by import By as by
from selenium.webdriver.common.keys import Keys

from pages.Index_Page.index import LoginPage
from common.semantic_controls import action_locator
from common.ui_state import wait_stable_state


class ProductInfoPage(LoginPage):
    product_info_route = "#/ui/configuration-center/product-information"

    sidebar_menu_root = (by.CSS_SELECTOR, "aside ul.ant-menu")
    sidebar_expand_button = (by.CSS_SELECTOR, "aside .trigger.anticon-menu-unfold")

    add_button = (by.CSS_SELECTOR, "main button.hst-add-button")
    delete_button = (by.CSS_SELECTOR, "main button.hst-delete-button")
    data_num = (by.CSS_SELECTOR, "main .table-wrapper > p.pagination-desc")
    page_size_changer = (by.CSS_SELECTOR, ".ant-pagination-options-size-changer")
    page_size_value = (
        by.CSS_SELECTOR,
        ".ant-pagination-options-size-changer .ant-select-selection-selected-value, "
        ".ant-pagination-options-size-changer .ant-select-selection-item",
    )
    quick_jump_input = (by.CSS_SELECTOR, ".ant-pagination-options-quick-jumper input")
    active_page_num = (by.CSS_SELECTOR, ".ant-pagination-item-active")

    save_result = (
        by.XPATH,
        "//div[contains(@class,'ant-message-notice-content')]"
        "//*[contains(@class,'ant-message') and normalize-space()] | "
        "//div[contains(@class,'ant-message-notice-content')]//*[normalize-space()]",
    )

    add_modal_step_title = "新增产品信息"
    edit_modal_step_title = "修改产品信息"
    product_name_placeholder = "产品名称"
    product_id_placeholder = "产品ID"

    def _visible_modal(self, timeout=10):
        end = time.time() + timeout
        while time.time() < end:
            for modal in self.driver.find_elements(by.CSS_SELECTOR, ".ant-modal-content"):
                try:
                    if modal.is_displayed():
                        return modal
                except Exception:
                    continue
            time.sleep(0.2)
        return None

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
                        if not element.is_displayed() or not element.is_enabled():
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
            time.sleep(0.1)
            element.send_keys(str(value))
            time.sleep(0.1)
            return (element.get_attribute("value") or "") == str(value)
        except Exception:
            return False

    def _replace_input_value(self, locator, value, timeout=10):
        element = self.wait_visible(locator, timeout=timeout)
        if element is False:
            return False
        return self._replace_element_value(element, value)

    def _replace_modal_input_by_placeholder(self, placeholder, value, timeout=10):
        end = time.time() + timeout
        while time.time() < end:
            modal = self._visible_modal(timeout=1)
            if modal is not None:
                for element in modal.find_elements(by.CSS_SELECTOR, "input"):
                    try:
                        if not element.is_displayed():
                            continue
                        if (element.get_attribute("placeholder") or "") != placeholder:
                            continue
                        return self._replace_element_value(element, value)
                    except Exception:
                        continue
            time.sleep(0.2)
        return False

    def _visible_modal_title(self, timeout=5):
        modal = self._visible_modal(timeout=timeout)
        if modal is None:
            return ""
        for locator in [
            (by.CSS_SELECTOR, ".ant-modal-title"),
            (by.CSS_SELECTOR, ".step .description"),
        ]:
            for element in modal.find_elements(*locator):
                try:
                    if element.is_displayed() and (element.text or "").strip():
                        return (element.text or "").strip()
                except Exception:
                    continue
        return ""

    def _click_visible_modal_primary_button(self, timeout=8):
        end = time.time() + timeout
        while time.time() < end:
            modal = self._visible_modal(timeout=1)
            if modal is None:
                time.sleep(0.2)
                continue
            for button in modal.find_elements(by.CSS_SELECTOR, "button.ant-btn-primary"):
                try:
                    if not button.is_displayed():
                        continue
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});", button
                    )
                    try:
                        button.click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", button)
                    return True
                except Exception:
                    continue
            time.sleep(0.2)
        return False

    def _close_visible_modal(self, timeout=5):
        locators = [
            (by.CSS_SELECTOR, ".ant-modal-close"),
            (by.XPATH, "//div[contains(@class,'ant-modal-content')]//button[normalize-space()='关 闭']"),
            (by.XPATH, "//div[contains(@class,'ant-modal-content')]//button[normalize-space()='关闭']"),
        ]
        return self._click_first_available_safe(locators, timeout=timeout)

    def _wait_modal_closed(self, timeout=10):
        end = time.time() + timeout
        while time.time() < end:
            if self._visible_modal(timeout=1) is None:
                return True
            time.sleep(0.2)
        return False

    def wait_for_operation_result(self, expected_text=None, timeout=8):
        end = time.time() + timeout
        while time.time() < end:
            for element in self.driver.find_elements(*self.save_result):
                try:
                    if not element.is_displayed():
                        continue
                    text = (element.text or "").strip()
                    if not text:
                        continue
                    if expected_text is None or expected_text in text:
                        return True
                except Exception:
                    continue
            time.sleep(0.2)
        return False

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

    def _enter_product_info_via_route(self):
        current_url = self.driver.current_url or ""
        if "#" in current_url:
            base_url = current_url.split("#", 1)[0]
        else:
            base_url = current_url.rstrip("/") + "/"
        if not base_url:
            base_url = self.url
        self.open_spa_route(self.product_info_route, timeout=5)

    def _hard_reload_product_info_page(self):
        self._enter_product_info_via_route()
        self.driver.refresh()
        self.wait_for_document_ready(timeout=5)
        return True

    def _ensure_page_ready(self):
        if self.product_info_route not in (self.driver.current_url or ''):
            return self.common_enter_product_info()
        ready_locators = [self.add_button, self.delete_button, self.quick_jump_input]
        if self._visible_in_any(ready_locators, timeout=2):
            return True
        self._hard_reload_product_info_page()
        if self._visible_in_any(ready_locators, timeout=5):
            return True
        return self.common_enter_product_info()

    def common_enter_product_info(self):
        self.common_login()
        self.dismiss_intro_if_present()
        self._dismiss_blocking_layers()
        self._enter_product_info_via_route()
        ready_locators = [self.add_button, self.delete_button, self.quick_jump_input]
        if not self._visible_in_any(ready_locators, timeout=10):
            raise AssertionError("Failed to enter product info page")
        assert self.wait_until(lambda: self.driver.execute_script(
            "const labels=[...document.querySelectorAll('main thead th')].map(e=>(e.innerText||'').replace(/\\s/g,''));return ['产品名称','产品ID'].every(x=>labels.includes(x));"
        ),timeout=8), '产品信息专属表头未就绪'
        assert self.wait_loading_finished(timeout=10), '产品列表尚未加载完成'
        return True

    def _product_row_locator(self, product_id):
        return (
            by.XPATH,
            f"//table//tbody//tr[td[4][normalize-space()='{product_id}']]",
        )

    def _product_name_cell_locator(self, product_id):
        return (
            by.XPATH,
            f"//table//tbody//tr[td[4][normalize-space()='{product_id}']]/td[3]",
        )

    def _product_action_locator(self, product_id, action_index):
        return (
            by.XPATH,
            f"//table//tbody//tr[td[4][normalize-space()='{product_id}']]"
            f"//td[last()]//a[{action_index}]",
        )

    def get_total_record_count(self):
        self._ensure_page_ready()
        text = None
        for element in self.driver.find_elements(*self.data_num):
            try:
                if element.is_displayed() and "总共" in (element.text or ""):
                    text = element.text
                    break
            except Exception:
                continue
        if not text:
            # Vue 3 can omit the legacy summary. A lower bound suffices only
            # for pagination preparation; CRUD success still checks exact ID.
            return self.driver.execute_script(
                """
                const pages=[...document.querySelectorAll('main .ant-pagination-item')]
                  .map(e=>Number((e.innerText||'').trim())).filter(Number.isFinite);
                const selected=document.querySelector('main .ant-pagination-options-size-changer .ant-select-selection-item,main .ant-pagination-options-size-changer .ant-select-selection-selected-value');
                const size=Number(((selected?.innerText||'').match(/\d+/)||['0'])[0]);
                const last=pages.length?Math.max(...pages):1;
                return last>1&&size?(last-1)*size+1:[...document.querySelectorAll('main tbody tr')]
                  .filter(e=>e.offsetParent!==null&&!e.classList.contains('ant-table-measure-row')&&!e.classList.contains('ant-table-placeholder')).length;
                """
            )
        numbers = re.findall(r"\d+", text)
        if not numbers:
            return None
        return int(numbers[-1])

    def wait_for_record_count_change(self, previous_count, timeout=20):
        end = time.time() + timeout
        while time.time() < end:
            current_count = self.get_total_record_count()
            if current_count is not None and current_count != previous_count:
                return current_count
            time.sleep(0.2)
        return None

    def get_pagination_summary_text(self):
        self._ensure_page_ready()
        for element in self.driver.find_elements(*self.data_num):
            try:
                if element.is_displayed():
                    return (element.text or "").strip()
            except Exception:
                continue
        return ""

    def get_current_page_text(self):
        self._ensure_page_ready()
        element = self.find_visible_now(self.active_page_num)
        return "" if element is False else (element.text or "")

    def get_current_page_size_text(self):
        self._ensure_page_ready()
        element = self.find_visible_now(self.page_size_value)
        return "" if element is False else (element.text or "")

    def _get_current_page_size_number(self):
        text = self.get_current_page_size_text()
        numbers = re.findall(r"\d+", text)
        if not numbers:
            return None
        return int(numbers[0])

    def _get_last_page_number(self):
        total = self.get_total_record_count()
        page_size = self._get_current_page_size_number()
        if total is None or not page_size:
            return None
        return max(1, int(math.ceil(total / float(page_size))))

    def set_result_page_size(self, page_size, timeout=8):
        target_size = int(page_size)
        option_locator = (
            by.XPATH,
            "//div[contains(@class,'ant-select-dropdown') and not(contains(@style,'display: none'))]"
            f"//*[self::li or contains(@class,'ant-select-item-option')]"
            f"[starts-with(normalize-space(),'{target_size}')]",
        )

        for attempt in range(2):
            self._ensure_page_ready()
            self._dismiss_blocking_layers()
            if self._get_current_page_size_number() == target_size:
                return True

            if not self._click_first_available_safe([
                self.page_size_changer,
                (by.CSS_SELECTOR, ".ant-pagination-options-size-changer .ant-select-selector"),
            ], timeout=5):
                if attempt == 0:
                    self._hard_reload_product_info_page()
                    continue
                return False

            time.sleep(0.3)
            option_clicked = self._click_first_available_safe([option_locator], timeout=timeout)
            if not option_clicked:
                option_clicked = self.driver.execute_script(
                    """
                    const target = String(arguments[0]).trim();
                    const items = Array.from(
                        document.querySelectorAll(
                            ".ant-select-dropdown li, .ant-select-dropdown-menu-item, .ant-select-item-option"
                        )
                    );
                    const item = items.find((el) => {
                        const text = (el.innerText || el.textContent || "").trim();
                        return text.startsWith(target);
                    });
                    if (!item) {
                        return false;
                    }
                    item.click();
                    return true;
                    """,
                    str(target_size),
                )
            if not option_clicked:
                if attempt == 0:
                    self._hard_reload_product_info_page()
                    continue
                return False

            end = time.time() + timeout
            while time.time() < end:
                if self._get_current_page_size_number() == target_size:
                    return True
                time.sleep(0.2)

            if attempt == 0:
                self._hard_reload_product_info_page()
        return False
        option_text = f"{page_size} 条/页"
        if option_text in self.get_current_page_size_text():
            return True

        if not self._click_first_available_safe([self.page_size_changer], timeout=5):
            return False

        option_locator = (
            by.XPATH,
            "//div[contains(@class,'ant-select-dropdown') and not(contains(@style,'display: none'))]"
            f"//li[normalize-space()='{option_text}']",
        )
        if not self._click_first_available_safe([option_locator], timeout=timeout):
            return False

        end = time.time() + timeout
        while time.time() < end:
            if option_text in self.get_current_page_size_text():
                return True
            time.sleep(0.2)
        return False

    def jump_to_result_page(self, page_num, timeout=8):
        self._ensure_page_ready()
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

    def _go_to_page_containing_product(self, product_id, timeout=15):
        self._ensure_page_ready()
        last_page = self._get_last_page_number()
        if last_page is None:
            raise AssertionError('产品查询无法确认页码，禁止据此判定不存在')

        current_page = self.get_current_page_text()
        if current_page and self.find_visible_now(self._product_row_locator(product_id)) is not False:
            return True

        for page_num in range(1, last_page + 1):
            if not self.jump_to_result_page(page_num, timeout=timeout):
                raise AssertionError(f'产品查询未到达第{page_num}页，禁止判定不存在')
            settled=wait_stable_state(self,lambda:self.table_snapshot() if self.wait_loading_finished(timeout=0.2)
                and self.get_current_page_text()==str(page_num) else False,timeout=8)
            if settled is False:raise AssertionError(f'产品第{page_num}页未完成渲染')
            if self.find_visible_now(self._product_row_locator(product_id)) is not False:
                return True
        return False

    def _click_product_action(self, product_id, action_index, timeout=8):
        locator = action_locator(self,'产品ID',product_id,{1:'修改',2:'删除'}[action_index])
        end = time.time() + timeout
        while time.time() < end:
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

    def find_product(self, product_id):
        self._ensure_page_ready()
        return self._go_to_page_containing_product(product_id, timeout=8)

    def enter_product_info(self):
        return self.common_enter_product_info()

    def add_product(self, product_name, product_id, result=None):
        self._ensure_page_ready()
        before_count = self.get_total_record_count()
        before_table = self.table_snapshot()

        if not self._click_first_available_safe([self.add_button], timeout=5):
            return False

        modal = self._visible_modal(timeout=10)
        if modal is None:
            return False

        if not self._replace_modal_input_by_placeholder(
            self.product_name_placeholder, product_name, timeout=10
        ):
            return False
        if not self._replace_modal_input_by_placeholder(
            self.product_id_placeholder, product_id, timeout=10
        ):
            return False

        for _ in range(2):
            if not self._click_visible_modal_primary_button(timeout=5):
                return False
            time.sleep(0.8)

        if not self._click_visible_modal_primary_button(timeout=5):
            return False

        evidence = self.wait_operation_evidence(
            [
                ("modal_closed", lambda: self._visible_modal(timeout=0.05) is None),
                ("table_changed", lambda: self.table_snapshot() != before_table),
                (
                    "count_changed",
                    lambda: before_count is not None
                    and self.get_total_record_count() > before_count,
                ),
                (
                    "toast",
                    lambda: bool(result and self.wait_for_operation_result(result, timeout=0.05)),
                ),
            ],
            timeout=6,
        )

        if self.find_product(product_id):
            return True
        return False

    def modify_product(self, product_id, new_product_name, result=None):
        self._ensure_page_ready()
        if not self._go_to_page_containing_product(product_id, timeout=10):
            return False

        if not self._click_product_action(product_id, 1, timeout=8):
            return False

        modal = self._visible_modal(timeout=10)
        if modal is None:
            return False

        if not self._replace_modal_input_by_placeholder(
            self.product_name_placeholder, new_product_name, timeout=10
        ):
            return False

        for _ in range(2):
            if not self._click_visible_modal_primary_button(timeout=5):
                return False
            time.sleep(0.8)

        if not self._click_visible_modal_primary_button(timeout=5):
            return False

        self._wait_modal_closed(timeout=10)
        if result:
            self.wait_for_operation_result(result, timeout=5)

        if not self._go_to_page_containing_product(product_id, timeout=10):
            return False
        return self.get_text_assert(
            new_product_name, self._product_name_cell_locator(product_id), timeout=5
        )

    def delete_product(self, product_id, result=None):
        self._ensure_page_ready()
        if not self._go_to_page_containing_product(product_id, timeout=10):
            return False

        before_count = self.get_total_record_count()
        delete_opened = self._click_product_action(product_id, 2, timeout=5)
        if not delete_opened:
            return False

        confirm_locators = [
            (by.XPATH, "//div[contains(@class,'ant-modal-confirm')]//button[normalize-space()='确 定']"),
            (by.XPATH, "//div[contains(@class,'ant-modal-confirm')]//button[contains(@class,'ant-btn-primary')]"),
            (by.CSS_SELECTOR, ".ant-popover:not(.ant-popover-hidden) button.ant-btn-primary"),
            (by.CSS_SELECTOR, ".ant-modal-content button.ant-btn-primary"),
        ]
        if not self._click_first_available_safe(confirm_locators, timeout=10):
            # Some builds delete directly. Reconcile through a fresh UI load;
            # a missing confirmation alone cannot decide success or failure.
            self._hard_reload_product_info_page()
            self.common_enter_product_info()
            return not self.find_product(product_id)

        row_locator = self._product_row_locator(product_id)
        self.wait_operation_evidence(
            [
                (
                    "row_absent",
                    lambda: self.wait_loading_finished(timeout=0.2)
                    and self.find_visible_now(row_locator) is False,
                ),
                (
                    "toast",
                    lambda: bool(result and self.wait_for_operation_result(result, timeout=0.05)),
                ),
                (
                    "count_changed",
                    lambda: before_count is not None
                    and self.get_total_record_count() < before_count,
                ),
            ],
            timeout=6,
        )

        self._hard_reload_product_info_page()
        self.common_enter_product_info()
        return not self.find_product(product_id)

    def cleanup_product_if_present(self, product_id):
        try:
            return self.delete_product(product_id)
        except Exception:
            if self._visible_modal(timeout=1) is not None:
                self._close_visible_modal(timeout=2)
            return False
