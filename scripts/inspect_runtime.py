# -*- coding: utf-8 -*-
"""Print the rendered sidebar structure for compatibility diagnostics."""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from selenium import webdriver
from selenium.webdriver.chrome.service import Service

from conftest import chrome_options, resolve_chromedriver_path
from common.product_profile import build_runtime_context, detect_build_profile
from conf.conf import ConfigManager
from pages.Index_Page.index import LoginPage


def main():
    browser = webdriver.Chrome(
        service=Service(resolve_chromedriver_path()),
        options=chrome_options(headless=True),
    )
    try:
        login = LoginPage(driver=browser)
        login.open_login_url()
        if not login.login_with_optional_captcha(
            ConfigManager.USERNAME, ConfigManager.PASSWORD
        ):
            raise RuntimeError(login.last_login_error or "管理员登录失败")
        login.dismiss_intro_if_present()
        context = build_runtime_context(
            browser, detect_build_profile(ConfigManager.HST_URL)
        )
        print(
            "RUNTIME_CONTEXT="
            + json.dumps(
                {
                    "profile": context.profile,
                    "menu_tree": context.menu_tree,
                    "authorized": sorted(context.authorized),
                    "unknown": context.unknown_menus,
                },
                ensure_ascii=True,
            )
        )
        sdk = browser.execute_script(
            """
            return [...document.querySelectorAll('.ant-layout-sider li.ant-menu-item')]
              .find(item => (item.innerText || '').trim().toLowerCase() === 'sdk') || null;
            """
        )
        if sdk is not None:
            browser.execute_script("arguments[0].click()", sdk)
            time.sleep(2)
            print(
                "SDK_PAGE="
                + json.dumps(
                    {
                        "url": browser.current_url,
                        "text": browser.execute_script(
                            "return (document.querySelector('main')?.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 1000)"
                        ),
                    },
                    ensure_ascii=True,
                )
            )
        ces = browser.execute_script(
            """
            return [...document.querySelectorAll('.ant-layout-sider li.ant-menu-item')]
              .find(item => (item.innerText || '').trim().toLowerCase() === 'ces') || null;
            """
        )
        if ces is not None:
            browser.execute_script("arguments[0].click()", ces)
            time.sleep(2)
            print(
                "CES_PAGE="
                + json.dumps(
                    {
                        "url": browser.current_url,
                        "text": browser.execute_script(
                            "return (document.querySelector('main')?.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 1000)"
                        ),
                    },
                    ensure_ascii=True,
                )
            )
        data = browser.execute_script(
            """
            const selectors = 'aside,nav,[class*=sider],[class*=menu]';
            return [...document.querySelectorAll(selectors)]
              .filter(element => element.offsetParent !== null)
              .slice(0, 100)
              .map(element => ({
                tag: element.tagName,
                cls: String(element.className || ''),
                text: String(element.innerText || '').replace(/\s+/g, ' ').slice(0, 800)
              }));
            """
        )
        print(json.dumps(data[:20], ensure_ascii=True, indent=2))
    finally:
        browser.quit()


if __name__ == "__main__":
    main()
