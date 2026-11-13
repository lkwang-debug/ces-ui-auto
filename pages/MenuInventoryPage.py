# -*- coding: utf-8 -*-
import os
import time
import pytest
from selenium.webdriver.common.by import By

from common.product_profile import detect_build_profile, feature_for_request, profile_entry
from conf.conf import ConfigManager
from pages.Index_Page.index import LoginPage
from common.ui_state import wait_stable_state


class MenuInventoryPage(LoginPage):
    inventory_route = "#/ui/organizational-management/user-management"
    sidebar = (
        By.CSS_SELECTOR,
        "aside ul.ant-menu, .ant-layout-sider ul.ant-menu-root",
    )
    sidebar_expand_button = (
        By.CSS_SELECTOR,
        "aside .anticon-menu-unfold, aside [aria-label='menu-unfold'], "
        ".ant-layout-sider .anticon-menu-unfold, "
        ".ant-layout-sider [aria-label='menu-unfold']",
    )
    content_root = (By.CSS_SELECTOR, "main, .ant-layout-content, .layout-content__main")

    def _ensure_sidebar_expanded(self):
        menu = self.wait_visible(self.sidebar, timeout=8)
        if menu is False:
            return False
        if "ant-menu-inline-collapsed" not in (menu.get_attribute("class") or ""):
            return True
        button = self.wait_clickable(self.sidebar_expand_button, timeout=3)
        if button is False:
            return False
        self.driver.execute_script("arguments[0].click();", button)
        return bool(
            self.wait_until(
                lambda: "ant-menu-inline-collapsed"
                not in (menu.get_attribute("class") or ""),
                timeout=3,
            )
        )
    def _find_submenu(self, group_name):
        for submenu in self.driver.find_elements(
            By.CSS_SELECTOR,
            "aside ul.ant-menu-root > li.ant-menu-submenu, "
            ".ant-layout-sider ul.ant-menu-root > li.ant-menu-submenu",
        ):
            try:
                title = submenu.find_element(
                    By.CSS_SELECTOR, ":scope > .ant-menu-submenu-title"
                )
                if (title.text or "").strip() == group_name:
                    return submenu, title
            except Exception:
                continue
        return None, None

    def _find_menu_item(self, submenu, item_name):
        try:
            for item in submenu.find_elements(By.CSS_SELECTOR, "li.ant-menu-item"):
                if (item.text or "").strip() == item_name:
                    return item
        except Exception:
            return None
        return None

    def _find_menu_item_by_group(self, group_name, item_name):
        submenu, _ = self._find_submenu(group_name)
        if submenu is None:
            return None
        return self._find_menu_item(submenu, item_name)

    def _content_snapshot(self):
        """Read the rendered router content, excluding cached/opened tab names."""
        return self.driver.execute_script(
            r"""
            const visible=e=>!!(e&&(e.offsetWidth||e.offsetHeight||e.getClientRects().length));
            const main=document.querySelector('main,.ant-layout-content,.layout-content__main');
            if(!main) return null;
            if([...main.querySelectorAll('.ant-spin-spinning,.ant-spin-blur,.el-loading-mask,[aria-busy=true]')]
                .some(visible)) return null;
            const root=[...main.querySelectorAll('.layout-content__main > .container')].find(visible)||main;
            const excluded='.layout-content__header,.ant-tabs-nav,.el-tabs__header,header';
            const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
            const parts=[];
            while(walker.nextNode()){
              const node=walker.currentNode, parent=node.parentElement;
              if(parent && !parent.closest(excluded) && visible(parent)) parts.push(node.textContent);
            }
            const clean=v=>String(v||'').replace(/\s+/g,' ').trim();
            const text=clean(parts.join(' '));
            const headers=[...root.querySelectorAll('th')].filter(visible)
              .map(e=>clean(e.innerText)).filter(Boolean);
            const tables=[...root.querySelectorAll('table')].filter(visible);
            if(!text || (tables.length && !headers.length)) return null;
            return {text,headers,
              tabs:[...main.querySelectorAll('.checked-tag,.ant-tabs-tab-active,.el-tabs__item.is-active')]
                .filter(visible).map(e=>clean(e.innerText))};
            """
        )

    def open_menu_item(self, group_name=None, item_name=None, feature_id=None):
        build = detect_build_profile(ConfigManager.HST_URL)
        profile = (
            profile_entry(feature_id, build)
            if feature_id
            else feature_for_request(group_name, item_name, build)
        )
        if not profile or profile.get("policy") == "excluded":
            return None
        group_name, item_name = profile["group"], profile["item"]
        current_url = self.driver.current_url or ""
        base_url = self.url.rstrip("/")
        if not current_url.startswith(base_url) or "#/ui/login" in current_url:
            self.open_login_url()
            authenticated = self.login_with_optional_captcha(
                ConfigManager.USERNAME, ConfigManager.PASSWORD
            )
            if not authenticated:
                detail = self.last_login_error or "no error message returned by login page"
                pytest.exit(
                    f"Admin login precondition failed for {ConfigManager.HST_URL}: {detail}",
                    returncode=2,
                )

        # Reuse the authenticated SPA shell. Reload the stable inventory route
        # only when the sidebar itself is no longer available.
        if self.find_visible_now(self.sidebar) is False:
            self.driver.get(base_url + "/" + self.inventory_route)
            self.wait_for_document_ready(timeout=5)
        if not self._ensure_sidebar_expanded():
            return None
        self.dismiss_intro_if_present()
        found_submenu = self.wait_until(
            lambda: self._find_submenu(group_name)[0], timeout=5, poll_frequency=0.2
        )
        submenu, title = self._find_submenu(group_name)
        if not found_submenu or submenu is None:
            return None
        if "ant-menu-submenu-open" not in (submenu.get_attribute("class") or ""):
            title.click()
            if self.wait_until(
                lambda: "ant-menu-submenu-open" in (
                    self._find_submenu(group_name)[0].get_attribute("class") or ""),
                timeout=3,
            ) is False:
                return None

        aliases={str(value).strip().casefold() for value in (item_name,*profile.get('item_aliases',[]))}
        def matching_item():
            current,_=self._find_submenu(group_name)
            if current is None:return False
            return next((e for e in current.find_elements(By.CSS_SELECTOR,'li.ant-menu-item')
                if e.is_displayed() and (e.text or '').strip().casefold() in aliases),False)
        self.wait_until(
            matching_item,
            timeout=3,
            poll_frequency=0.2,
        )
        item = matching_item()
        if item is not False:
            item_name=(item.text or '').strip()
            profile={**profile,'item':item_name}
        else:
            item=None
        previous_url = self.driver.current_url
        previous_content = self._content_snapshot()
        if item is None:
            # Some builds render a group containing one authorized feature as
            # a direct entry without a child <li>. The detected catalog still
            # supplies the only valid route; click the group first so this is
            # a real menu interaction, then use the registered route if the
            # lazy child remains absent.
            title.click()
        else:
            item.click()
        self.wait_for_document_ready(timeout=5)
        navigated = self.wait_until(
            lambda: profile["route"] in (self.driver.current_url or ""),
            timeout=3,
            poll_frequency=0.2,
        )
        current_url = self.driver.current_url or ""
        if not navigated:
            # A collapsed/lazily rendered submenu occasionally absorbs the
            # first click while retaining the prior route. Recover only to
            # this known page route, then still require its actual title.
            if not self.open_spa_route(profile["route"], timeout=5):
                return None
            self.wait_for_document_ready(timeout=5)
            current_url = self.driver.current_url or ""
        if profile["route"] not in current_url:
            return None
        page_markers = [profile["title"], *profile.get("page_markers", [])]

        def target_main():
            if profile["route"] not in (self.driver.current_url or ""):
                return False
            snapshot = self._content_snapshot()
            if not snapshot:
                return False
            expected_titles = {profile["title"], item_name}
            if snapshot["tabs"] and not any(
                title in expected_titles for title in snapshot["tabs"]
            ):
                return False
            if previous_content and profile["route"] not in previous_url:
                if snapshot["text"] == previous_content["text"]:
                    return False
            # These screens can render search controls before their actual
            # data schema. Do not confuse the shell with the loaded page.
            required_headers = {
                "organization": {"部门ID", "部门名称"},
                "user": {"用户名", "昵称"},
            }.get(profile["feature_id"], set())
            if required_headers and not required_headers.issubset(snapshot["headers"]):
                return False
            if profile["feature_id"] == "node_authorization" and not all(
                marker in snapshot["text"] for marker in ("版本信息", "授权内容", "节点信息")
            ):
                return False
            if not snapshot["tabs"] and not snapshot["headers"]:
                # A page without a tab/table must expose its registered content
                # marker; a route and arbitrary nonempty body never suffice.
                if not any(marker in snapshot["text"] for marker in page_markers):
                    return False
            return snapshot

        body = wait_stable_state(self, target_main, timeout=10)
        if not body:
            if not self._recover_menu_content(group_name, item_name, profile['route']):
                return None
            body = wait_stable_state(self, target_main, timeout=10)
        if not body:
            return None
        current_url = self.driver.current_url or ""
        if profile["route"] not in current_url:
            return None
        return {
            "url": current_url,
            "text": body["text"],
            "headers": body["headers"],
            "active_tabs": body["tabs"],
            "feature_id": profile["feature_id"],
            "group": group_name,
            "item": item_name,
            "profile": build,
        }

    def _recover_menu_content(self, group_name, item_name, route):
        """Remount a delayed SPA page without discarding its authenticated shell."""
        if '#/ui/login' in (self.driver.current_url or ''):
            return False
        if route != self.inventory_route and not self.open_spa_route(self.inventory_route, timeout=5):
            return False
        recovered_item = self._find_menu_item_by_group(group_name, item_name)
        if recovered_item is not None and recovered_item.is_displayed():
            recovered_item.click()
        return self.open_spa_route(route, timeout=5)

    def hold_page_for_visual_check(self):
        """Keep a verified menu page visible during headed inventory runs."""
        if os.getenv("UIAUTO_HEADLESS", "1").strip().lower() in {"1", "true", "yes", "on"}:
            return
        seconds = max(0.0, ConfigManager.MENU_VISUAL_DWELL_SECONDS)
        if seconds:
            time.sleep(seconds)
