# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
import hashlib
from pathlib import Path

import allure
import pytest
from conf.conf import ConfigManager


pytestmark = [pytest.mark.regression, pytest.mark.security]
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PASSWORD_DATA = json.loads(
    (PROJECT_ROOT / "data" / "personal_password_data.json").read_text(
        encoding="utf-8"
    )
)
RECOVERY_DIR = PROJECT_ROOT / ".recovery"
NORMAL_USERNAME = ConfigManager.PROFILE_PASSWORD_USERNAME
NORMAL_PASSWORD = ConfigManager.PROFILE_PASSWORD_PASSWORD
_VERIFIER = None


@pytest.fixture(scope='module')
def personal_profile(verification_driver):
    from pages.PersonalProfilePage import PersonalProfilePage
    global _VERIFIER
    _VERIFIER = PersonalProfilePage(driver=verification_driver)
    yield _VERIFIER
    _VERIFIER = None


def _password_metadata(password):
    value = str(password)
    return {
        "长度": len(value),
        "包含数字": bool(re.search(r"\d", value)),
        "包含字母": bool(re.search(r"[A-Za-z]", value)),
        "特殊符号": sorted({char for char in value if not char.isalnum()}),
    }


def _attach_result(name, result, password=None):
    evidence = {
        "保存成功": result.get("saved"),
        "字段错误": result.get("field_errors"),
        "页面消息": result.get("message"),
        "弹窗关闭": result.get("modal_closed"),
        "可见层": result.get("visible_layers"),
    }
    if password is not None:
        evidence["密码特征"] = _password_metadata(password)
    allure.attach(
        json.dumps(evidence, ensure_ascii=False, indent=2),
        name,
        allure.attachment_type.JSON,
    )


def _invalid_values(case, original_password):
    mode = case["mode"]
    old_password = original_password
    new_password = "Auto123$"
    confirm_password = new_password
    if mode == "old_empty":
        old_password = ""
    elif mode == "wrong_old":
        old_password = "WrongOld1$"
    elif mode == "new_empty":
        new_password = ""
        confirm_password = ""
    elif mode == "confirm_empty":
        confirm_password = ""
    elif mode == "same_old":
        new_password = original_password
        confirm_password = original_password
    elif mode == "confirm_mismatch":
        confirm_password = "Auto123#"
    elif mode == "custom":
        new_password = case["password"]
        confirm_password = new_password
    return old_password, new_password, confirm_password


def _recovery_file(account_key):
    username=ConfigManager.USERNAME if account_key=='admin' else NORMAL_USERNAME
    scope=hashlib.sha256((ConfigManager.HST_URL.rstrip('/')+'|'+username).encode()).hexdigest()[:16]
    return RECOVERY_DIR / f"{scope}-{account_key}-password-state.json"


def _write_recovery_state(account_key, section, case_id):
    RECOVERY_DIR.mkdir(parents=True, exist_ok=True)
    _recovery_file(account_key).write_text(
        json.dumps(
            {"section": section, "case_id": case_id, 'target':ConfigManager.HST_URL,
             'account':ConfigManager.USERNAME if account_key=='admin' else NORMAL_USERNAME}, ensure_ascii=False
        ),
        encoding="utf-8",
    )


def _clear_recovery_state(account_key):
    _recovery_file(account_key).unlink(missing_ok=True)


def _candidate_from_state(account_key, original_password):
    path = _recovery_file(account_key)
    if not path.exists():
        return ""
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        section = state["section"]
        case = PASSWORD_DATA[section][state["case_id"]]
        if section == "invalid":
            return _invalid_values(case, original_password)[1]
        return case["password"]
    except (KeyError, OSError, ValueError, TypeError):
        return ""


def _login_known_password(personal_profile, username, password, attempts=1):
    for _ in range(attempts):
        if personal_profile.login_as(username, password):
            return True
    return False


