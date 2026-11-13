# -*- coding: utf-8 -*-
"""Inspect the rendered controls used by the meeting email notification flow."""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from selenium import webdriver
from selenium.webdriver.chrome.service import Service

from conftest import chrome_options, resolve_chromedriver_path
from conf.conf import ConfigManager
from pages.FeatureCatalogPage import FeatureCatalogPage
from pages.Index_Page.index import LoginPage
from pages.ContactList_Page.UserPage import UserManagerPage
from pages.Meeting_Page.MeetingInfoPage import MeetingInfoPage
from pages.Server_Page.GlobalSettingsPage import GlobalSettingsPage


INSPECT_SCRIPT = r"""
const root = arguments[0] === 'modal'
  ? [...document.querySelectorAll('.ant-modal-content')].filter(e => e.offsetParent !== null).at(-1)
  : document.querySelector('main');
if (!root) return null;
const clean = value => String(value || '').replace(/\s+/g, ' ').trim();
const info = element => ({
  tag: element.tagName,
  text: clean(element.innerText || element.textContent),
  type: element.getAttribute('type'),
  name: element.getAttribute('name'),
  id: element.id,
  placeholder: element.getAttribute('placeholder'),
  cls: String(element.className || ''),
  html: element.outerHTML.slice(0, 1200),
});
return {
  text: clean(root.innerText).slice(0, 10000),
  labels: [...root.querySelectorAll('label')].map(info),
  inputs: [...root.querySelectorAll('input')].filter(e => e.offsetParent !== null).map(info),
  buttons: [...root.querySelectorAll('button,a')].filter(e => e.offsetParent !== null).map(info),
  rows: [...root.querySelectorAll('tbody tr')].filter(e => e.offsetParent !== null).slice(0, 3).map(info),
  emailCompatibility: arguments[0] === 'main' ? {
    labels: [...root.querySelectorAll('label')].filter(e => ['邮件服务器地址','邮箱帐号','邮箱密码','SSL 端口'].includes(clean(e.innerText))).map(e => ({
      text:clean(e.innerText), formItem:e.closest('.ant-form-item')?.outerHTML.slice(0, 3000) || ''
    })),
    xpathCounts: ['邮件服务器地址','邮箱帐号','邮箱密码'].map(text => ({text, count:document.evaluate(
      `//main//label[normalize-space()='${text}']/ancestor::*[contains(@class,'ant-form-item')][1]//input`,
      document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null).snapshotLength
    }))
  } : null,
};
"""


def dump(browser, name, scope="main"):
    value = browser.execute_script(INSPECT_SCRIPT, scope)
    print(name + "=" + json.dumps(value, ensure_ascii=True))


def click_exact_text(browser, text, root="main"):
    return browser.execute_script(
        r"""
        const expected = arguments[0];
        const root = arguments[1] === 'main' ? document.querySelector('main') : document;
        const visible = element => !!(element && element.offsetParent !== null);
        const clean = value => String(value || '').replace(/\s+/g, '').trim();
        const target = [...root.querySelectorAll('button,a,li,div,span')]
          .filter(element => visible(element) && clean(element.innerText) === clean(expected))
          .sort((left, right) => left.children.length - right.children.length)[0];
        if (!target) return false;
        (target.closest('button,a,li') || target).click();
        return true;
        """,
        text,
        root,
    )


