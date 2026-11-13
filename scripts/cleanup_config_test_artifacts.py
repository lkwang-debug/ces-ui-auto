# -*- coding: utf-8 -*-
"""Remove only configuration-centre records created by UI automation."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from selenium import webdriver
from selenium.webdriver.chrome.service import Service

from conftest import chrome_options, resolve_chromedriver_path
from conf.conf import ConfigManager
from pages.Index_Page.index import LoginPage


TARGETS = (
    ("#/ui/configuration-center/property-management", ("feature_case_",)),
    ("#/ui/configuration-center/product-information", ("AUTO_PROD_", "product_case_")),
    ("#/ui/configuration-center/characteristic-parameter-management", ("auto_vendor_",)),
)


def visible(element):
    try:
        return element.is_displayed()
    except Exception:
        return False


def delete_matching_rows(browser, prefixes):
    rows = [
        row
        for row in browser.find_elements("css selector", "main tbody tr")
        if visible(row)
        and "ant-table-measure-row" not in (row.get_attribute("class") or "")
        and any(prefix in (row.text or "") for prefix in prefixes)
    ]
    if not rows:
        return 0
    for row in rows:
        checkboxes = row.find_elements("css selector", "input[type=checkbox]")
        if checkboxes and not checkboxes[0].is_selected():
            browser.execute_script("arguments[0].click()", checkboxes[0])
    delete_button = next(
        (
            button
            for button in browser.find_elements("css selector", "main button.hst-delete-button")
            if visible(button) and button.is_enabled()
        ),
        None,
    )
    if delete_button is None:
        raise RuntimeError("未找到配置中心顶部删除按钮")
    browser.execute_script("arguments[0].click()", delete_button)
    time.sleep(0.3)
    confirm = next(
        (
            button
            for button in browser.find_elements(
                "css selector", ".ant-modal-content button.ant-btn-primary"
            )
            if visible(button)
        ),
        None,
    )
    if confirm is None:
        raise RuntimeError("删除确认弹窗未出现")
    browser.execute_script("arguments[0].click()", confirm)
    time.sleep(1)
    return len(rows)


def go_next(browser):
    button = next(
        (
            item
            for item in browser.find_elements("css selector", "main .ant-pagination-next")
            if visible(item)
        ),
        None,
    )
    if button is None or "disabled" in (button.get_attribute("class") or ""):
        return False
    browser.execute_script("arguments[0].click()", button)
    time.sleep(0.7)
    return True


def main():
    browser = webdriver.Chrome(
        service=Service(resolve_chromedriver_path()),
        options=chrome_options(headless=True),
    )
    removed = 0
    try:
        login = LoginPage(driver=browser)
        login.open_login_url()
        if not login.login_with_optional_captcha(ConfigManager.USERNAME, ConfigManager.PASSWORD):
            raise RuntimeError(login.last_login_error or "管理员登录失败")
        for route, prefixes in TARGETS:
            browser.get(ConfigManager.HST_URL.rstrip("/") + "/" + route)
            time.sleep(1.5)
            while True:
                count = delete_matching_rows(browser, prefixes)
                removed += count
                if count:
                    continue
                if not go_next(browser):
                    break
        print(f"已清理配置中心自动化临时记录: {removed} 条")
    finally:
        browser.quit()


if __name__ == "__main__":
    main()
