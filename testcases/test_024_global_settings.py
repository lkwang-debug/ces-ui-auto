# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import json

import allure
import pytest

from common.product_profile import detect_build_profile, feature_for_request
from conf.conf import ConfigManager
from pages.Index_Page.index import LoginPage
from pages.Meeting_Page.MeetingInfoPage import MeetingInfoPage
from pages.Server_Page.GlobalSettingsPage import GlobalSettingsPage
from testcases.feature_assertions import assert_page_feature


@pytest.fixture
def retained_email_data():
    data={'说明':'按此前测试要求保留邮件样本，不执行删除或恢复邮件配置','环境':ConfigManager.HST_URL,
        '用户已创建':False,'会议室已创建':False,'通知已保存':False,'邮件发送成功':False}
    yield data
    allure.attach(json.dumps(data,ensure_ascii=False,indent=2),'执行后保留的数据',allure.attachment_type.JSON)


def test_global_settings_structure(feature_catalog):
    profile = feature_for_request(
        "服务器管理", "全局设置", detect_build_profile(ConfigManager.HST_URL)
    )
    assert profile is not None
    assert feature_catalog._ensure_authenticated() is True
    assert feature_catalog.open_spa_route(profile["route"], timeout=5) is True
    def global_settings_content():
        return feature_catalog.driver.execute_script(
            """
            const specific=['分级管理','H.323','邮件发送服务','全局'];
            for (const main of [...document.querySelectorAll('main,.ant-layout-content')]) {
              if (main.offsetParent===null) continue;
              const text=(main.innerText||'').replace(/\s+/g,' ');
              const inputs=main.querySelectorAll('input,[role=switch]').length;
              const buttons=main.querySelectorAll('button').length;
              if (specific.some(marker=>text.includes(marker)) && inputs+buttons>=2)
                return {text,inputs,buttons};
            }
            return false;
            """
        )

    loaded = feature_catalog.wait_until(
        global_settings_content,
        timeout=6,
        poll_frequency=0.1,
    )
    if loaded is False:
        feature_catalog.driver.refresh()
        feature_catalog.wait_for_document_ready(timeout=5)
        loaded = feature_catalog.wait_until(
            global_settings_content,
            timeout=6,
            poll_frequency=0.1,
        )
    assert loaded is not False
    assert profile["route"] in feature_catalog.driver.current_url
    assert loaded["text"] and loaded["inputs"] + loaded["buttons"] >= 2


@pytest.mark.regression
def test_meeting_email_notification_end_to_end(driver, user,retained_email_data):
    """Configure SMTP and retain a real user/meeting after sending email."""
    assert ConfigManager.ADDRESSEE, "conf.py 的 ADDRESSEE 至少需要配置一个收件邮箱"
    recipient = str(ConfigManager.ADDRESSEE[0]).strip()
    assert "@" in recipient, f"收件邮箱格式无效：{recipient!r}"

    stamp = datetime.now().strftime("%m%d%H%M%S")
    username = f"mail_{stamp}"
    meeting_name = f"mail_meeting_{stamp}"
    subject = f"UI自动化邮件通知_{stamp}"
    start_time = ""
    retained_email_data.update(用户=username,电子邮箱=recipient,会议室=meeting_name,会议主题=subject)

    with allure.step("配置服务器管理中的邮件发送服务"):
        settings = GlobalSettingsPage(driver=driver)
        assert settings.configure_email_service(
            ConfigManager.EMAIL_INFO
        ) is True, settings.last_email_error

    with allure.step("新增填写收件邮箱的测试用户"):
        assert user.common_enter_user() is True
        assert user.add_user_with_email(
            username, "uipass12", recipient, "添加成功"
        ) is True
        retained_email_data['用户已创建']=True
        assert user.search_user(username) is True

    with allure.step("重新登录当前浏览器会话加载最新授权目录"):
        login = LoginPage(driver=driver)
        login.reset_login_state()
        assert login.login_with_optional_captcha(
            ConfigManager.USERNAME, ConfigManager.PASSWORD
        ) is True
        login.dismiss_intro_if_present(timeout=1)
        notification_page = MeetingInfoPage(driver=driver)

    with allure.step("新增会议室并将测试用户授权为管理员"):
        assert notification_page.common_enter_meeting_info() is True
        assert notification_page.add_meeting(meeting_name, "新增成功") is True
        retained_email_data['会议室已创建']=True
        assert notification_page.authorize_user_with_role(
            meeting_name, username, role="管理员", result="操作成功"
        ) is True, notification_page.last_authorization_error

    with allure.step("创建一分钟后的会议邮件通知"):
        def choose_start_time():
            value=(datetime.now()+timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')
            retained_email_data['开始时间']=value
            return value
        assert notification_page.send_email_notification(
            meeting_name=meeting_name,
            username=username,
            subject=subject,
            start_time=choose_start_time,
            result="操作成功",
        ) is True, notification_page.last_notification_error
        start_time=notification_page.last_notification_start_time
        retained_email_data['通知已保存']=True

    with allure.step("查看通知结果并确认邮件发送成功"):
        result_text = notification_page.wait_email_notification_success(
            meeting_name, timeout=90
        )
        assert "邮件全部发送成功" in result_text
        assert subject in result_text
        retained_email_data['邮件发送成功']=True
