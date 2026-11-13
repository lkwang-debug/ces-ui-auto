# -*- coding: utf-8 -*-
import time
import json

import allure
import pytest

from conf.conf import ConfigManager
from common.ui_state import wait_query_finished


pytestmark = pytest.mark.requires_capability("ai_model")


def _required_keys_present():
    missing = [item["key"] for item in ConfigManager.AI_MODEL_CONFIGS if not item["api_key"]]
    if not missing:
        return
    message = "AI模型真实API KEY未配置：" + ", ".join(missing)
    if ConfigManager.ACCEPTANCE_MODE:
        pytest.fail(message)
    pytest.skip(message)


def test_ai_model_page_structure(ai_models):
    page = ai_models.open_models()
    assert page is not None
    assert "大语言模型设置" in page["text"]
    assert "新增模型" in page["text"]
    assert "连通性测试" in page["text"]


def test_ai_model_valid_lifecycle(ai_models):
    _run_ai_model_lifecycle(ai_models,ConfigManager.AI_MODEL_CONFIGS[0])


@pytest.mark.parametrize('model_key',[item['key'] for item in ConfigManager.AI_MODEL_CONFIGS[1:]])
def test_ai_model_other_valid_lifecycle(ai_models,model_key):
    configured=next(item for item in ConfigManager.AI_MODEL_CONFIGS if item['key']==model_key)
    _run_ai_model_lifecycle(ai_models,configured)


def _run_ai_model_lifecycle(ai_models,configured):
    __tracebackhide__=True
    ai_models.last_lifecycle_evidence={}
    _required_keys_present()
    suffix = str(time.time_ns())[-8:]
    created = []
    original_default = ""
    try:
        assert ai_models.open_models() is not None, "模型页面未就绪，禁止修改默认模型"
        assert wait_query_finished(ai_models, 0, timeout=10, request_path='/serv/v1/ai/model/page'), "读取默认模型前列表请求未完成"
        original_default = ai_models.default_model_name()
        assert original_default, "前置条件：未读取到原默认模型，禁止修改默认配置"
        for index, configured in enumerate([configured]):
            payload = dict(configured)
            safe_key = "".join(char for char in configured["key"] if char.isalnum())
            payload["name"] = f"uiautoAI{safe_key}{suffix}"
            modified = payload["name"] + "M"
            created.extend([payload['name'],modified])
            with allure.step(f"新增并刷新验证模型：{configured['name']}"):
                assert ai_models.create(payload) is True, ai_models.last_messages
                assert ai_models.exists(payload["name"], refresh=True)
            with allure.step('新增后执行真实连通性测试'):
                before=ai_models.test_connectivity(payload['name'],'连通性测试通过',ConfigManager.AI_CONNECT_SUCCESS_TIMEOUT)
                allure.attach(str(before),'修改前连通性结果',allure.attachment_type.TEXT)
            with allure.step("API KEY留空并仅修改模型名称"):
                assert ai_models.modify_name_keep_key(payload["name"], modified) is True, ai_models.last_modify_evidence
                assert ai_models.exists(modified, refresh=True)
            with allure.step("10秒内完成真实连通性测试"):
                result = ai_models.test_connectivity(
                    modified, "连通性测试通过", ConfigManager.AI_CONNECT_SUCCESS_TIMEOUT
                )
                allure.attach(str(result), "连通性测试结果", allure.attachment_type.TEXT)
                ai_models.last_lifecycle_evidence={'key':configured['key'],'before':before,'after':result}
                if not before['matched'] or not result['matched']:
                    from common.ai_diagnostics import diagnose_model_service
                    ai_models.last_lifecycle_evidence['upstream']=diagnose_model_service(configured)
                    allure.attach(json.dumps(ai_models.last_lifecycle_evidence,ensure_ascii=False),'UI失败与上游诊断（不替代UI断言）',allure.attachment_type.JSON)
                assert before['matched'] is True and result["matched"] is True, ai_models.last_lifecycle_evidence
                assert result["elapsed"] <= ConfigManager.AI_CONNECT_SUCCESS_TIMEOUT
            if index == 0:
                with allure.step("设为默认并刷新确认"):
                    assert ai_models.set_default(modified) is True
                    assert ai_models.exists(modified, refresh=True)
                    assert ai_models.default_model_name() == modified
    finally:
        try:
            assert ai_models.close_modal() is True
            if original_default and ai_models.exists(original_default, refresh=True):
                assert ai_models.set_default(original_default) is True
                assert ai_models.exists(original_default,refresh=True)
                assert ai_models.default_model_name() == original_default
        finally:
            cleanup={}
            for name in reversed(created):
                try:
                    cleanup[name]=ai_models.delete(name)
                except Exception as error:
                    cleanup[name]=type(error).__name__
            allure.attach(str(cleanup), "AI临时模型清理结果", allure.attachment_type.TEXT)
            assert all(value is True for value in cleanup.values()),f'AI临时模型清理失败: {cleanup}'


