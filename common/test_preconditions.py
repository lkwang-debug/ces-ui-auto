# -*- coding:utf-8 -*-
import pytest
import time
from contextlib import contextmanager
import allure
from conf.conf import ConfigManager


@contextmanager
def pagination_records(page, enter, create, remove, prefix, minimum_total=11):
    """Prepare only missing rows for this case; never depend on a prior CRUD."""
    assert enter() is True, '分页前置：目标页面未就绪'
    reset=getattr(page,'reset_search',lambda:page.jump_to_result_page(1))
    assert reset() is not False, '分页前置：查询条件未恢复'
    def count_ready():
        value=page.get_total_record_count()
        return {'total':value} if isinstance(value,int) else False
    observed=page.wait_until(count_ready,timeout=10)
    assert observed is not False, '分页前置：未读取到当前模块总数，禁止按数据不足跳过'
    total=observed['total']
    owned=[]
    try:
        stamp=time.time_ns()%1000000000
        for index in range(max(0,minimum_total-total)):
            identifier=f'{prefix}{stamp}_{index}'
            owned.append(identifier)
            assert create(identifier) is True,f'分页独立数据创建失败: {identifier}'
        assert reset() is not False
        assert page.get_total_record_count()>=minimum_total, '分页独立数据未达到前置数量'
        yield
    finally:
        cleanup={}
        for identifier in reversed(owned):
            try:cleanup[identifier]=remove(identifier)
            except Exception as error:cleanup[identifier]=type(error).__name__
        allure.attach(str(cleanup),'分页独立数据清理结果',allure.attachment_type.TEXT)
        assert all(value is True for value in cleanup.values()),f'分页独立数据清理失败: {cleanup}'


def require_minimum_records(
    page_object,
    minimum_total=11,
    module_name="当前模块",
    scenario_name="分页测试",
):
    """
    Skip environment-dependent tests when the current page does not contain
    enough records to exercise pagination behavior.
    """
    total = page_object.get_total_record_count()
    if total is None:
        message=f"前置条件：{module_name}{scenario_name}未能获取总记录数，无法确认至少 {minimum_total} 条数据"
        if ConfigManager.ACCEPTANCE_MODE:pytest.fail(message)
        pytest.skip(message)
    if total < minimum_total:
        message=f"前置条件：{module_name}{scenario_name}当前仅有 {total} 条数据，至少需要 {minimum_total} 条数据"
        if ConfigManager.ACCEPTANCE_MODE:pytest.fail(message)
        pytest.skip(message)
    return total


def require_tab_has_data(page_object, tab_name="当前标签页"):
    """
    Skip data assertions when the current log tab is empty in the environment.
    """
    if page_object.current_tab_has_no_data():
        message=f'前置条件：{tab_name}当前环境下该标签页暂无数据'
        if ConfigManager.ACCEPTANCE_MODE:pytest.fail(message)
        pytest.skip(message)
    return True
