from pages.Meeting_Page.MeetingRecordsPage import has_record_detail_content


def test_detail_headings_and_empty_states_cannot_prove_content():
    assert not has_record_detail_content({'text': '会议纪要 智能总结 文字转写 全局录制(0) 下载'})
    assert not has_record_detail_content({'summary_content': '暂无会议纪要'})
    assert not has_record_detail_content({'summary_content': '正在生成会议纪要'})


def test_summary_template_name_is_not_a_business_requirement():
    assert has_record_detail_content({'summary_content': '培训纪要\n培训主题：测试\n核心知识点：数据查询'})


def test_recording_requires_filename_duration_and_download_control():
    complete = {'name': 'meeting_10004_1.mp4', 'duration': '00:03:23', 'download_available': True}
    assert has_record_detail_content({'recordings': [complete]})
    for field in complete:
        incomplete = dict(complete)
        incomplete.pop(field)
        assert not has_record_detail_content({'recordings': [incomplete]})
