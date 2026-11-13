# -*- coding:utf-8 -*-
import json
import time

import allure
from common.Base import Base
from common.captcha_ocr import captcha_recognizer
from common.click_captcha import click_captcha_recognizer
from conf.conf import ConfigManager
from selenium.webdriver.common.by import By as by
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import StaleElementReferenceException
from common.ui_state import wait_stable_state

_LOGIN_TRANSPORT_OBSERVER = r"""
(() => {
  if (window.__cesLoginTransport) return;
  const state=window.__cesLoginTransport={pending:{},completed:[],sequence:0};
  const pathOf=u=>{try{return new URL(u,location.href).pathname}catch{return ''}};
  const relevant=p=>p.startsWith('/auth/v1/login') || ['/serv/v1/index/info','/serv/v1/index/link'].includes(p);
  const begin=p=>{if(!relevant(p))return null;const id=++state.sequence;
    state.pending[id]={path:p,start:performance.now()};return id};
  const end=(id,status)=>{if(!id||!state.pending[id])return;
    state.completed.push({...state.pending[id],status,end:performance.now()});
    delete state.pending[id];state.completed=state.completed.slice(-30)};
  const open=XMLHttpRequest.prototype.open, send=XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open=function(method,url,...args){this.__cesPath=pathOf(url);return open.call(this,method,url,...args)};
  XMLHttpRequest.prototype.send=function(...args){const id=begin(this.__cesPath||'');
    this.addEventListener('loadend',()=>end(id,this.status),{once:true});
    try{return send.apply(this,args)}catch(error){end(id,0);throw error}};
  const fetch=window.fetch;
  if(fetch)window.fetch=function(input,...args){const id=begin(pathOf(typeof input==='string'?input:input?.url));
    return fetch.call(this,input,...args).then(response=>{end(id,response.status);return response},error=>{end(id,0);throw error})};
})();
"""


