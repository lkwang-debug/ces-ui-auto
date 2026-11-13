import ssl
from types import SimpleNamespace
from urllib.error import URLError
from urllib.request import Request

import pytest

import common.product_profile as profile
from conf.conf import ConfigManager


@pytest.fixture(autouse=True)
def isolated_profile(monkeypatch):
    detector = profile.detect_build_profile
    detector.cache_clear()
    monkeypatch.delenv('UIAUTO_PRODUCT_PROFILE', raising=False)
    monkeypatch.setattr(ConfigManager, 'PRODUCT_PROFILE', 'auto')
    monkeypatch.setattr(ConfigManager, 'HST_URL', 'https://ces.example:28443')
    monkeypatch.setattr(ConfigManager, 'HTTPS_VERIFY_CERTIFICATE', False)
    yield
    detector.cache_clear()


@pytest.mark.parametrize('scheme,markers,expected', [
    ('http', 'user-call background-permission-management', profile.LEGACY),
    ('https', '/ui/ai-model model-settings client-feature developer-ces', profile.MODERN),
])
def test_both_build_families_use_real_bundle_fingerprints(monkeypatch, scheme, markers, expected):
    seen = []
    def read(url):
        seen.append(url)
        return '<script src="/js/app.123.js"></script>' if len(seen) == 1 else markers
    monkeypatch.setattr(profile, '_read_url', read)
    assert profile.detect_build_profile(scheme+'://ces.example:28443') == expected
    assert seen[-1].endswith('/js/app.123.js')


def test_network_failure_is_explicit_and_not_cached(monkeypatch):
    def failed(url):
        raise URLError(ssl.SSLCertVerificationError('IP address mismatch'))
    monkeypatch.setattr(profile, '_read_url', failed)
    with pytest.raises(profile.ProfileDetectionError, match='IP address mismatch'):
        profile.detect_build_profile()
    assert profile.detect_build_profile.cache_info().currsize == 0
    monkeypatch.setattr(profile, '_read_url', lambda url: '<script src="/js/app.123.js"></script>'
                        if not url.endswith('.js') else 'user-call background-permission-management')
    assert profile.detect_build_profile() == profile.LEGACY


@pytest.mark.parametrize('html,bundle', [('<html>no app script</html>', ''),
    ('<script src="/js/app.123.js"></script>', 'unregistered future build')])
def test_missing_assets_or_unknown_build_cannot_silently_remove_tests(monkeypatch, html, bundle):
    monkeypatch.setattr(profile, '_read_url', lambda url: bundle if url.endswith('.js') else html)
    with pytest.raises(profile.ProfileDetectionError):
        profile.detect_build_profile()


def test_local_insecure_probe_is_scoped_and_does_not_change_global_ssl(monkeypatch):
    captured = []
    default_factory = ssl._create_default_https_context
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'frontend'
    class Opener:
        def open(self, request, timeout): return Response()
    def opener(*handlers):
        captured.extend(handlers)
        return Opener()
    monkeypatch.setattr(profile, 'build_opener', opener)
    calls = []
    monkeypatch.setattr(profile, 'urlopen', lambda request, **kw: calls.append(request.full_url) or Response())
    assert profile._read_url('https://ces.example:28443/js/app.js') == 'frontend'
    assert captured[0]._context.verify_mode == ssl.CERT_NONE
    assert not captured[0]._context.check_hostname
    profile._read_url('https://other.example/js/app.js')
    profile._read_url('https://ces.example:9443/js/app.js')
    profile._read_url('http://ces.example/js/app.js')
    assert len(calls) == 3
    assert ssl._create_default_https_context is default_factory


def test_strict_policy_preserves_certificate_errors(monkeypatch):
    monkeypatch.setattr(ConfigManager, 'HTTPS_VERIFY_CERTIFICATE', True)
    monkeypatch.setattr(profile, 'build_opener', lambda *args: pytest.fail('strict mode bypassed SSL'))
    def failed(*args, **kwargs): raise ssl.SSLCertVerificationError('untrusted')
    monkeypatch.setattr(profile, 'urlopen', failed)
    with pytest.raises(ssl.SSLCertVerificationError):
        profile._read_url(ConfigManager.HST_URL)


def test_insecure_probe_redirect_cannot_extend_exception_to_other_origins():
    redirect = profile._SameOriginRedirect()
    request = Request('https://ces.example:28443/')
    assert redirect.redirect_request(request, None, 302, '', {}, 'https://ces.example:28443/login')
    with pytest.raises(profile.ProfileDetectionError):
        redirect.redirect_request(request, None, 302, '', {}, 'https://other.example/')


def test_forced_profile_reads_conf_without_fetching(monkeypatch):
    monkeypatch.setattr(ConfigManager, 'PRODUCT_PROFILE', profile.MODERN)
    monkeypatch.setattr(profile, '_read_url', lambda url: pytest.fail('forced profile fetched network'))
    assert profile.detect_build_profile() == profile.MODERN


def test_runner_stops_before_pytest_and_records_preflight_error(monkeypatch, tmp_path):
    import run
    monkeypatch.setattr(run, 'PROJECT_ROOT', tmp_path)
    monkeypatch.setattr(run, 'find_allure', lambda: 'allure')
    import common.stability
    monkeypatch.setattr(common.stability, 'source_manifest', lambda root: {'code_sha256':'unit'})
    def failed(*args): raise profile.ProfileDetectionError('证书验证失败')
    monkeypatch.setattr(profile, 'detect_build_profile', failed)
    monkeypatch.setattr(run.subprocess, 'Popen', lambda *a, **kw: pytest.fail('pytest started after preflight failure'))
    args = SimpleNamespace(full=True, headless=True, shuffle_seed=None, pytest_args=[])
    assert run._execute(args) == 2
    import json
    failures = list((tmp_path/'reports/runs').glob('*/preflight-error.json'))
    assert len(failures) == 1
    assert json.loads(failures[0].read_text(encoding='utf-8'))['tests_started'] is False


def test_menu_recovery_keeps_spa_shell_and_does_not_hide_expired_login():
    from pages.MenuInventoryPage import MenuInventoryPage
    class Driver:
        current_url = 'https://ces.example/#/ui/organization'
        def refresh(self): pytest.fail('recovery reloaded authenticated shell')
        def get(self, url): pytest.fail('recovery discarded authenticated shell')
    class Item:
        def is_displayed(self): return True
        def click(self): calls.append('real menu click')
    class Page:
        driver = Driver()
        inventory_route = '#/ui/users'
        def open_spa_route(self, route, **kwargs): calls.append(route); return True
        def _find_menu_item_by_group(self, *args): return Item()
    calls = []
    page = Page()
    assert MenuInventoryPage._recover_menu_content(page, '通讯录', '组织管理', '#/ui/organization')
    assert calls == ['#/ui/users', 'real menu click', '#/ui/organization']
    page.driver.current_url = 'https://ces.example/#/ui/login'
    calls.clear()
    assert not MenuInventoryPage._recover_menu_content(page, '通讯录', '组织管理', '#/ui/organization')
    assert calls == []
