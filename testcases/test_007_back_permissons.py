# -*- coding:utf-8 -*-
import time
import pytest

pytestmark = pytest.mark.requires_capability("back_permissions")


ROLE_NAME = f"role_case_{int(time.time())}"
ROLE_DESC = "stable_desc"
UPDATED_ROLE_DESC = f"updated_desc_{int(time.time())}"


@pytest.fixture
def role_case(back_permissions, request):
    name = f"uiauto_role_{time.time_ns() % 1000000000}"
    if request.node.originalname != 'test_add_role_permissions_success':
        assert back_permissions.add_role(name, ROLE_DESC, permission_names=['系统信息'], result='操作成功') is True
    yield name
    if back_permissions.search_role(name):
        assert back_permissions.delete_role(name, result='删除成功') is True
    assert back_permissions.search_role(name) is False


def test_enter_back_permissions(back_permissions):
    assert back_permissions.common_enter_back_permissions() is True


def test_add_role_permissions_success(back_permissions, role_case):
    add_result = back_permissions.add_role(
        role_case,
        ROLE_DESC,
        permission_names=["系统信息"],
        result="操作成功",
    )
    assert add_result is True


def test_find_role_permissions(back_permissions, role_case):
    assert back_permissions.search_role(role_case) is True


def test_modify_role_permissions(back_permissions, role_case):
    modify_result = back_permissions.modify_role_description(
        role_case, UPDATED_ROLE_DESC, result="修改成功"
    )
    assert modify_result is True


def test_delete_role_permissions(back_permissions, role_case):
    delete_result = back_permissions.delete_role(role_case, result="删除成功")
    assert delete_result is True
