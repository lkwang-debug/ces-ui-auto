# -*- coding: utf-8 -*-
"""CES build/profile detection and runtime menu capability discovery."""

from __future__ import annotations

import json
import os
import re
import ssl
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen, build_opener, HTTPSHandler, HTTPRedirectHandler

from conf.conf import ConfigManager


LEGACY = "legacy"
MODERN = "4.39.8"
UNKNOWN = "unknown"
CATALOG_FILE = Path(__file__).parents[1] / "data" / "menu_catalog.json"
_RUNTIME_MENU_LABELS = {}


class ProfileDetectionError(RuntimeError):
    """The build must be known before selecting or navigating test cases."""


def _origin(url):
    parsed = urlsplit(url)
    return parsed.scheme.lower(), parsed.hostname, parsed.port or (443 if parsed.scheme == 'https' else 80)


class _SameOriginRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if _origin(req.full_url) != _origin(newurl):
            raise ProfileDetectionError('前端探测禁止携带内网证书例外跳转到其他源')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _read_url(url: str, timeout: float = 8) -> str:
    request = Request(url, headers={"User-Agent": "CES-UIAuto/profile-probe"})
    if (not ConfigManager.HTTPS_VERIFY_CERTIFICATE and urlsplit(url).scheme == 'https'
            and _origin(url) == _origin(ConfigManager.HST_URL)):
        # A local opener affects only this target's frontend probe. Never alter
        # Python's global SSL defaults or forward this exception across origins.
        opener = build_opener(HTTPSHandler(context=ssl._create_unverified_context()), _SameOriginRedirect())
        with opener.open(request, timeout=timeout) as response:
            return response.read().decode('utf-8', errors='replace')
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


@lru_cache(maxsize=8)
def detect_build_profile(base_url: str | None = None) -> str:
    forced = os.getenv("UIAUTO_PRODUCT_PROFILE", ConfigManager.PRODUCT_PROFILE).strip().lower()
    if forced in {LEGACY, MODERN}:
        return forced
    if forced != 'auto':
        raise ProfileDetectionError('PRODUCT_PROFILE必须是auto、legacy或4.39.8')

    root = (base_url or ConfigManager.HST_URL).rstrip("/") + "/"
    stage = '读取首页'
    try:
        html = _read_url(root)
        scripts = re.findall(
            r"(?:src|href)\s*=\s*[\"']?([^\"' >]*?/js/app[^\"' >]*?\.js)",
            html,
            flags=re.I,
        )
        if not scripts:
            scripts = re.findall(r"(?:src|href)=([^ >]*?/js/app[^ >]*?\.js)", html, re.I)
        if not scripts:
            raise ProfileDetectionError('首页没有找到实际加载的app.*.js')
        stage = '读取前端脚本'
        bundle = _read_url(urljoin(root, scripts[-1]))
    except Exception as exc:
        from common.privacy import redact
        raise ProfileDetectionError(
            redact(f'前端版本识别失败：{stage}，目标{root}；{type(exc).__name__}: {exc}。'
                   '已停止测试，未将功能判为不支持。请检查地址、证书和前端资源。')
        ) from exc

    modern_markers = ("/ui/ai-model", "model-settings", "client-feature", "developer-ces")
    legacy_markers = ("user-call", "background-permission-management")
    if all(marker in bundle for marker in modern_markers):
        return MODERN
    if all(marker in bundle for marker in legacy_markers):
        return LEGACY
    raise ProfileDetectionError(f'前端版本识别失败：{root}的脚本不匹配已登记路由指纹，已停止测试')


@lru_cache(maxsize=1)
def menu_catalog() -> dict:
    return json.loads(CATALOG_FILE.read_text(encoding="utf-8"))


def profile_entry(feature_id: str, profile: str | None = None) -> dict | None:
    selected = profile or detect_build_profile()
    feature = menu_catalog().get(feature_id, {})
    entry = feature.get("profiles", {}).get(selected)
    if not entry:
        return None
    actual = _RUNTIME_MENU_LABELS.get((selected, feature_id), {})
    return {**feature, **entry, **actual, "feature_id": feature_id, "profile": selected}


def supported_feature_ids(profile: str | None = None, include_excluded: bool = False) -> set[str]:
    selected = profile or detect_build_profile()
    result = set()
    for feature_id, feature in menu_catalog().items():
        if selected not in feature.get("profiles", {}):
            continue
        if not include_excluded and feature.get("policy") == "excluded":
            continue
        result.add(feature_id)
    return result


def feature_for_request(group_name: str, item_name: str, profile: str | None = None) -> dict | None:
    selected = profile or detect_build_profile()
    normalized_group = str(group_name).strip().lower()
    normalized_item = str(item_name).strip().lower()
    matches = []
    for feature_id, feature in menu_catalog().items():
        entry = feature.get("profiles", {}).get(selected)
        if not entry:
            continue
        groups = {entry["group"], *feature.get("group_aliases", [])}
        items = {entry["item"], *feature.get("item_aliases", [])}
        actual = _RUNTIME_MENU_LABELS.get((selected,feature_id),{})
        if actual:
            groups.add(actual['group']);items.add(actual['item'])
        if normalized_group in {value.strip().lower() for value in groups} and normalized_item in {
            value.strip().lower() for value in items
        }:
            matches.append({**feature, **entry, **actual, "feature_id": feature_id, "profile": selected})
    if matches:
        return matches[0]
    return None


