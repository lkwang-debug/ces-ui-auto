# -*- coding:utf-8 -*-
import allure
import pytest

from common.base_analyze import analyze_data


def _build_target_settings(original, params, resolutions):
    # Choose a value actually offered by the licensed UI in this environment.
    # Persistence remains strict, including when the backend normalizes it.
    assert resolutions, "当前授权未提供录制分辨率选项"
    resolution = next(
        (value for value in resolutions if value != original['resolution']),
        original['resolution'],
    )
    display_mode = (
        "等比裁剪显示" if original["display_mode"] != "等比裁剪显示" else "等比完整显示"
    )
    # Video resolution/display settings are normalized by the backend when
    # audio-only recording is selected. Validate video fields and recording
    # mode in two persisted phases instead of asserting an invalid combination.
    record_mode = original["record_mode"]

    slice_duration = str(params["slice_duration"])
    no_stream_timeout = str(params["without_stream_over_record_time"])
    if slice_duration == str(original["slice_duration"]):
        slice_duration = "45" if slice_duration != "45" else "60"
    if no_stream_timeout == str(original["without_stream_over_record_time"]):
        no_stream_timeout = "30" if no_stream_timeout != "30" else "60"

    return {
        "slice_duration": slice_duration,
        "without_stream_over_record_time": no_stream_timeout,
        "resolution": resolution,
        "display_mode": display_mode,
        "record_mode": record_mode,
    }


def test_enter_global_record(global_record):
    assert global_record.common_enter_global_record() is True


@pytest.mark.parametrize("params", analyze_data("set_record_data.json"))
def test_modify_global_record_round_trip(global_record, params):
    original = global_record.get_current_settings()
    target = _build_target_settings(original, params, global_record.available_resolution_options())
    allure.attach(str({'原配置': original, '目标配置': target}), '录制配置往返输入', allure.attachment_type.TEXT)

    try:
        assert (
            global_record.set_basic_settings(
                slice_duration=target["slice_duration"],
                without_stream_over_record_time=target["without_stream_over_record_time"],
                resolution=target["resolution"],
                display_mode=target["display_mode"],
                record_mode=target["record_mode"],
            )
            is True
        )
        assert global_record.save_changes("设置成功") is True
        assert global_record.refresh_and_wait() is True
        assert global_record.settings_match(target) is True
        alternate_mode = (
            "仅录音频" if original["record_mode"] != "仅录音频" else "完整录制"
        )
        assert global_record.set_basic_settings(
            slice_duration=target["slice_duration"],
            without_stream_over_record_time=target["without_stream_over_record_time"],
            resolution=target["resolution"],
            display_mode=target["display_mode"],
            record_mode=alternate_mode,
        ) is True
        assert global_record.save_changes("设置成功") is True
        assert global_record.refresh_and_wait() is True
        assert global_record.get_current_settings()["record_mode"] == alternate_mode
    finally:
        restored = global_record.restore_basic_settings(original)
        allure.attach(str({'原配置恢复成功': restored, '原配置': original}),
                      '录制配置清理结果', allure.attachment_type.TEXT)
        assert restored is True, '录制原配置恢复或刷新持久化验证失败'


@pytest.mark.requires_profile("4.39.8")
def test_recording_service_new_fields_and_switch_restore(global_record):
    snapshot = global_record.modern_settings_snapshot()
    allure.attach(str(snapshot), "录制服务设置新版字段快照", allure.attachment_type.TEXT)
    for label in (
        "入会自动录制", "录制存储阈值设置", "定时清理",
        "录制视频播放水印", "文字水印", "时间水印", "图片水印",
    ):
        assert label in snapshot["text"]
    assert snapshot["numbers"][0]["min"] == "30" and snapshot["numbers"][0]["max"] == "120"
    assert snapshot["numbers"][1]["min"] == "1" and snapshot["numbers"][1]["max"] == "999"

    label = "录制视频播放水印"
    original = global_record.get_switch_state(label)
    assert original is not None
    try:
        assert global_record.set_switch_state(label, not original) is True
        assert global_record.save_changes("设置成功") is True
        assert global_record.refresh_and_wait() is True
        assert global_record.get_switch_state(label) is (not original)
    finally:
        assert global_record.set_switch_state(label, original) is True
        assert global_record.save_changes("设置成功") is True
        assert global_record.refresh_and_wait() is True
        assert global_record.get_switch_state(label) is original


@pytest.mark.requires_profile("4.39.8")
@pytest.mark.extended
def test_recording_service_invalid_slice_duration_not_persisted(global_record):
    original = global_record.get_current_settings()
    try:
        assert global_record.set_number_value(0, "29") is True
        saved = global_record.save_changes("设置成功", timeout=3)
        messages = global_record.visible_validation_messages()
        allure.attach(str({"saved": saved, "messages": messages}), "切片时长越界结果", allure.attachment_type.TEXT)
        assert global_record.refresh_and_wait() is True
        assert global_record.get_current_settings()["slice_duration"] != "29"
    finally:
        assert global_record.set_basic_settings(
            slice_duration=original["slice_duration"],
            without_stream_over_record_time=original["without_stream_over_record_time"],
            resolution=original["resolution"],
            display_mode=original["display_mode"],
            record_mode=original["record_mode"],
        ) is True
        assert global_record.save_changes("设置成功") is True
        assert global_record.refresh_and_wait() is True
        assert global_record.settings_match(
            {
                "slice_duration": original["slice_duration"],
                "without_stream_over_record_time": original["without_stream_over_record_time"],
                "resolution": original["resolution"],
                "display_mode": original["display_mode"],
                "record_mode": original["record_mode"],
            }
        ) is True
