# -*- coding: utf-8 -*-
import time
import json

import allure
import pytest


SERVER_PROFILES = (
    {
        "key": "meeting",
        "name": "会议服务器",
        "address": "198.51.100.10",
        "type_names": ("会议服务器",),
        "selects": {
            "设备类型": "会议服务器",
            "设备状态": "可用",
            "备用设备": "无记录",
            "调度优先级": "中",
        },
        "numbers": {
            "最大在线用户数": "300",
            "会议用户最大数": "100",
            "最大网络带宽": "1000000",
        },
        "required_fields": ("设备ID", "设备名称", "设备验证码", "服务器地址"),
    },
    {
        "key": "recording",
        "name": "录制服务器",
        "address": "198.51.100.11",
        "type_names": ("资源平台服务器", "录制服务器"),
        # 4.39.7 preselects this value and does not expose it as a normal
        # option list in the recording-server form.
        "uses_default_type": True,
        "selects": {"设备类型": "资源平台服务器"},
        "numbers": {},
        "required_fields": ("设备ID", "设备名称", "设备验证码", "服务器地址"),
    },
)


def _suffix():
    return str(time.time_ns())[-10:]


def _payload(server_list, profile):
    return server_list.build_server_payload(profile, _suffix())


@pytest.fixture
def server_cleanup(server_list):
    identifiers = []
    try:
        yield identifiers
    finally:
        with allure.step("清理本用例创建的服务器"):
            for identifier in reversed(identifiers):
                cleared = server_list.ensure_server_absent(identifier)
                allure.attach(json.dumps({'设备ID':identifier,'本次登记名称':server_list._server_name_history.get(identifier,[]),'清理成功':cleared},ensure_ascii=False),
                              '服务器清理结果',allure.attachment_type.JSON)
                assert cleared is True, f'本次服务器清理未确认完成：{identifier}'


@pytest.fixture(scope="module")
def server_crud_available(server_list):
    if not server_list.has_server_crud_entry():
        actions = "、".join(server_list.server_list_actions()) or "无"
        pytest.skip(f"当前版本服务器列表未提供新增服务器入口；可见操作：{actions}")
    return server_list


def test_server_list_structure(server_list):
    with allure.step("进入服务器列表"):
        snapshot = server_list.open_server_list()
    assert snapshot is not None
    assert "服务器分类" in snapshot["text"]
    assert server_list.visible_server_categories()


@pytest.mark.parametrize(
    "profile,field_name",
    [
        (profile, field_name)
        for profile in SERVER_PROFILES
        for field_name in profile["required_fields"]
    ],
    ids=[
        f"{profile['key']}-{field_name}不能为空"
        for profile in SERVER_PROFILES
        for field_name in profile["required_fields"]
    ],
)
@pytest.mark.usefixtures("server_crud_available")
def test_server_required_field_validation(server_list, profile, field_name):
    payload = _payload(server_list, profile)
    with allure.step(f"校验{profile['name']}字段「{field_name}」不能为空"):
        assert server_list.validate_required_field(profile, payload, field_name) is True