def inventory_cases(profile: str | None = None) -> list[dict]:
    selected = profile or detect_build_profile()
    cases = []
    for feature_id in menu_catalog():
        entry = profile_entry(feature_id, selected)
        if entry and entry.get("policy") != "excluded":
            cases.append(entry)
    return cases


def _clean_text(value) -> str:
    return " ".join((value or "").split()).strip()


def scan_visible_menu_tree(driver) -> dict[str, list[str]]:
    """Expand every real sidebar group once and capture its rendered children."""
    tree: dict[str, list[str]] = {}
    menu = next(
        (
            element
            for element in driver.find_elements(
                "css selector", "aside ul.ant-menu, .ant-layout-sider ul.ant-menu-root"
            )
            if element.is_displayed()
        ),
        None,
    )
    if menu is None:
        return tree
    if "ant-menu-inline-collapsed" in (menu.get_attribute("class") or ""):
        button = next(
            (
                element
                for element in driver.find_elements(
                    "css selector",
                    "aside .anticon-menu-unfold, aside [aria-label='menu-unfold'], "
                    ".ant-layout-sider .anticon-menu-unfold, "
                    ".ant-layout-sider [aria-label='menu-unfold'], .ant-layout-sider .trigger",
                )
                if element.is_displayed()
            ),
            None,
        )
        if button is not None:
            driver.execute_script("arguments[0].click()", button)
            time.sleep(0.5)

    submenus = driver.find_elements(
        "css selector",
        "aside ul.ant-menu-root > li.ant-menu-submenu, "
        ".ant-layout-sider ul.ant-menu-root > li.ant-menu-submenu",
    )
    for submenu in submenus:
        try:
            title = submenu.find_element("css selector", ":scope > .ant-menu-submenu-title")
            group_name = _clean_text(title.text)
            if not group_name:
                continue
            if "ant-menu-submenu-open" not in (submenu.get_attribute("class") or ""):
                driver.execute_script("arguments[0].click()", title)
            end = time.time() + 1.5
            items = []
            while time.time() < end and not items:
                items = driver.execute_script(
                    """
                    const expected = arguments[0];
                    const titles = [...document.querySelectorAll(
                      '.ant-layout-sider .ant-menu-submenu-title, aside .ant-menu-submenu-title'
                    )];
                    const title = titles.find(item =>
                      (item.innerText || '').replace(/\s+/g, ' ').trim() === expected
                    );
                    const submenu = title && title.closest('li.ant-menu-submenu');
                    if (!submenu || !submenu.classList.contains('ant-menu-submenu-open')) return [];
                    return [...submenu.querySelectorAll('li.ant-menu-item')]
                      .filter(item => item.offsetParent !== null)
                      .map(item => (item.innerText || '').replace(/\s+/g, ' ').trim())
                      .filter(Boolean);
                    """,
                    group_name,
                )
                if not items:
                    time.sleep(0.1)
            tree[group_name] = items
        except Exception:
            continue
    return tree


def capability_for_menu(group_name: str, item_name: str, profile: str) -> str | None:
    entry = feature_for_request(group_name, item_name, profile)
    return entry['feature_id'] if entry else None


@dataclass
class RuntimeProductContext:
    profile: str
    menu_tree: dict[str, list[str]]
    authorized: set[str]
    unknown_menus: list[tuple[str, str]]

    def has(self, feature_id: str) -> bool:
        return feature_id in self.authorized

    def status(self, feature_id: str) -> str:
        if feature_id not in supported_feature_ids(self.profile, include_excluded=True):
            return "版本不支持"
        feature = menu_catalog().get(feature_id, {})
        if feature.get("policy") == "excluded":
            return "策略排除"
        return "已授权" if self.has(feature_id) else "环境未授权"


def build_runtime_context(driver, profile: str | None = None) -> RuntimeProductContext:
    selected = profile or detect_build_profile()
    tree = scan_visible_menu_tree(driver)
    authorized = set()
    unknown = []
    for group_name, item_names in tree.items():
        if not item_names:
            group_features = [
                feature_id
                for feature_id in supported_feature_ids(
                    selected, include_excluded=True
                )
                if (profile_entry(feature_id, selected) or {}).get("group")
                == group_name
            ]
            if len(group_features) == 1:
                authorized.add(group_features[0])
            continue
        for item_name in item_names:
            feature_id = capability_for_menu(group_name, item_name, selected)
            if feature_id:
                authorized.add(feature_id)
            elif group_name not in {"直播管理"}:
                unknown.append((group_name, item_name))
    context = RuntimeProductContext(selected, tree, authorized, unknown)
    # Keep registered aliases bound to the actual rendered labels in this run.
    context.actual_entries = {
        feature_id: {"group": group, "item": item}
        for group, items in tree.items() for item in items
        if (feature_id := capability_for_menu(group, item, selected))
    }
    for feature_id, labels in context.actual_entries.items():
        _RUNTIME_MENU_LABELS[(selected, feature_id)] = labels
    return context
