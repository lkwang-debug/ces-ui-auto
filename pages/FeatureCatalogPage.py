# -*- coding: utf-8 -*-
import json
from pathlib import Path

import allure
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

from conf.conf import ConfigManager
from common.product_profile import detect_build_profile, feature_for_request
from common.runtime_artifacts import clean_directory, wait_for_download, prepare_download
from pages.MenuInventoryPage import MenuInventoryPage


FEATURE_FILE = Path(__file__).parents[1] / "data" / "page_features.json"
PAGE_FEATURES = json.loads(FEATURE_FILE.read_text(encoding="utf-8"))


class FeatureCatalogPage(MenuInventoryPage):
    main = (By.CSS_SELECTOR, "main, .ant-layout-content, .layout-content__main")

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

    def _ensure_authenticated(self):
        current_url = self.driver.current_url or ""
        if not current_url.startswith(self.url) or "#/ui/login" in current_url:
            self.open_login_url()
            return self.login_with_optional_captcha(
                ConfigManager.USERNAME, ConfigManager.PASSWORD
            )
        return True

    def open_feature(self, group_name, item_name, timeout=12):
        profile = feature_for_request(group_name,item_name,detect_build_profile(ConfigManager.HST_URL))
        if not profile or not self._ensure_authenticated():
            return None
        content = self._content_snapshot()
        titles = {profile['title'],profile['item']}
        already_ready = (profile['route'] in (self.driver.current_url or '') and content
            and (bool(titles.intersection(content['tabs'])) or any(
                marker in content['text'] for marker in [profile['title'],*profile.get('page_markers',[])])))
        if not already_ready:
            if not self.open_menu_item(feature_id=profile['feature_id']):
                return None
        main = self.wait_visible(self.main,timeout=timeout)
        snapshot = None if main is False else self.snapshot_main(main)
        if not snapshot or not self._content_snapshot():
            return None
        snapshot.update(expected_route=profile['route'],identity_verified=True)
        allure.attach(snapshot['text'][:5000], '页面主体内容', allure.attachment_type.TEXT)
        return snapshot


    def snapshot_main(self, main=None):
        try:
            data = self.driver.execute_script(
                """
            const main = arguments[0] || document.querySelector(
              'main, .ant-layout-content, .layout-content__main');
            if (!main) return null;
            const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
            const clean = value => (value || '').replace(/\\s+/g, ' ').trim();
            return {
              text: clean(main.innerText),
              activeTitle: clean([...document.querySelectorAll('.ant-tabs-tab-active')]
                .filter(visible).map(e=>e.innerText).join(' ')),
              bodyText: clean(document.body.innerText),
              buttons: [...main.querySelectorAll('button')].filter(visible)
                .map(e => clean(e.innerText || e.title)).filter(Boolean),
              inputs: [...main.querySelectorAll('input')].filter(visible)
                .map(e => e.placeholder || e.type || 'input'),
              headers: [...main.querySelectorAll('th')].filter(visible)
                .map(e => clean(e.innerText)).filter(Boolean)
            };
            """,
                main,
            )
        except Exception:
            data = None
        if not data:
            return None
        return {
            "url": self.driver.current_url,
            "text": " ".join(
                value for value in (data.get("activeTitle", ""), data["text"]) if value
            ),
            "body_text": data["bodyText"],
            "buttons": data["buttons"],
            "inputs": data["inputs"],
            "headers": data["headers"],
        }

    def fill_first_search(self, value):
        main = self.wait_visible(self.main, timeout=5)
        if main is False:
            return False
        inputs = [
            e for e in main.find_elements(By.CSS_SELECTOR, "input")
            if e.is_displayed()
            and e.is_enabled()
            and not e.get_attribute("readonly")
            and (e.get_attribute("type") or "text").lower() in {"text", "search"}
        ]
        if not inputs:
            return False
        field = inputs[0]
        try:
            field.clear()
            field.send_keys(value)
            field.send_keys(Keys.ENTER)
        except Exception:
            return False
        return True

    def download_from_feature(self, group_name, item_name, labels, extensions, timeout=25):
        if not self.open_feature(group_name, item_name):
            return None
        directory = prepare_download(self.driver)
        existing = {path.name for path in directory.iterdir()}
        for label in labels:
            locator = (
                By.XPATH,
                f"//main//button[contains(normalize-space(.),'{label}')]"
                f" | //main//a[contains(normalize-space(.),'{label}')]",
            )
            if self._click_first_available_safe([locator], timeout=3):
                return wait_for_download(directory, existing, extensions, timeout=timeout, driver=self.driver)
        return None
