# -*- coding: utf-8 -*-
"""Offline recognition for the 4.39.8+ ordered Chinese click challenge."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from io import BytesIO
from typing import Iterable

import ddddocr
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance


@dataclass(frozen=True)
class ClickCandidate:
    text: str
    confidence: float
    box: tuple[int, int, int, int]
    center: tuple[float, float]
    variant: str


@dataclass(frozen=True)
class ClickSolution:
    targets: tuple[str, ...]
    candidates: tuple[ClickCandidate, ...]
    selected: tuple[ClickCandidate, ...]
    image_size: tuple[int, int]

    def details(self):
        return {
            "targets": list(self.targets),
            "image_size": list(self.image_size),
            "selected": [asdict(item) for item in self.selected],
            "candidates": [asdict(item) for item in self.candidates],
        }


class ClickCaptchaRecognizer:
    """Detect characters, classify each crop and map targets to unique boxes."""

    def __init__(self):
        self._detector = None
        self._classifier = None

    def _engines(self):
        if self._detector is None:
            self._detector = ddddocr.DdddOcr(det=True, ocr=False, show_ad=False)
        if self._classifier is None:
            self._classifier = ddddocr.DdddOcr(beta=True, show_ad=False)
        return self._detector, self._classifier

    @staticmethod
    def parse_targets(prompt: str) -> tuple[str, ...]:
        value = (prompt or "").replace("请依次点击", "").replace("：", "")
        return tuple(char for char in value if "\u4e00" <= char <= "\u9fff")

    @staticmethod
    def _crop_variants(image: Image.Image, box: Iterable[int], extended=False):
        x1, y1, x2, y2 = [int(value) for value in box]
        paddings = (0, 12) if extended else (2, 5, 8)
        contrasts = (1.0, 1.5, 1.8, 2.2) if extended else (1.0, 1.8)
        for padding in paddings:
            crop = image.crop(
                (
                    max(0, x1 - padding),
                    max(0, y1 - padding),
                    min(image.width, x2 + padding),
                    min(image.height, y2 + padding),
                )
            )
            crop = crop.resize((crop.width * 3, crop.height * 3))
            for contrast in contrasts:
                if contrast == 1.0:
                    yield f"padding={padding},raw", crop
                else:
                    yield (
                        f"padding={padding},contrast-{contrast}",
                        ImageEnhance.Contrast(crop).enhance(contrast),
                    )

    @staticmethod
    def _png(image: Image.Image) -> bytes:
        output = BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()

    def recognize(self, image_bytes: bytes, prompt: str, min_score: float, min_margin: float):
        targets = self.parse_targets(prompt)
        if not targets:
            raise ValueError("安全验证未提供需要点击的中文字符")

        detector, classifier = self._engines()
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        boxes = [tuple(int(value) for value in box) for box in (detector.detection(image_bytes) or [])]
        best_by_box_and_text = {}
        def collect(box_collection, extended):
            for box in box_collection:
                for variant_name, crop in self._crop_variants(image, box, extended=extended):
                    result = classifier.classification(self._png(crop), probability=True)
                    text = (result.get("text") or "").strip()
                    if len(text) != 1:
                        continue
                    confidence = float(result.get("confidence") or 0.0)
                    key = (box, text)
                    candidate = ClickCandidate(
                        text=text,
                        confidence=confidence,
                        box=box,
                        center=((box[0] + box[2]) / 2, (box[1] + box[3]) / 2),
                        variant=variant_name,
                    )
                    current = best_by_box_and_text.get(key)
                    if current is None or candidate.confidence > current.confidence:
                        best_by_box_and_text[key] = candidate

        collect(boxes, extended=False)
        try:
            return self._build_solution(
                targets, tuple(best_by_box_and_text.values()), image.size,
                min_score, min_margin,
            )
        except ValueError:
            collect(boxes, extended=True)
            try:
                return self._build_solution(
                    targets, tuple(best_by_box_and_text.values()), image.size,
                    min_score, min_margin,
                )
            except ValueError:
                fallback_boxes = self._fallback_boxes(image_bytes, image.size, boxes)
                collect(fallback_boxes, extended=False)
                collect(fallback_boxes, extended=True)
                return self._build_solution(
                    targets, tuple(best_by_box_and_text.values()), image.size,
                    min_score, min_margin,
                )

    @staticmethod
    def _fallback_boxes(image_bytes, image_size, known_boxes):
        """Generate local character windows when the text detector misses split strokes."""
        array = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(array, cv2.IMREAD_GRAYSCALE)
        if image is None:
            return []
        mask = (image < 165).astype(np.uint8) * 255
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        width, height = image_size
        centers = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w * h < 15 or w < 3 or h < 5 or w > 45 or h > 45:
                continue
            centers.append((x + w / 2, y + h / 2))

        candidates = []
        for center_x, center_y in centers:
            x1 = max(0, int(round(center_x - 20)))
            y1 = max(0, int(round(center_y - 20)))
            x2 = min(width, x1 + 40)
            y2 = min(height, y1 + 40)
            x1 = max(0, x2 - 40)
            y1 = max(0, y2 - 40)
            box = (x1, y1, x2, y2)
            box_center = ((x1 + x2) / 2, (y1 + y2) / 2)
            if any(
                abs(box_center[0] - (existing[0] + existing[2]) / 2) < 7
                and abs(box_center[1] - (existing[1] + existing[3]) / 2) < 7
                for existing in [*known_boxes, *candidates]
            ):
                continue
            candidates.append(box)
        return candidates

    @staticmethod
    def _build_solution(targets, candidates, image_size, min_score, min_margin):
        selected = []
        used_boxes = set()
        for target in targets:
            matches = sorted(
                (item for item in candidates if item.text == target and item.box not in used_boxes),
                key=lambda item: item.confidence,
                reverse=True,
            )
            unique_matches = []
            for item in matches:
                if any(
                    abs(item.center[0] - existing.center[0]) <= 20
                    and abs(item.center[1] - existing.center[1]) <= 20
                    for existing in unique_matches
                ):
                    continue
                unique_matches.append(item)
            matches = unique_matches
            if not matches or matches[0].confidence < min_score:
                raise ValueError(f"未可靠识别目标字符：{target}")
            if len(matches) > 1 and matches[0].confidence - matches[1].confidence < min_margin:
                raise ValueError(f"目标字符存在位置歧义：{target}")
            selected.append(matches[0])
            used_boxes.add(matches[0].box)

        return ClickSolution(
            targets=targets,
            candidates=candidates,
            selected=tuple(selected),
            image_size=image_size,
        )

    @staticmethod
    def annotate(image_bytes: bytes, solution: ClickSolution) -> bytes:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        draw = ImageDraw.Draw(image)
        selected_boxes = {item.box: index for index, item in enumerate(solution.selected, 1)}
        for item in solution.candidates:
            color = "#d62728" if item.box in selected_boxes else "#777777"
            draw.rectangle(item.box, outline=color, width=2)
            if item.box in selected_boxes:
                index = selected_boxes[item.box]
                x1, y1, _, _ = item.box
                draw.ellipse((x1 - 6, y1 - 6, x1 + 8, y1 + 8), fill="#d62728")
                draw.text((x1 - 2, y1 - 5), str(index), fill="white")
        return ClickCaptchaRecognizer._png(image)


click_captcha_recognizer = ClickCaptchaRecognizer()
