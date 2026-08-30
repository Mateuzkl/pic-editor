"""Saved atlas regions and sprite coverage calculations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Iterable

from src.models.pic import Pic, SPRITE_SIZE


@dataclass(slots=True)
class AtlasRegion:
    """A real-pixel rectangle inside one zero-based PIC image."""

    name: str
    image_index: int
    x: int
    y: int
    width: int
    height: int
    image_width: int = 0
    image_height: int = 0
    notes: str = ""

    @property
    def right(self) -> int:
        """Exclusive right edge."""
        return self.x + self.width

    @property
    def bottom(self) -> int:
        """Exclusive bottom edge."""
        return self.y + self.height

    def normalized(self) -> "AtlasRegion":
        x, y, width, height = self.x, self.y, self.width, self.height
        if width < 0:
            x += width
            width = -width
        if height < 0:
            y += height
            height = -height
        return AtlasRegion(
            self.name,
            self.image_index,
            x,
            y,
            width,
            height,
            self.image_width,
            self.image_height,
            self.notes,
        )

    def to_dict(self) -> dict:
        data = asdict(self)
        return {
            "name": data["name"],
            "imageIndex": data["image_index"],
            "x": data["x"],
            "y": data["y"],
            "width": data["width"],
            "height": data["height"],
            "imageWidth": data["image_width"],
            "imageHeight": data["image_height"],
            "notes": data["notes"],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AtlasRegion":
        return cls(
            name=str(data.get("name", "REGION")),
            image_index=int(data.get("imageIndex", 0)),
            x=int(data.get("x", 0)),
            y=int(data.get("y", 0)),
            width=int(data.get("width", 0)),
            height=int(data.get("height", 0)),
            image_width=int(data.get("imageWidth", 0)),
            image_height=int(data.get("imageHeight", 0)),
            notes=str(data.get("notes", "")),
        ).normalized()


@dataclass(frozen=True, slots=True)
class SpriteCoverage:
    start_col: int
    end_col: int
    start_row: int
    end_row: int
    indexes: tuple[int, ...]

    @property
    def columns(self) -> int:
        return self.end_col - self.start_col + 1

    @property
    def rows(self) -> int:
        return self.end_row - self.start_row + 1


def sprite_coverage(
    x: int,
    y: int,
    width: int,
    height: int,
    image_width_sprites: int,
) -> SpriteCoverage | None:
    """Return every 32x32 sprite touched by an exclusive-edge rectangle."""
    if width <= 0 or height <= 0 or image_width_sprites <= 0:
        return None
    start_col = x // SPRITE_SIZE
    start_row = y // SPRITE_SIZE
    end_col = (x + width - 1) // SPRITE_SIZE
    end_row = (y + height - 1) // SPRITE_SIZE
    indexes = tuple(
        row * image_width_sprites + col
        for row in range(start_row, end_row + 1)
        for col in range(start_col, end_col + 1)
    )
    return SpriteCoverage(
        start_col, end_col, start_row, end_row, indexes
    )


@dataclass(slots=True)
class RegionProject:
    signature: int
    file_size: int
    sha256: str
    source_name: str
    regions: list[AtlasRegion] = field(default_factory=list)
    format_version: int = 1

    @staticmethod
    def hash_file(file_path: str) -> str:
        digest = hashlib.sha256()
        with open(file_path, "rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @classmethod
    def for_pic(cls, pic: Pic) -> "RegionProject":
        if not pic.file_path:
            return cls(pic.signature, 0, "", "")
        path = Path(pic.file_path)
        return cls(
            signature=pic.signature,
            file_size=path.stat().st_size,
            sha256=cls.hash_file(str(path)),
            source_name=path.name,
        )

    def matches_pic(self, pic: Pic) -> bool:
        if self.signature != pic.signature or not pic.file_path:
            return False
        path = Path(pic.file_path)
        return (
            self.file_size == path.stat().st_size
            and self.sha256 == self.hash_file(str(path))
        )

    def to_dict(self) -> dict:
        return {
            "formatVersion": self.format_version,
            "pic": {
                "signature": self.signature,
                "fileSize": self.file_size,
                "sha256": self.sha256,
                "sourceName": self.source_name,
            },
            "regions": [region.to_dict() for region in self.regions],
        }

    def save(self, file_path: str) -> None:
        Path(file_path).write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    @classmethod
    def load(cls, file_path: str) -> "RegionProject":
        data = json.loads(Path(file_path).read_text(encoding="utf-8"))
        pic = data.get("pic", {})
        return cls(
            signature=int(pic.get("signature", 0)),
            file_size=int(pic.get("fileSize", 0)),
            sha256=str(pic.get("sha256", "")),
            source_name=str(pic.get("sourceName", "")),
            regions=[
                AtlasRegion.from_dict(item)
                for item in data.get("regions", [])
            ],
            format_version=int(data.get("formatVersion", 1)),
        )

    def replace_regions(self, regions: Iterable[AtlasRegion]) -> None:
        self.regions = list(regions)