def main():
    browser = webdriver.Chrome(
        service=Service(resolve_chromedriver_path()),
        options=chrome_options(headless=True),
    )
    try:
        login = LoginPage(driver=browser)
        login.open_login_url()
        if not login.login_with_optional_captcha(ConfigManager.USERNAME, ConfigManager.PASSWORD):
            raise RuntimeError(login.last_login_error or "管理员登录失败")
        login.dismiss_intro_if_present()

        catalog = FeatureCatalogPage(driver=browser)
        if not catalog.open_feature("服务器管理", "全局设置"):
            raise RuntimeError("无法进入全局设置")
        if not click_exact_text(browser, "邮件发送服务"):
            raise RuntimeError("无法切换邮件发送服务")
        time.sleep(1)
        dump(browser, "GLOBAL_EMAIL_SETTINGS")
        settings = GlobalSettingsPage(driver=browser)
        print(
            "EMAIL_PAGE_OBJECT="
            + json.dumps(
                {
                    "server": bool(settings._email_input(settings.email_server, "邮件服务器地址", timeout=1)),
                    "account": bool(settings._email_input(settings.email_account, "邮箱帐号", timeout=1)),
                    "password": bool(settings._email_input(settings.email_password, "邮箱密码", timeout=1)),
                    "port": bool(settings._email_input(settings.ssl_port, "SSL端口", timeout=1)),
                },
                ensure_ascii=True,
            )
        )

        user = UserManagerPage(driver=browser)
        if not user.common_enter_user():
            raise RuntimeError("无法进入用户管理")
        user.click_add_button()
        dump(browser, "ADD_USER_MODAL", "modal")
        user.click_cancel_button()

        meeting = MeetingInfoPage(driver=browser)
        if not meeting.common_enter_meeting_info():
            raise RuntimeError("无法进入会议室信息")
        time.sleep(1)
        dump(browser, "MEETING_LIST")
        inspect_meeting = os.getenv("UIAUTO_INSPECT_MEETING", "").strip()
        if inspect_meeting:
            if not meeting._find_exact_meeting_row_via_search(inspect_meeting):
                raise RuntimeError(f"未找到诊断会议室：{inspect_meeting}")
            inspect_user = os.getenv("UIAUTO_INSPECT_USER", "").strip()
            if inspect_user:
                if not meeting._click_first_available_safe(
                    [meeting._exact_meeting_authorize_button_locator(inspect_meeting)], timeout=8
                ):
                    raise RuntimeError("无法打开授权弹窗")
                time.sleep(1)
                dump(browser, "MEETING_AUTHORIZATION_MODAL", "modal")
                found = meeting._search_authorize_left_user(inspect_user)
                print("AUTHORIZATION_SEARCH_FOUND=" + json.dumps(bool(found)))
                time.sleep(1)
                dump(browser, "MEETING_AUTHORIZATION_SEARCHED", "modal")
                meeting._close_authorize_modal()
        if inspect_meeting:
            meeting._find_exact_meeting_row_via_search(inspect_meeting)
            notification_clicked = meeting._click_meeting_row_action(
                inspect_meeting, "通知", timeout=8
            )
        else:
            notification_clicked = browser.execute_script(
            r"""
            const clean = value => String(value || '').replace(/\s+/g, '').trim();
            const rows = [...document.querySelectorAll('main tbody tr')]
              .filter(row => row.offsetParent !== null && !row.classList.contains('ant-table-measure-row'));
            const button = rows.flatMap(row => [...row.querySelectorAll('button,a')])
              .find(element => clean(element.innerText) === '通知');
            if (!button) return false;
            button.click(); return true;
            """
            )
        if not notification_clicked:
            raise RuntimeError("无法打开会议通知弹窗")
        time.sleep(1)
        dump(browser, "MEETING_NOTIFICATION_MODAL", "modal")
        browser.execute_script(
            "document.querySelector('.ant-modal-content input[value=email]')?.click()"
        )
        time.sleep(0.5)
        dump(browser, "MEETING_NOTIFICATION_EMAIL_SELECTED", "modal")
        browser.execute_script(
            "document.querySelector('.ant-modal-content #form_item_startTime, .ant-modal-content input[placeholder=\"开始时间\"]')?.click()"
        )
        time.sleep(0.5)
        picker = browser.execute_script(
            r"""
            const visible = e => !!(e && e.offsetParent !== null);
            const clean = value => String(value || '').replace(/\s+/g, ' ').trim();
            return [...document.querySelectorAll(
              '.ant-picker-dropdown,.ant-calendar-picker-container,.ant-calendar,.ant-time-picker-panel'
            )].filter(visible).map(root => ({
              text: clean(root.innerText).slice(0, 5000),
              inputs: [...root.querySelectorAll('input')].filter(visible).map(e => ({
                value:e.value, placeholder:e.placeholder, cls:String(e.className || '')
              })),
              buttons: [...root.querySelectorAll('button,a,td,li')].filter(visible).slice(0, 100)
                .map(e => ({text:clean(e.innerText), title:e.title, cls:String(e.className || '')}))
            }));
            """
        )
        print("START_TIME_PICKER=" + json.dumps(picker, ensure_ascii=True))
        browser.execute_script("document.body.click()")
        click_exact_text(browser, "取消", root="document") or click_exact_text(browser, "关闭", root="document")
        time.sleep(0.5)
        if browser.execute_script(
            r"""
            const clean = value => String(value || '').replace(/\s+/g, '').trim();
            const rows = [...document.querySelectorAll('main tbody tr')]
              .filter(row => row.offsetParent !== null && !row.classList.contains('ant-table-measure-row'));
            const button = rows.flatMap(row => [...row.querySelectorAll('button,a')])
              .find(element => clean(element.innerText) === '查看');
            if (!button) return false;
            button.click(); return true;
            """
        ):
            time.sleep(1)
            dump(browser, "MEETING_NOTIFICATION_RESULT_MODAL", "modal")
    finally:
        browser.quit()


if __name__ == "__main__":
    main()
