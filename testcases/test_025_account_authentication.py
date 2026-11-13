# -*- coding: utf-8 -*-
from common.product_profile import detect_build_profile, feature_for_request
from conf.conf import ConfigManager


def test_account_authentication_structure(feature_catalog):
    profile = feature_for_request(
        "服务器管理", "帐号认证管理", detect_build_profile(ConfigManager.HST_URL)
    )
    assert profile is not None
    assert feature_catalog._ensure_authenticated() is True
    assert feature_catalog.open_spa_route(profile["route"], timeout=5) is True
    def authentication_content():
        return feature_catalog.driver.execute_script(
            """
            const text=(document.querySelector('main')?.innerText||'').replace(/\s+/g,' ');
            return text.includes('当前认证')
              && text.includes('AD域认证')
              && text.includes('FSMEETING认证') ? text : false;
            """
        )

    loaded = feature_catalog.wait_until(
        authentication_content,
        timeout=6,
        poll_frequency=0.1,
    )
    if loaded is False:
        if not feature_catalog.is_logged_in(timeout=0.5):
            feature_catalog.open_login_url()
            assert feature_catalog.login_with_optional_captcha(
                ConfigManager.USERNAME, ConfigManager.PASSWORD
            ) is True
            feature_catalog.dismiss_intro_if_present(timeout=1)
            assert feature_catalog.open_spa_route(profile["route"], timeout=5) is True
        else:
            feature_catalog.driver.refresh()
            feature_catalog.wait_for_document_ready(timeout=5)
        loaded = feature_catalog.wait_until(
            authentication_content, timeout=6, poll_frequency=0.1
        )
    assert loaded is not False
    page = feature_catalog.snapshot_main()
    assert profile["route"] in page["url"]
    assert all(text in page["text"] for text in ("当前认证", "AD域认证", "FSMEETING认证"))
    assert any("保存" in text.replace(" ", "") for text in page["buttons"])
