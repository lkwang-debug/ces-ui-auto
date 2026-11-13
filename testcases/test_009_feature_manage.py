# -*- coding:utf-8 -*-
import time
import pytest


FEATURE_CODE = f"feature_case_{int(time.time())}"
FEATURE_NAME = f"特性用例_{int(time.time())}"
FEATURE_VALUE = "20"
UPDATED_FEATURE_VALUE = "21"


@pytest.fixture
def feature_case(feature_manage, request):
    code = f"uiauto_feature_{time.time_ns() % 1000000000}"
    if request.node.originalname != 'test_add_feature_success':
        assert feature_manage.add_feature(code, code, FEATURE_VALUE, result='新增成功') is True
    yield code
    if feature_manage.search_feature(code):
        assert feature_manage.delete_feature(code, result='删除成功') is True
    assert feature_manage.search_feature(code) is False


def test_enter_feature(feature_manage):
    assert feature_manage.common_enter_feature_manage() is True


def test_add_feature_success(feature_manage, feature_case):
    add_result = feature_manage.add_feature(
        feature_case,
        feature_case,
        FEATURE_VALUE,
        result="新增成功",
    )
    assert add_result is True


def test_find_feature(feature_manage, feature_case):
    assert feature_manage.search_feature(feature_case) is True


def test_find_missing_feature(feature_manage):
    assert feature_manage.search_feature(f"missing_feature_{time.time_ns()}") is False


def test_modify_feature(feature_manage, feature_case):
    modify_result = feature_manage.modify_feature(
        feature_case,
        UPDATED_FEATURE_VALUE,
        result="修改成功",
    )
    assert modify_result is True


def test_delete_feature(feature_manage, feature_case):
    delete_result = feature_manage.delete_feature(
        feature_case,
        result="删除成功",
    )
    assert delete_result is True