def _verify_credentials_in_fresh_browser(username, password, attempts=1):
    # A fresh authentication session in the fixed verifier, not a third Chrome.
    if _VERIFIER is None:
        raise RuntimeError('登录验证必须由固定隔离浏览器 fixture 提供')
    verified = _VERIFIER.login_as(username, password)
    _VERIFIER._verified_identity = hashlib.sha256((username+'\0'+password).encode()).hexdigest() if verified else None
    return verified


def _ensure_original_password(
    personal_profile, account_key, username, original_password
):
    candidate = _candidate_from_state(account_key, original_password)
    if not _recovery_file(account_key).exists() and personal_profile.has_verified_login(username,original_password):
        allure.attach('当前隔离会话已通过原密码真实登录；复用前置身份，新密码验证仍重新登录。','账号前置证据',allure.attachment_type.TEXT)
        return True
    if candidate and personal_profile.login_as(username, candidate):
        result = personal_profile.change_password(candidate, original_password)
        _attach_result(f"{account_key}中断恢复结果", result)
        restored = result["saved"] and _verify_credentials_in_fresh_browser(
            username, original_password
        )
        if restored:
            _clear_recovery_state(account_key)
        return restored
    if _login_known_password(personal_profile, username, original_password):
        _clear_recovery_state(account_key)
        return True
    return False


def _restore_password(
    personal_profile,
    account_key,
    username,
    original_password,
    candidate,
    candidate_is_active,
):
    # A successful login in the verifier can invalidate the original browser's
    # session. Restore only after authenticating this browser with the password
    # known to be active, before trying the now-obsolete original password.
    identity = hashlib.sha256((username+'\0'+candidate).encode()).hexdigest()
    already_verified = personal_profile.has_verified_login(username,candidate)
    if candidate_is_active and (already_verified or personal_profile.login_as(username, candidate)):
        result = personal_profile.change_password(candidate, original_password)
        _attach_result(f"{account_key}恢复原密码结果", result)
        if result["saved"] and _verify_credentials_in_fresh_browser(
            username, original_password
        ):
            _clear_recovery_state(account_key)
            return True
    if _login_known_password(personal_profile, username, original_password):
        _clear_recovery_state(account_key)
        return True
    if candidate and personal_profile.login_as(username, candidate):
        result = personal_profile.change_password(candidate, original_password)
        _attach_result(f"{account_key}兜底恢复原密码结果", result)
        if result["saved"] and _verify_credentials_in_fresh_browser(
            username, original_password
        ):
            _clear_recovery_state(account_key)
            return True
    return False


def _run_password_round_trip(
    personal_profile,
    user,
    account_key,
    username,
    original_password,
    section,
    case_id,
):
    __tracebackhide__ = True  # Keep password arguments out of failure traces.
    case = PASSWORD_DATA[section][case_id]
    new_password = case["password"]
    candidate_is_active = False
    allure.dynamic.parameter("账号类型", "admin" if account_key == "admin" else "非admin")
    allure.dynamic.parameter("密码场景", case["scenario"])
    allure.dynamic.parameter("密码长度", len(new_password))
    if case.get("symbol"):
        allure.dynamic.parameter("特殊符号", case["symbol"])
    assert new_password != original_password
    prepared = _ensure_original_password(personal_profile, account_key, username, original_password)
    if account_key == "admin" and not prepared:
        pytest.exit("管理员有效密码无法确认，停止后续改密，避免账户锁定。", returncode=1)
    assert prepared is True
    _write_recovery_state(account_key, section, case_id)
    try:
        with allure.step("通过修改资料设置临时密码"):
            result = personal_profile.change_password(
                original_password, new_password
            )
            _attach_result("修改密码结果", result, new_password)
            assert result["saved"] is True, result
            candidate_is_active = True
        with allure.step("使用隔离Chrome验证新密码登录"):
            login_verified = _verify_credentials_in_fresh_browser(
                username, new_password
            )
            allure.attach(
                json.dumps(
                    {
                        "新密码登录成功": login_verified,
                        "登录失败原因": personal_profile.last_login_error,
                    },
                    ensure_ascii=False,
                ),
                "新密码登录验证结果",
                allure.attachment_type.JSON,
            )
            assert login_verified is True
    finally:
        with allure.step("恢复原密码并验证登录"):
            restored = _restore_password(
                    personal_profile,
                    account_key,
                    username,
                    original_password,
                    new_password,
                    candidate_is_active,
                )
            allure.attach(
                json.dumps({"原密码恢复成功": restored}, ensure_ascii=False),
                "密码恢复状态",
                allure.attachment_type.JSON,
            )
            if account_key == "admin" and not restored:
                pytest.exit(
                    "管理员原密码恢复失败：已停止后续用例；保留中断恢复状态。",
                    returncode=1,
                )
            assert restored is True


