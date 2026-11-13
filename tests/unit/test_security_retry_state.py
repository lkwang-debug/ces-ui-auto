"""Exercise challenge retry boundaries without a browser or real credentials."""
from pages.Index_Page.index import LoginPage


class FakeSecurity:
    security_image = ('id', 'unit_image')
    last_login_error = ''

    class Driver:
        def get_screenshot_as_png(self):
            return b'unit diagnostic'

    driver = Driver()

    def __init__(self, mode):
        self.mode = mode
        self.clicks = 0
        self.version = 1
        self.polls = 0
        self.refreshes = 0
        self.message = '验证码错误' if mode == 'old_notice' else ''

    def is_click_security_visible(self, **kwargs):
        return True

    def wait_visible(self, *args, **kwargs):
        return self

    def get_attribute(self, name):
        return str(self.version)

    def recognize_click_security(self, **kwargs):
        return {}

    def click_security_solution(self, solution):
        self.clicks += 1
        if self.mode == 'retry' and self.clicks == 1:
            self.message = '验证码错误'
            self.version += 1
        if self.mode == 'credential':
            self.message = '用户名或密码错误'
            self.version += 1

    def _authenticated_route_and_shell(self):
        return (self.mode == 'retry' and self.clicks >= 2) or (
            self.mode == 'old_notice' and self.polls >= 2
        )

    def is_logged_in(self, **kwargs):
        return self._authenticated_route_and_shell()

    def get_login_error_msg(self):
        return self.message

    def _click_security_image_changed(self, before):
        return str(self.version) != before

    def refresh_click_security(self):
        self.refreshes += 1
        self.version += 1
        return True

    def wait_until(self, condition, **kwargs):
        for _ in range(3):
            self.polls += 1
            value = condition()
            if value:
                return value
        return False


def test_captcha_rejection_retries_only_challenge_and_can_succeed():
    page = FakeSecurity('retry')
    assert LoginPage.solve_click_security(page, max_attempts=2)
    assert page.clicks == 2


def test_credential_error_stops_even_when_image_changes():
    page = FakeSecurity('credential')
    assert not LoginPage.solve_click_security(page, max_attempts=2)
    assert page.clicks == 1
    assert page.refreshes == 0


def test_old_captcha_toast_cannot_abort_a_new_successful_attempt():
    page = FakeSecurity('old_notice')
    assert LoginPage.solve_click_security(page, max_attempts=2)
    assert page.clicks == 1


def test_unknown_submission_result_is_not_resubmitted():
    page = FakeSecurity('timeout')
    assert not LoginPage.solve_click_security(page, max_attempts=2)
    assert page.clicks == 1
