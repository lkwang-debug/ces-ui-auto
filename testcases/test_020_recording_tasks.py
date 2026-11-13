# -*- coding: utf-8 -*-
from common.runtime_artifacts import require_external_data
from conf.conf import ConfigManager
from testcases.feature_assertions import assert_page_feature


def test_recording_task_structure(feature_catalog):
    assert_page_feature(feature_catalog, "录制管理", "录制任务管理")


def test_preseeded_recording_task(recording_tasks):
    keyword = require_external_data(
        ConfigManager.RECORD_TASK_KEYWORD, "UIAUTO_RECORD_TASK_KEYWORD"
    )
    assert recording_tasks.open_tasks()
    assert recording_tasks.search_task(keyword)
    assert recording_tasks.target_task_is_visible()
    assert recording_tasks.clear_search()


def test_preseeded_recording_task_search_clear_and_download(recording_tasks):
    keyword = require_external_data(
        ConfigManager.RECORD_TASK_KEYWORD, "UIAUTO_RECORD_TASK_KEYWORD"
    )
    assert recording_tasks.open_tasks()
    assert recording_tasks.search_task(keyword)
    assert recording_tasks.target_task_is_visible()
    downloaded = recording_tasks.download_target_task(keyword)
    assert downloaded is not None and downloaded.stat().st_size > 0, recording_tasks.last_download_error
    assert recording_tasks.clear_search()
