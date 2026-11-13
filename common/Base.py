# -*- coding:utf-8 -*-
import time

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains


def open_browser(browser: str, options=None):
    """
    封装打开浏览器的函数
    :param browser: 具体打开的浏览器 chrome firefox edge
    :return:
    """
    if browser.lower() == 'chrome':
        if options is None:
            return webdriver.Chrome()
        return webdriver.Chrome(options=options)
    elif browser.lower() == 'firefox':
        return webdriver.Firefox()
    elif browser.lower() == 'edge':
        return webdriver.Edge()

    else:
        print("输入的浏览器不合法,请输入 chrome firefox edge")
        return None


class Base(object):
    def __init__(self, browser="chrome", driver=None):
        if driver is not None:
            self.driver = driver
        else:
            self.driver = open_browser(browser)
            if self.driver is None:
                raise ValueError(f"Unsupported browser: {browser}")

        # The runner owns the viewport of an injected browser. Maximizing it
        # here can reset headless Chrome to 800x600 and also breaks resolution
        # tests when another Page Object is constructed.
        if driver is None:
            try:
                self.driver.maximize_window()
            except Exception:
                pass

    def open_url(self, url: str):
        """
        打开网页
        :param url:网页的地址,可以输入域名
        :return:
        """
        try:
            # 判断输入的网址是否是 http://或者https://开头,是就直接打开,不是就在前面加上http://
            if url.startswith('http://') or url.startswith('https://'):
                self.driver.get(url)
            else:
                url = "http://" + url
                self.driver.get(url)
        except Exception as e:
            print(f"网页打开失败,失败提示:{e}")
            print(f"输入网址是{url}")

    def find_element(self, locator: tuple, timeout=20):
        """
        单个元素定位,成功返回元素,失败返回False
        :param locator: 定位器
        :param timeout: 超时时间
        :return:
        """
        try:
            return WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located(locator))

        except Exception as e:
            print(f"元素“{locator}”定位失败{e}")
            return False

    def find_elements(self, locator: tuple, timeout=20):
        """
        多个元素定位,定位成功返回元素列表,失败返回False
        :param locator:定位器
        :param timeout: 超时时间
        :return:
        """
        try:
            return WebDriverWait(self.driver, timeout).until(EC.presence_of_all_elements_located(locator))
        except Exception as e:
            print(f"元素定位失败{e}")
            return False

    def wait_visible(self, locator: tuple, timeout=20):
        """
        Wait until the element is visible.
        """
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located(locator)
            )
        except Exception as e:
            print(f"Element wait_visible failed: {locator}, {e}")
            return False

    def wait_clickable(self, locator: tuple, timeout=20):
        """
        Wait until the element is clickable.
        """
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable(locator)
            )
        except Exception as e:
            print(f"Element wait_clickable failed: {locator}, {e}")
            return False

    def wait_text_contains(self, locator: tuple, expected_text: str, timeout=20):
        """
        Wait until the element text contains expected text.
        """
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.text_to_be_present_in_element(locator, expected_text)
            )
        except Exception as e:
            print(f"Element wait_text_contains failed: {locator}, {e}")
            return False

    def wait_until(self, condition, timeout=5, poll_frequency=0.2):
        """
        Poll a callable until it returns a truthy value.
        """
        end = time.time() + timeout
        while time.time() < end:
            try:
                value = condition()
                if value:
                    return value
            except Exception:
                pass
            time.sleep(poll_frequency)
        return False

    def find_visible_now(self, locator):
        """Return the first currently visible element without introducing a wait."""
        for element in self.driver.find_elements(*locator):
            try:
                if element.is_displayed():
                    return element
            except Exception:
                continue
        return False

    def ensure_page_ready_fast(self, route=None, locators=()):
        """Cheap route and marker check used before a slower compatibility path."""
        if route and route not in (self.driver.current_url or ""):
            return False
        return any(self.find_visible_now(locator) is not False for locator in locators)

    def open_spa_route(self, route, timeout=5):
        """Navigate inside the authenticated SPA without reloading its shell."""
        route = str(route or "")
        if not route:
            return False
        current = self.driver.current_url or ""
        if route in current:
            return True
        base = current.split("#", 1)[0]
        can_use_hash = bool(base and "login" not in current.lower())
        if can_use_hash:
            try:
                self.driver.execute_script("window.location.hash = arguments[0];", route)
                changed = self.wait_until(
                    lambda: route in (self.driver.current_url or ""),
                    timeout=timeout,
                    poll_frequency=0.05,
                )
                if changed is not False:
                    return True
            except Exception:
                pass
        target = (base or "").rstrip("/") + "/" + route
        self.driver.get(target)
        return bool(
            self.wait_for_document_ready(timeout=timeout)
            and route in (self.driver.current_url or "")
        )

    def wait_loading_finished(self, timeout=5, poll_frequency=0.1):
        """Wait for visible Ant Design loading masks to disappear."""
        def finished():
            return bool(self.driver.execute_script(
                """
                const visible = element => !!(element && (
                  element.offsetWidth || element.offsetHeight || element.getClientRects().length));
                const selectors = [
                  '.ant-spin-spinning', '.ant-table-loading', '.ant-skeleton-active',
                  '.ant-modal-confirm-loading', '[aria-busy="true"]'
                ];
                return !selectors.some(selector =>
                  [...document.querySelectorAll(selector)].some(visible));
                """
            ))
        return self.wait_until(finished, timeout=timeout, poll_frequency=poll_frequency) is not False

    def table_snapshot(self):
        """Capture visible table rows and active page for mutation-based waits."""
        return self.driver.execute_script(
            """
            const visible = element => !!(element && (
              element.offsetWidth || element.offsetHeight || element.getClientRects().length));
            const rows = [...document.querySelectorAll('main tbody tr')]
              .filter(row => visible(row) && !row.classList.contains('ant-table-measure-row'))
              .map(row => (row.innerText || '').replace(/\s+/g, ' ').trim());
            const page = [...document.querySelectorAll('main .ant-pagination-item-active')]
              .filter(visible).map(item => (item.innerText || '').trim())[0] || '';
            return JSON.stringify({page, rows});
            """
        ) or ""

    def wait_table_changed(self, previous_snapshot, timeout=5, poll_frequency=0.1):
        """Wait for a completed table mutation, not for a fixed delay."""
        return self.wait_until(
            lambda: self.wait_loading_finished(timeout=0.2, poll_frequency=0.05)
            and self.table_snapshot() != previous_snapshot,
            timeout=timeout,
            poll_frequency=poll_frequency,
        ) is not False

    def wait_modal_state(self, visible, timeout=5, poll_frequency=0.1):
        """Wait for the top active Ant Design modal to appear or disappear."""
        def modal_visible():
            return bool(self.driver.execute_script(
                """
                const visible = element => !!(element && (
                  element.offsetWidth || element.offsetHeight || element.getClientRects().length));
                return [...document.querySelectorAll(
                  '.ant-modal-content,.ant-drawer-content,.ant-modal-confirm')].some(visible);
                """
            ))
        return self.wait_until(
            lambda: modal_visible() is bool(visible),
            timeout=timeout,
            poll_frequency=poll_frequency,
        ) is not False

    def wait_operation_evidence(self, conditions, timeout=6, poll_frequency=0.1):
        """Return the first named observable evidence produced by an operation."""
        def evidence():
            for name, condition in conditions:
                try:
                    value = condition()
                    if value:
                        return {"name": name, "value": value}
                except Exception:
                    continue
            return False
        return self.wait_until(evidence, timeout=timeout, poll_frequency=poll_frequency)

    def wait_for_document_ready(self, timeout=5, poll_frequency=0.1):
        """
        Wait until document.readyState becomes complete.
        """
        return self.wait_until(
            lambda: self.driver.execute_script("return document.readyState") == "complete",
            timeout=timeout,
            poll_frequency=poll_frequency,
        )

    def send_keys(self, locator: tuple, text: str, timeout=20):
        """
        定位之后进行输入内容
        :param text: 输入的文本信息
        :param locator: 定位器
        :param timeout: 超时时间
        :return:
        """
        element = self.wait_visible(locator, timeout)
        if element is not False:
            element.send_keys(str(text))
        else:
            print("元素定位失败了,不能输入信息")

    def click(self, locator: tuple, timeout=10):
        """
        根据输入元素进行点击
        :param locator:
        :param timeout:
        :return:
        """
        element = self.wait_clickable(locator, timeout)
        if element is not False:
            try:
                element.click()
            except Exception:
                # Fallback for transient overlays intercepting native click.
                self.driver.execute_script("arguments[0].click();", element)
        else:
            print("元素定位失败了,不能点击")


    def js_click(self, locator: tuple, timeout=20):
        """
        根据输入元素进行点击,因为其他元素遮挡，使用js的点击方法
        :param locator:
        :param timeout:
        :return:
        """
        element = self.find_element(locator, timeout)
        if element is not False:
            # self.driver.execute_script("arguments[0].click();", element)
            self.driver.execute_script("""
                        var event = new MouseEvent('click', {
                            bubbles: true,
                            cancelable: true,
                            view: window
                        });
                        arguments[0].dispatchEvent(event);
                    """, element)
        else:
            print("元素定位失败了,不能点击")


    def clear(self, locator: tuple, timeout=20):
        """
        根据输入元素进行清空
        :param locator:
        :param timeout:
        :return:
        """
        element = self.find_element(locator, timeout)
        if element is not False:
            element.clear()
        else:
            print("元素定位失败了,不能清空")

    def clear_by_javascript(self, locator: tuple, timeout=20):
        """
        使用JavaScript强制清空输入框内容
        :param locator: 元素定位器
        :param timeout: 超时时间
        :return: 清空成功返回True，否则返回False
        """
        element = self.find_element(locator, timeout)
        if element is False:
            print("元素定位失败,无法清空")
            return False

        try:
            # 使用JavaScript直接设置元素值为空
            self.driver.execute_script(
                "arguments[0].value = '';",
                element
            )

            # 触发input事件（确保React/Vue/Angular等框架能够检测到变化）
            self.driver.execute_script(
                "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));",
                element
            )

            # 触发change事件（适用于传统表单）
            self.driver.execute_script(
                "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
                element
            )

            # 验证清空是否成功
            if element.get_attribute('value') == '':
                return True
            else:
                print("JavaScript清空操作未完全生效")
                return False

        except Exception as e:
            print(f"JavaScript清空操作异常: {str(e)}")
            return False


    def get_attribute(self,locator,attribute_name):
        """
        获取元素的属性
        """
        element = self.find_element(locator)
        if element is not False:
            return element.get_attribute(attribute_name)
        else:
            print("元素定位失败了,不能清空")

    def is_selected(self, locator: tuple, timeout=20):
        try:
            element = self.find_element(locator, timeout)
        except Exception as e:
            print(f"元素未找到{e}")
        else:
            return element.is_selected()

    def scroll_bar(self, x, y):
        """
        滚动条方法封装
        :param x: 横向移动,x初始为0
        :param y: 纵向移动,y初始为0
        :return:
        """
        js = f"window.scrollTo({x},{y})"
        self.driver.execute_script(js)

    def get_element_text(self, locator: tuple, timeout=10):
        """获取元素的文本信息"""
        element = self.find_element(locator, timeout)
        if element:
            try:
                # 额外等待元素可见
                WebDriverWait(self.driver, timeout).until(
                    EC.visibility_of(element)
                )
                return element.text
            except Exception:
                return None
        return None

    def get_text_assert(self, expected, locator: tuple, timeout=20):
        """
        获取文本信息进行断言
        :param expected: 预期结果
        :param locator: 定位器
        :param timeout: 超时时间
        :return: 预期内容和文本相等返回 True  不同返回False
        """
        text_content = self.get_element_text(locator, timeout)
        if text_content is not None:
            if expected == text_content:
                return True
            else:
                return False
        else:
            return False

    def get_text_assert_in(self, expected, locator: tuple, timeout=20):
        """
        获取文本信息进行断言
        :param expected: 预期结果
        :param locator: 定位器
        :param timeout: 超时时间
        :return: 预期内容在获取内容里面返回 True  不同返回False
        """
        text_content = self.get_element_text(locator, timeout)
        if text_content is not None:
            if expected in text_content:
                return True
            else:
                return False
        else:
            return False


    def send_keys_tab(self, locator: tuple, timeout=20):
        """
        键入tab
        """
        element = self.find_element(locator, timeout)
        if element is not False:
            element.send_keys(Keys.TAB)
        else:
            print("元素定位失败了,不能输入信息")


    def send_keys_enter(self, locator: tuple, timeout=20):
        """
        键入回车键(Enter)
        """
        element = self.find_element(locator, timeout)
        if element is not False:
            element.send_keys(Keys.ENTER)
        else:
            print("元素定位失败，无法执行回车操作")

    def switch_iframe(self, iframe_location: tuple, timeout=20):
        """
        切换到指定的iframe框架
        :param iframe_location: iframe元素的定位信息
        :param timeout: 超时时间
        :return: 布尔值，表示切换是否成功
        """
        try:
            # 查找iframe元素
            iframe_element = self.find_element(iframe_location, timeout)

            if iframe_element is not False:
                # 切换到指定的iframe
                self.driver.switch_to.frame(iframe_element)
                print("成功切换到iframe框架")
                return True
            else:
                print("iframe元素定位失败，无法切换")
                return False

        except Exception as e:
            print(f"切换iframe时发生异常: {str(e)}")
            return False

    def switch_popup(self, popup_location: tuple, close_button_location: tuple = None, timeout=20):
        """
        切换弹窗状态（打开或关闭）
        :param popup_location: 弹窗元素的定位信息
        :param close_button_location: 关闭按钮的定位信息（可选）
        :param timeout: 超时时间
        :return: 布尔值，表示操作是否成功
        """
        try:
            # 查找弹窗元素
            popup_element = self.find_element(popup_location, timeout)

            if popup_element is not False:
                # 如果弹窗存在，尝试关闭它
                if close_button_location:
                    # 如果有指定关闭按钮，点击关闭按钮
                    close_btn = self.find_element(close_button_location, timeout)
                    if close_btn is not False:
                        close_btn.click()
                        print("弹窗已通过关闭按钮关闭")
                        return True
                    else:
                        print("关闭按钮定位失败")
                        return False
                else:
                    # 如果没有指定关闭按钮，直接点击弹窗外部或按ESC（这里需要根据实际情况调整）
                    # 这里可以添加其他关闭弹窗的逻辑，比如按ESC键等
                    print("弹窗存在，但未提供关闭按钮定位")
                    return True
            else:
                # 如果弹窗不存在，尝试触发显示弹窗
                # 这里需要根据实际情况触发弹窗显示，比如点击某个按钮
                print("弹窗不存在，可能需要触发显示")
                return False

        except Exception as e:
            print(f"切换弹窗时发生异常: {str(e)}")
            return False

    def send_keys_enter_after_input_by_js(self, locator: tuple, value: str, timeout=20):
        element = self.find_element(locator, timeout)
        if element is not False:
            # 设置元素的值
            self.driver.execute_script("arguments[0].value = arguments[1]", element, value)

            # 触发input事件
            self.driver.execute_script("""
                var event = new Event('input', { bubbles: true });
                arguments[0].dispatchEvent(event);
            """, element)

            # 触发change事件（有些组件监听change事件）
            self.driver.execute_script("""
                var event = new Event('change', { bubbles: true });
                arguments[0].dispatchEvent(event);
            """, element)

            # 触发keydown事件（Enter键）
            self.driver.execute_script("""
                var event = new KeyboardEvent('keydown', {
                    key: 'Enter',
                    code: 'Enter',
                    keyCode: 13,
                    which: 13,
                    bubbles: true
                });
                arguments[0].dispatchEvent(event);
            """, element)

            # 触发keyup事件（Enter键）
            self.driver.execute_script("""
                var event = new KeyboardEvent('keyup', {
                    key: 'Enter',
                    code: 'Enter',
                    keyCode: 13,
                    which: 13,
                    bubbles: true
                });
                arguments[0].dispatchEvent(event);
            """, element)

            # 也可以尝试触发blur事件（因为有时输入后失去焦点才会触发）
            # self.driver.execute_script("arguments[0].blur();", element)

        else:
            print("元素定位失败，无法执行JS输入+回车操作")



    def verify_data_count(self, locator: tuple, expected_count: int, timeout=20) -> bool:
        """
        验证指定元素集合的数量是否符合预期
        :param locator: 定位多个元素的定位器
        :param expected_count: 期望的元素数量
        :param timeout: 查找元素的超时时间
        :return: 数量符合预期返回True，否则返回False
        """
        try:
            # 查找元素集合
            elements = self.find_elements(locator, timeout)

            if elements is not False:
                # 获取实际数量
                actual_count = len(elements)

                # 验证数量是否符合预期
                if actual_count == expected_count:
                    print(f"验证成功: 找到 {actual_count} 个元素，符合预期数量 {expected_count}")
                    return True
                else:
                    print(f"验证失败: 找到 {actual_count} 个元素，但预期数量为 {expected_count}")
                    return False
            else:
                print("元素定位失败，无法验证数量")
                return False
        except Exception as e:
            print(f"验证数据数量时发生异常: {str(e)}")
            return False

    def js_send_keys(self, locator: tuple, text: str, timeout=20):
        """
        使用JavaScript直接设置元素的value属性来输入内容
        适用于常规send_keys无法交互的元素（如隐藏、禁用或只读元素）

        :param locator: 定位器 (By, value)
        :param text: 要输入的文本
        :param timeout: 查找元素的超时时间
        :return: 操作是否成功
        """
        element = self.find_element(locator, timeout)

        if element is False:
            print(f"元素定位失败, 无法输入文本: {text}")
            return False

        try:
            # 使用JavaScript直接设置元素的value属性
            self.driver.execute_script(
                "arguments[0].value = arguments[1];",
                element,
                str(text)
            )

            # 触发输入事件（模拟用户输入）
            self.driver.execute_script(
                "var event = new Event('input', { bubbles: true });"
                "arguments[0].dispatchEvent(event);",
                element
            )

            # 触发变更事件（模拟内容变更）
            self.driver.execute_script(
                "var event = new Event('change', { bubbles: true });"
                "arguments[0].dispatchEvent(event);",
                element
            )

            print(f"通过JS成功输入文本: {text}")
            return True

        except Exception as e:
            print(f"JS输入文本失败: {str(e)}")
            # 截图记录错误
            self.driver.save_screenshot("js_send_keys_error.png")
            return False

    def js_get_text(self, locator: tuple, timeout=20, include_hidden=False):
        """
        使用JavaScript获取元素的文本内容

        相比常规的element.text方法，此方法可以：
        - 获取隐藏元素的文本
        - 获取伪元素内容(::before, ::after)
        - 获取表单元素的值
        - 获取被截断的文本

        :param locator: 定位器 (By, value)
        :param timeout: 查找元素的超时时间
        :param include_hidden: 是否包含隐藏元素的内容
        :return: 元素的文本内容（字符串），找不到元素时返回None
        """
        element = self.find_element(locator, timeout)

        if element is False:
            print(f"元素定位失败, 无法获取文本: {locator}")
            return None

        try:
            # 使用JavaScript获取文本内容
            script = """
            // 获取元素
            var element = arguments[0];

            // 处理不同的元素类型
            if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                // 表单元素返回value
                return element.value || '';
            } else if (element.tagName === 'SELECT') {
                // 下拉框返回选中项的文本
                return element.options[element.selectedIndex]?.text || '';
            } else {
                // 其他元素
                if (arguments[1]) {
                    // 包含隐藏内容时使用textContent
                    return element.textContent || '';
                } else {
                    // 只获取可见文本时使用innerText
                    return element.innerText || '';
                }
            }
            """

            # 执行JavaScript并返回结果
            text = self.driver.execute_script(script, element, include_hidden)

            # 清理文本（去除多余空格）
            cleaned_text = ' '.join(str(text).split()).strip()

            return cleaned_text if cleaned_text else None

        except Exception as e:
            print(f"JS获取文本失败: {str(e)}")
            # 尝试使用常规方法作为后备
            try:
                return element.text.strip() if element.text.strip() else None
            except:
                return None

    def refresh(self):
        """页面刷新"""
        self.driver.refresh()

    def close_browser(self):
        self.driver.quit()


if __name__ == '__main__':
    # open_browser('chrome')
    # open_browser("Edge")
    bs = Base('chrome')
    bs.open_url('http://192.168.10.150/dashboard/analysis')

