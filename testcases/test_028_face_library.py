# -*- coding: utf-8 -*-
import time
from pathlib import Path

import allure
import pytest

from conf.conf import ConfigManager


pytestmark = pytest.mark.requires_capability("face_library")
IMAGE_DIR = Path(ConfigManager.FACE_IMAGE_DIR)
VALID_IMAGES = (
    IMAGE_DIR / "保存成功提示操作成功.png",
    IMAGE_DIR / "保存成功提示操作成功_2.png",
)
ABNORMAL_IMAGES = (
    IMAGE_DIR / "提示图片大小建议小于5MB.png",
    IMAGE_DIR / "提示图片中没有检测到人脸.png",
    IMAGE_DIR / "提示人脸区域过小.jpg",
    IMAGE_DIR / "提示人脸过于倾斜或者侧脸角度过大.jpg",
    IMAGE_DIR / "图片格式不对提示参数错误.bmp",
)


def _images_exist(paths):
    missing = [str(path) for path in paths if not path.is_file()]
    assert not missing, f"缺少人脸测试图片：{missing}"


def test_face_library_page_structure(face_library):
    page = face_library.open_faces()
    assert page is not None
    for expected in ("人脸照片", "姓名", "职位", "录入时间", "新增", "删除"):
        assert expected in page["text"]


def test_face_valid_lifecycle_and_batch_cleanup(face_library):
    _images_exist(VALID_IMAGES)
    suffix = str(time.time_ns())[-8:]
    first = f"uiauto_face_{suffix}_a"
    second = f"uiauto_face_{suffix}_b"
    modified = f"uiauto_face_{suffix}_m"
    try:
        assert face_library.create(first, "自动化测试", VALID_IMAGES[0]) is True, (
            face_library.last_create_evidence
        )
        assert face_library.search(first) is True
        modified_ok = face_library.modify(
            first, modified, "修改后职位", VALID_IMAGES[1]
        )
        allure.attach(
            str(face_library.last_modify_evidence),
            "人脸修改持久化证据",
            allure.attachment_type.TEXT,
        )
        assert modified_ok is True, face_library.last_modify_evidence
        assert face_library.exists(modified, refresh=True)
        assert face_library.create(second, "批量删除", VALID_IMAGES[0]) is True, (
            face_library.last_create_evidence
        )
        assert face_library.delete_batch([modified, second]) is True
        assert not face_library.exists(modified, refresh=True)
        assert not face_library.exists(second)
    finally:
        result = face_library.cleanup_records([first, modified, second])
        allure.attach(str(result), "人脸临时数据清理结果", allure.attachment_type.TEXT)
        assert result is True


@pytest.mark.extended
@pytest.mark.parametrize(
    "name,position,image,privacy",
    [
        ("", "职位", VALID_IMAGES[0], True),
        ("uiauto_face_empty_position", "", VALID_IMAGES[0], True),
        ("uiauto_face_no_image", "职位", None, True),
        ("uiauto_face_no_privacy", "职位", VALID_IMAGES[0], False),
    ],
    ids=["姓名为空", "职位为空", "照片为空", "未接受隐私协议"],
)
def test_face_required_and_privacy_validation(face_library, name, position, image, privacy):
    _images_exist([item for item in (image,) if item])
    rejected, messages = face_library.create_rejected(
        name, position, image, privacy, timeout=4
    )
    assert rejected is True
    if privacy:
        field = "姓名" if not name else "职位" if not position else "人脸照片"
        actual = face_library.last_field_errors.get(field, "")
        assert "不能为空" in actual, {"字段": field, "实际错误": actual, "消息": messages}
    else:
        assert face_library.last_privacy_checked is False


@pytest.mark.extended
@pytest.mark.parametrize("image", ABNORMAL_IMAGES, ids=[path.stem for path in ABNORMAL_IMAGES])
def test_face_abnormal_images_rejected(face_library, image):
    _images_exist([image])
    name = f"uiauto_face_bad_{str(time.time_ns())[-8:]}"
    rejected, messages = face_library.create_rejected(
        name, "异常图片", image, True, timeout=20
    )
    assert rejected is True
    assert messages, f"异常图片未返回可观察错误提示：{image.name}"
    assert face_library.exists(name) is False


@pytest.mark.extended
def test_face_name_and_position_length_boundaries(face_library):
    _images_exist([VALID_IMAGES[0]])
    prefix = f"uiauto_face_len_{time.time_ns()}_"
    name = prefix + "N" * (64 - len(prefix))
    try:
        created = face_library.create(name, "P" * 64, VALID_IMAGES[0])
        assert created is True, face_library.last_create_evidence
        assert face_library.exists(name, refresh=True)
    finally:
        face_library.close_modal()
        assert face_library._set_search(name) is True
        if face_library.exists(name):
            assert face_library.delete_batch([name]) is True
        assert face_library._set_search(name) is True
        assert not face_library.exists(name)

    long_prefix = f"uiauto_face_long_{time.time_ns()}_"
    long_name = long_prefix + "A" * (65 - len(long_prefix))
    rejected, messages = face_library.create_rejected(
        long_name, "职位", VALID_IMAGES[0], timeout=4
    )
    assert rejected is True
    assert messages

    position_name = f"uiauto_face_len_{str(time.time_ns())[-8:]}"
    rejected, messages = face_library.create_rejected(
        position_name, "职" * 65, VALID_IMAGES[0], timeout=4
    )
    assert rejected is True
    assert messages
    assert face_library.cleanup_records([long_name, position_name]) is True
