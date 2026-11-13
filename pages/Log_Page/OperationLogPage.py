# -*- coding:utf-8 -*-
import re
import time

from selenium.webdriver.common.by import By as by
from selenium.webdriver.common.keys import Keys

from pages.Index_Page.index import LoginPage
from common.ui_state import wait_query_finished
from common.semantic_controls import set_date_field


class OperationLogPage(LoginPage):
    operation_log_route = "#/ui/log-management/operation-log"

    sidebar_menu_root = (by.CSS_SELECTOR, "aside ul.ant-menu")
    sidebar_expand_button = (by.CSS_SELECTOR, "aside .trigger.anticon-menu-unfold")

    page_root = (by.CSS_SELECTOR, "main .right-box")
    username_search_input = (
        by.CSS_SELECTOR,
        "main .right-bar .search-box input.ant-input[type='text']:not([readonly])",
    )
    search_button = (
        by.CSS_SELECTOR,
        "main .right-bar .search-box button.ant-btn-primary.ant-btn-icon-only",
    )
    data_num = (
        by.CSS_SELECTOR,
        "main .pagination-box .pagination-word, main .pagination-desc, "
        "main [class*='pagination'] > p",
    )
    page_size_changer = (by.CSS_SELECTOR, "main .ant-pagination-options-size-changer")
    page_size_value = (
        by.CSS_SELECTOR,
        "main .ant-pagination-options-size-changer .ant-select-selection-selected-value, "
        "main .ant-pagination-options-size-changer .ant-select-selection-item",
    )
    quick_jump_input = (by.CSS_SELECTOR, "main .ant-pagination-options-quick-jumper input")
    active_page_num = (by.CSS_SELECTOR, "main .ant-pagination-item-active")
    table_rows = (by.CSS_SELECTOR, "main table tbody tr")
    table_placeholder = (by.CSS_SELECTOR, "main .ant-table-placeholder")

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

    def _replace_input_value(self, locator, value, timeout=10):
        element = self.wait_visible(locator, timeout=timeout)
        if element is False:
            return False
        try:
            element.click()
            element.send_keys(Keys.CONTROL, "a")
            element.send_keys(Keys.DELETE)
            time.sleep(0.1)
            if value:
                element.send_keys(str(value))
        except Exception:
            self.clear_by_javascript(locator)
            if value:
                self.send_keys(locator, value)
            element = self.wait_visible(locator, timeout=timeout)
            if element is False:
                return False
        time.sleep(0.1)
        current_value = element.get_attribute("value") or ""
        return current_value == str(value)

    def _enter_operation_log_via_route(self):
        current_url = self.driver.current_url or ""
        if "#" in current_url:
            base_url = current_url.split("#", 1)[0]
        else:
            base_url = current_url.rstrip("/") + "/"
        if not base_url:
            base_url = self.url
        self.open_spa_route(self.operation_log_route, timeout=5)

    def _hard_reload_operation_log_page(self):
        self._enter_operation_log_via_route()
        self.driver.refresh()
        self.wait_for_document_ready(timeout=5)
        return True

    def _ensure_page_ready(self):
        if self.operation_log_route not in (self.driver.current_url or ''):
            return self.common_enter_operation_log()
        ready_locators = [self.page_root, self.username_search_input, self.search_button]
        if self._visible_in_any(ready_locators, timeout=2):
            return True
        self._hard_reload_operation_log_page()
        if self._visible_in_any(ready_locators, timeout=5):
            return True
        return self.common_enter_operation_log()

    def common_enter_operation_log(self):
        self.common_login()
        self.dismiss_intro_if_present()
        self._dismiss_blocking_layers()
        self._enter_operation_log_via_route()
        ready_locators = [self.page_root, self.username_search_input, self.search_button]
        if not self._visible_in_any(ready_locators, timeout=10):
            raise AssertionError("Failed to enter operation log page")
        return True

    def get_visible_rows(self):
        self._ensure_page_ready()
        rows = []
        for row in self.driver.find_elements(*self.table_rows):
            try:
                if not row.is_displayed():
                    continue
                cells = [cell.text.strip() for cell in row.find_elements(by.CSS_SELECTOR, "td")]
                if len(cells) >= 7 and any(cells):
                    rows.append(
                        {
                            "serial": cells[0],
                            "username": cells[1],
                            "login_ip": cells[2],
                            "operation_time": cells[3],
                            "operation_content": cells[4],
                            "result": cells[5],
                            "error_desc": cells[6],
                        }
                    )
            except Exception:
                continue
        return rows

    def get_total_record_count(self):
        self._ensure_page_ready()
        element = self.find_visible_now(self.data_num)
        text = "" if element is False else (element.text or "")
        numbers = re.findall(r"\d+", text)
        if numbers:
            return int(numbers[-1])
        return self.driver.execute_script(
            """
            const rows=[...document.querySelectorAll('main tbody tr')]
              .filter(e=>e.offsetParent!==null&&!e.classList.contains('ant-table-measure-row'));
            const pages=[...document.querySelectorAll('main .ant-pagination-item')]
              .map(e=>Number((e.innerText||'').trim())).filter(Number.isFinite);
            const selected=document.querySelector('main .ant-pagination-options-size-changer .ant-select-selection-item, main .ant-pagination-options-size-changer .ant-select-selection-selected-value');
            const size=Number(((selected?.innerText||'').match(/\d+/)||['0'])[0]);
            const last=pages.length?Math.max(...pages):1;
            return last>1&&size ? (last-1)*size+1 : rows.length;
            """
        )

    def get_pagination_summary_text(self):
        self._ensure_page_ready()
        element = self.find_visible_now(self.data_num)
        summary = "" if element is False else (element.text or "")
        if summary:
            return summary
        return self.driver.execute_script(
            """
            const page=(document.querySelector('main .ant-pagination-item-active')?.innerText||'').trim();
            const row=[...document.querySelectorAll('main tbody tr')]
              .find(e=>e.offsetParent!==null&&!e.classList.contains('ant-table-measure-row'));
            return page&&row ? `page=${page};row=${(row.innerText||'').replace(/\s+/g,' ').trim()}` : '';
            """
        )

    def get_current_page_text(self):
        self._ensure_page_ready()
        element = self.find_visible_now(self.active_page_num)
        return "" if element is False else (element.text or "")

    def get_current_page_size_text(self):
        self._ensure_page_ready()
        element = self.find_visible_now(self.page_size_value)
        return "" if element is False else (element.text or "")

    def set_result_page_size(self, page_size, timeout=8):
        self._ensure_page_ready()
        def selected():
            numbers = re.findall(r'\d+', self.get_current_page_size_text())
            return bool(numbers and int(numbers[0]) == int(page_size))
        if selected():
            return True
        trigger = (by.CSS_SELECTOR, 'main .ant-pagination-options-size-changer .ant-select-selector,main .ant-pagination-options-size-changer .ant-select-selection')
        deadline = time.monotonic()+timeout
        for _ in range(3):
            if not self._click_first_available_safe([trigger], timeout=1):
                continue
            option = self.wait_until(lambda: self.driver.execute_script(
                """
                const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                return [...document.querySelectorAll('.ant-select-dropdown .ant-select-item-option,.ant-select-dropdown [role=option],.ant-select-dropdown li')]
                  .find(e=>{if(!visible(e)||(e.innerText||'').replace(/\s/g,'')!==arguments[0]+'条/页')return false;
                    const r=e.getBoundingClientRect();if(r.width<5||r.height<5)return false;
                    const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
                    return hit&&(hit===e||e.contains(hit));})||null;
                """, str(page_size)), timeout=min(2,max(0.1,deadline-time.monotonic())))
            if option is False:
                self.driver.find_element(by.TAG_NAME,'body').send_keys(Keys.ESCAPE)
                continue
            started = self.driver.execute_script('return performance.now()')
            option.click()
            return wait_query_finished(self, started, timeout=max(1,deadline-time.monotonic()),request_path='/logger/v1/operation/page') and selected()
        return False

    def jump_to_result_page(self, page_num, timeout=8):
        self._ensure_page_ready()
        target_page = str(page_num)
        if self.get_current_page_text() == target_page:
            return True

        numbered = (by.CSS_SELECTOR, f'main .ant-pagination-item[title="{target_page}"]')
        button = self.find_visible_now(numbered)
        if button is not False:
            started = self.driver.execute_script('return performance.now()')
            button.click()
            return wait_query_finished(self, started, timeout=timeout,request_path='/logger/v1/operation/page') and self.get_current_page_text() == target_page

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
        started = self.driver.execute_script('return performance.now()')
        if not self._click_first_available_safe([self.search_button], timeout=5):
            return False
        return wait_query_finished(self, started, timeout=10,request_path='/logger/v1/operation/page')

    def search_by_username(self, username):
        if not self._ensure_page_ready():
            return []
        if not self._replace_input_value(self.username_search_input, username, timeout=8):
            return []
        if not self.submit_search():
            return []
        # The backend query is asynchronous. A fixed short sleep can return
        # the rows from the preceding query, especially on 4.39.7.
        end = time.time() + 4
        last_rows = []
        empty_seen_at = None
        while time.time() < end:
            rows = self.get_visible_rows()
            if rows:
                last_rows = rows
                if all(row["username"] == username for row in rows):
                    return rows
            elif self.has_no_data():
                # The table briefly shows an empty placeholder while the new
                # query is in flight. Treat it as final only after settling.
                empty_seen_at = empty_seen_at or time.time()
                if self.wait_loading_finished(timeout=0.2) and time.time() - empty_seen_at >= 0.3:
                    return []
            time.sleep(0.2)
        return last_rows

    def reset_search(self):
        self._ensure_page_ready()
        button=self.driver.execute_script("return [...document.querySelectorAll('main button')].find(e=>e.offsetParent!==null&&(e.innerText||'').replace(/\\s/g,'')==='清空')||null")
        if button is None:
            raise AssertionError('操作日志清空按钮未定位')
        started=self.driver.execute_script('return performance.now()');button.click()
        if not wait_query_finished(self,started,timeout=10,request_path='/logger/v1/operation/page'):
            raise AssertionError('操作日志清空请求未完成')
        def cleared():
            fields=[self.find_visible_now((by.CSS_SELECTOR,f'main input[placeholder="{name}"]')) for name in ('开始时间','结束时间')]
            fields.append(self.find_visible_now(self.username_search_input))
            return all(field is not False and not (field.get_attribute('value') or '') for field in fields)
        return self.wait_until(cleared,timeout=3) is not False

    def search_by_date_and_username(self, start, end, username):
        if not self._ensure_page_ready():
            return False
        if not self.reset_search():
            raise AssertionError('组合筛选前未清空旧日期与用户名条件')
        set_date_field(self,'开始时间',start)
        set_date_field(self,'结束时间',end)
        self.last_filter_values={key:self.driver.find_element(by.CSS_SELECTOR,f'main input[placeholder="{key}"]').get_attribute('value')
            for key in ('开始时间','结束时间')}
        return bool(self._replace_input_value(self.username_search_input, username, timeout=5) and self.submit_search())

    def has_no_data(self):
        for element in self.driver.find_elements(*self.table_placeholder):
            try:
                if element.is_displayed() and "暂无数据" in (element.text or ""):
                    return True
            except Exception:
                continue
        return False

    def search_username_exact(self, username):
        rows = self.search_by_username(username)
        if not rows:
            return False
        return all(row["username"] == username for row in rows)

    def search_username_failed(self, username):
        rows = self.search_by_username(username)
        value = self.find_visible_now(self.username_search_input)
        return (
            not rows
            and self.has_no_data()
            and value is not False
            and (value.get_attribute("value") or "") == username
        )

    def enter_operation_log(self):
        return self.common_enter_operation_log()
