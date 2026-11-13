# -*- coding: utf-8 -*-
import allure


def assert_page_feature(page, group_name, item_name, require_controls=True):
    with allure.step(f"打开菜单：{group_name} / {item_name}"):
        snapshot = page.open_feature(group_name, item_name)
    assert snapshot is not None, f"目标页面未渲染：{group_name} / {item_name}"
    assert item_name in snapshot["text"] or snapshot.get("identity_verified") is True, (
        f"目标页面缺少标题且路由/专属控件身份校验失败：{group_name} / {item_name}"
    )
    if require_controls:
        assert snapshot["buttons"] or snapshot["inputs"] or snapshot["headers"], (
            f"No page-specific controls found: {group_name} / {item_name}"
        )
    return snapshot
