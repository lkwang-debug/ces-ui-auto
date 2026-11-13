# -*- coding: utf-8 -*-
"""Allure report labels shared by every UI test.

The test file names intentionally stay stable for pytest discovery.  This module
separates that technical naming from the Chinese names shown to test users in
Allure.
"""

from __future__ import annotations

from pathlib import Path


MODULES = {
    "test_000_menu_inventory.py": ("全局导航", "菜单遍历"),
    "test_001_login.py": ("登录认证", "后台登录"),
    "test_002_organization.py": ("通讯录", "组织管理"),
    "test_003_user.py": ("通讯录", "用户管理"),
    "test_004_terminal.py": ("通讯录", "终端管理"),
    "test_005_global_record.py": ("录制管理", "全局录制设置"),
    "test_006_meetinginfo.py": ("会议管理", "会议室信息"),
    "test_007_back_permissons.py": ("服务器管理", "后台权限管理"),
    "test_008_data.py": ("服务器管理", "数据管理"),
    "test_009_feature_manage.py": ("配置中心", "特性管理"),
    "test_010_product_info.py": ("配置中心", "产品信息"),
    "test_011_feature_params_manage.py": ("配置中心", "特性参数管理"),
    "test_012_call.py": ("通讯录", "呼叫管理"),
    "test_013_operation_logs.py": ("日志管理", "操作日志"),
    "test_014_server_logs.py": ("日志管理", "服务器日志"),
    "test_015_node_authorization.py": ("系统信息", "节点授权信息"),
    "test_016_meeting_records.py": ("会议管理", "会议记录"),
    "test_017_meeting_scenarios.py": ("会议管理", "会议场景管理"),
    "test_018_meeting_statistics.py": ("会议管理", "会议统计"),
    "test_019_online_meetings.py": ("会议管理", "在线会议室"),
    "test_020_recording_tasks.py": ("录制管理", "录制任务管理"),
    "test_021_meeting_logs.py": ("日志管理", "会议日志"),
    "test_022_terminal_logs.py": ("日志管理", "终端日志"),
    "test_023_server_list.py": ("服务器管理", "服务器列表"),
    "test_024_global_settings.py": ("服务器管理", "全局设置"),
    "test_025_account_authentication.py": ("服务器管理", "帐号认证管理"),
    "test_026_developer.py": ("开发者中心", "开发者"),
    "test_027_ai_models.py": ("AI模型配置", "模型设置"),
    "test_028_face_library.py": ("人脸库管理", "人脸库"),
    "test_029_client_feature.py": ("功能权限管理", "客户端功能管理"),
    "test_030_personal_profile.py": ("个人中心", "修改资料"),
}


