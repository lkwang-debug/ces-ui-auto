# -*- coding: utf-8 -*-
import time

import allure
import pytest

from common.base_analyze import analyze_data
from conf.conf import ConfigManager


pytestmark = [pytest.mark.regression, pytest.mark.security]
LOGIN_CASES = analyze_data("login_data.json")


@pytest.fixture(scope="module")
def login_test_account():
    return {
        "username": ConfigManager.LOGIN_TEST_USERNAME,
        "password": ConfigManager.LOGIN_TEST_PASSWORD,
    }


def _resolve(value, account):
    if value == "$VALID":
        return account["username"]
    if value == "$PASSWORD":
        return account["password"]
    if value == "$VALID_UPPER":
        return account["username"].upper()
    return value.replace("$VALID", account["username"])


def _assert_rejected(login, expect_message=True):
    time.sleep(0.8)
    assert login.is_logged_in(timeout=1) is False
    assert "login" in (login.driver.current_url or "").lower()
    message = login.wait_until(
        lambda: login.get_login_error_msg()
        or login.last_login_error
        or ("验证码已触发" if login.is_captcha_visible(timeout=0.1) else False),
        timeout=5,
        poll_frequency=0.2,
    )
    if message is False:
        message = ""
    if expect_message:
        assert message, "登录失败后页面没有展示校验或认证错误信息"
    return message


def _recover_account(login, account):
    login.reset_login_state()
    assert login.login_with_optional_captcha(
        account["username"], account["password"]
    ) is True
    login.reset_login_state()

@pytest.mark.parametrize("params", LOGIN_CASES, ids=lambda item: item["scenario"])
def test_login_credential_matrix(login, login_test_account, params):
    username = _resolve(params["username"], login_test_account)
    password = _resolve(params["password"], login_test_account)
    login.reset_login_state()

    if params["scenario"] == "username_case_changed":
        expected = login_test_account["username"]
        assert username != expected and username.casefold() == expected.casefold(), "大小写场景必须实际改变账号字母大小写"
        try:
            assert login.login_with_optional_captcha(username, password, expected_username=expected) is True
            actual = login.get_index_user_name_text()
            assert actual == expected, "变更大小写后必须登录到同一原始账号"
            allure.attach(f"输入账号：{username}\n实际账号：{actual}", "用户名不区分大小写登录结果", allure.attachment_type.TEXT)
        finally:
            login.reset_login_state()
        return

    if params["scenario"] == "valid":
        assert login.login_with_optional_captcha(username, password) is True
        actual = login.get_index_user_name_text()
        assert actual == login_test_account["username"]
        allure.attach(
            f"expected: {login_test_account['username']}\nactual: {actual}",
            "assertion_success",
            allure.attachment_type.TEXT,
        )
        login.reset_login_state()
        return

    if username and password:
        login.login_with_optional_captcha(username, password)
    else:
        login.login_with(username, password)
    _assert_rejected(login)
    if not username or not password:
        required = {field for field, value in (("用户名", username), ("密码", password)) if not value}
        errors = login.wait_until(
            lambda: current if required.issubset(current := login.login_field_errors()) else False,
            timeout=5,
            poll_frequency=0.1,
        )
        assert errors is not False, f"必填字段未出现对应提示: {sorted(required)}"
        assert login.is_click_security_visible(timeout=0.1) is False
    if username and password:
        _recover_account(login, login_test_account)


@pytest.mark.smoke
def test_admin_login_smoke(login):
    login.reset_login_state()
    assert login.login_with_optional_captcha(
        ConfigManager.USERNAME, ConfigManager.PASSWORD
    ) is True
    assert login.get_index_user_name_text() == ConfigManager.USERNAME
    login.reset_login_state()


@pytest.mark.requires_profile("legacy")
def test_captcha_required_after_three_wrong_passwords(login, login_test_account):
    _recover_account(login, login_test_account)
    for _ in range(3):
        started = login.login_with(login_test_account["username"], "WrongPass123!")
        response = login.wait_login_response(started)
        assert response is not False, "本次错误密码登录请求未完成，禁止读取上次提示继续提交"
        assert response['status'] > 0, "本次错误密码登录请求网络失败"
        assert login.wait_until(
            lambda: login.get_login_error_msg() or login.is_captcha_visible(timeout=0),
            timeout=8,
            poll_frequency=0.1,
        ) is not False, "错误密码请求未返回认证结果"

    ready = login.is_captcha_visible(timeout=12)
    allure.attach(str(login.captcha_diagnostics()), "三次错误密码后的验证码状态", allure.attachment_type.TEXT)
    assert ready is True, "三次错误密码后验证码图片未完成加载"

    login.login_with(login_test_account["username"], login_test_account["password"], "")
    empty_message = _assert_rejected(login)
    assert empty_message

    login.login_with(
        login_test_account["username"], login_test_account["password"], "WRONG"
    )
    wrong_message = _assert_rejected(login)
    assert wrong_message

    old_code = login.recognize_visible_captcha()
    assert old_code
    assert login.refresh_captcha() is True
    login.login_with(
        login_test_account["username"], login_test_account["password"], old_code
    )
    _assert_rejected(login)

    assert login.login_with_ocr(
        login_test_account["username"], login_test_account["password"]
    ) is True
    assert login.get_index_user_name_text() == login_test_account["username"]
    login.reset_login_state()


