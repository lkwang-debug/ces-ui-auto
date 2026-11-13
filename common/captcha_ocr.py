# -*- coding: utf-8 -*-
import re

import ddddocr


class CaptchaRecognizer:
    """Offline captcha recognizer with one lazily-created OCR model."""

    def __init__(self):
        self._engine = None

    def recognize(self, image_bytes):
        if self._engine is None:
            self._engine = ddddocr.DdddOcr(show_ad=False)
        value = self._engine.classification(image_bytes) or ""
        return re.sub(r"[^0-9A-Za-z]", "", value).strip()


captcha_recognizer = CaptchaRecognizer()
