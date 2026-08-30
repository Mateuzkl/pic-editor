"""Read-only foreground component detection for rendered PIC images."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable

import numpy as np
from PIL import Image


@dataclass(frozen=True, slots=True)
class DetectionOptions:
    tolerance: int = 0
    minimum_width: int = 2
    minimum_height: int = 2
    minimum_area: int = 4
    merge_distance: int = 0
    include_transparent: bool = False
    connectivity: int = 8


def foreground_mask(
    image: Image.Image,
    background: tuple[int, int, int],
    tolerance: int = 0,
    include_transparent: bool = False,
) -> np.ndarray:
    rgba = np.asarray(image.convert("RGBA"), dtype=np.int16)
    background_array = np.asarray(background, dtype=np.int16)
    color_distance = np.max(np.abs(rgba[:, :, :3] - background_array), axis=2)
    foreground = color_distance > max(0, tolerance)
    if include_transparent:
        foreground |= rgba[:, :, 3] == 0
    else:
        foreground &= rgba[:, :, 3] != 0
    return foreground


def _neighbors(connectivity: int) -> tuple[tuple[int, int], ...]:
    basic = ((-1, 0), (1, 0), (0, -1), (0, 1))
    if connectivity == 4:
        return basic
    return basic + ((-1, -1), (-1, 1), (1, -1), (1, 1))


def component_at(
    mask: np.ndarray,
    x: int,
    y: int,
    connectivity: int = 8,
) -> tuple[int, int, int, int] | None:
    height, width = mask.shape
    if not (0 <= x < width and 0 <= y < height) or not bool(mask[y, x]):
        return None
    visited = np.zeros(mask.shape, dtype=np.bool_)
    queue = deque(((x, y),))
    visited[y, x] = True
    min_x = max_x = x
    min_y = max_y = y
    for_x_y = _neighbors(connectivity)
    while queue:
        current_x, current_y = queue.popleft()
        min_x = min(min_x, current_x)
        max_x = max(max_x, current_x)
        min_y = min(min_y, current_y)
        max_y = max(max_y, current_y)
        for dx, dy in for_x_y:
            next_x, next_y = current_x + dx, current_y + dy
            if (
                0 <= next_x < width
                and 0 <= next_y < height
                and not visited[next_y, next_x]
                and bool(mask[next_y, next_x])
            ):
                visited[next_y, next_x] = True
                queue.append((next_x, next_y))
    return min_x, min_y, max_x - min_x + 1, max_y - min_y + 1


def detect_regions(
    image: Image.Image,
    background: tuple[int, int, int],
    options: DetectionOptions,
    progress: Callable[[int], None] | None = None,
) -> list[tuple[int, int, int, int]]:
    work = foreground_mask(
        image,
        background,
        options.tolerance,
        options.include_transparent,
    ).copy()
    height, width = work.shape
    boxes: list[tuple[int, int, int, int]] = []
    directions = _neighbors(options.connectivity)
    for y in range(height):
        if progress and (y % 32 == 0 or y == height - 1):
            progress(int((y + 1) * 100 / max(1, height)))
        for x in np.flatnonzero(work[y]):
            x = int(x)
            if not work[y, x]:
                continue
            queue = deque(((x, y),))
            work[y, x] = False
            min_x = max_x = x
            min_y = max_y = y
            area = 0
            while queue:
                current_x, current_y = queue.popleft()
                area += 1
                if progress and area % 8192 == 0:
                    progress(int((y + 1) * 100 / max(1, height)))
                min_x = min(min_x, current_x)
                max_x = max(max_x, current_x)
                min_y = min(min_y, current_y)
                max_y = max(max_y, current_y)
                for dx, dy in directions:
                    next_x, next_y = current_x + dx, current_y + dy
                    if (
                        0 <= next_x < width
                        and 0 <= next_y < height
                        and work[next_y, next_x]
                    ):
                        work[next_y, next_x] = False
                        queue.append((next_x, next_y))
            box_width = max_x - min_x + 1
            box_height = max_y - min_y + 1
            if (
                box_width >= options.minimum_width
                and box_height >= options.minimum_height
                and area >= options.minimum_area
            ):
                boxes.append((min_x, min_y, box_width, box_height))
    return merge_regions(boxes, options.merge_distance)


def _boxes_near(
    first: tuple[int, int, int, int],
    second: tuple[int, int, int, int],
    distance: int,
) -> bool:
    ax, ay, aw, ah = first
    bx, by, bw, bh = second
    return not (
        ax + aw + distance < bx
        or bx + bw + distance < ax
        or ay + ah + distance < by
        or by + bh + distance < ay
    )


def merge_regions(
    boxes: list[tuple[int, int, int, int]], distance: int
) -> list[tuple[int, int, int, int]]:
    if distance <= 0:
        return sorted(boxes, key=lambda box: (box[1], box[0]))
    pending = list(boxes)
    merged: list[tuple[int, int, int, int]] = []
    while pending:
        current = pending.pop()
        changed = True
        while changed:
            changed = False
            remaining = []
            for candidate in pending:
                if _boxes_near(current, candidate, distance):
                    x1 = min(current[0], candidate[0])
                    y1 = min(current[1], candidate[1])
                    x2 = max(current[0] + current[2], candidate[0] + candidate[2])
                    y2 = max(current[1] + current[3], candidate[1] + candidate[3])
                    current = (x1, y1, x2 - x1, y2 - y1)
                    changed = True
                else:
                    remaining.append(candidate)
            pending = remaining
        merged.append(current)
    return sorted(merged, key=lambda box: (box[1], box[0]))
