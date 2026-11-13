# -*- coding:utf-8 -*-
import time
import pytest

pytestmark = pytest.mark.requires_capability("call")


MISSING_USER_KEYWORD = f"call_user_missing_{int(time.time())}"


def test_enter_call(call):
    assert call.common_enter_call() is True


def test_find_author_user_accurately(call):
    username = call.get_first_authorized_username()
    assert username
    assert call.search_authorized_user_exact(username) is True


def test_find_author_user_vaguely(call):
    username = call.get_first_authorized_username()
    assert username
    keyword = username[:2] if len(username) >= 2 else username
    assert call.search_authorized_user_vague(keyword, username) is True


def test_find_author_failed(call):
    assert call.search_authorized_user_failed(MISSING_USER_KEYWORD) is True


def test_clear_authorized_user_search(call):
    username = call.get_first_authorized_username()
    assert username
    assert call.search_authorized_user_exact(username) is True
    assert call.clear_search_content() is True
    assert call.get_authorized_usernames()


def test_move_author_user_round_trip(call):
    username = call.get_first_authorized_username()
    assert username
    assert call.move_authorized_user_round_trip(username, result="操作成功") is True
