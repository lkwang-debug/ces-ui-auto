# -*- coding:utf-8 -*-
import pytest
import time
from common.test_preconditions import require_minimum_records,pagination_records


PRODUCT_SUFFIX = str(int(time.time()))
PRODUCT_NAME = f"product_case_{PRODUCT_SUFFIX}"
PRODUCT_ID = f"AUTO_PROD_{PRODUCT_SUFFIX}"
UPDATED_PRODUCT_NAME = f"product_updated_{PRODUCT_SUFFIX}"


@pytest.fixture
def product_case(product_info, request):
    suffix = str(time.time_ns() % 1000000000)
    data = {'id':f'UIAUTO_{suffix}', 'name':f'uiauto_product_{suffix}', 'updated':f'uiauto_updated_{suffix}'}
    if request.node.originalname != 'test_add_product_success':
        assert product_info.add_product(data['name'], data['id']) is True
    yield data
    if product_info.find_product(data['id']):
        assert product_info.delete_product(data['id']) is True
    assert product_info.find_product(data['id']) is False

def test_enter_product(product_info):
    assert product_info.common_enter_product_info() is True


@pytest.fixture
def product_pagination_data(product_info):
    with pagination_records(product_info,product_info.common_enter_product_info,
        lambda value:product_info.add_product(value,value),
        lambda value:product_info.delete_product(value) if product_info.find_product(value) else True,'UIP'):
        yield


def test_change_product_page_size(product_info,product_pagination_data):
    require_minimum_records(
        product_info,
        minimum_total=11,
        module_name="产品信息",
        scenario_name="分页相关测试",
    )
    try:
        assert product_info.jump_to_result_page(1) is True
        assert product_info.set_result_page_size(10) is True
        assert "10" in (product_info.get_current_page_size_text() or "")
    finally:
        product_info.set_result_page_size(15)
        product_info.jump_to_result_page(1)


def test_jump_product_page(product_info,product_pagination_data):
    require_minimum_records(
        product_info,
        minimum_total=11,
        module_name="产品信息",
        scenario_name="分页相关测试",
    )
    try:
        assert product_info.jump_to_result_page(1) is True
        assert product_info.set_result_page_size(10) is True
        first_page_summary = product_info.get_pagination_summary_text()
        assert product_info.jump_to_result_page(2) is True
        assert product_info.get_current_page_text() == "2"
        second_page_summary = product_info.get_pagination_summary_text()
        assert second_page_summary
        assert second_page_summary != first_page_summary
        assert product_info.jump_to_result_page(1) is True
        assert product_info.get_current_page_text() == "1"
    finally:
        product_info.set_result_page_size(15)
        product_info.jump_to_result_page(1)


def test_add_product_success(product_info, product_case):
    add_result = product_info.add_product(product_case['name'], product_case['id'])
    assert add_result is True


def test_find_product(product_info, product_case):
    assert product_info.find_product(product_case['id']) is True


def test_find_missing_product(product_info):
    assert product_info.find_product(f"MISSING_PRODUCT_{time.time_ns()}") is False


def test_modify_product(product_info, product_case):
    modify_result = product_info.modify_product(product_case['id'], product_case['updated'])
    assert modify_result is True


def test_delete_product(product_info, product_case):
    delete_result = product_info.delete_product(product_case['id'])
    assert delete_result is True