CASE_TITLES = {
    "test_enterprise_templates_and_default_restore": "企业场景模板与默认场景保存、刷新和恢复",
    "test_ai_model_other_valid_lifecycle": "其他有效AI模型独立生命周期验证",
    "test_meeting_email_notification_end_to_end": "会议室邮件通知端到端验证",
    "test_add_meeting_advanced_settings_and_recording_matrix": "新增会议室高级设置与录制方式矩阵验证",
    "test_modify_meeting_advanced_recording_modes_and_persistence": "修改会议室录制方式与配置持久化验证",
    "test_menu_item_is_reachable": "子菜单页面可达性验证",
    "test_menu_catalog_matches_authorized_tree": "菜单登记与实际授权清单一致性",
    "test_login_credential_matrix": "登录凭据校验矩阵",
    "test_admin_login_smoke": "管理员登录冒烟验证",
    "test_captcha_required_after_three_wrong_passwords": "连续错误密码触发验证码并 OCR 登录",
    "test_click_security_dialog_refresh_and_close": "安全验证弹窗展示、刷新与关闭",
    "test_click_security_incomplete_click_does_not_submit": "安全验证未点完时禁止提交登录",
    "test_click_security_wrong_order_is_rejected": "安全验证错误点击顺序被拒绝",
    "test_click_security_recognition_stability": "安全验证连续三十张识别稳定性",
    "test_click_security_coordinate_scaling": "安全验证不同分辨率坐标换算与登录",
    "test_click_security_three_consecutive_logins": "安全验证连续三轮独立登录",
    "test_add_user_phone_segment_compatibility": "新增用户手机号段兼容验证",
    "test_modify_user_phone_segment_compatibility": "修改用户手机号段兼容验证",
    "test_modify_user_nickname_middle_dot_compatibility": "修改用户昵称中文间隔号兼容验证",
    "test_server_list_structure": "服务器列表页面结构验证",
    "test_data_empty_state": "备份列表空状态或数据状态验证",
    "test_open_add_backup_dialog_and_cancel": "打开并取消新增备份弹窗",
    "test_open_upload_backup_dialog": "备份上传弹窗与文件格式验证",
    "test_backup_download_and_upload": "下载现有备份并上传验证",
    "test_data_table_headers": "备份列表表头验证",
    "test_server_required_field_validation": "服务器必填字段校验",
    "test_server_invalid_value_validation": "服务器非法参数校验",
    "test_ai_model_page_structure": "大语言模型设置页面结构校验",
    "test_ai_model_valid_lifecycle": "Deepseek模型完整生命周期与连通性验证",
    "test_ai_model_validation_matrix": "AI模型字段异常与边界校验矩阵",
    "test_ai_model_length_boundaries": "AI模型字段长度上限与越界校验",
    "test_ai_model_unreachable_connectivity": "不可连接AI模型失败时限验证",
    "test_face_library_page_structure": "人脸库页面结构校验",
    "test_face_name_and_position_length_boundaries": "人脸姓名和职位长度边界校验",
    "test_face_valid_lifecycle_and_batch_cleanup": "人脸新增修改查询与批量删除",
    "test_face_required_and_privacy_validation": "人脸必填字段与隐私协议校验",
    "test_face_abnormal_images_rejected": "异常人脸图片拒绝校验",
    "test_meeting_record_authorized_detail_entries": "会议记录授权详情入口校验",
    "test_recording_service_new_fields_and_switch_restore": "录制服务新增字段与开关恢复验证",
    "test_recording_service_invalid_slice_duration_not_persisted": "录制服务切片时长越界校验",
    "test_client_feature_page_structure": "客户端功能权限页面结构校验",
    "test_client_feature_default_permission_restore": "注册用户默认权限持久化与恢复",
    "test_client_feature_anonymous_permission_restore": "匿名用户权限持久化与恢复",
    "test_client_feature_user_scope_dialog": "指定用户范围弹窗校验",
    "test_admin_developer_crud_and_client_id": "管理员SDK应用新增查询修改停用与删除",
    "test_admin_sdk_and_ces_full_lifecycle": "管理员SDK与CES应用完整生命周期",
    "test_normal_user_password_special_symbol": "普通用户修改密码特殊符号验证",
    "test_normal_user_password_valid_equivalence": "普通用户修改密码合法等价类验证",
    "test_normal_user_password_invalid_matrix": "普通用户修改密码非法与边界验证",
    "test_admin_password_special_symbol_round_trip": "管理员修改密码特殊符号与恢复验证",
}


PHRASES = {
    "change_operation_log_page_size": "修改操作日志分页大小",
    "change_organize_page_size": "修改组织管理分页大小",
    "change_meeting_page_size": "修改会议室分页大小",
    "terminal_page_size_options": "终端管理分页控件与可选值验证",
    "change_product_page_size": "修改产品信息分页大小",
    "jump_operation_log_page": "跳转操作日志分页",
    "jump_organize_page": "跳转组织管理分页",
    "jump_meeting_page": "跳转会议室分页",
    "jump_product_page": "跳转产品信息分页",
    "server_parameter_validation": "服务器字段参数校验",
    "server_create_success": "新增服务器并持久化验证",
    "server_modify_success": "修改服务器并持久化验证",
    "server_search_success": "搜索新增服务器验证",
    "server_delete_success": "删除新增服务器验证",
}


