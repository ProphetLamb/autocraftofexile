from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(slots=True, frozen=True)
class Coordinates:
    x: int
    y: int


@dataclass(slots=True, frozen=True)
class SpriteDetection:
    left: int
    top: int
    right: int
    bottom: int
    click: Coordinates
    confidence: float

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


@dataclass(slots=True, frozen=True)
class _Fragment:
    left: int
    top: int
    right: int
    bottom: int
    area: int


class StashSpriteDetector:
    """Detect item sprites directly in image space.

    The detector does not use stash-cell occupancy or any fixture layout. It:
    1. removes the two dominant stash backgrounds (dark empty and dark red);
    2. extracts visible sprite fragments;
    3. joins nearby fragments belonging to one continuous sprite;
    4. rejects borders, grid artifacts, and tiny isolated highlights.
    """

    def __init__(
        self,
        *,
        minimum_fragment_area: int = 10,
        minimum_sprite_area: int = 45,
        fragment_gap: int = 2,
        maximum_sprite_width: int = 68,
        maximum_sprite_height: int = 100,
    ) -> None:
        self.minimum_fragment_area = minimum_fragment_area
        self.minimum_sprite_area = minimum_sprite_area
        self.fragment_gap = fragment_gap
        self.maximum_sprite_width = maximum_sprite_width
        self.maximum_sprite_height = maximum_sprite_height

    def detect(self, image: np.ndarray) -> tuple[SpriteDetection, ...]:
        bounds = self._detect_stash_bounds(image)
        mask = self._foreground_mask(image, bounds)
        fragments = self._extract_fragments(mask, bounds)
        groups = self._merge_fragments(fragments)
        detections = self._groups_to_detections(groups, mask, bounds)
        return tuple(sorted(detections, key=lambda item: (item.top, item.left)))

    @staticmethod
    def _detect_stash_bounds(image: np.ndarray) -> tuple[int, int, int, int]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
        x_gradient = np.mean(np.abs(np.diff(gray, axis=1)), axis=0)
        y_gradient = np.mean(np.abs(np.diff(gray, axis=0)), axis=1)
        height, width = gray.shape
        margin_x = max(12, width // 12)
        margin_y = max(12, height // 12)
        return (
            int(np.argmax(x_gradient[:margin_x])) + 1,
            int(np.argmax(y_gradient[:margin_y])) + 1,
            width - int(np.argmax(x_gradient[-margin_x:][::-1])) - 1,
            height - int(np.argmax(y_gradient[-margin_y:][::-1])) - 1,
        )

    @staticmethod
    def _foreground_mask(
        image: np.ndarray,
        bounds: tuple[int, int, int, int],
    ) -> np.ndarray:
        blue, green, red = cv2.split(image.astype(np.int16))
        maximum = np.maximum(np.maximum(blue, green), red)
        minimum = np.minimum(np.minimum(blue, green), red)
        chroma = maximum - minimum

        # Item artwork is brighter or more chromatic than both stash
        # backgrounds. The second clause retains pale metallic artwork.
        colorful = (maximum >= 46) & (chroma >= 11)
        metallic = (maximum >= 76) & ((maximum - minimum) >= 5)
        red_background = (
            (red >= 24) & (red < 92) & (red >= green * 1.45) & (red >= blue * 1.45)
        )
        mask = ((colorful | metallic) & ~red_background).astype(np.uint8) * 255

        left, top, right, bottom = bounds
        outside = np.ones(mask.shape, dtype=bool)
        outside[top:bottom, left:right] = False
        mask[outside] = 0

        # Remove the border and regular grid lines before morphology so they
        # cannot connect unrelated sprites.
        mask[max(0, top - 2) : top + 3, :] = 0
        mask[max(0, bottom - 2) : bottom + 3, :] = 0
        mask[:, max(0, left - 2) : left + 3] = 0
        mask[:, max(0, right - 2) : right + 3] = 0

        cell_width = (right - left) / 24
        cell_height = (bottom - top) / 24
        for index in range(1, 24):
            x = round(left + index * cell_width)
            y = round(top + index * cell_height)
            # Only remove the darkest pixels on grid lines. Bright sprite
            # pixels crossing a line are preserved.
            vertical = mask[:, max(0, x - 1) : x + 2]
            vertical_dark = maximum[:, max(0, x - 1) : x + 2] < 42
            vertical[vertical_dark] = 0
            horizontal = mask[max(0, y - 1) : y + 2, :]
            horizontal_dark = maximum[max(0, y - 1) : y + 2, :] < 42
            horizontal[horizontal_dark] = 0

        mask = cv2.morphologyEx(
            mask,
            cv2.MORPH_CLOSE,
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)),
        )
        return mask

    def _extract_fragments(
        self,
        mask: np.ndarray,
        bounds: tuple[int, int, int, int],
    ) -> list[_Fragment]:
        count, _, stats, _ = cv2.connectedComponentsWithStats(mask)
        left, top, right, bottom = bounds
        fragments: list[_Fragment] = []
        for index in range(1, count):
            x, y, width, height, area = (int(value) for value in stats[index])
            if area < self.minimum_fragment_area:
                continue
            if x <= left + 2 or y <= top + 2:
                continue
            if x + width >= right - 2 or y + height >= bottom - 2:
                continue
            if width > self.maximum_sprite_width or height > self.maximum_sprite_height:
                continue
            fragments.append(_Fragment(x, y, x + width, y + height, area))
        return fragments

    def _merge_fragments(
        self,
        fragments: list[_Fragment],
    ) -> list[list[_Fragment]]:
        """Attach small fragments to dominant sprite fragments without chaining.

        A union-find merge is deliberately avoided: a sequence of tiny
        highlights can bridge several adjacent items. Groups grow around a
        fixed dominant seed and must retain axis overlap or a very small
        diagonal gap.
        """
        groups: list[list[_Fragment]] = []
        boxes: list[_Fragment] = []

        for fragment in sorted(fragments, key=lambda value: value.area, reverse=True):
            best_index: int | None = None
            best_distance = float("inf")

            for index, box in enumerate(boxes):
                horizontal_gap = max(
                    0,
                    max(box.left, fragment.left) - min(box.right, fragment.right),
                )
                vertical_gap = max(
                    0,
                    max(box.top, fragment.top) - min(box.bottom, fragment.bottom),
                )
                horizontal_overlap = min(box.right, fragment.right) > max(
                    box.left, fragment.left
                )
                vertical_overlap = min(box.bottom, fragment.bottom) > max(
                    box.top, fragment.top
                )
                continuous = (
                    (horizontal_overlap and vertical_gap <= self.fragment_gap)
                    or (vertical_overlap and horizontal_gap <= self.fragment_gap)
                    or (horizontal_gap <= 2 and vertical_gap <= 2)
                )
                if not continuous:
                    continue

                left = min(box.left, fragment.left)
                top = min(box.top, fragment.top)
                right = max(box.right, fragment.right)
                bottom = max(box.bottom, fragment.bottom)
                if (
                    right - left > self.maximum_sprite_width
                    or bottom - top > self.maximum_sprite_height
                ):
                    continue

                distance = horizontal_gap * horizontal_gap + vertical_gap * vertical_gap
                if distance < best_distance:
                    best_index = index
                    best_distance = distance

            if best_index is None:
                groups.append([fragment])
                boxes.append(fragment)
                continue

            groups[best_index].append(fragment)
            box = boxes[best_index]
            boxes[best_index] = _Fragment(
                left=min(box.left, fragment.left),
                top=min(box.top, fragment.top),
                right=max(box.right, fragment.right),
                bottom=max(box.bottom, fragment.bottom),
                area=box.area + fragment.area,
            )

        return groups

    def _groups_to_detections(
        self,
        groups: Iterable[list[_Fragment]],
        mask: np.ndarray,
        bounds: tuple[int, int, int, int],
    ) -> list[SpriteDetection]:
        left_bound, top_bound, right_bound, bottom_bound = bounds
        detections: list[SpriteDetection] = []
        for group in groups:
            left = min(fragment.left for fragment in group)
            top = min(fragment.top for fragment in group)
            right = max(fragment.right for fragment in group)
            bottom = max(fragment.bottom for fragment in group)
            area = sum(fragment.area for fragment in group)
            width = right - left
            height = bottom - top
            if area < self.minimum_sprite_area or width < 6 or height < 6:
                continue
            if width > self.maximum_sprite_width or height > self.maximum_sprite_height:
                continue
            if not (
                left_bound < left < right < right_bound
                and top_bound < top < bottom < bottom_bound
            ):
                continue

            patch = mask[top:bottom, left:right]
            fill = area / max(1, width * height)
            if fill < 0.025:
                continue

            # Use the median foreground coordinate rather than the bounding box
            # center, keeping the click on visible artwork for asymmetric items.
            ys, xs = np.where(patch > 0)
            click_x = left + int(np.median(xs))
            click_y = top + int(np.median(ys))
            confidence = min(1.0, fill * 2.5 + min(0.35, area / 1500))
            detections.append(
                SpriteDetection(
                    left=left,
                    top=top,
                    right=right,
                    bottom=bottom,
                    click=Coordinates(click_x, click_y),
                    confidence=confidence,
                )
            )
        return detections


def annotate_detections(
    image: np.ndarray,
    detections: Iterable[SpriteDetection],
) -> np.ndarray:
    annotated = image.copy()
    for index, detection in enumerate(detections, start=1):
        cv2.rectangle(
            annotated,
            (detection.left, detection.top),
            (detection.right, detection.bottom),
            (0, 255, 0),
            1,
        )
        cv2.circle(
            annotated,
            (detection.click.x, detection.click.y),
            3,
            (0, 255, 255),
            -1,
        )
        cv2.putText(
            annotated,
            str(index),
            (detection.click.x + 3, detection.click.y - 3),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.3,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
    return annotated
