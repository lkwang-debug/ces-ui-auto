from testcases import test_030_personal_profile as cases
from pages.Index_Page.index import LoginPage


def test_new_password_proof_always_performs_a_real_login_even_if_identity_is_cached(monkeypatch):
    class Verifier:
        calls=0
        _verified_identity='already-authenticated'
        def login_as(self,username,password):self.calls+=1;return True
    verifier=Verifier()
    monkeypatch.setattr(cases,'_VERIFIER',verifier)
    assert cases._verify_credentials_in_fresh_browser('unit-user','synthetic-password')
    assert cases._verify_credentials_in_fresh_browser('unit-user','synthetic-password')
    assert verifier.calls==2


def test_known_click_challenge_does_not_wait_for_an_absent_legacy_captcha():
    class Driver:
        def execute_script(self,*args):return False
    class Page:
        driver=Driver()
        confirmed=False
        def login_with(self,*args):pass
        def wait_until(self,condition,**kwargs):return condition()
        def _authenticated_route_and_shell(self):return False
        def is_click_security_visible(self,timeout):assert timeout==0;return True
        def is_captcha_visible(self,timeout):raise AssertionError('不应再次等待旧验证码')
        def solve_click_security(self):return True
        def _confirm_login_identity(self,username):self.confirmed=True;return username=='unit'
    page=Page()
    assert LoginPage.login_with_optional_captcha(page,'unit','synthetic') is True
    assert page.confirmed


def test_case_insensitive_login_submits_changed_case_and_checks_canonical_identity():
    class Driver:
        def execute_script(self,*args):return False
    class Page:
        driver=Driver()
        submitted=None
        checked=None
        def login_with(self,username,password):self.submitted=username
        def wait_until(self,condition,**kwargs):return condition()
        def _authenticated_route_and_shell(self):return True
        def _confirm_login_identity(self,username):self.checked=username;return username=='unit_user'
    page=Page()
    assert LoginPage.login_with_optional_captcha(page,'UNIT_USER','synthetic',expected_username='unit_user')
    assert page.submitted=='UNIT_USER'
    assert page.checked=='unit_user'