WORDS = {
    "add": "新增",
    "admin": "管理员",
    "author": "授权",
    "authorized": "已授权",
    "authorization": "授权",
    "back": "后台",
    "batch": "批量",
    "basic": "基础",
    "cancel": "取消",
    "captcha": "验证码",
    "clear": "清空",
    "configured": "已配置",
    "credential": "凭据",
    "data": "数据",
    "delete": "删除",
    "developer": "开发者",
    "download": "下载",
    "duplicate": "重复",
    "empty": "空状态",
    "enter": "进入",
    "export": "导出",
    "failed": "失败",
    "feature": "特性",
    "fields": "字段",
    "find": "查询",
    "first": "首条",
    "global": "全局",
    "import": "导入",
    "info": "信息",
    "log": "日志",
    "logs": "日志",
    "meeting": "会议",
    "missing": "无结果",
    "modify": "修改",
    "node": "节点",
    "no": "无",
    "online": "在线",
    "open": "打开",
    "operation": "操作",
    "overwrite": "覆盖",
    "page": "分页",
    "params": "参数",
    "permissions": "权限",
    "preseeded": "预置",
    "product": "产品",
    "record": "录制",
    "records": "记录",
    "receiver": "接收人",
    "reset": "重置",
    "role": "角色",
    "round": "往返",
    "search": "搜索",
    "server": "服务器",
    "settings": "设置",
    "smoke": "冒烟",
    "statistics": "统计",
    "structure": "页面结构",
    "success": "成功",
    "supports": "支持",
    "tab": "标签",
    "task": "任务",
    "template": "模板",
    "terminal": "终端",
    "user": "用户",
    "valid": "有效性",
    "warning": "告警",
    "web": "Web",
    "workbook": "工作簿",
}


SCENARIO_TITLES = {
    "valid": "正确用户名和密码",
    "wrong_password": "正确用户名与错误密码",
    "wrong_username": "错误用户名与正确格式密码",
    "wrong_both": "用户名和密码均错误",
    "empty_username": "用户名为空",
    "empty_password": "密码为空",
    "empty_both": "用户名和密码均为空",
    "username_whitespace": "用户名包含前后空格",
    "username_case_changed": "用户名不区分大小写且登录同一账号",
    "oversized_values": "用户名和密码超长输入",
    "special_characters": "用户名和密码包含特殊字符",
}


def module_for_item(item):
    filename = Path(str(item.fspath)).name
    profile = getattr(item.config, "_ces_product_profile", "legacy")
    if profile == "4.39.8":
        if filename == "test_005_global_record.py":
            return "录制管理", "录制服务设置"
        if filename == "test_007_back_permissons.py":
            return "功能权限管理", "后台权限管理"
        if filename == "test_026_developer.py":
            callspec = getattr(item, "callspec", None)
            feature_id = (callspec.params.get("feature_id") or callspec.params.get('channel')) if callspec else None
            return "开发者中心", "服务端 API 接入" if feature_id == "developer_ces" else "客户端 SDK接入"
    return MODULES.get(filename)


def _translated_function_name(function_name):
    if function_name in CASE_TITLES:
        return CASE_TITLES[function_name]
    raw = function_name.removeprefix("test_")
    if raw in PHRASES:
        return PHRASES[raw]
    return "".join(WORDS.get(token, "") for token in raw.split("_")) or "自动化校验"


def case_title(item):
    title = _translated_function_name(item.originalname or item.name.split("[", 1)[0])
    params = getattr(item, "callspec", None)
    if params is None:
        return title
    values = params.params
    if 'model_key' in values:
        manager=getattr(item.module,'ConfigManager',None)
        configured=getattr(manager,'AI_MODEL_CONFIGS',[])
        name=next((x['name'] for x in configured if x['key']==values['model_key']),values['model_key'])
        return f"{title}：{name}"
    if 'case_id' in values:
        for section in getattr(item.module,'PASSWORD_DATA',{}).values():
            if values['case_id'] in section:
                return f"{title}：{section[values['case_id']]['scenario']}"
    if 'width' in values and 'height' in values:
        return f"{title}：{values['width']}×{values['height']}"
    if "group_name" in values and "item_name" in values:
        return f"菜单可达性：{values['group_name']} / {values['item_name']}"
    payload = values.get("params")
    if isinstance(payload, dict):
        scenario = payload.get("scenario") or payload.get("description")
        if scenario:
            return f"{title}：{SCENARIO_TITLES.get(str(scenario), scenario)}"
    return title


def report_title_template(item):
    """Return an Allure title template that is safe for shared parametrized functions."""
    function_name = item.originalname or item.name.split("[", 1)[0]
    if function_name == "test_menu_item_is_reachable":
        return "菜单可达性验证：{group_name} / {item_name}"
    return _translated_function_name(function_name)


def validate_collected_items(items):
    missing = []
    for item in items:
        if module_for_item(item) is None:
            missing.append(str(item.fspath))
    if missing:
        unique = "\n".join(sorted(set(missing)))
        raise RuntimeError(f"Allure 中文元数据缺少模块映射：\n{unique}")