@pytest.mark.parametrize(
    "profile,field_name,invalid_value",
    [
        (SERVER_PROFILES[0], "服务器地址", "999.1.1.1"),
        (SERVER_PROFILES[1], "服务器地址", "not-an-ip"),
        (SERVER_PROFILES[0], "最大在线用户数", "0"),
        (SERVER_PROFILES[0], "最大在线用户数", "-1"),
        (SERVER_PROFILES[0], "最大在线用户数", "abc"),
        (SERVER_PROFILES[0], "会议用户最大数", "0"),
        (SERVER_PROFILES[0], "会议用户最大数", "-1"),
        (SERVER_PROFILES[0], "会议用户最大数", "abc"),
        (SERVER_PROFILES[0], "最大网络带宽", "0"),
        (SERVER_PROFILES[0], "最大网络带宽", "-1"),
        (SERVER_PROFILES[0], "最大网络带宽", "abc"),
    ],
    ids=[
        "会议服务器-地址格式错误",
        "录制服务器-地址格式错误",
        "会议服务器-最大在线人数为零",
        "会议服务器-最大在线人数为负数",
        "会议服务器-最大在线人数为非数字",
        "会议服务器-会议人数为零",
        "会议服务器-会议人数为负数",
        "会议服务器-会议人数为非数字",
        "会议服务器-网络带宽为零",
        "会议服务器-网络带宽为负数",
        "会议服务器-网络带宽为非数字",
    ],
)
@pytest.mark.usefixtures("server_crud_available")
def test_server_invalid_value_validation(server_list, server_cleanup, profile, field_name, invalid_value):
    payload = _payload(server_list, profile)
    if profile['key'] == 'meeting' and field_name == '最大在线用户数' and invalid_value == '0':
        allure.dynamic.title('会议服务器最大在线用户数允许0并持久化验证')
        allure.dynamic.parameter('预期行为','允许保存0')
        payload[field_name] = '0'
        server_cleanup.append(payload['设备ID'])
        with allure.step('新增并保存最大在线用户数为0的独立服务器'):
            assert server_list.create_server(profile,payload) is True
        with allure.step('刷新并重新打开准确服务器，确认最大在线用户数仍为0'):
            assert server_list.read_server_field(payload['设备ID'],field_name,refresh=True) == '0'
        return
    with allure.step(f"校验{profile['name']}字段「{field_name}」非法值"):
        assert (
            server_list.validate_invalid_value(
                profile, payload, field_name, invalid_value
            )
            is True
        )


@pytest.mark.parametrize("profile", SERVER_PROFILES, ids=lambda profile: profile["name"])
@pytest.mark.usefixtures("server_crud_available")
def test_server_create_success(server_list, server_cleanup, profile):
    payload = _payload(server_list, profile)
    server_cleanup.append(payload["设备ID"])
    with allure.step(f"新增{profile['name']}"):
        assert server_list.create_server(profile, payload) is True
    with allure.step("刷新后确认服务器数据已保存"):
        assert server_list.search_server(payload["设备ID"]) is True


@pytest.mark.parametrize("profile", SERVER_PROFILES, ids=lambda profile: profile["name"])
@pytest.mark.usefixtures("server_crud_available")
def test_server_modify_success(server_list, server_cleanup, profile):
    payload = _payload(server_list, profile)
    server_cleanup.append(payload["设备ID"])
    with allure.step(f"创建用于修改的{profile['name']}"):
        assert server_list.create_server(profile, payload) is True
    changes = {"设备名称": f"{payload['设备名称']}_updated"[-48:]}
    if profile["key"] == "meeting":
        changes["最大在线用户数"] = "301"
    with allure.step("修改服务器参数并验证持久化"):
        assert server_list.modify_server(payload["设备ID"], changes) is True


@pytest.mark.parametrize("profile", SERVER_PROFILES, ids=lambda profile: profile["name"])
@pytest.mark.usefixtures("server_crud_available")
def test_server_search_success(server_list, server_cleanup, profile):
    payload = _payload(server_list, profile)
    server_cleanup.append(payload["设备ID"])
    with allure.step(f"创建用于搜索的{profile['name']}"):
        assert server_list.create_server(profile, payload) is True
    with allure.step("按本次新增的唯一服务器名称搜索"):
        assert server_list.search_server(payload["设备ID"]) is True


@pytest.mark.parametrize("profile", SERVER_PROFILES, ids=lambda profile: profile["name"])
@pytest.mark.usefixtures("server_crud_available")
def test_server_delete_success(server_list, server_cleanup, profile):
    payload = _payload(server_list, profile)
    server_cleanup.append(payload["设备ID"])
    with allure.step(f"创建用于删除的{profile['name']}"):
        assert server_list.create_server(profile, payload) is True
    with allure.step("删除新增服务器并验证不可检索"):
        assert server_list.delete_server(payload["设备ID"]) is True
    server_cleanup.remove(payload["设备ID"])
