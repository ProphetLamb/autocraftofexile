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

    @property
    def area(self) -> int:
        return self.width * self.height


@dataclass(slots=True, frozen=True)
class _Fragment:
    left: int
    top: int
    right: int
    bottom: int
    area: int


class StashSpriteDetector:
    """Detect item sprites directly in image space.

    The final reconciliation pass merges duplicate detections belonging to one
    large item, while explicitly protecting adjacent compact 1x1 items.
    """

    def __init__(
        self,
        *,
        minimum_fragment_area: int = 10,
        minimum_sprite_area: int = 20,
        fragment_gap: int = 2,
        maximum_sprite_width: int = 68,
        maximum_sprite_height: int = 128,
        duplicate_gap: int | None = None,
        duplicate_overlap: float = 0.55,
        duplicate_bridge_support: float = 0.12,
    ) -> None:
        self.minimum_fragment_area = minimum_fragment_area
        self.minimum_sprite_area = minimum_sprite_area
        self.fragment_gap = fragment_gap
        self.maximum_sprite_width = maximum_sprite_width
        self.maximum_sprite_height = maximum_sprite_height
        self.duplicate_gap = (
            max(fragment_gap + 1, fragment_gap * 3)
            if duplicate_gap is None
            else duplicate_gap
        )
        self.duplicate_overlap = duplicate_overlap
        self.duplicate_bridge_support = duplicate_bridge_support

    def detect(self, image: np.ndarray) -> tuple[SpriteDetection, ...]:
        mask = self._foreground_mask(image)
        fragments = self._extract_fragments(mask)
        groups = self._merge_fragments(fragments)
        detections = self._groups_to_detections(groups, mask)
        detections = self._reconcile_duplicates(detections, mask)
        return tuple(sorted(detections, key=lambda item: (item.top, item.left)))

    @staticmethod
    def _foreground_mask(image: np.ndarray) -> np.ndarray:
        inverted: np.ndarray = 255 - cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, otsu = cv2.threshold(
            inverted,
            0,
            255,
            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
        )
        _, binary = cv2.threshold(
            inverted,
            150,
            255,
            cv2.THRESH_BINARY_INV,
        )
        mask = cv2.add(otsu, binary)

        kernel = np.ones((2, 2), np.uint8)
        kernel[1, 1] = 0
        mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel)
        return cv2.morphologyEx(
            mask,
            cv2.MORPH_ERODE,
            kernel,
            iterations=2,
        )

    def _extract_fragments(self, mask: np.ndarray) -> list[_Fragment]:
        count, _, stats, _ = cv2.connectedComponentsWithStats(mask)
        fragments: list[_Fragment] = []
        for index in range(1, count):
            x, y, width, height, area = (int(value) for value in stats[index])
            if area < self.minimum_fragment_area:
                continue
            if width > self.maximum_sprite_width or height > self.maximum_sprite_height:
                continue
            fragments.append(_Fragment(x, y, x + width, y + height, area))
        return fragments

    def _merge_fragments(
        self,
        fragments: list[_Fragment],
    ) -> list[list[_Fragment]]:
        groups: list[list[_Fragment]] = []
        boxes: list[_Fragment] = []

        for fragment in sorted(
            fragments,
            key=lambda value: value.area,
            reverse=True,
        ):
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

                distance = horizontal_gap**2 + vertical_gap**2
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
    ) -> list[SpriteDetection]:
        detections: list[SpriteDetection] = []
        for group in groups:
            left = min(fragment.left for fragment in group)
            top = min(fragment.top for fragment in group)
            right = max(fragment.right for fragment in group)
            bottom = max(fragment.bottom for fragment in group)
            area = sum(fragment.area for fragment in group)
            width = right - left
            height = bottom - top
            if area < self.minimum_sprite_area or width < 2 or height < 2:
                continue
            if width > self.maximum_sprite_width or height > self.maximum_sprite_height:
                continue

            patch = mask[top:bottom, left:right]
            fill = area / max(1, width * height)
            if fill < 0.025:
                continue

            ys, xs = np.where(patch > 0)
            if not len(xs):
                continue
            detections.append(
                SpriteDetection(
                    left=left,
                    top=top,
                    right=right,
                    bottom=bottom,
                    click=Coordinates(
                        left + int(np.median(xs)),
                        top + int(np.median(ys)),
                    ),
                    confidence=min(
                        1.0,
                        fill * 2.5 + min(0.35, area / 1500),
                    ),
                )
            )
        return detections

    def _reconcile_duplicates(
        self,
        detections: list[SpriteDetection],
        mask: np.ndarray,
    ) -> list[SpriteDetection]:
        """Merge duplicate halves without joining neighboring 1x1 items.

        Two boxes are merged only when one of these is true:
        * boxes overlap substantially or one mostly contains the other;
        * boxes align strongly on one axis, have a small gap on the other axis,
          and foreground pixels bridge that gap.

        The proximity rule is disabled when both boxes are compact enough to be
        1x1 items. Overlapping compact boxes can still be deduplicated.
        """
        result = sorted(detections, key=lambda item: item.area, reverse=True)
        changed = True

        while changed:
            changed = False
            for first_index in range(len(result)):
                for second_index in range(first_index + 1, len(result)):
                    first = result[first_index]
                    second = result[second_index]
                    if not self._are_duplicates(first, second, mask):
                        continue

                    merged = self._merge_detections(first, second, mask)
                    result[first_index] = merged
                    del result[second_index]
                    result.sort(key=lambda item: item.area, reverse=True)
                    changed = True
                    break
                if changed:
                    break

        return result

    def _are_duplicates(
        self,
        first: SpriteDetection,
        second: SpriteDetection,
        mask: np.ndarray,
    ) -> bool:
        intersection_width = max(
            0,
            min(first.right, second.right) - max(first.left, second.left),
        )
        intersection_height = max(
            0,
            min(first.bottom, second.bottom) - max(first.top, second.top),
        )
        intersection = intersection_width * intersection_height
        first_area = max(1, first.area)
        second_area = max(1, second.area)
        union = first_area + second_area - intersection
        iou = intersection / max(1, union)
        containment = intersection / min(first_area, second_area)

        # Safe duplicate suppression. Distinct 1x1 items do not overlap.
        if iou >= 0.35 or containment >= 0.65:
            return True

        horizontal_gap = max(
            0,
            max(first.left, second.left) - min(first.right, second.right),
        )
        vertical_gap = max(
            0,
            max(first.top, second.top) - min(first.bottom, second.bottom),
        )
        horizontal_overlap_ratio = intersection_width / max(
            1,
            min(first.width, second.width),
        )
        vertical_overlap_ratio = intersection_height / max(
            1,
            min(first.height, second.height),
        )

        compact_width = max(4, self.maximum_sprite_width // 2)
        compact_height = max(4, self.maximum_sprite_height // 4)
        first_is_compact = (
            first.width <= compact_width and first.height <= compact_height
        )
        second_is_compact = (
            second.width <= compact_width and second.height <= compact_height
        )
        if first_is_compact and second_is_compact:
            return False

        vertical_join = (
            horizontal_overlap_ratio >= self.duplicate_overlap
            and vertical_gap <= self.duplicate_gap
        )
        horizontal_join = (
            vertical_overlap_ratio >= self.duplicate_overlap
            and horizontal_gap <= self.duplicate_gap
        )
        if not (vertical_join or horizontal_join):
            return False

        combined_left = min(first.left, second.left)
        combined_top = min(first.top, second.top)
        combined_right = max(first.right, second.right)
        combined_bottom = max(first.bottom, second.bottom)
        if (
            combined_right - combined_left > self.maximum_sprite_width
            or combined_bottom - combined_top > self.maximum_sprite_height
        ):
            return False

        return self._bridge_support(first, second, mask) >= (
            self.duplicate_bridge_support
        )

    def _bridge_support(
        self,
        first: SpriteDetection,
        second: SpriteDetection,
        mask: np.ndarray,
    ) -> float:
        """Return foreground support in the actual gap between two boxes."""
        padding = max(1, self.duplicate_gap)
        horizontal_overlap_left = max(first.left, second.left)
        horizontal_overlap_right = min(first.right, second.right)
        vertical_overlap_top = max(first.top, second.top)
        vertical_overlap_bottom = min(first.bottom, second.bottom)

        horizontal_gap = max(
            0,
            max(first.left, second.left) - min(first.right, second.right),
        )
        vertical_gap = max(
            0,
            max(first.top, second.top) - min(first.bottom, second.bottom),
        )

        if vertical_gap and horizontal_overlap_right > horizontal_overlap_left:
            left = max(0, horizontal_overlap_left)
            right = min(mask.shape[1], horizontal_overlap_right)
            top = max(
                0,
                min(first.bottom, second.bottom) - padding,
            )
            bottom = min(
                mask.shape[0],
                max(first.top, second.top) + padding + 1,
            )
        elif horizontal_gap and vertical_overlap_bottom > vertical_overlap_top:
            left = max(
                0,
                min(first.right, second.right) - padding,
            )
            right = min(
                mask.shape[1],
                max(first.left, second.left) + padding + 1,
            )
            top = max(0, vertical_overlap_top)
            bottom = min(mask.shape[0], vertical_overlap_bottom)
        else:
            left = max(0, max(first.left, second.left))
            right = min(mask.shape[1], min(first.right, second.right))
            top = max(0, max(first.top, second.top))
            bottom = min(mask.shape[0], min(first.bottom, second.bottom))

        corridor = mask[top:bottom, left:right]
        return float(np.mean(corridor > 0)) if corridor.size else 0.0

    @staticmethod
    def _merge_detections(
        first: SpriteDetection,
        second: SpriteDetection,
        mask: np.ndarray,
    ) -> SpriteDetection:
        left = min(first.left, second.left)
        top = min(first.top, second.top)
        right = max(first.right, second.right)
        bottom = max(first.bottom, second.bottom)
        patch = mask[top:bottom, left:right]
        ys, xs = np.where(patch > 0)

        if len(xs):
            click = Coordinates(
                left + int(np.median(xs)),
                top + int(np.median(ys)),
            )
            fill = len(xs) / max(1, (right - left) * (bottom - top))
        else:
            click = Coordinates(
                (left + right) // 2,
                (top + bottom) // 2,
            )
            fill = 0.0

        return SpriteDetection(
            left=left,
            top=top,
            right=right,
            bottom=bottom,
            click=click,
            confidence=max(
                first.confidence,
                second.confidence,
                min(1.0, fill * 2.5),
            ),
        )


def annotate_fragment(
    image: np.ndarray,
    fragments: Iterable[_Fragment],
) -> np.ndarray:
    annotated = image.copy()
    for fragment in fragments:
        cv2.rectangle(
            annotated,
            (fragment.left, fragment.top),
            (fragment.right, fragment.bottom),
            (0, 255, 0),
            1,
        )
    return annotated


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
