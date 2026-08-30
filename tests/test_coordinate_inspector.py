from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image
from PyQt6.QtCore import QPoint, QPointF, QRect, QSize
from PyQt6.QtWidgets import QApplication

from src.models.pic import Pic, PicImage
from src.models.region import AtlasRegion, RegionProject, sprite_coverage
from src.parsers.pic_parser import PicParser
from src.ui.coordinate_inspector import CoordinateInspector
from src.ui.inspectable_image_canvas import InspectableImageCanvas
from src.ui.image_viewer import ImageViewer
from src.utils.code_generator import cpp_constants, rect_text, sanitize_cpp_identifier
from src.utils.coordinate_transform import CoordinateTransform
from src.utils.region_detector import DetectionOptions, component_at, detect_regions, foreground_mask


APP = QApplication.instance() or QApplication([])


class CoordinateTransformTests(unittest.TestCase):
    def test_round_trip_at_every_supported_reference_zoom(self):
        image_point = QPointF(724.25, 266.75)
        for zoom in (0.25, 1.0, 4.0, 8.0, 16.0):
            transform = CoordinateTransform(zoom, QSize(1024, 768))
            result = transform.widget_to_image(transform.image_to_widget(image_point))
            self.assertAlmostEqual(result.x(), image_point.x())
            self.assertAlmostEqual(result.y(), image_point.y())

    def test_rectangle_transform_uses_real_dimensions(self):
        transform = CoordinateTransform(4.0, QSize(100, 100))
        mapped = transform.image_rect_to_widget(QRect(2, 3, 8, 9))
        self.assertEqual((mapped.x(), mapped.y(), mapped.width(), mapped.height()), (8, 12, 32, 36))


class CanvasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = APP

    def setUp(self):
        self.canvas = InspectableImageCanvas()
        self.canvas.set_image(Image.new("RGBA", (128, 96), (255, 0, 255, 255)))
        self.canvas.set_inspection_enabled(True)

    def test_reverse_selection_is_normalized_and_inclusive_of_dragged_pixels(self):
        rect = self.canvas._selection_from_points(QPoint(63, 47), QPoint(32, 16))
        self.assertEqual((rect.x(), rect.y(), rect.width(), rect.height()), (32, 16, 32, 32))

    def test_selection_is_identical_at_each_zoom(self):
        expected = (12, 18, 32, 24)
        for zoom in (0.25, 1.0, 4.0, 8.0, 16.0):
            self.canvas.set_zoom(zoom)
            self.canvas.set_selection(QRect(*expected))
            rect = self.canvas.selection
            self.assertEqual((rect.x(), rect.y(), rect.width(), rect.height()), expected)

    def test_grid_snap_aligns_all_edges(self):
        self.canvas.set_snap_to_grid(True)
        self.canvas.set_selection(QRect(13, 35, 41, 20))
        rect = self.canvas.selection
        self.assertEqual((rect.x(), rect.y(), rect.width(), rect.height()), (0, 32, 64, 32))

    def test_saved_unaligned_region_bypasses_current_snap_mode(self):
        self.canvas.set_snap_to_grid(True)
        self.canvas.set_selection(QRect(13, 35, 41, 20), apply_snap=False)
        rect = self.canvas.selection
        self.assertEqual((rect.x(), rect.y(), rect.width(), rect.height()), (13, 35, 41, 20))

    def test_selection_clamps_without_changing_size_when_moved(self):
        self.canvas.set_selection(QRect(90, 70, 20, 20))
        self.canvas.move_selection(100, 100)
        rect = self.canvas.selection
        self.assertEqual((rect.x(), rect.y(), rect.width(), rect.height()), (108, 76, 20, 20))

    def test_viewer_supports_requested_zoom_range(self):
        viewer = ImageViewer()
        viewer.set_image(Image.new("RGBA", (64, 64)))
        viewer._set_zoom(16.0)
        self.assertEqual(viewer.canvas.zoom, 16.0)
        viewer._set_zoom(0.25)
        self.assertEqual(viewer.canvas.zoom, 0.25)

    def test_scroll_and_pan_do_not_change_real_selection(self):
        viewer = ImageViewer()
        viewer.resize(220, 180)
        viewer.set_image(Image.new("RGBA", (512, 384)))
        viewer._set_zoom(2.0)
        viewer.show()
        APP.processEvents()
        viewer.canvas.set_selection(QRect(100, 80, 32, 40))
        viewer.scroll_area.horizontalScrollBar().setValue(150)
        viewer.scroll_area.verticalScrollBar().setValue(90)
        before = viewer.canvas.selection
        viewer._pan(-20, -15)
        after = viewer.canvas.selection
        self.assertEqual(after, before)
        sample = QPointF(123.5, 91.25)
        mapped = viewer.canvas.widget_to_image(viewer.canvas.image_to_widget(sample))
        self.assertAlmostEqual(mapped.x(), sample.x())
        self.assertAlmostEqual(mapped.y(), sample.y())
        viewer.close()


