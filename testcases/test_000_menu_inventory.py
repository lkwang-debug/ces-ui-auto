# -*- coding: utf-8 -*-
import allure
import pytest

from common.product_profile import detect_build_profile, inventory_cases
from conf.conf import ConfigManager

BUILD_PROFILE = detect_build_profile(ConfigManager.HST_URL)
MENU_CASES = inventory_cases(BUILD_PROFILE)


@pytest.mark.smoke
def test_menu_catalog_matches_authorized_tree(product_context):
    allure.attach(str(product_context.menu_tree), "实际菜单清单", allure.attachment_type.TEXT)
    assert not product_context.unknown_menus, f"发现未登记的新菜单：{product_context.unknown_menus}"


@pytest.fixture(scope="module")
def menu_inventory(driver):
    from pages.MenuInventoryPage import MenuInventoryPage

    return MenuInventoryPage(driver=driver)


@pytest.mark.smoke
@pytest.mark.parametrize(
    "feature_id,group_name,item_name",
    [(case["feature_id"], case["group"], case["item"]) for case in MENU_CASES],
    ids=[f'{case["group"]}-{case["item"]}' for case in MENU_CASES],
)
def test_menu_item_is_reachable(
    menu_inventory, product_context, feature_id, group_name, item_name
):
    if not product_context.has(feature_id):
        if feature_id in ConfigManager.REQUIRED_CAPABILITIES:
            pytest.fail(f"必测菜单未授权：{group_name} / {item_name}")
        pytest.skip(f"当前环境未授权：{group_name} / {item_name}")
    with allure.step(f"打开菜单：{group_name} / {item_name}"):
        result = menu_inventory.open_menu_item(feature_id=feature_id)
    with allure.step("校验目标路由和页面主体内容"):
        assert result is not None, f"菜单不可达: {group_name} / {item_name}"
        assert result["url"]
        assert result["text"], f"页面主内容为空: {group_name} / {item_name}"
        assert result["feature_id"] == feature_id
        allure.attach(result["url"], "页面路由", allure.attachment_type.TEXT)
        allure.attach(result["text"][:3000], "页面主体内容", allure.attachment_type.TEXT)
    with allure.step("保留当前菜单页面，供人工观察"):
        menu_inventory.hold_page_for_visual_check()
