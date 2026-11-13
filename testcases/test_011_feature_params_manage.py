# -*- coding:utf-8 -*-
import time
import pytest


FEATURE_NAME = "屏幕共享声音"
FEATURE_CODE = "VNCAudio"
VENDOR_NAME = f"auto_vendor_{int(time.time())}"
RETURN_VALUE = "true"
UPDATED_RETURN_VALUE = "false"


@pytest.fixture
def vendor_case(feature_params_manage, request):
    vendor = f'uiauto_vendor_{time.time_ns() % 1000000000}'
    if request.node.originalname != 'test_add_feature_param_success':
        assert feature_params_manage.add_feature_param(feature_name=FEATURE_NAME, feature_code=FEATURE_CODE,
            vendor_name=vendor, return_value=RETURN_VALUE, result='添加成功') is True
    yield vendor
    if feature_params_manage.search_feature_param(FEATURE_CODE, vendor):
        assert feature_params_manage.delete_feature_param(FEATURE_CODE, vendor, result='删除成功') is True
    assert feature_params_manage.search_feature_param(FEATURE_CODE, vendor) is False


def test_enter_feature_params(feature_params_manage):
    assert feature_params_manage.common_enter_feature_params_manage() is True


def test_add_feature_param_success(feature_params_manage, vendor_case):
    add_result = feature_params_manage.add_feature_param(
        feature_name=FEATURE_NAME,
        feature_code=FEATURE_CODE,
        vendor_name=vendor_case,
        return_value=RETURN_VALUE,
        result="添加成功",
    )
    assert add_result is True


def test_find_feature_params(feature_params_manage, vendor_case):
    assert feature_params_manage.search_feature_param(FEATURE_CODE, vendor_case) is True


def test_find_missing_feature_params(feature_params_manage):
    assert feature_params_manage.search_feature_param(
        FEATURE_CODE, f"missing_vendor_{time.time_ns()}"
    ) is False


def test_modify_feature_params(feature_params_manage, vendor_case):
    modify_result = feature_params_manage.modify_feature_param(
        feature_code=FEATURE_CODE,
        vendor_name=vendor_case,
        new_return_value=UPDATED_RETURN_VALUE,
        result="修改成功",
    )
    assert modify_result is True


def test_delete_feature_params(feature_params_manage, vendor_case):
    delete_result = feature_params_manage.delete_feature_param(
        feature_code=FEATURE_CODE,
        vendor_name=vendor_case,
        result="删除成功",
    )
    assert delete_result is True