@pytest.mark.parametrize("case_id", PASSWORD_DATA["normal_default"].keys())
def test_normal_user_password_special_symbol(personal_profile, user, case_id):
    _run_password_round_trip(
        personal_profile,
        user,
        "normal",
        NORMAL_USERNAME,
        NORMAL_PASSWORD,
        "normal_default",
        case_id,
    )


@pytest.mark.extended
@pytest.mark.parametrize(
    "case_id", PASSWORD_DATA["normal_valid_extended"].keys()
)
def test_normal_user_password_valid_equivalence(personal_profile, user, case_id):
    _run_password_round_trip(
        personal_profile,
        user,
        "normal",
        NORMAL_USERNAME,
        NORMAL_PASSWORD,
        "normal_valid_extended",
        case_id,
    )


@pytest.mark.extended
@pytest.mark.parametrize("case_id", PASSWORD_DATA["invalid"].keys())
def test_normal_user_password_invalid_matrix(personal_profile, user, case_id):
    case = PASSWORD_DATA["invalid"][case_id]
    old_password, new_password, confirm_password = _invalid_values(
        case, NORMAL_PASSWORD
    )
    candidate_is_active = False
    allure.dynamic.parameter("账号类型", "非admin")
    allure.dynamic.parameter("密码场景", case["scenario"])
    allure.dynamic.parameter("密码长度", len(new_password))
    assert _ensure_original_password(personal_profile, 'normal', NORMAL_USERNAME, NORMAL_PASSWORD) is True
    original_verified = False
    _write_recovery_state("normal", "invalid", case_id)
    try:
        result = personal_profile.change_password(
            old_password, new_password, confirm_password
        )
        candidate_is_active = bool(result.get('saved'))
        _attach_result("非法密码校验结果", result, new_password)
        assert result["saved"] is False, result
        if case.get("field"):
            actual = result["field_errors"].get(case["field"], "")
            # Supported frontends run required/format/matching validators in
            # different orders. Only accept registered messages on this exact
            # field, while still requiring the attempted save to be rejected.
            expected_messages = [case['message'], *case.get('alternate_messages', [])]
            assert any(message in actual for message in expected_messages), result
        else:
            assert case["message"] in result["message"], result
        personal_profile.close_profile()
        with allure.step("重新使用原密码登录，确认密码没有改变"):
            assert personal_profile.login_as(
                NORMAL_USERNAME, NORMAL_PASSWORD
            ) is True
            original_verified = True
            _clear_recovery_state('normal')
    finally:
        restored = original_verified or _restore_password(
            personal_profile, 'normal', NORMAL_USERNAME, NORMAL_PASSWORD,
            new_password, candidate_is_active,
        )
        allure.attach(
            json.dumps({"非admin原密码可登录": restored}, ensure_ascii=False),
            "非法场景账号恢复状态",
            allure.attachment_type.JSON,
        )
        assert restored is True


@pytest.mark.extended
@pytest.mark.parametrize("case_id", PASSWORD_DATA["admin_symbols"].keys())
def test_admin_password_special_symbol_round_trip(personal_profile, user, case_id):
    _run_password_round_trip(
        personal_profile,
        user,
        "admin",
        ConfigManager.USERNAME,
        ConfigManager.PASSWORD,
        "admin_symbols",
        case_id,
    )