class LoginPage(Base):
    """Login page object shared by all modules."""

    url = ConfigManager.HST_URL

    login_name = (by.CSS_SELECTOR, "form input:not([type='password']):not([type='checkbox']):not(#inputCode):not([placeholder*='验证码'])")
    password = (by.CSS_SELECTOR, "form input[type='password']")
    input_code = (by.CSS_SELECTOR, "form input[placeholder*='验证码']")
    login_button = (by.CSS_SELECTOR, "form button.ant-btn-primary, form button")
    img_code = (by.CSS_SELECTOR, "form img")

    security_layer = (by.CSS_SELECTOR, ".layer_body")
    security_image = (by.CSS_SELECTOR, ".layer_body .verify_img")
    security_prompt = (by.CSS_SELECTOR, ".layer_body .verify_text")
    security_refresh = (by.CSS_SELECTOR, ".layer_body .layer_refresh")
    security_close = (by.CSS_SELECTOR, ".layer_body .layer_close")
    security_markers = (by.CSS_SELECTOR, ".layer_body .point_num")

    close_button = (by.CLASS_NAME, "introjs-skipbutton")
    index_user_name = (
        by.CSS_SELECTOR,
        "header .hst-user-name",
    )
    authenticated_shell = (by.CSS_SELECTOR, "main, aside")

    login_error_tips = [
        (by.CSS_SELECTOR, ".ant-message-notice-content"),
        (by.CSS_SELECTOR, ".ant-notification-notice-message"),
        (
            by.CSS_SELECTOR,
            "form .ant-form-explain, form .ant-form-item-explain-error, "
            "form .ant-form-item-explain-connected, form [role='alert']",
        ),
    ]

    last_login_error = ""
    last_authenticated_username = ""
    last_security_solution = None

    def open_login_url(self):
        self._install_login_observer()
        self.open_url(self.url)
        self.wait_for_document_ready(timeout=10)

    def _install_login_observer(self):
        if not getattr(self.driver, '_ces_login_observer_installed', False):
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': _LOGIN_TRANSPORT_OBSERVER})
            self.driver._ces_login_observer_installed = True
        self.driver.execute_script(_LOGIN_TRANSPORT_OBSERVER)

    def wait_login_form_ready(self, timeout=10):
        def ready():
            return self.driver.execute_script(
                """
                const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                const user=[...document.querySelectorAll(arguments[0])].find(visible);
                const password=[...document.querySelectorAll(arguments[1])].find(visible);
                const pending=Object.values(window.__cesLoginTransport?.pending||{});
                return location.hash.includes('login') && document.readyState==='complete' &&
                  user && password && !pending.length ? {document:performance.timeOrigin} : null;
                """, self.login_name[1], self.password[1],
            )
        return wait_stable_state(self, ready, timeout=timeout, stable_for=0.25) is not False

    def send_users_name(self, username):
        self._fill_login_input(self.login_name, username)

    def send_passwords(self, password):
        self._fill_login_input(self.password, password)

    def _fill_login_input(self, locator, value):
        value = str(value or "")
        for attempt in range(3):
            try:
                field = self.wait_visible(locator, timeout=8)
                if field is False:
                    raise AssertionError("登录输入框未显示")
                maxlength = field.get_attribute("maxlength")
                expected = value[:int(maxlength)] if maxlength and int(maxlength) >= 0 else value
                field.click()
                field.send_keys(Keys.CONTROL, "a")
                field.send_keys(Keys.BACKSPACE)
                if value:
                    field.send_keys(value)
                field.send_keys(Keys.TAB)

                def committed():
                    current = self._first_visible(locator)
                    if current is False or current.get_attribute("value") != expected:
                        return False
                    return {"committed": True}

                if wait_stable_state(self, committed, timeout=4, stable_for=0.15) is False:
                    if attempt < 2 and self.wait_login_form_ready():
                        continue  # Refill only; no extra authentication request.
                    raise AssertionError(f"登录字段值在第{attempt+1}次填写后仍未稳定，未提交登录")
                return
            except StaleElementReferenceException:
                if attempt == 2:
                    raise

    def click_button(self):
        self.click(self.login_button)

    def reset_login_state(self):
        self.last_login_error = ""
        self.last_login_request_started = None
        self._install_login_observer()
        try:
            self.driver.delete_all_cookies()
            self.driver.execute_script(
                "window.localStorage.clear(); window.sessionStorage.clear();"
            )
        except Exception:
            pass
        # Discard the old document and its pending response handlers. Navigating
        # to the same hash alone can reuse Vue components and erase new inputs.
        self.driver.get('about:blank')
        # Go to the actual login route instead of the application root, whose
        # asynchronous session/bootstrap redirects can erase newly typed fields.
        self.open_url(self.url.rstrip('/') + '/#/ui/login')
        self.wait_for_document_ready(timeout=10)
        return self.wait_login_form_ready()

    def login_with(self, username, password, captcha=None):
        manager=getattr(self.driver,'_ces_management_driver',None)
        if manager is not None and str(username)==ConfigManager.USERNAME:
            manager._needs_admin_login=True
        self._install_login_observer()
        if not self.wait_login_form_ready():
            raise AssertionError("登录初始化请求尚未完成，未填写或提交凭据")
        for attempt in range(2):
            self.send_users_name(username)
            self.send_passwords(password)
            matched = self.driver.execute_script(
                """
                const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                const field=s=>[...document.querySelectorAll(s)].find(visible);
                const matches=(el,value)=>!!el && el.value===String(value).slice(0,el.maxLength<0?undefined:el.maxLength);
                return matches(field(arguments[0]),arguments[2]) && matches(field(arguments[1]),arguments[3]);
                """, self.login_name[1], self.password[1], str(username or ''), str(password or ''),
            )
            if matched:
                break
            if attempt == 1:
                raise AssertionError("提交前凭据字段被重绘覆盖，未提交登录")
        if captcha is not None and self.is_captcha_visible():
            self.send_captcha(captcha)
        self.last_login_request_started = self.driver.execute_script('return performance.now()')
        self.click_button()
        return self.last_login_request_started

    def wait_login_response(self, started=None, timeout=10):
        started = started if started is not None else self.last_login_request_started
        return self.wait_until(
            lambda: self.driver.execute_script(
                """
                return (window.__cesLoginTransport?.completed||[]).find(e=>
                  e.path==='/auth/v1/login' && e.start>=arguments[0]) || null;
                """, started,
            ), timeout=timeout, poll_frequency=0.1,
        )

    def captcha_diagnostics(self):
        # Never include full image URLs, verification tokens or credentials.
        return self.driver.execute_script(
            """
            const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
            const image=[...document.querySelectorAll('form img')].find(visible);
            return {inputVisible:[...document.querySelectorAll('form input')].some(e=>visible(e)&&(e.placeholder||'').includes('验证码')),
              imageVisible:!!image,complete:image?.complete||false,width:image?.naturalWidth||0,
              requests:(window.__cesLoginTransport?.completed||[]).map(e=>({path:e.path,status:e.status}))};
            """
        )

    def send_captcha(self, value):
        self.clear_by_javascript(self.input_code)
        self.send_keys(self.input_code, value)

    def _first_visible(self, locator, timeout=0):
        end = time.time() + max(0, timeout)
        while True:
            for element in self.driver.find_elements(*locator):
                try:
                    if element.is_displayed():
                        return element
                except Exception:
                    continue
            if time.time() >= end:
                return False
            time.sleep(0.05)

    def is_captcha_visible(self, timeout=1):
        def ready():
            return self.driver.execute_script(
                """
                const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
                const input=[...document.querySelectorAll('form input')].find(e=>
                  visible(e)&&(e.placeholder||'').includes('验证码'));
                const image=[...document.querySelectorAll('form img')].find(e=>visible(e));
                return !!(input&&image&&image.complete&&image.naturalWidth>0);
                """
            )
        if timeout <= 0:
            return bool(ready())
        return self.wait_until(ready, timeout=timeout, poll_frequency=0.1) is not False

    def is_click_security_visible(self, timeout=1):
        image = self._first_visible(self.security_image, timeout=timeout)
        prompt = self._first_visible(self.security_prompt, timeout=0)
        return image is not False and prompt is not False

    def get_click_security_prompt(self):
        prompt = self.wait_visible(self.security_prompt, timeout=2)
        return "" if prompt is False else (prompt.text or "").strip()

    def get_click_security_marker_count(self):
        count = 0
        for marker in self.driver.find_elements(*self.security_markers):
            try:
                if marker.is_displayed():
                    count += 1
            except Exception:
                continue
        return count

    def refresh_click_security(self):
        image = self.wait_visible(self.security_image, timeout=3)
        refresh = self.wait_clickable(self.security_refresh, timeout=3)
        if image is False or refresh is False:
            return False
        before = image.get_attribute("src") or ""
        try:
            refresh.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", refresh)
        changed = self.wait_until(
            lambda: self._click_security_image_changed(before),
            timeout=5,
            poll_frequency=0.1,
        )
        return changed is not False

    def close_click_security(self):
        close = self.wait_clickable(self.security_close, timeout=2)
        if close is False:
            return False
        try:
            close.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", close)
        return self.wait_until(
            lambda: not self.is_click_security_visible(timeout=0.1),
            timeout=3,
            poll_frequency=0.1,
        ) is not False

    def recognize_click_security(self, attempt=1):
        image = self.wait_visible(self.security_image, timeout=3)
        if image is False:
            raise ValueError("安全验证图片未显示")
        prompt = self.get_click_security_prompt()
        image_bytes = image.screenshot_as_png
        allure.attach(
            image_bytes,
            name=f"安全验证原图_第{attempt}次",
            attachment_type=allure.attachment_type.PNG,
        )
        allure.attach(
            prompt,
            name=f"安全验证目标文字_第{attempt}次",
            attachment_type=allure.attachment_type.TEXT,
        )
        solution = click_captcha_recognizer.recognize(
            image_bytes,
            prompt,
            ConfigManager.SECURITY_VERIFY_MIN_SCORE,
            ConfigManager.SECURITY_VERIFY_MIN_MARGIN,
        )
        self.last_security_solution = solution
        allure.attach(
            click_captcha_recognizer.annotate(image_bytes, solution),
            name=f"安全验证识别标注_第{attempt}次",
            attachment_type=allure.attachment_type.PNG,
        )
        allure.attach(
            json.dumps(solution.details(), ensure_ascii=False, indent=2),
            name=f"安全验证识别结果_第{attempt}次",
            attachment_type=allure.attachment_type.JSON,
        )
        return solution

    def recognize_click_security_with_retry(self, max_attempts=None):
        attempts = max_attempts or ConfigManager.SECURITY_VERIFY_MAX_ATTEMPTS
        last_error = None
        for attempt in range(1, attempts + 1):
            try:
                return self.recognize_click_security(attempt=attempt)
            except Exception as exc:
                last_error = exc
                if attempt < attempts and not self.refresh_click_security():
                    break
        raise ValueError(f"安全验证连续识别失败：{last_error}")

    def click_security_solution(self, solution, limit=None, reverse=False):
        image = self.wait_visible(self.security_image, timeout=3)
        if image is False:
            return False
        selected = list(solution.selected)
        if reverse:
            selected.reverse()
        if limit is not None:
            selected = selected[:limit]
        css_width = float(image.rect["width"])
        css_height = float(image.rect["height"])
        image_width, image_height = solution.image_size
        converted = []
        for index, item in enumerate(selected, 1):
            css_x = item.center[0] * css_width / image_width
            css_y = item.center[1] * css_height / image_height
            ActionChains(self.driver).move_to_element_with_offset(image,
                round(css_x - css_width / 2),
                round(css_y - css_height / 2),
            ).click().perform()
            converted.append(
                {
                    "顺序": index,
                    "字符": item.text,
                    "截图坐标": [round(item.center[0], 2), round(item.center[1], 2)],
                    "页面坐标": [round(css_x, 2), round(css_y, 2)],
                    "置信度": round(item.confidence, 6),
                }
            )
            if index<len(solution.selected) and self.wait_until(
                lambda:self.get_click_security_marker_count()==index,timeout=2,poll_frequency=0.05
            ) is False:
                raise AssertionError(f'第{index}次点击后未出现对应序号标记')
        allure.attach(
            json.dumps(converted, ensure_ascii=False, indent=2),
            name="安全验证点击顺序与坐标",
            attachment_type=allure.attachment_type.JSON,
        )
        return True

    def solve_click_security(self, max_attempts=None):
        if ConfigManager.SECURITY_VERIFY_MODE != "auto":
            self.last_login_error = "安全验证仅支持 auto 自动识别模式"
            return False
        attempts = max_attempts or ConfigManager.SECURITY_VERIFY_MAX_ATTEMPTS
        failures = []
        for attempt in range(1, attempts + 1):
            if not self.is_click_security_visible(timeout=ConfigManager.SECURITY_VERIFY_WAIT_SECONDS):
                return self.is_logged_in(timeout=0.2)
            image = self.wait_visible(self.security_image, timeout=2)
            before = "" if image is False else (image.get_attribute("src") or "")
            previous_error = self.get_login_error_msg()
            try:
                with allure.step(f"第{attempt}次识别并按顺序点击安全验证汉字"):
                    solution = self.recognize_click_security(attempt=attempt)
                    self.click_security_solution(solution)
            except Exception as exc:
                failures.append(f"第{attempt}次识别失败：{exc}")
                if attempt < attempts:
                    self.refresh_click_security()
                continue

            def submission_outcome():
                if self._authenticated_route_and_shell():
                    return "success"
                message = self.get_login_error_msg()
                challenge_error = message and any(word in message for word in ("验证码", "安全验证")) and any(
                    word in message for word in ("错误", "失败", "过期", "失效", "不正确", "未通过")
                )
                # A previous challenge toast can outlive the next submission.
                # Credential/business errors must stop even if the image changed.
                if message and not challenge_error and message != previous_error:
                    return f"error:{message}"
                if self._click_security_image_changed(before):
                    return "retry"
                # The server refreshes rejected challenges itself. Wait for that
                # image, rather than racing it with a second manual refresh.
                return False

            outcome = self.wait_until(
                submission_outcome,
                timeout=ConfigManager.SECURITY_VERIFY_WAIT_SECONDS,
                poll_frequency=0.2,
            )
            if outcome == "success":
                return True
            if isinstance(outcome, str) and outcome.startswith("error:"):
                self.last_login_error = outcome.split(":", 1)[1]
                return False
            failures.append(f"第{attempt}次点击后验证未通过")
            if outcome != "retry":
                # An unknown submission result is not permission to submit again.
                break

        self.last_login_error = "；".join(failures) or "安全验证识别失败"
        allure.attach(
            self.last_login_error,
            name="安全验证最终失败详情",
            attachment_type=allure.attachment_type.TEXT,
        )
        allure.attach(
            self.driver.get_screenshot_as_png(),
            name="安全验证最终失败页面",
            attachment_type=allure.attachment_type.PNG,
        )
        return False

    def _click_security_image_changed(self, previous_src):
        image = self._first_visible(self.security_image, timeout=0)
        if image is False:
            return False
        current = image.get_attribute("src") or ""
        return bool(current and current != previous_src)

    def refresh_captcha(self):
        image = self.wait_visible(self.img_code, timeout=3)
        if image is False:
            return False
        before = image.get_attribute("src") or ""
        try:
            image.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", image)
        time.sleep(0.3)
        after = image.get_attribute("src") or ""
        return bool(after) and (after != before or self.is_captcha_visible())

    def recognize_visible_captcha(self):
        image = self.wait_visible(self.img_code, timeout=3)
        if image is False:
            return ""
        image_bytes = image.screenshot_as_png
        value = captcha_recognizer.recognize(image_bytes)
        allure.attach(
            image_bytes,
            name="captcha_image",
            attachment_type=allure.attachment_type.PNG,
        )
        allure.attach(
            value,
            name="captcha_ocr_result",
            attachment_type=allure.attachment_type.TEXT,
        )
        return value

    def login_with_ocr(self, username, password, max_attempts=None):
        attempts = max_attempts or ConfigManager.OCR_MAX_ATTEMPTS
        for attempt in range(1, attempts + 1):
            if not self.is_captcha_visible(timeout=2):
                self.last_login_error = "验证码状态已变化且账号未登录"
                return False
            value = self.recognize_visible_captcha()
            if value:
                self.login_with(username, password, captcha=value)
                if self.wait_for_login_success(timeout=6):
                    return True
            if attempt < attempts:
                self.refresh_captcha()
        allure.attach(
            self.driver.get_screenshot_as_png(),
            name="captcha_ocr_failure_page",
            attachment_type=allure.attachment_type.PNG,
        )
        self.last_login_error = "验证码OCR连续识别失败"
        return False

    def login_with_optional_captcha(self, username, password, expected_username=None):
        identity = str(username) if expected_username is None else str(expected_username)
        self.last_login_error = ""
        self.last_authenticated_username = str(username)
        legacy_field=self.driver.execute_script(
            "return [...document.querySelectorAll('form input')].some(e=>e.offsetParent!==null&&(e.id==='inputCode'||(e.placeholder||'').includes('验证码')))"
        )
        if legacy_field:
            return self.login_with_ocr(username, password) and self._confirm_login_identity(identity)
        self.login_with(username, password)
        outcome = self.wait_until(
            lambda: (
                "success" if self._authenticated_route_and_shell() else
                "click_security" if self.is_click_security_visible(timeout=0) else
                "captcha" if self.is_captcha_visible(timeout=0) else
                self.get_login_error_msg() or False
            ),
            timeout=ConfigManager.SECURITY_VERIFY_WAIT_SECONDS,
            poll_frequency=0.2,
        )
        if outcome == "success":
            return self._confirm_login_identity(identity)
        if outcome == "captcha":
            return self.login_with_ocr(username, password) and self._confirm_login_identity(identity)
        if outcome == "click_security":
            return self.solve_click_security() and self._confirm_login_identity(identity)
        if outcome:
            self.last_login_error = str(outcome)
            allure.attach(
                self.last_login_error,
                name="login_error",
                attachment_type=allure.attachment_type.TEXT,
            )
        return False

    def _confirm_login_identity(self,username):
        actual=self.wait_until(lambda:self.get_index_user_name_text() or False,
            timeout=ConfigManager.SECURITY_VERIFY_WAIT_SECONDS,poll_frequency=0.1)
        if actual!=str(username):
            self.last_login_error=f'登录后页面账号与目标不一致：页面={actual or "未显示"}，目标={username}'
            return False
        self.driver._ces_authenticated_username=actual
        self.driver._ces_session_invalidated=False
        if getattr(self.driver,'_ces_management_driver',None) is None and actual==ConfigManager.USERNAME:
            self.driver._needs_admin_login=False
            verifier=getattr(self.driver,'_ces_verification_driver',None)
            if verifier is not None and getattr(verifier,'_ces_authenticated_username',None)==actual:
                verifier._ces_session_invalidated=True
        return True

    def get_index_user_name_text(self):
        for element in self.driver.find_elements(*self.index_user_name):
            try:
                text = (element.text or "").strip()
                if element.is_displayed() and text:
                    return text
            except Exception:
                continue
        return ""

    def get_login_error_msg(self):
        return self.driver.execute_script(
            """
            const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
            const selector='.ant-message-notice-content,.ant-notification-notice-message,'+
              'form .ant-form-explain,form .ant-form-item-explain-error,'+
              'form .ant-form-item-explain-connected,form [role=alert],'+
              'form .has-error .ant-form-explain,form .ant-form-item-has-error [role=alert]';
            return [...new Set([...document.querySelectorAll(selector)].filter(visible)
              .map(e=>(e.innerText||'').trim()).filter(Boolean))].join(' ');
            """
        )

    def login_field_errors(self):
        return self.driver.execute_script(
            """
            const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
            const form=[...document.querySelectorAll('form')].find(visible);
            const result={};
            if(!form) return result;
            for(const input of form.querySelectorAll('input')){
              if(!visible(input)||input.id==='inputCode') continue;
              const item=input.closest('.ant-form-item');
              const errors=[...(item?.querySelectorAll(
                '.ant-form-explain,.ant-form-item-explain-error,[role=alert]')||[])];
              const text=errors.filter(visible).map(e=>(e.innerText||'').trim()).filter(Boolean).join(' ');
              if(text) result[input.type==='password'?'密码':'用户名']=text;
            }
            return result;
            """
        ) or {}

    def wait_for_login_success(self, timeout=15):
        return self.wait_until(
            self._authenticated_route_and_shell,
            timeout=timeout,
            poll_frequency=0.3,
        ) is not False

    def is_logged_in(self, timeout=2):
        return self.wait_until(
            self._authenticated_route_and_shell,
            timeout=timeout,
            poll_frequency=0.2,
        ) is not False

    def _authenticated_route_and_shell(self):
        current_url = (self.driver.current_url or "").lower()
        if not current_url or "login" in current_url:
            return False
        for element in self.driver.find_elements(*self.authenticated_shell):
            try:
                if element.is_displayed():
                    return True
            except Exception:
                continue
        return False

    def dismiss_intro_if_present(self, timeout=0):
        # The intro is a one-time overlay. Waiting two seconds for its absence
        # on every authenticated page open added several minutes to a full run.
        end = time.time() + max(0, timeout)
        while True:
            for element in self.driver.find_elements(*self.close_button):
                try:
                    if not element.is_displayed():
                        continue
                    try:
                        element.click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", element)
                    return True
                except Exception:
                    continue
            if time.time() >= end:
                return False
            time.sleep(0.1)

    def click_login_button_three_times(self):
        for _ in range(3):
            self.click(self.login_button)
            time.sleep(1)

    def common_login(self):
        if not getattr(self.driver,'_needs_admin_login',False) and self.is_logged_in(timeout=0.1) and self.get_index_user_name_text()==ConfigManager.USERNAME:
            self.dismiss_intro_if_present()
            return True
        self.reset_login_state()
        if not self.login_with_optional_captcha(
            ConfigManager.USERNAME, ConfigManager.PASSWORD
        ):
            return False
        self.dismiss_intro_if_present()
        return True