@pytest.mark.extended
@pytest.mark.parametrize(
    "overrides",
    [
        {"name": ""},
        {"vendor": ""},
        {"model": ""},
        {"url": ""},
        {"api_key": ""},
        {"name": "uiauto_ai_bad@name"},
        {"name": "uiauto-ai-dot.name"},
        {"model": "中文模型"},
        {"url": "ftp://invalid.example/v1"},
        {"url": "http:///missing-host"},
        {"api_key": "bad key with spaces"},
    ],
    ids=[
        "名称为空", "厂商为空", "模型为空", "地址为空", "密钥为空",
        "名称下划线特殊字符", "名称连字符和点号", "模型含中文", "非法协议", "地址缺少主机", "密钥含空格",
    ],
)
def test_ai_model_validation_matrix(ai_models, overrides):
    payload = {
        "name": f"uiautoAIInvalid{str(time.time_ns())[-8:]}",
        "vendor": "Deepseek",
        "model": "deepseek-v4-flash",
        "url": "http://198.51.100.10/v1/chat/completions",
        "api_key": "uiauto-valid-key_123",
    }
    payload.update(overrides)
    if overrides.get('name'):
        payload['name'] += str(time.time_ns())[-6:]
    try:
        target_field=next(iter(overrides))
        rejected, errors = ai_models.validate_rejected(payload,target_field=target_field)
        assert rejected is True
        assert errors, "非法AI模型参数未显示字段错误提示"
        assert ai_models.last_validation_fields.get(target_field), f'目标字段未拒绝输入: {target_field}'
        assert ai_models.exists(payload.get("name", ""),refresh=True) is False
    finally:
        ai_models.close_modal()
        if payload.get('name'):
            assert ai_models.delete(payload['name']) is True


@pytest.mark.extended
def test_ai_model_length_boundaries(ai_models):
    prefix='uiautoAI'+str(time.time_ns())[-8:]
    name = prefix+'A'*(64-len(prefix))
    payload = {
        "name": name,
        "vendor": "Deepseek",
        "model": "m" * 64,
        "url": "http://198.51.100.10/v1/chat/completions",
        "api_key": "k" * 128,
    }
    try:
        assert ai_models.create(payload) is True, ai_models.last_messages
        assert ai_models.exists(name, refresh=True)
    finally:
        assert ai_models.delete(name) is True

    snapshot = ai_models.input_length_snapshot("N" * 65, "m" * 65, "k" * 129)
    assert snapshot["form_item_name"] == {"maxlength": 64, "length": 64}
    assert snapshot["form_item_modelId"] == {"maxlength": 64, "length": 64}
    assert snapshot["form_item_apiKey"] == {"maxlength": 128, "length": 128}


@pytest.mark.extended
def test_ai_model_unreachable_connectivity(ai_models):
    name = f"uiautoAIUnreachable{str(time.time_ns())[-8:]}"
    payload = {
        "name": name,
        "vendor": "Deepseek",
        "model": "deepseek-v4-flash",
        "url": "http://198.51.100.254:65534/v1/chat/completions",
        "api_key": "uiauto-invalid-key",
    }
    try:
        assert ai_models.create(payload) is True
        result = ai_models.test_connectivity(
            name, "失败", ConfigManager.AI_CONNECT_FAILURE_TIMEOUT
        )
        allure.attach(str(result), "不可连接模型测试结果", allure.attachment_type.TEXT)
        assert result["matched"] is True, result
        assert result["elapsed"] <= ConfigManager.AI_CONNECT_FAILURE_TIMEOUT
    finally:
        assert ai_models.delete(name) is True
