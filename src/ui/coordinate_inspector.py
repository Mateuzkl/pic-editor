"""Coordinate Inspector panel and sidecar region-project management."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from PIL import Image
from PyQt6.QtCore import QObject, QRect, QThread, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.models.pic import Pic, PicImage
from src.models.region import AtlasRegion, RegionProject, sprite_coverage
from src.ui.image_viewer import ImageViewer
from src.utils.code_generator import (
    cpp_constants,
    cpp_struct,
    csv_text,
    draw_picture_call,
    json_text,
    rect_text,
    sanitize_cpp_identifier,
)
from src.utils.i18n import tr
from src.utils.region_detector import (
    DetectionOptions,
    component_at,
    detect_regions,
    foreground_mask,
)


class DetectionWorker(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(
        self,
        image: Image.Image,
        background: tuple[int, int, int],
        options: DetectionOptions,
    ):
        super().__init__()
        self._image = image
        self._background = background
        self._options = options

    @pyqtSlot()
    def run(self) -> None:
        try:
            regions = detect_regions(
                self._image, self._background, self._options, self._report_progress
            )
            self.finished.emit(regions)
        except InterruptedError:
            self.cancelled.emit()
        except Exception as exc:  # UI boundary: report instead of crashing the thread
            self.failed.emit(str(exc))

    def _report_progress(self, value: int) -> None:
        if QThread.currentThread().isInterruptionRequested():
            raise InterruptedError
        self.progress.emit(value)


class CoordinateInspector(QWidget):
    """Read-only inspection tools for the currently rendered PIC atlas."""

    region_activated = pyqtSignal(object)

    def __init__(self, viewer: ImageViewer, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("coordinateInspector")
        self.viewer = viewer
        self.pic: Optional[Pic] = None
        self.pic_image: Optional[PicImage] = None
        self.image: Optional[Image.Image] = None
        self.image_index = -1
        self.project: Optional[RegionProject] = None
        self.project_path: Optional[str] = None
        self._syncing_selection = False
        self._mask_cache: dict[tuple[int, int, bool], object] = {}
        self._detection_thread: Optional[QThread] = None
        self._detection_worker: Optional[DetectionWorker] = None
        self._detection_image_index = -1
        self._setup_ui()
        self._connect_canvas()
        self.setEnabled(False)

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        outer.addWidget(self.scroll)
        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        self.content_layout.setSpacing(8)
        self.scroll.setWidget(content)

        self.info_group = QGroupBox(tr("inspector_info"))
        self.info_form = QFormLayout(self.info_group)
        self.image_info_label = QLabel("—")
        self.mouse_info_label = QLabel("—")
        self.mouse_info_label.setWordWrap(True)
        self.selection_info_label = QLabel("—")
        self.selection_info_label.setWordWrap(True)
        self.sprite_info_label = QLabel("—")
        self.sprite_info_label.setWordWrap(True)
        self.info_form.addRow(tr("inspector_image"), self.image_info_label)
        self.info_form.addRow(tr("inspector_mouse"), self.mouse_info_label)
        self.info_form.addRow(tr("inspector_selection"), self.selection_info_label)
        self.info_form.addRow(tr("inspector_sprites"), self.sprite_info_label)
        self.content_layout.addWidget(self.info_group)

        self.selection_group = QGroupBox(tr("inspector_selection"))
        selection_layout = QGridLayout(self.selection_group)
        self.coordinate_spins: dict[str, QSpinBox] = {}
        for column, key in enumerate(("X", "Y", "W", "H")):
            label = QLabel(key)
            spin = QSpinBox()
            spin.setRange(0 if key in ("X", "Y") else 1, 1_000_000)
            spin.valueChanged.connect(self._spin_selection_changed)
            self.coordinate_spins[key] = spin
            selection_layout.addWidget(label, 0, column)
            selection_layout.addWidget(spin, 1, column)
        self.snap_combo = QComboBox()
        self.snap_combo.addItems((tr("inspector_snap_pixel"), tr("inspector_snap_grid")))
        self.snap_combo.currentIndexChanged.connect(
            lambda index: self.viewer.canvas.set_snap_to_grid(index == 1)
        )
        selection_layout.addWidget(self.snap_combo, 2, 0, 1, 4)
        buttons = QHBoxLayout()
        self.clear_button = QPushButton(tr("inspector_clear"))
        self.clear_button.clicked.connect(self.viewer.canvas.clear_selection)
        self.full_button = QPushButton(tr("inspector_full_image"))
        self.full_button.clicked.connect(self.viewer.canvas.select_all)
        buttons.addWidget(self.clear_button)
        buttons.addWidget(self.full_button)
        selection_layout.addLayout(buttons, 3, 0, 1, 4)
        self.content_layout.addWidget(self.selection_group)

        self.overlay_group = QGroupBox(tr("inspector_overlays"))
        overlay_layout = QVBoxLayout(self.overlay_group)
        self.sprite_grid_checkbox = QCheckBox(tr("inspector_sprite_grid"))
        self.pixel_grid_checkbox = QCheckBox(tr("inspector_pixel_grid"))
        self.rulers_checkbox = QCheckBox(tr("inspector_rulers"))
        self.coordinates_checkbox = QCheckBox(tr("inspector_coordinates"))
        for checkbox in (
            self.sprite_grid_checkbox,
            self.pixel_grid_checkbox,
            self.rulers_checkbox,
            self.coordinates_checkbox,
        ):
            overlay_layout.addWidget(checkbox)
            checkbox.toggled.connect(self._apply_overlays)
        self.content_layout.addWidget(self.overlay_group)

        self.code_group = QGroupBox(tr("inspector_code"))
        code_layout = QVBoxLayout(self.code_group)
        self.code_form = QFormLayout()
        self.name_edit = QLineEdit("REGION")
        self.name_edit.setPlaceholderText("CHAT_TOGGLE")
        self.image_expression_edit = QLineEdit("GUI_UI_IMAGE")
        self.renderer_expression_edit = QLineEdit("renderer")
        self.code_form.addRow(tr("inspector_constant_name"), self.name_edit)
        self.code_form.addRow(tr("inspector_image_expression"), self.image_expression_edit)
        self.code_form.addRow(tr("inspector_renderer_expression"), self.renderer_expression_edit)
        code_layout.addLayout(self.code_form)
        code_buttons = QGridLayout()
        self.copy_rect_button = self._code_button(tr("inspector_copy_rect"), "rect")
        self.copy_constants_button = self._code_button(tr("inspector_copy_cpp"), "constants")
        self.copy_struct_button = self._code_button(tr("inspector_copy_struct"), "struct")
        self.copy_draw_button = self._code_button(tr("inspector_copy_draw"), "draw")
        self.copy_json_button = self._code_button(tr("inspector_copy_json"), "json")
        self.copy_csv_button = self._code_button(tr("inspector_copy_csv"), "csv")
        for index, button in enumerate((
            self.copy_rect_button,
            self.copy_constants_button,
            self.copy_struct_button,
            self.copy_draw_button,
            self.copy_json_button,
            self.copy_csv_button,
        )):
            code_buttons.addWidget(button, index // 2, index % 2)
        code_layout.addLayout(code_buttons)
        self.content_layout.addWidget(self.code_group)

        self.detect_group = QGroupBox(tr("inspector_detection"))
        detect_layout = QGridLayout(self.detect_group)
        self.tolerance_spin = self._option_spin(0, 255, 0)
        self.minimum_width_spin = self._option_spin(1, 4096, 2)
        self.minimum_height_spin = self._option_spin(1, 4096, 2)
        self.minimum_area_spin = self._option_spin(1, 16_000_000, 4)
        self.merge_distance_spin = self._option_spin(0, 256, 0)
        self.margin_spin = self._option_spin(-32, 128, 0)
        labels_and_widgets = (
            ("inspector_tolerance", self.tolerance_spin),
            ("inspector_min_width", self.minimum_width_spin),
            ("inspector_min_height", self.minimum_height_spin),
            ("inspector_min_area", self.minimum_area_spin),
            ("inspector_merge", self.merge_distance_spin),
            ("inspector_margin", self.margin_spin),
        )
        self.detect_labels: dict[str, QLabel] = {}
        for row, (key, widget) in enumerate(labels_and_widgets):
            label = QLabel(tr(key))
            self.detect_labels[key] = label
            detect_layout.addWidget(label, row, 0)
            detect_layout.addWidget(widget, row, 1)
        self.connectivity_combo = QComboBox()
        self.connectivity_combo.addItems(("4-neighbor", "8-neighbor"))
        self.connectivity_combo.setCurrentIndex(1)
        self.connectivity_label = QLabel(tr("inspector_connectivity"))
        detect_layout.addWidget(self.connectivity_label, 6, 0)
        detect_layout.addWidget(self.connectivity_combo, 6, 1)
        self.include_transparent_checkbox = QCheckBox(tr("inspector_include_transparent"))
        detect_layout.addWidget(self.include_transparent_checkbox, 7, 0, 1, 2)
        self.magic_checkbox = QCheckBox(tr("inspector_magic_select"))
        self.magic_checkbox.toggled.connect(self.viewer.canvas.set_magic_select_enabled)
        detect_layout.addWidget(self.magic_checkbox, 8, 0, 1, 2)
        detect_buttons = QHBoxLayout()
        self.detect_button = QPushButton(tr("inspector_detect"))
        self.detect_button.clicked.connect(self._start_detection)
        self.clear_detect_button = QPushButton(tr("inspector_clear_boxes"))
        self.clear_detect_button.clicked.connect(self.viewer.canvas.clear_detected_regions)
        detect_buttons.addWidget(self.detect_button)
        detect_buttons.addWidget(self.clear_detect_button)
        detect_layout.addLayout(detect_buttons, 9, 0, 1, 2)
        self.detect_progress = QProgressBar()
        self.detect_progress.setRange(0, 100)
        self.detect_progress.setVisible(False)
        detect_layout.addWidget(self.detect_progress, 10, 0, 1, 2)
        self.content_layout.addWidget(self.detect_group)

        self.regions_group = QGroupBox(tr("inspector_saved_regions"))
        regions_layout = QVBoxLayout(self.regions_group)
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText(tr("inspector_notes"))
        self.notes_edit.setMaximumHeight(56)
        regions_layout.addWidget(self.notes_edit)
        self.regions_tree = QTreeWidget()
        self.regions_tree.setHeaderLabels(self._region_headers())
        self.regions_tree.setRootIsDecorated(False)
        self.regions_tree.setMinimumHeight(150)
        self.regions_tree.itemClicked.connect(self._activate_tree_item)
        regions_layout.addWidget(self.regions_tree)
        region_buttons = QGridLayout()
        self.add_region_button = self._action_button(tr("inspector_add"), self._add_region)
        self.rename_region_button = self._action_button(tr("inspector_rename"), self._rename_region)
        self.duplicate_region_button = self._action_button(tr("inspector_duplicate"), self._duplicate_region)
        self.remove_region_button = self._action_button(tr("inspector_remove"), self._remove_region)
        self.sort_region_button = self._action_button(tr("inspector_sort"), self._sort_regions)
        for index, button in enumerate((
            self.add_region_button,
            self.rename_region_button,
            self.duplicate_region_button,
            self.remove_region_button,
            self.sort_region_button,
        )):
            region_buttons.addWidget(button, index // 3, index % 3)
        regions_layout.addLayout(region_buttons)
        project_buttons = QGridLayout()
        self.save_project_button = self._action_button(tr("inspector_save_project"), self._save_project)
        self.load_project_button = self._action_button(tr("inspector_load_project"), self._load_project)
        self.export_region_button = self._action_button(tr("inspector_export_region"), self._export_selected_region)
        self.export_all_regions_button = self._action_button(tr("inspector_export_all_regions"), self._export_all_regions)
        for index, button in enumerate((
            self.save_project_button,
            self.load_project_button,
            self.export_region_button,
            self.export_all_regions_button,
        )):
            project_buttons.addWidget(button, index // 2, index % 2)
        regions_layout.addLayout(project_buttons)
        self.content_layout.addWidget(self.regions_group)
        self.content_layout.addStretch(1)

    def _connect_canvas(self) -> None:
        self.viewer.canvas.mouse_image_position_changed.connect(self._mouse_changed)
        self.viewer.canvas.selection_changed.connect(self._selection_changed)
        self.viewer.canvas.magic_select_requested.connect(self._magic_select)

    def _code_button(self, text: str, format_name: str) -> QPushButton:
        button = QPushButton(text)
        button.clicked.connect(lambda _checked=False, value=format_name: self.copy_format(value))
        return button

    @staticmethod
    def _option_spin(minimum: int, maximum: int, value: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        return spin

    @staticmethod
    def _action_button(text: str, callback) -> QPushButton:
        button = QPushButton(text)
        button.clicked.connect(callback)
        return button

    def set_pic(self, pic: Optional[Pic]) -> None:
        self.pic = pic
        self.project = RegionProject.for_pic(pic) if pic is not None else None
        self.project_path = f"{pic.file_path}.regions.json" if pic and pic.file_path else None
        if self.project_path and Path(self.project_path).is_file() and pic is not None:
            try:
                saved_project = RegionProject.load(self.project_path)
                if saved_project.matches_pic(pic):
                    self.project = saved_project
                else:
                    QMessageBox.warning(self, tr("warning"), tr("inspector_hash_mismatch"))
            except (OSError, ValueError, TypeError) as exc:
                QMessageBox.warning(self, tr("warning"), str(exc))
        self._refresh_regions()
        self.setEnabled(pic is not None)

    def refresh_pic_identity(self) -> None:
        """Refresh sidecar metadata after an explicit PIC save."""
        if self.pic is None:
            return
        old_source_name = self.project.source_name if self.project is not None else ""
        regions = list(self.project.regions) if self.project is not None else []
        self.project = RegionProject.for_pic(self.pic)
        self.project.regions = regions
        used_old_default = (
            self.project_path is not None
            and old_source_name
            and Path(self.project_path).name == f"{old_source_name}.regions.json"
        )
        if self.pic.file_path and (not self.project_path or used_old_default):
            self.project_path = f"{self.pic.file_path}.regions.json"

    def set_context(
        self,
        pic: Pic,
        image_index: int,
        pic_image: PicImage,
        image: Image.Image,
    ) -> None:
        self.pic = pic
        self.image_index = image_index
        self.pic_image = pic_image
        self.image = image if image.mode == "RGBA" else image.convert("RGBA")
        self._mask_cache.clear()
        self.image_info_label.setText(
            f"ID {image_index} (0-based) · {image.width} × {image.height} px\n"
            f"{pic_image.width} × {pic_image.height} sprites · "
            f"BG #{pic_image.bg_color[0]:02X}{pic_image.bg_color[1]:02X}{pic_image.bg_color[2]:02X}"
        )
        self._configure_selection_limits()
        self._selection_changed(self.viewer.canvas.selection)

    def _configure_selection_limits(self) -> None:
        if self.image is None:
            return
        self.coordinate_spins["X"].setMaximum(max(0, self.image.width - 1))
        self.coordinate_spins["Y"].setMaximum(max(0, self.image.height - 1))
        self.coordinate_spins["W"].setMaximum(self.image.width)
        self.coordinate_spins["H"].setMaximum(self.image.height)

    def _mouse_changed(self, data: Optional[dict]) -> None:
        if data is None or self.pic_image is None:
            self.mouse_info_label.setText("—")
            return
        x, y, color = data["x"], data["y"], data["color"]
        col, row = x // 32, y // 32
        index = row * self.pic_image.width + col
        rgba = tuple(color) if isinstance(color, tuple) else (color,)
        color_text = "RGBA" if len(rgba) == 4 else "RGB"
        self.mouse_info_label.setText(
            f"X={x} Y={y} · {color_text}{rgba}\n"
            f"sprite: col={col} row={row} index={index}"
        )

    def _selection_changed(self, rect: Optional[QRect]) -> None:
        self._syncing_selection = True
        try:
            if rect is None:
                self.selection_info_label.setText("—")
                self.sprite_info_label.setText("—")
                for key, value in (("X", 0), ("Y", 0), ("W", 1), ("H", 1)):
                    self.coordinate_spins[key].setValue(value)
                return
            values = (rect.x(), rect.y(), rect.width(), rect.height())
            for key, value in zip(("X", "Y", "W", "H"), values):
                self.coordinate_spins[key].setValue(value)
            self.selection_info_label.setText(
                f"X={rect.x()} Y={rect.y()} W={rect.width()} H={rect.height()}\n"
                f"Right={rect.x() + rect.width()} Bottom={rect.y() + rect.height()} (exclusive)"
            )
            if self.pic_image is not None:
                coverage = sprite_coverage(*values, self.pic_image.width)
                if coverage is not None:
                    indexes = ", ".join(map(str, coverage.indexes[:24]))
                    if len(coverage.indexes) > 24:
                        indexes += ", …"
                    self.sprite_info_label.setText(
                        f"cols {coverage.start_col}..{coverage.end_col} · "
                        f"rows {coverage.start_row}..{coverage.end_row}\n"
                        f"{coverage.columns} × {coverage.rows} · indexes: {indexes}"
                    )
        finally:
            self._syncing_selection = False

    def _spin_selection_changed(self) -> None:
        if self._syncing_selection or self.image is None:
            return
        x = min(self.coordinate_spins["X"].value(), self.image.width - 1)
        y = min(self.coordinate_spins["Y"].value(), self.image.height - 1)
        width = min(self.coordinate_spins["W"].value(), self.image.width - x)
        height = min(self.coordinate_spins["H"].value(), self.image.height - y)
        self.viewer.canvas.set_selection(QRect(x, y, max(1, width), max(1, height)))

    def _apply_overlays(self) -> None:
        self.viewer.canvas.set_overlay_options(
            sprite_grid=self.sprite_grid_checkbox.isChecked(),
            pixel_grid=self.pixel_grid_checkbox.isChecked(),
            rulers=self.rulers_checkbox.isChecked(),
            coordinates=self.coordinates_checkbox.isChecked(),
        )

    def toggle_sprite_grid(self) -> None:
        self.sprite_grid_checkbox.toggle()

    def toggle_pixel_grid(self) -> None:
        self.pixel_grid_checkbox.toggle()

    def _current_region(self) -> Optional[AtlasRegion]:
        rect = self.viewer.canvas.selection
        if rect is None or self.pic_image is None or self.image_index < 0:
            return None
        return AtlasRegion(
            name=sanitize_cpp_identifier(self.name_edit.text()),
            image_index=self.image_index,
            x=rect.x(),
            y=rect.y(),
            width=rect.width(),
            height=rect.height(),
            image_width=self.pic_image.pixel_width,
            image_height=self.pic_image.pixel_height,
            notes=self.notes_edit.toPlainText().strip(),
        )

    def copy_format(self, format_name: str) -> None:
        region = self._current_region()
        if region is None:
            QMessageBox.warning(self, tr("warning"), tr("inspector_select_first"))
            return
        generators = {
            "rect": rect_text,
            "constants": cpp_constants,
            "struct": cpp_struct,
            "json": json_text,
            "csv": csv_text,
        }
        if format_name == "draw":
            text = draw_picture_call(
                region,
                self.image_expression_edit.text().strip() or "GUI_UI_IMAGE",
                self.renderer_expression_edit.text().strip() or "renderer",
            )
        else:
            text = generators[format_name](region)
        QApplication.clipboard().setText(text)

    def _detection_options(self) -> DetectionOptions:
        return DetectionOptions(
            tolerance=self.tolerance_spin.value(),
            minimum_width=self.minimum_width_spin.value(),
            minimum_height=self.minimum_height_spin.value(),
            minimum_area=self.minimum_area_spin.value(),
            merge_distance=self.merge_distance_spin.value(),
            include_transparent=self.include_transparent_checkbox.isChecked(),
            connectivity=4 if self.connectivity_combo.currentIndex() == 0 else 8,
        )

    def _start_detection(self) -> None:
        if self.image is None or self.pic_image is None or self._detection_thread is not None:
            return
        self.detect_button.setEnabled(False)
        self.detect_progress.setValue(0)
        self.detect_progress.setVisible(True)
        thread = QThread(self)
        worker = DetectionWorker(self.image.copy(), self.pic_image.bg_color, self._detection_options())
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self.detect_progress.setValue)
        worker.finished.connect(self._detection_finished)
        worker.failed.connect(self._detection_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.cancelled.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        worker.cancelled.connect(worker.deleteLater)
        thread.finished.connect(self._detection_cleanup)
        thread.finished.connect(thread.deleteLater)
        self._detection_thread = thread
        self._detection_worker = worker
        self._detection_image_index = self.image_index
        thread.start()

    def _detection_finished(self, regions: list[tuple[int, int, int, int]]) -> None:
        if self._detection_image_index == self.image_index:
            self.viewer.canvas.set_detected_regions(regions)
        self.detect_progress.setValue(100)

    def _detection_failed(self, message: str) -> None:
        QMessageBox.critical(self, tr("error"), message)

    def _detection_cleanup(self) -> None:
        self._detection_thread = None
        self._detection_worker = None
        self._detection_image_index = -1
        self.detect_button.setEnabled(True)
        self.detect_progress.setVisible(False)

    def shutdown(self) -> None:
        """Stop a background detector before the window is destroyed."""
        if self._detection_thread is None:
            return
        self._detection_thread.requestInterruption()
        self._detection_thread.quit()
        self._detection_thread.wait(5000)

    def _magic_select(self, x: int, y: int) -> None:
        if self.image is None or self.pic_image is None:
            return
        key = (
            self.image_index,
            self.tolerance_spin.value(),
            self.include_transparent_checkbox.isChecked(),
        )
        mask = self._mask_cache.get(key)
        if mask is None:
            mask = foreground_mask(
                self.image,
                self.pic_image.bg_color,
                self.tolerance_spin.value(),
                self.include_transparent_checkbox.isChecked(),
            )
            self._mask_cache[key] = mask
        box = component_at(
            mask,
            x,
            y,
            4 if self.connectivity_combo.currentIndex() == 0 else 8,
        )
        if box is None:
            return
        bx, by, width, height = box
        margin = self.margin_spin.value()
        left = min(max(bx - margin, 0), self.image.width - 1)
        top = min(max(by - margin, 0), self.image.height - 1)
        right = min(max(bx + width + margin, left + 1), self.image.width)
        bottom = min(max(by + height + margin, top + 1), self.image.height)
        self.viewer.canvas.set_selection(QRect(left, top, right - left, bottom - top))

    def _add_region(self) -> None:
        region = self._current_region()
        if region is None or self.project is None:
            QMessageBox.warning(self, tr("warning"), tr("inspector_select_first"))
            return
        self.project.regions.append(region)
        self._refresh_regions()

    def _selected_region_index(self) -> Optional[int]:
        item = self.regions_tree.currentItem()
        if item is None:
            return None
        value = item.data(0, 256)
        return int(value) if value is not None else None

    def _rename_region(self) -> None:
        index = self._selected_region_index()
        if index is None or self.project is None:
            return
        region = self.project.regions[index]
        new_name = sanitize_cpp_identifier(self.name_edit.text())
        region.name = new_name
        region.notes = self.notes_edit.toPlainText().strip()
        self._refresh_regions()

    def _duplicate_region(self) -> None:
        index = self._selected_region_index()
        if index is None or self.project is None:
            return
        region = self.project.regions[index]
        duplicate = AtlasRegion.from_dict(region.to_dict())
        duplicate.name = f"{region.name}_COPY"
        self.project.regions.insert(index + 1, duplicate)
        self._refresh_regions()

    def _remove_region(self) -> None:
        index = self._selected_region_index()
        if index is None or self.project is None:
            return
        del self.project.regions[index]
        self._refresh_regions()

    def _sort_regions(self) -> None:
        if self.project is None:
            return
        self.project.regions.sort(key=lambda region: (region.image_index, region.name, region.y, region.x))
        self._refresh_regions()

    def _refresh_regions(self) -> None:
        self.regions_tree.clear()
        if self.project is None:
            return
        for index, region in enumerate(self.project.regions):
            item = QTreeWidgetItem((
                region.name,
                str(region.image_index),
                str(region.x),
                str(region.y),
                str(region.width),
                str(region.height),
            ))
            item.setData(0, 256, index)
            item.setToolTip(0, region.notes)
            self.regions_tree.addTopLevelItem(item)
        for column in range(6):
            self.regions_tree.resizeColumnToContents(column)

    def _activate_tree_item(self, item: QTreeWidgetItem, _column: int = 0) -> None:
        if self.project is None:
            return
        index = int(item.data(0, 256))
        region = self.project.regions[index]
        self.name_edit.setText(region.name)
        self.notes_edit.setPlainText(region.notes)
        self.region_activated.emit(region)

    def _save_project(self) -> None:
        if self.project is None:
            return
        suggested = self.project_path or "Tibia.pic.regions.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self, tr("inspector_save_project"), suggested, "JSON (*.json)"
        )
        if not file_path:
            return
        try:
            self.project.save(file_path)
        except OSError as exc:
            QMessageBox.critical(self, tr("error"), str(exc))
            return
        self.project_path = file_path

    def _load_project(self) -> None:
        if self.pic is None:
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, tr("inspector_load_project"), "", "JSON (*.json)"
        )
        if not file_path:
            return
        try:
            project = RegionProject.load(file_path)
        except (OSError, ValueError, TypeError) as exc:
            QMessageBox.critical(self, tr("error"), str(exc))
            return
        if not project.matches_pic(self.pic):
            QMessageBox.warning(self, tr("warning"), tr("inspector_hash_mismatch"))
            return
        self.project = project
        self.project_path = file_path
        self._refresh_regions()

    @staticmethod
    def _safe_file_name(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_.") or "REGION"

    def _export_selected_region(self) -> None:
        region = self._current_region()
        if region is None or self.image is None:
            QMessageBox.warning(self, tr("warning"), tr("inspector_select_first"))
            return
        suggested = (
            f"image_{region.image_index}_{self._safe_file_name(region.name)}_"
            f"{region.x}_{region.y}_{region.width}x{region.height}.png"
        )
        file_path, _ = QFileDialog.getSaveFileName(
            self, tr("inspector_export_region"), suggested, tr("png_files")
        )
        if file_path:
            try:
                self._crop_region(self.image, region).save(file_path, "PNG")
            except OSError as exc:
                QMessageBox.critical(self, tr("error"), str(exc))

    def _export_all_regions(self) -> None:
        if self.pic is None or self.project is None or not self.project.regions:
            return
        folder = QFileDialog.getExistingDirectory(self, tr("select_folder"))
        if not folder:
            return
        try:
            for region in self.project.regions:
                if not (0 <= region.image_index < len(self.pic.images)):
                    continue
                source = self.pic.images[region.image_index]._cached_image
                if source is None:
                    continue
                file_name = (
                    f"image_{region.image_index}_{self._safe_file_name(region.name)}_"
                    f"{region.x}_{region.y}_{region.width}x{region.height}.png"
                )
                self._crop_region(source, region).save(str(Path(folder) / file_name), "PNG")
        except OSError as exc:
            QMessageBox.critical(self, tr("error"), str(exc))

    @staticmethod
    def _crop_region(image: Image.Image, region: AtlasRegion) -> Image.Image:
        return image.crop((region.x, region.y, region.right, region.bottom))

    def retranslate_ui(self) -> None:
        """Update the main Inspector labels after a language change."""
        self.info_group.setTitle(tr("inspector_info"))
        self.selection_group.setTitle(tr("inspector_selection"))
        self.overlay_group.setTitle(tr("inspector_overlays"))
        self.code_group.setTitle(tr("inspector_code"))
        self.detect_group.setTitle(tr("inspector_detection"))
        self.regions_group.setTitle(tr("inspector_saved_regions"))
        self.clear_button.setText(tr("inspector_clear"))
        self.full_button.setText(tr("inspector_full_image"))
        snap_index = self.snap_combo.currentIndex()
        self.snap_combo.blockSignals(True)
        self.snap_combo.clear()
        self.snap_combo.addItems((tr("inspector_snap_pixel"), tr("inspector_snap_grid")))
        self.snap_combo.setCurrentIndex(snap_index)
        self.snap_combo.blockSignals(False)
        self.sprite_grid_checkbox.setText(tr("inspector_sprite_grid"))
        self.pixel_grid_checkbox.setText(tr("inspector_pixel_grid"))
        self.rulers_checkbox.setText(tr("inspector_rulers"))
        self.coordinates_checkbox.setText(tr("inspector_coordinates"))
        self.magic_checkbox.setText(tr("inspector_magic_select"))
        self.detect_button.setText(tr("inspector_detect"))
        self.clear_detect_button.setText(tr("inspector_clear_boxes"))
        self.copy_rect_button.setText(tr("inspector_copy_rect"))
        self.copy_constants_button.setText(tr("inspector_copy_cpp"))
        self.copy_struct_button.setText(tr("inspector_copy_struct"))
        self.copy_draw_button.setText(tr("inspector_copy_draw"))
        self.copy_json_button.setText(tr("inspector_copy_json"))
        self.copy_csv_button.setText(tr("inspector_copy_csv"))
        self.add_region_button.setText(tr("inspector_add"))
        self.rename_region_button.setText(tr("inspector_rename"))
        self.duplicate_region_button.setText(tr("inspector_duplicate"))
        self.remove_region_button.setText(tr("inspector_remove"))
        self.sort_region_button.setText(tr("inspector_sort"))
        self.save_project_button.setText(tr("inspector_save_project"))
        self.load_project_button.setText(tr("inspector_load_project"))
        self.export_region_button.setText(tr("inspector_export_region"))
        self.export_all_regions_button.setText(tr("inspector_export_all_regions"))
        self.notes_edit.setPlaceholderText(tr("inspector_notes"))
        for field, key in (
            (self.name_edit, "inspector_constant_name"),
            (self.image_expression_edit, "inspector_image_expression"),
            (self.renderer_expression_edit, "inspector_renderer_expression"),
        ):
            label = self.code_form.labelForField(field)
            if label is not None:
                label.setText(tr(key))
        for field, key in (
            (self.image_info_label, "inspector_image"),
            (self.mouse_info_label, "inspector_mouse"),
            (self.selection_info_label, "inspector_selection"),
            (self.sprite_info_label, "inspector_sprites"),
        ):
            label = self.info_form.labelForField(field)
            if label is not None:
                label.setText(tr(key))
        for key, label in self.detect_labels.items():
            label.setText(tr(key))
        self.connectivity_label.setText(tr("inspector_connectivity"))
        self.include_transparent_checkbox.setText(tr("inspector_include_transparent"))
        self.regions_tree.setHeaderLabels(self._region_headers())

    @staticmethod
    def _region_headers() -> tuple[str, ...]:
        return (
            tr("inspector_region_name"),
            tr("inspector_region_image"),
            "X",
            "Y",
            "W",
            "H",
        )
