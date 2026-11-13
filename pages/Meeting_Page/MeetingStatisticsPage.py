from pages.FeatureActionsPage import FeatureActionsPage
from datetime import date
import calendar
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time


class MeetingStatisticsPage(FeatureActionsPage):
    group_name, item_name = "会议管理", "会议统计"
    metrics = ("会议次数", "参会人数", "最大并发点数", "参会总时长", "会议时长", "会议室数量")
    periods = ("近7天", "近30天", "近90天", "近180天")

    def _custom_range_failed(self, reason):
        self.last_custom_range_error = reason
        return False

    def open_statistics(self):
        page = self.open_page(self.group_name, self.item_name)
        return page or self.open_page(self.group_name, self.item_name)

    def select_metric(self, metric):
        locator = ("xpath", f"//main//*[contains(@class,'ant-tabs-tab') or self::div or self::span][normalize-space()='{metric}']")
        return self._click_first_available_safe([locator], timeout=4)

    def select_period(self, period):
        label = next(
            (
                item
                for item in self.driver.find_elements(By.CSS_SELECTOR, "main label")
                if item.is_displayed()
                and "".join((item.text or "").split()) == "".join(period.split())
            ),
            None,
        )
        if label is None:
            return False
        input_element = label.find_element(By.CSS_SELECTOR, "input[type='radio']")
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", label)
        try:
            label.click()
        except Exception:
            self.driver.execute_script(
                """
                const input = arguments[0];
                for (const type of ['mousedown','mouseup','click']) {
                  input.dispatchEvent(new MouseEvent(type,{bubbles:true,cancelable:true,view:window}));
                }
                """,
                input_element,
            )
        if not input_element.is_selected():
            try:
                input_element.send_keys(" ")
            except Exception:
                pass
        return bool(self.wait_until(
            lambda: input_element.is_selected(),
            timeout=3,
        ))

    def select_custom_month_range(self):
        self.last_custom_range_error = ""
        legacy_custom_icon = self.driver.execute_script(
            """
            const picker=[...document.querySelectorAll(
              'main .radio-warp.ant-calendar-picker'
            )].find(item => item.offsetParent !== null &&
              (item.innerText || '').includes('自定义'));
            return picker?.querySelector('.anticon-calendar') || null;
            """
        )
        selected_custom = False
        if legacy_custom_icon is None:
            selected_custom = self.select_period("自定义")
        legacy_picker_open = any(
            item.is_displayed()
            for item in self.driver.find_elements(By.CSS_SELECTOR, ".ant-calendar-picker-container")
        )
        if legacy_custom_icon is not None and not legacy_picker_open:
            self.driver.execute_script("arguments[0].click()", legacy_custom_icon)
            legacy_picker_open = self.wait_until(
                lambda: any(
                    item.is_displayed()
                    for item in self.driver.find_elements(
                        By.CSS_SELECTOR, ".ant-calendar-picker-container"
                    )
                ),
                timeout=4,
                poll_frequency=.1,
            ) is not False
            if not legacy_picker_open:
                return self._custom_range_failed("点击自定义周期后日历未打开")
        elif not selected_custom and not legacy_picker_open:
            custom_trigger = self.driver.execute_script(
                """
                const picker=[...document.querySelectorAll(
                  'main .radio-warp.ant-calendar-picker, main .ant-calendar-picker'
                )].find(item => item.offsetParent !== null &&
                  (item.innerText || '').includes('自定义'));
                return picker?.querySelector('.anticon-calendar') || picker || null;
                """
            )
            if custom_trigger is None:
                return self._custom_range_failed("未找到自定义周期触发器")
            self.driver.execute_script("arguments[0].click()", custom_trigger)
            legacy_picker_open = self.wait_until(
                lambda: any(
                    item.is_displayed()
                    for item in self.driver.find_elements(
                        By.CSS_SELECTOR, ".ant-calendar-picker-container"
                    )
                ),
                timeout=4,
                poll_frequency=.1,
            ) is not False
            if not legacy_picker_open:
                return self._custom_range_failed("点击自定义周期后日历未打开")
        # Ant Design Vue 3 renders a range picker with two editable inputs and
        # `.ant-picker-*` cells. Select today and the same day next month.
        modern_inputs = self.driver.find_elements(
            By.CSS_SELECTOR,
            "main .ant-picker input[placeholder='开始日期'], main .ant-picker input[placeholder='结束日期']",
        )
        if len(modern_inputs) >= 2:
            today = date.today()
            next_month = 1 if today.month == 12 else today.month + 1
            next_year = today.year + 1 if today.month == 12 else today.year
            end_day = min(today.day, calendar.monthrange(next_year, next_month)[1])
            start_title = today.isoformat()
            end_title = date(next_year, next_month, end_day).isoformat()
            picker = modern_inputs[0].find_element(
                By.XPATH,
                "ancestor::div[contains(concat(' ',normalize-space(@class),' '),' ant-picker ')][1]",
            )
            calendar_icon = picker.find_element(By.CSS_SELECTOR, ".ant-picker-suffix .anticon-calendar")
            self.driver.execute_script("arguments[0].click()", calendar_icon)

            def click_date(title):
                return bool(self.driver.execute_script(
                    """
                    const title = arguments[0];
                    const visible = e => !!(e && (e.offsetWidth || e.offsetHeight || e.getClientRects().length));
                    const cell = [...document.querySelectorAll('.ant-picker-dropdown td.ant-picker-cell')]
                      .find(e => visible(e) && e.getAttribute('title') === title &&
                        !e.classList.contains('ant-picker-cell-disabled'));
                    if (!cell) return false;
                    cell.click();
                    return true;
                    """,
                    title,
                ))

            if not self.wait_until(lambda: click_date(start_title), timeout=5):
                return self._custom_range_failed(f"日期面板未找到当天 {start_title}")
            if not self.wait_until(lambda: click_date(end_title), timeout=5):
                return self._custom_range_failed(f"日期面板未找到下月日期 {end_title}")
            selected = bool(self.wait_until(
                lambda: (modern_inputs[0].get_attribute("value") or "").strip()
                and (modern_inputs[1].get_attribute("value") or "").strip(),
                timeout=5,
            ))
            if not selected:
                return self._custom_range_failed("选择日期后输入框未持久显示范围")
            return True

        # The custom range control is itself a radio-button date picker. Its
        # calendar icon both activates the custom option and opens the picker.
        calendar_icon = None
        deadline = time.time() + 4
        while time.time() < deadline and calendar_icon is None:
            calendar_icon = self.driver.execute_script(
                """
                return [...document.querySelectorAll(
                  'main .ant-calendar-picker .anticon-calendar, main .ant-picker .anticon-calendar'
                )].find(icon => icon.offsetParent !== null) || null;
                """
            )
            if calendar_icon is None:
                time.sleep(0.2)
        if calendar_icon is None:
            return False
        if not legacy_picker_open:
            self.driver.execute_script("arguments[0].click()", calendar_icon)
        # This version displays a two-month Ant calendar with no editable
        # range inputs. Select today's cell in the left panel and the same
        # (or earlier) day in next month's right panel, then confirm.
        if not self.wait_until(
            lambda: any(
                item.is_displayed()
                for item in self.driver.find_elements(By.CSS_SELECTOR, "td.ant-calendar-today")
            ),
            timeout=4,
        ):
            return False
        start_cell = self.driver.execute_script(
            """
            return [...document.querySelectorAll(
              '.ant-calendar-range-left td.ant-calendar-today, '
              + '.ant-calendar-range-left td.ant-calendar-selected-start-date'
            )].find(cell =>
              cell.offsetParent !== null &&
              !cell.classList.contains('ant-calendar-last-month-cell') &&
              !cell.classList.contains('ant-calendar-next-month-btn-day')
            ) || null;
            """
        )
        if start_cell is None:
            return False
        request_mark = self.driver.execute_script("return performance.now()")
        start_clicked = self.driver.execute_script(
            """
            const cell=[...document.querySelectorAll(
              '.ant-calendar-range-left td.ant-calendar-today,'+
              '.ant-calendar-range-left td.ant-calendar-selected-start-date'
            )].find(cell => cell.offsetParent !== null &&
              !cell.classList.contains('ant-calendar-last-month-cell') &&
              !cell.classList.contains('ant-calendar-next-month-btn-day'));
            const target=cell?.querySelector('.ant-calendar-date')||cell;
            if(!target) return false;
            target.scrollIntoView({block:'center'});
            target.click();
            return true;
            """
        )
        if not start_clicked:
            return self._custom_range_failed("旧版日历无法点击开始日期")
        start_selected = self.wait_until(
            lambda: len(
                [
                    element
                    for element in self.driver.find_elements(
                        By.CSS_SELECTOR,
                        ".ant-calendar-picker-container input.ant-calendar-input",
                    )
                    if (element.get_attribute("value") or "").strip()
                ]
            ) >= 1,
            timeout=3,
            poll_frequency=.1,
        )
        if start_selected is False:
            return self._custom_range_failed("旧版日历点击开始日期后未产生选中状态")
        # Clicking the start date rerenders the calendar. Re-query the right
        # panel, selecting the same day next month, or its last valid day for
        # shorter months (for example 31 January -> 28 February).
        end_cell = None
        deadline = time.time() + 4
        while time.time() < deadline and end_cell is None:
            end_cell = self.driver.execute_script(
                """
                const targetDay = String(arguments[0]);
                const cells = [...document.querySelectorAll(
                  '.ant-calendar-range-right td.ant-calendar-cell'
                )].filter(cell =>
                  cell.offsetParent !== null &&
                  !cell.classList.contains('ant-calendar-last-month-cell') &&
                  !cell.classList.contains('ant-calendar-next-month-btn-day') &&
                  !cell.classList.contains('ant-calendar-disabled-cell')
                );
                return cells.find(cell => (cell.querySelector('.ant-calendar-date')?.innerText || '').trim() === targetDay) ||
                  cells.at(-1) || null;
                """,
                date.today().day,
            )
            if end_cell is None:
                time.sleep(0.2)
        if end_cell is None:
            return False
        end_clicked = self.driver.execute_script(
            """
            const targetDay=String(arguments[0]);
            const cells=[...document.querySelectorAll(
              '.ant-calendar-range-right td.ant-calendar-cell'
            )].filter(cell => cell.offsetParent !== null &&
              !cell.classList.contains('ant-calendar-last-month-cell') &&
              !cell.classList.contains('ant-calendar-next-month-btn-day') &&
              !cell.classList.contains('ant-calendar-disabled-cell'));
            const cell=cells.find(cell =>
              (cell.querySelector('.ant-calendar-date')?.innerText||'').trim()===targetDay)
              || cells.at(-1);
            const target=cell?.querySelector('.ant-calendar-date')||cell;
            if(!target) return false;
            target.scrollIntoView({block:'center'});
            target.click();
            return true;
            """,
            date.today().day,
        )
        if not end_clicked:
            return self._custom_range_failed("旧版日历无法点击结束日期")
        end_selected = self.wait_until(
            lambda: len(
                [
                    element
                    for element in self.driver.find_elements(
                        By.CSS_SELECTOR,
                        ".ant-calendar-picker-container input.ant-calendar-input",
                    )
                    if (element.get_attribute("value") or "").strip()
                ]
            ) >= 2
            or not any(
                item.is_displayed()
                for item in self.driver.find_elements(
                    By.CSS_SELECTOR, ".ant-calendar-picker-container"
                )
            ),
            timeout=3,
            poll_frequency=.1,
        )
        if end_selected is False:
            return self._custom_range_failed("旧版日历点击结束日期后未产生选中状态")
        def range_values_selected():
            values = [
                (element.get_attribute("value") or "").strip()
                for element in self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "main .ant-calendar-range-picker-input, "
                    "main .ant-calendar-picker input, "
                    ".ant-calendar-picker-container input.ant-calendar-input",
                )
                if (element.get_attribute("value") or "").strip()
            ]
            return len(values) >= 2

        values_selected = self.wait_until(
            lambda: range_values_selected()
            or not any(
                item.is_displayed()
                for item in self.driver.find_elements(
                    By.CSS_SELECTOR, ".ant-calendar-picker-container"
                )
            ),
            timeout=5,
        )
        if not values_selected:
            return self._custom_range_failed("旧版日历选择后未写入开始和结束日期")
        picker_open = any(
            item.is_displayed()
            for item in self.driver.find_elements(
                By.CSS_SELECTOR, ".ant-calendar-picker-container"
            )
        )
        confirmed = None if not picker_open else self.driver.execute_script(
                """
                const visible = [...document.querySelectorAll('.ant-calendar-ok-btn')]
                  .find(button => button.offsetParent !== null);
                if (!visible) return null;
                if (visible.classList.contains('ant-calendar-ok-btn-disabled')) return false;
                visible.click();
                return true;
                """
        )
        # Date-only legacy pickers close immediately after the end date and do
        # not require an OK action. A present but disabled OK is a real error.
        if confirmed is False:
            return self._custom_range_failed("旧版日期范围已选择，但确定按钮仍不可用")
        if picker_open and confirmed is None:
            try:
                self.driver.switch_to.active_element.send_keys(Keys.ESCAPE)
            except Exception:
                self.driver.execute_script("document.body.click()")
        closed = self.wait_until(
            lambda: not any(
                item.is_displayed()
                for item in self.driver.find_elements(
                    By.CSS_SELECTOR, ".ant-calendar-picker-container"
                )
            ),
            timeout=4,
        )
        request_completed = self.wait_until(
            lambda: self.driver.execute_script(
                """
                const mark=arguments[0];
                return performance.getEntriesByType('resource').some(item =>
                  item.startTime >= mark &&
                  ['fetch','xmlhttprequest'].includes(item.initiatorType));
                """,
                request_mark,
            ),
            timeout=5,
            poll_frequency=.1,
        ) is not False
        range_persisted = False
        if closed and not range_values_selected() and not request_completed:
            reopen_icon = self.driver.execute_script(
                """
                return [...document.querySelectorAll(
                  'main .ant-calendar-picker .anticon-calendar, main .ant-picker .anticon-calendar'
                )].find(icon => icon.offsetParent !== null) || null;
                """
            )
            if reopen_icon is not None:
                self.driver.execute_script("arguments[0].click()", reopen_icon)
                range_persisted = self.wait_until(
                    lambda: self.driver.execute_script(
                        """
                        const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                        const selected=[...document.querySelectorAll(
                          '.ant-calendar-range-start,.ant-calendar-range-end,'+
                          '.ant-calendar-selected-start-date,.ant-calendar-selected-end-date,'+
                          '.ant-calendar-in-range-cell,.ant-calendar-selected-day'
                        )].filter(visible);
                        return selected.length >= 2;
                        """
                    ),
                    timeout=4,
                    poll_frequency=.1,
                ) is not False
                try:
                    self.driver.switch_to.active_element.send_keys(Keys.ESCAPE)
                except Exception:
                    self.driver.execute_script("document.body.click()")
        if closed and (
            range_values_selected() or request_completed or range_persisted
        ):
            return True
        values = [
            (element.get_attribute("value") or "").strip()
            for element in self.driver.find_elements(
                By.CSS_SELECTOR,
                "main .ant-calendar-range-picker-input, main .ant-calendar-picker input",
            )
        ]
        return self._custom_range_failed(
            f"旧版日期范围最终状态异常：弹层关闭={bool(closed)}，"
            f"请求完成={request_completed}，范围持久化={range_persisted}，"
            f"输入值={values!r}"
        )