def _open_click_security(login):
    login.reset_login_state()
    login.login_with(ConfigManager.USERNAME, ConfigManager.PASSWORD)
    assert login.is_click_security_visible(timeout=5) is True


@pytest.mark.requires_profile("4.39.8")
def test_click_security_dialog_refresh_and_close(login):
    _open_click_security(login)
    prompt = login.get_click_security_prompt()
    solution = login.recognize_click_security_with_retry()
    assert len(solution.targets) >= 3
    assert len(solution.selected) == len(solution.targets)
    assert all(target in prompt for target in solution.targets)
    assert login.get_click_security_marker_count() == 0
    assert login.refresh_click_security() is True
    assert login.get_click_security_marker_count() == 0
    assert login.close_click_security() is True
    assert login.is_logged_in(timeout=0.5) is False


@pytest.mark.requires_profile("4.39.8")
def test_click_security_incomplete_click_does_not_submit(login):
    _open_click_security(login)
    solution = login.recognize_click_security_with_retry()
    click_count = len(solution.targets) - 1
    assert click_count > 0
    assert login.click_security_solution(solution, limit=click_count) is True
    assert login.get_click_security_marker_count() == click_count
    assert login.is_logged_in(timeout=1) is False
    assert login.is_click_security_visible(timeout=0.5) is True
    login.close_click_security()


@pytest.mark.requires_profile("4.39.8")
def test_click_security_wrong_order_is_rejected(login):
    _open_click_security(login)
    image = login.wait_visible(login.security_image, timeout=3)
    before = image.get_attribute("src")
    solution = login.recognize_click_security_with_retry()
    assert len(solution.targets) > 1
    assert login.click_security_solution(solution, reverse=True) is True
    rejected = login.wait_until(
        lambda: (
            login._click_security_image_changed(before)
            or bool(login.get_login_error_msg())
            or not login.is_click_security_visible(timeout=0.1)
        ),
        timeout=ConfigManager.SECURITY_VERIFY_WAIT_SECONDS,
        poll_frequency=0.2,
    )
    assert rejected is not False
    assert login.is_logged_in(timeout=0.5) is False
    login.reset_login_state()


@pytest.mark.extended
@pytest.mark.requires_profile("4.39.8")
def test_click_security_recognition_stability(login):
    _open_click_security(login)
    recognized = 0
    failures = []
    for index in range(1, 31):
        try:
            solution = login.recognize_click_security(attempt=index)
            if len(solution.selected) == len(solution.targets):
                recognized += 1
        except Exception as exc:
            failures.append(f"第{index}张：{exc}")
        if index < 30:
            assert login.refresh_click_security() is True
    allure.attach(
        f"识别成功：{recognized}/30\n" + "\n".join(failures),
        "30张安全验证识别统计",
        allure.attachment_type.TEXT,
    )
    assert recognized >= 29, f"单次识别成功率低于95%：{recognized}/30"
    login.close_click_security()


@pytest.mark.extended
@pytest.mark.requires_profile("4.39.8")
@pytest.mark.parametrize("window_size", [(1920, 1080), (1366, 768)], ids=["1920x1080", "1366x768"])
def test_click_security_coordinate_scaling(login, window_size):
    try:
        login.driver.set_window_size(*window_size)
        login.reset_login_state()
        assert login.login_with_optional_captcha(
            ConfigManager.USERNAME, ConfigManager.PASSWORD
        ) is True
        assert login.get_index_user_name_text() == ConfigManager.USERNAME
    finally:
        login.driver.set_window_size(1920, 1080)
        login.reset_login_state()


@pytest.mark.extended
@pytest.mark.requires_profile("4.39.8")
def test_click_security_three_consecutive_logins(login):
    for round_number in range(1, 4):
        login.reset_login_state()
        assert login.login_with_optional_captcha(
            ConfigManager.USERNAME, ConfigManager.PASSWORD
        ) is True, f"第{round_number}轮安全验证登录失败：{login.last_login_error}"
        assert login.get_index_user_name_text() == ConfigManager.USERNAME
    login.reset_login_state()