class RegionTests(unittest.TestCase):
    def test_sprite_grid_mapping(self):
        coverage = sprite_coverage(32, 64, 32, 32, 10)
        self.assertEqual((coverage.start_col, coverage.start_row), (1, 2))
        self.assertEqual(coverage.indexes, (21,))

    def test_region_crossing_unaligned_sprites(self):
        coverage = sprite_coverage(31, 31, 34, 34, 10)
        self.assertEqual((coverage.start_col, coverage.end_col), (0, 2))
        self.assertEqual((coverage.start_row, coverage.end_row), (0, 2))
        self.assertEqual(coverage.indexes, (0, 1, 2, 10, 11, 12, 20, 21, 22))

    def test_code_generation_is_exact_and_identifier_is_safe(self):
        region = AtlasRegion("3 chat toggle!", 3, 724, 266, 32, 32)
        self.assertEqual(sanitize_cpp_identifier(region.name), "REGION_3_CHAT_TOGGLE")
        self.assertEqual(rect_text(region), "724, 266, 32, 32")
        code = cpp_constants(region)
        self.assertIn("REGION_3_CHAT_TOGGLE_SRC_X = 724", code)
        self.assertIn("REGION_3_CHAT_TOGGLE_HEIGHT = 32", code)

    def test_project_roundtrip_and_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as folder:
            pic_path = Path(folder) / "Tibia.pic"
            pic_path.write_bytes(b"PIC-A")
            pic = Pic(signature=123, file_path=str(pic_path))
            project = RegionProject.for_pic(pic)
            project.regions.append(AtlasRegion("ICON", 0, 1, 2, 3, 4, 32, 32, "note"))
            json_path = Path(folder) / "Tibia.pic.regions.json"
            project.save(str(json_path))
            loaded = RegionProject.load(str(json_path))
            self.assertTrue(loaded.matches_pic(pic))
            self.assertEqual(loaded.regions[0].to_dict(), project.regions[0].to_dict())
            pic_path.write_bytes(b"PIC-B")
            self.assertFalse(loaded.matches_pic(pic))

    def test_matching_default_sidecar_reopens_automatically(self):
        with tempfile.TemporaryDirectory() as folder:
            pic_path = Path(folder) / "Tibia.pic"
            pic_path.write_bytes(b"PIC-C")
            pic = Pic(signature=456, file_path=str(pic_path))
            project = RegionProject.for_pic(pic)
            project.regions.append(AtlasRegion("AUTO", 0, 2, 3, 4, 5))
            project.save(f"{pic_path}.regions.json")
            inspector = CoordinateInspector(ImageViewer())
            inspector.set_pic(pic)
            self.assertEqual([region.name for region in inspector.project.regions], ["AUTO"])

    def test_png_crop_has_exact_size_and_pixels(self):
        image = Image.new("RGBA", (10, 10), (0, 0, 0, 255))
        image.putpixel((4, 5), (12, 34, 56, 255))
        region = AtlasRegion("PIXEL", 0, 4, 5, 3, 2)
        crop = CoordinateInspector._crop_region(image, region)
        self.assertEqual(crop.size, (3, 2))
        self.assertEqual(crop.getpixel((0, 0)), (12, 34, 56, 255))

    def test_copy_cpp_places_exact_text_on_clipboard(self):
        viewer = ImageViewer()
        inspector = CoordinateInspector(viewer)
        image = Image.new("RGBA", (128, 96), (255, 0, 255, 255))
        pic_image = PicImage(width=4, height=3)
        pic = Pic(signature=7, images=[pic_image])
        viewer.set_image(image)
        inspector.set_pic(pic)
        inspector.set_context(pic, 0, pic_image, image)
        inspector.name_edit.setText("chat toggle")
        viewer.canvas.set_selection(QRect(12, 18, 32, 24))
        inspector.copy_format("constants")
        clipboard = APP.clipboard().text()
        self.assertIn("CHAT_TOGGLE_SRC_X = 12", clipboard)
        self.assertIn("CHAT_TOGGLE_HEIGHT = 24", clipboard)
        inspector.image_expression_edit.setText("GUI_CUSTOM_IMAGE")
        inspector.renderer_expression_edit.setText("g_renderer")
        inspector.copy_format("draw")
        draw_call = APP.clipboard().text()
        self.assertIn("g_renderer->drawPicture(", draw_call)
        self.assertIn("GUI_CUSTOM_IMAGE", draw_call)


class DetectionTests(unittest.TestCase):
    def setUp(self):
        self.background = (255, 0, 255)
        self.image = Image.new("RGBA", (32, 24), (*self.background, 255))
        for y in range(6, 12):
            for x in range(5, 14):
                self.image.putpixel((x, y), (20, 40, 60, 255))

    def test_auto_detect_uses_background_and_does_not_change_pixels(self):
        before = self.image.tobytes()
        boxes = detect_regions(
            self.image,
            self.background,
            DetectionOptions(minimum_width=2, minimum_height=2, minimum_area=4),
        )
        self.assertEqual(boxes, [(5, 6, 9, 6)])
        self.assertEqual(self.image.tobytes(), before)

    def test_magic_component_at(self):
        mask = foreground_mask(self.image, self.background)
        self.assertEqual(component_at(mask, 7, 8, 8), (5, 6, 9, 6))
        self.assertIsNone(component_at(mask, 0, 0, 8))


class PicIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pic_path = os.environ.get("TIBIA_PIC_PATH")

    def test_real_tibia_pic_load_render_and_roundtrip(self):
        if not self.pic_path or not Path(self.pic_path).is_file():
            self.skipTest("Set TIBIA_PIC_PATH to run the real-file integration test")
        parser = PicParser()
        pic = parser.load(self.pic_path)
        self.assertGreater(pic.num_images, 0)
        rendered = [parser.render_image(image) for image in pic.images]
        self.assertEqual(len(rendered), pic.num_images)
        for source, result in zip(pic.images, rendered):
            self.assertEqual(result.size, (source.pixel_width, source.pixel_height))
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "roundtrip.pic"
            parser.save(pic, str(output))
            reopened = PicParser().load(str(output))
            self.assertEqual(reopened.signature, pic.signature)
            self.assertEqual(reopened.num_images, pic.num_images)
            self.assertEqual(
                [(item.width, item.height) for item in reopened.images],
                [(item.width, item.height) for item in pic.images],
            )


if __name__ == "__main__":
    unittest.main()
