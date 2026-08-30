"""Clipboard/export formats for inspected atlas rectangles."""

from __future__ import annotations

import csv
import io
import json
import re

from src.models.region import AtlasRegion


def sanitize_cpp_identifier(value: str) -> str:
    identifier = re.sub(r"[^A-Za-z0-9_]", "_", value.strip().upper())
    identifier = re.sub(r"_+", "_", identifier).strip("_") or "REGION"
    if identifier[0].isdigit():
        identifier = f"REGION_{identifier}"
    return identifier


def rect_text(region: AtlasRegion) -> str:
    return f"{region.x}, {region.y}, {region.width}, {region.height}"


def cpp_constants(region: AtlasRegion) -> str:
    name = sanitize_cpp_identifier(region.name)
    return "\n".join(
        (
            f"constexpr int {name}_SRC_X = {region.x};",
            f"constexpr int {name}_SRC_Y = {region.y};",
            f"constexpr int {name}_WIDTH = {region.width};",
            f"constexpr int {name}_HEIGHT = {region.height};",
        )
    )


def cpp_struct(region: AtlasRegion) -> str:
    name = sanitize_cpp_identifier(region.name)
    return (
        f"constexpr SpriteRect {name}_RECT{{{region.x}, {region.y}, "
        f"{region.width}, {region.height}}};"
    )


def draw_picture_call(
    region: AtlasRegion,
    image_expression: str = "GUI_UI_IMAGE",
    renderer_expression: str = "renderer",
) -> str:
    return "\n".join(
        (
            f"{renderer_expression}->drawPicture(",
            f"    {image_expression},",
            f"    {region.x},",
            f"    {region.y},",
            "    destinationX,",
            "    destinationY,",
            f"    {region.width},",
            f"    {region.height}",
            ");",
        )
    )


def json_text(region: AtlasRegion) -> str:
    return json.dumps(region.to_dict(), indent=2, ensure_ascii=False)


def csv_text(region: AtlasRegion) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(("name", "imageIndex", "x", "y", "width", "height", "notes"))
    writer.writerow(
        (
            region.name,
            region.image_index,
            region.x,
            region.y,
            region.width,
            region.height,
            region.notes,
        )
    )
    return output.getvalue().strip("\r\n")
