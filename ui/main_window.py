"""
Main application window for Photo Sorter.
"""
from pathlib import Path
from typing import List, Optional
import sys
import logging

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QScrollArea, QFileDialog, QMessageBox, QProgressDialog, QApplication,
    QMenu
)
from PySide6.QtCore import Qt, QThread, Signal, QMimeData, QSettings
from PySide6.QtGui import QShortcut, QKeySequence, QDragEnterEvent, QDropEvent, QIcon

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import APP_NAME, APP_VERSION, ALL_SUPPORTED_EXTENSIONS, DEFAULT_LOCATION_FORMAT
from core.photo import Photo
from core.metadata import extract_metadata
from core.thumbnail import ThumbnailManager
from core.geocoding import GeocodingService
from core.operations import FileOperations
from utils.rotate import rotate_photos
from sorting.date_sorter import DateSorter
from sorting.location_sorter import LocationSorter
from sorting.camera_sorter import CameraSorter
from sorting.dynamic_sorter import DynamicCompoundSorter
from sorting.grouped import PhotoGrouper

from .toolbar import ToolBar
from .group_widget import GroupWidget
from .preview_panel import PreviewPanel
from .metadata_panel import MetadataPanel
from .rename_dialog import RenameDialog
from .filter_panel import FilterPanel
from .location_dialog import LocationDialog
from .settings_dialog import SettingsDialog
from .about_dialog import AboutDialog

logger = logging.getLogger(__name__)


class PhotoLoaderWorker(QThread):
    """Worker thread for loading photos."""
    progress = Signal(int, int)  # current, total
    photo_loaded = Signal(Photo)
    finished = Signal(list)  # list of Photo objects
    
    def __init__(self, folder_path: Path, thumbnail_manager: ThumbnailManager):
        super().__init__()
        self.folder_path = folder_path
        self.thumbnail_manager = thumbnail_manager
    
    def run(self):
        """Load all photos from the folder."""
        photos = []
        
        # Find all image files
        image_files = []
        for ext in ALL_SUPPORTED_EXTENSIONS:
            image_files.extend(self.folder_path.glob(f"*{ext}"))
            image_files.extend(self.folder_path.glob(f"*{ext.upper()}"))
        
        # Also search subdirectories
        for ext in ALL_SUPPORTED_EXTENSIONS:
            image_files.extend(self.folder_path.rglob(f"*{ext}"))
            image_files.extend(self.folder_path.rglob(f"*{ext.upper()}"))
        
        # Remove duplicates
        image_files = list(set(image_files))
        
        # Filter out macOS resource fork files (start with "._")
        image_files = [f for f in image_files if not f.name.startswith("._")]
        
        total = len(image_files)
        
        for i, file_path in enumerate(image_files):
            try:
                # Create photo object
                photo = Photo(path=file_path)
                
                # Extract metadata
                metadata = extract_metadata(file_path)
                photo.date_taken = metadata.get('date_taken')
                photo.gps_latitude = metadata.get('gps_latitude')
                photo.gps_longitude = metadata.get('gps_longitude')
                photo.camera_make = metadata.get('camera_make')
                photo.camera_model = metadata.get('camera_model')
                photo.width = metadata.get('width')
                photo.height = metadata.get('height')
                
                # Generate thumbnail
                thumb_path = self.thumbnail_manager.get_thumbnail(file_path)
                photo.thumbnail_path = thumb_path
                
                photos.append(photo)
                self.photo_loaded.emit(photo)
                
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")
            
            self.progress.emit(i + 1, total)
        
        self.finished.emit(photos)


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        
        # Initialize services
        self.thumbnail_manager = ThumbnailManager()
        self.geocoding_service = GeocodingService()
        self.file_operations = FileOperations()
        
        # Load location format from settings
        qsettings = QSettings('PhotoTidy', 'PhotoTidy')
        location_format = qsettings.value('location_format', DEFAULT_LOCATION_FORMAT, type=str)
        
        # Initialize individual sorters
        self.sorters = {
            'date': DateSorter(format_type=DateSorter.FORMAT_YEAR_MONTH_DAY),
            'location': LocationSorter(format_type=location_format, geocoding_service=self.geocoding_service),
            'camera': CameraSorter(),
        }
        
        # Dynamic compound sorter (combines active filters)
        self.dynamic_sorter = DynamicCompoundSorter()
        self.current_sorter = self.dynamic_sorter
        
        # Photo grouper
        self.grouper = PhotoGrouper()
        
        # UI state
        self._current_photo: Optional[Photo] = None
        self._group_widgets: List[GroupWidget] = []
        self._view_mode: str = "thumbnails"
        self._loader_worker: Optional[PhotoLoaderWorker] = None
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Set up the main window UI."""
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(1200, 800)
        
        # Set window icon
        icon_path = Path(__file__).parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Toolbar
        self.toolbar = ToolBar()
        main_layout.addWidget(self.toolbar)
        
        # Main content area with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: Filter panel
        self.filter_panel = FilterPanel()
        self.filter_panel.set_active_filters(['date'])  # Default: date filter
        splitter.addWidget(self.filter_panel)
        
        # Center: Photo grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #121212;
                border: none;
            }
        """)
        
        self.grid_container = QWidget()
        self.grid_layout = QVBoxLayout(self.grid_container)
        self.grid_layout.setContentsMargins(12, 12, 12, 12)
        self.grid_layout.setSpacing(12)
        self.grid_layout.addStretch()
        
        self.scroll_area.setWidget(self.grid_container)
        splitter.addWidget(self.scroll_area)
        
        # Right side: Preview and metadata
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(8)
        
        self.preview_panel = PreviewPanel()
        right_layout.addWidget(self.preview_panel, stretch=2)
        
        self.metadata_panel = MetadataPanel()
        right_layout.addWidget(self.metadata_panel, stretch=1)
        
        splitter.addWidget(right_panel)
        
        # Set splitter sizes (filter panel / photo grid / preview: 200/600/300)
        splitter.setSizes([200, 600, 300])
        
        main_layout.addWidget(splitter, stretch=1)
        
        # Initialize dynamic sorter with default filter
        self._update_sorter_from_filters(['date'])
        
        # Apply dark theme
        self._apply_theme()
    
    def _apply_theme(self):
        """Apply dark theme to the application."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
            }
            QWidget {
                background-color: #121212;
                color: #e0e0e0;
            }
            QScrollBar:vertical {
                background-color: #1a1a1a;
                width: 12px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background-color: #3a3a3a;
                min-height: 30px;
                border-radius: 6px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #4a4a4a;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QSplitter::handle {
                background-color: #333;
            }
        """)
    
    def _connect_signals(self):
        """Connect UI signals to handlers."""
        # Toolbar signals
        self.toolbar.open_folder_clicked.connect(self._open_folder)
        self.toolbar.rename_clicked.connect(self._rename_selected)
        self.toolbar.rotate_cw_clicked.connect(self._rotate_clockwise)
        self.toolbar.rotate_ccw_clicked.connect(self._rotate_counterclockwise)
        self.toolbar.set_location_clicked.connect(self._set_location)
        self.toolbar.move_clicked.connect(self._move_selected)
        self.toolbar.copy_clicked.connect(self._copy_selected)
        self.toolbar.undo_clicked.connect(self._undo_last)
        self.toolbar.select_all_clicked.connect(self._select_all)
        self.toolbar.deselect_all_clicked.connect(self._deselect_all)
        self.toolbar.open_files_clicked.connect(self._open_files)
        self.toolbar.add_folder_clicked.connect(self._add_folder)
        
        # Filter panel signals
        self.filter_panel.filters_changed.connect(self._on_filters_changed)
        self.filter_panel.sort_order_changed.connect(self._on_sort_order_changed)
        
        # View mode
        self.toolbar.view_mode_changed.connect(self._on_view_mode_changed)
        
        # Settings/About
        self.toolbar.settings_clicked.connect(self._show_settings)
        self.toolbar.about_clicked.connect(self._show_about)
        
        # Preview navigation
        self.preview_panel.navigate_previous.connect(self._navigate_previous)
        self.preview_panel.navigate_next.connect(self._navigate_next)
        
        # File operations
        self.file_operations.operation_completed.connect(self._on_operation_completed)
        
        # Keyboard shortcuts
        self._setup_shortcuts()
        
        # Drag and drop
        self._setup_drag_drop()
    
    def _setup_shortcuts(self):
        """Set up keyboard shortcuts."""
        # File operations
        QShortcut(QKeySequence("Ctrl+O"), self, self._open_folder)
        QShortcut(QKeySequence("Ctrl+A"), self, self._select_all)
        QShortcut(QKeySequence("Ctrl+D"), self, self._deselect_all)
        QShortcut(QKeySequence("Ctrl+Z"), self, self._undo_last)
        
        # View
        QShortcut(QKeySequence("F5"), self, self._refresh)
        QShortcut(QKeySequence("Ctrl+1"), self, lambda: self._set_view("thumbnails"))
        QShortcut(QKeySequence("Ctrl+2"), self, lambda: self._set_view("tiles"))
        QShortcut(QKeySequence("Ctrl+3"), self, lambda: self._set_view("list"))
        QShortcut(QKeySequence("Ctrl+4"), self, lambda: self._set_view("details"))
        
        # Actions
        QShortcut(QKeySequence("F2"), self, self._rename_selected)
        QShortcut(QKeySequence("Delete"), self, self._delete_selected)
        
        # Help
        QShortcut(QKeySequence("F1"), self, self._show_about)
        QShortcut(QKeySequence("Ctrl+,"), self, self._show_settings)
    
    def _setup_drag_drop(self):
        """Enable drag and drop for files and folders."""
        self.setAcceptDrops(True)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter - accept if it's files or folders."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop - load folder or add individual files."""
        urls = event.mimeData().urls()
        if not urls:
            return
        
        first_path = Path(urls[0].toLocalFile())
        
        if first_path.is_dir():
            # Dropped a folder - load it (replaces current view)
            self._load_from_path(first_path)
        else:
            # Dropped files - add only those files to current view
            dropped_files = [Path(url.toLocalFile()) for url in urls]
            self._add_individual_files(dropped_files)
    
    def _load_from_path(self, folder_path: Path, select_files: List[Path] = None):
        """Load photos from a path."""
        self._current_folder = folder_path
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION} - {folder_path}")
        
        # Clear existing
        self._clear_groups()
        self.grouper.clear()
        
        # Start loading
        self._loader_worker = PhotoLoaderWorker(folder_path, self.thumbnail_manager)
        self._loader_worker.progress.connect(self._on_load_progress)
        self._loader_worker.finished.connect(
            lambda photos: self._on_photos_loaded(photos, select_files)
        )
        self._loader_worker.start()
    
    def _set_view(self, mode: str):
        """Set view mode via keyboard."""
        self.toolbar._set_view_mode(mode)
    
    def _refresh(self):
        """Refresh current folder."""
        if hasattr(self, '_current_folder') and self._current_folder:
            self._load_from_path(self._current_folder)
    
    def _delete_selected(self):
        """Delete selected photos (move to recycle bin)."""
        selected = self.grouper.selected_photos
        if not selected:
            return
        
        reply = QMessageBox.warning(
            self,
            "Delete Photos",
            f"Move {len(selected)} photo(s) to Recycle Bin?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._delete_photos(selected)
    
    def _on_delete_photo(self, photo: Photo):
        """Handle delete request for a single photo from context menu."""
        reply = QMessageBox.warning(
            self,
            "Delete Photo",
            f"Move '{photo.filename}' to Recycle Bin?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._delete_photos([photo])
    
    def _delete_photos(self, photos: List[Photo]):
        """Delete photos by moving them to Recycle Bin."""
        try:
            from send2trash import send2trash
        except ImportError:
            QMessageBox.warning(self, "Missing Dependency", 
                "send2trash is required for delete. Install with: pip install send2trash")
            return
        
        deleted = 0
        errors = []
        for photo in photos:
            try:
                send2trash(str(photo.path))
                deleted += 1
            except Exception as e:
                errors.append(f"{photo.filename}: {e}")
        
        # Remove from view
        self._remove_photos_from_view(photos)
        
        # Show result
        msg = f"Moved {deleted} photo(s) to Recycle Bin."
        if errors:
            msg += f"\n\n{len(errors)} errors:\n" + "\n".join(errors[:5])
        QMessageBox.information(self, "Delete Complete", msg)
    
    def _on_remove_photo(self, photo: Photo):
        """Handle remove from view request for a single photo."""
        self._remove_photos_from_view([photo])
    
    def _remove_photos_from_view(self, photos: List[Photo]):
        """Remove photos from the current view without deleting files."""
        # Remove from grouper's photo list
        for photo in photos:
            if photo in self.grouper.photos:
                self.grouper.photos.remove(photo)
        
        # Rebuild the UI
        if self.grouper.total_count > 0:
            self.grouper.set_strategy(self.current_sorter)
            self._rebuild_groups()
        else:
            self._clear_groups()
        
        self._update_selection_count()
    
    def _show_about(self):
        """Show about dialog."""
        dialog = AboutDialog(self)
        dialog.exec()
    
    def _show_settings(self):
        """Show settings dialog."""
        dialog = SettingsDialog(self)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()
    
    def _on_settings_changed(self, settings: dict):
        """Handle settings changes."""
        # Update location format
        location_format = settings.get('location_format', DEFAULT_LOCATION_FORMAT)
        self.sorters['location'].format_type = location_format
        
        # If we have photos loaded, rebuild to apply the new format
        if self.grouper.total_count > 0:
            # Clear cached location names so they get re-resolved with new format
            for photo in self.grouper.photos:
                if photo.has_location:
                    photo.location_name = None
            self.grouper.set_strategy(self.current_sorter)
            self._rebuild_groups()
    
    def _open_folder(self):
        """Open folder selection dialog."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Photo Folder",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder:
            self._load_photos(Path(folder))
    
    def _open_files(self):
        """Open file selection dialog for individual images."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Photos",
            "",
            "Images (*.jpg *.jpeg *.png *.heic *.heif *.tiff *.tif *.webp *.bmp *.gif *.cr2 *.cr3 *.nef *.arw *.dng *.orf *.rw2 *.raf *.srw *.pef *.raw);;All Files (*)"
        )
        
        if files:
            file_paths = [Path(f) for f in files]
            self._add_individual_files(file_paths)
    
    def _add_folder(self):
        """Add folder contents to current view (cumulative)."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Add Folder (append to current view)",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder:
            self._append_folder(Path(folder))
    
    def _add_individual_files(self, file_paths: List[Path]):
        """Add individual files to the current view."""
        if not file_paths:
            return
        
        # Show progress
        self.progress = QProgressDialog("Loading photos...", "Cancel", 0, len(file_paths), self)
        self.progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress.setMinimumDuration(200)
        
        new_photos = []
        for i, file_path in enumerate(file_paths):
            if not file_path.suffix.lower() in ALL_SUPPORTED_EXTENSIONS:
                continue
            try:
                photo = Photo(path=file_path)
                metadata = extract_metadata(file_path)
                photo.date_taken = metadata.get('date_taken')
                photo.gps_latitude = metadata.get('gps_latitude')
                photo.gps_longitude = metadata.get('gps_longitude')
                photo.camera_make = metadata.get('camera_make')
                photo.camera_model = metadata.get('camera_model')
                photo.width = metadata.get('width')
                photo.height = metadata.get('height')
                photo.thumbnail_path = self.thumbnail_manager.get_thumbnail(file_path)
                new_photos.append(photo)
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")
            
            self.progress.setValue(i + 1)
        
        self.progress.close()
        
        if not new_photos:
            QMessageBox.information(self, "No Photos", "No supported photos found in the selection.")
            return
        
        # Append to existing or set new
        if self.grouper.total_count > 0:
            self.grouper.add_photos(new_photos)
        else:
            self.grouper.set_photos(new_photos)
        
        self.grouper.set_strategy(self.current_sorter)
        self._rebuild_groups()
        self._update_selection_count()
    
    def _append_folder(self, folder_path: Path):
        """Append folder contents to current view."""
        # Find all images in folder
        image_files = []
        for ext in ALL_SUPPORTED_EXTENSIONS:
            image_files.extend(folder_path.rglob(f"*{ext}"))
            image_files.extend(folder_path.rglob(f"*{ext.upper()}"))
        
        image_files = list(set(image_files))
        image_files = [f for f in image_files if not f.name.startswith("._")]
        
        if not image_files:
            QMessageBox.information(self, "No Photos", f"No supported photos found in {folder_path}")
            return
        
        self._add_individual_files(image_files)
    
    def _load_photos(self, folder_path: Path):
        """Load photos from the selected folder."""
        # Clear existing photos
        self._clear_groups()
        self.grouper.clear()
        
        # Show progress dialog
        self.progress = QProgressDialog("Loading photos...", "Cancel", 0, 100, self)
        self.progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress.setMinimumDuration(500)
        
        # Create and start worker thread
        self._loader_worker = PhotoLoaderWorker(folder_path, self.thumbnail_manager)
        self._loader_worker.progress.connect(self._on_load_progress)
        self._loader_worker.finished.connect(self._on_photos_loaded)
        self._loader_worker.start()
    
    def _on_load_progress(self, current: int, total: int):
        """Handle loading progress update."""
        if hasattr(self, 'progress'):
            self.progress.setMaximum(total)
            self.progress.setValue(current)
            self.progress.setLabelText(f"Loading photos... ({current}/{total})")
    
    def _on_photos_loaded(self, photos: List[Photo], select_files: List[Path] = None):
        """Handle photos loaded."""
        if hasattr(self, 'progress'):
            self.progress.close()
        
        if not photos:
            QMessageBox.information(self, "No Photos", "No supported photos found in the selected folder.")
            return
        
        # Set photos and apply current sorting
        self.grouper.set_photos(photos)
        self.grouper.set_strategy(self.current_sorter)
        
        # Rebuild the groups UI
        self._rebuild_groups()
        
        # Select dropped files if any
        if select_files:
            for photo in photos:
                if photo.path in select_files:
                    photo.is_selected = True
        
        # Update selection count
        self._update_selection_count()
    
    def _rebuild_groups(self):
        """Rebuild the group widgets."""
        self._clear_groups()
        
        for group in self.grouper.groups:
            group_widget = GroupWidget(group, view_mode=self._view_mode)
            group_widget.add_photos(self.thumbnail_manager)
            group_widget.photo_clicked.connect(self._on_photo_clicked)
            group_widget.photo_double_clicked.connect(self._on_photo_double_clicked)
            group_widget.selection_changed.connect(self._update_selection_count)
            group_widget.delete_requested.connect(self._on_delete_photo)
            group_widget.remove_requested.connect(self._on_remove_photo)
            
            self._group_widgets.append(group_widget)
            self.grid_layout.insertWidget(self.grid_layout.count() - 1, group_widget)
    
    def _clear_groups(self):
        """Clear all group widgets."""
        for widget in self._group_widgets:
            self.grid_layout.removeWidget(widget)
            widget.deleteLater()
        self._group_widgets.clear()
    
    def _on_filters_changed(self, filter_ids: list):
        """Handle filter panel changes."""
        self._update_sorter_from_filters(filter_ids)
        
        if self.grouper.total_count > 0:
            self.grouper.set_strategy(self.current_sorter)
            self._rebuild_groups()
    
    def _update_sorter_from_filters(self, filter_ids: list):
        """Update the dynamic sorter with the selected filters."""
        strategies = []
        for filter_id in filter_ids:
            if filter_id in self.sorters:
                strategies.append(self.sorters[filter_id])
        
        self.dynamic_sorter.set_strategies(strategies)
        self.current_sorter = self.dynamic_sorter
    
    def _on_sort_order_changed(self, ascending: bool):
        """Handle sort order change (ascending/descending)."""
        # Update all sorters' ascending setting
        for sorter in self.sorters.values():
            if hasattr(sorter, 'ascending'):
                sorter.ascending = ascending
        
        self.dynamic_sorter.set_ascending(ascending)
        
        # Update grouper's sort order for photos within groups
        self.grouper.set_sort_ascending(ascending)
        
        # Rebuild groups if we have photos
        if self.grouper.total_count > 0:
            self.grouper.set_strategy(self.current_sorter)
            self._rebuild_groups()
    
    def _on_view_mode_changed(self, mode: str):
        """Handle view mode change."""
        self._view_mode = mode
        if self.grouper.total_count > 0:
            self._rebuild_groups()
    
    def _on_photo_clicked(self, photo: Photo):
        """Handle photo click."""
        self._current_photo = photo
        self.preview_panel.set_photo(photo)
        self.metadata_panel.set_photo(photo)
        
        # Update highlight
        for gw in self._group_widgets:
            gw.highlight_photo(photo)
        
        self._update_navigation_buttons()
    
    def _on_photo_double_clicked(self, photo: Photo):
        """Handle photo double click - toggle selection."""
        photo.is_selected = not photo.is_selected
        self._update_selection_count()
        
        # Update the thumbnail widget
        for gw in self._group_widgets:
            for tw in gw._thumbnail_widgets:
                if tw.photo == photo:
                    tw.update_selection_display()
    
    def _update_selection_count(self):
        """Update the selection count in toolbar."""
        selected = self.grouper.selected_count
        total = self.grouper.total_count
        self.toolbar.update_selection_count(selected, total)
        self.toolbar.set_undo_enabled(self.file_operations.can_undo())
        
        # Update group count labels
        for gw in self._group_widgets:
            gw.update_count_label()
    
    def _select_all(self):
        """Select all photos."""
        self.grouper.select_all()
        for gw in self._group_widgets:
            gw._update_thumbnail_selections()
            gw._update_select_button()
        self._update_selection_count()
    
    def _deselect_all(self):
        """Deselect all photos."""
        self.grouper.deselect_all()
        for gw in self._group_widgets:
            gw._update_thumbnail_selections()
            gw._update_select_button()
        self._update_selection_count()
    
    def _navigate_previous(self):
        """Navigate to previous photo in current group."""
        if not self._current_photo:
            return
        
        group = self.grouper.get_group_for_photo(self._current_photo)
        if group:
            idx = group.photos.index(self._current_photo)
            if idx > 0:
                self._on_photo_clicked(group.photos[idx - 1])
    
    def _navigate_next(self):
        """Navigate to next photo in current group."""
        if not self._current_photo:
            return
        
        group = self.grouper.get_group_for_photo(self._current_photo)
        if group:
            idx = group.photos.index(self._current_photo)
            if idx < len(group.photos) - 1:
                self._on_photo_clicked(group.photos[idx + 1])
    
    def _update_navigation_buttons(self):
        """Update navigation button states."""
        if not self._current_photo:
            self.preview_panel.set_navigation_enabled(False, False)
            return
        
        group = self.grouper.get_group_for_photo(self._current_photo)
        if group:
            idx = group.photos.index(self._current_photo)
            self.preview_panel.set_navigation_enabled(idx > 0, idx < len(group.photos) - 1)
    
    def _move_selected(self):
        """Move selected photos to destination."""
        self._transfer_selected("move")
    
    def _copy_selected(self):
        """Copy selected photos to destination."""
        self._transfer_selected("copy")
    
    def _transfer_selected(self, operation: str):
        """Transfer selected photos (move or copy)."""
        selected = self.grouper.selected_photos
        if not selected:
            return
        
        # Get destination folder
        dest_folder = QFileDialog.getExistingDirectory(
            self,
            f"Select Destination Folder for {operation.title()}",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if not dest_folder:
            return
        
        dest_path = Path(dest_folder)
        
        # Build file destinations based on current sorting
        file_destinations = []
        for photo in selected:
            group = self.grouper.get_group_for_photo(photo)
            if group:
                folder_name = group.folder_name
                dest_file = dest_path / folder_name / photo.filename
            else:
                dest_file = dest_path / photo.filename
            
            file_destinations.append((photo.path, dest_file))
        
        # Confirm
        reply = QMessageBox.question(
            self,
            f"Confirm {operation.title()}",
            f"Are you sure you want to {operation} {len(file_destinations)} photos to:\n{dest_folder}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Perform operation
        if operation == "move":
            self.file_operations.move_files(file_destinations)
        else:
            self.file_operations.copy_files(file_destinations)
    
    def _on_operation_completed(self, batch):
        """Handle file operation completion."""
        msg = f"Completed: {batch.successful_count} successful"
        if batch.failed_count > 0:
            msg += f", {batch.failed_count} failed"
        
        QMessageBox.information(self, "Operation Complete", msg)
        self.toolbar.set_undo_enabled(self.file_operations.can_undo())
    
    def _undo_last(self):
        """Undo the last operation."""
        if self.file_operations.can_undo():
            result = self.file_operations.undo_last()
            if result:
                QMessageBox.information(
                    self, 
                    "Undo Complete", 
                    f"Undid: {result.description}"
                )
            self.toolbar.set_undo_enabled(self.file_operations.can_undo())
    
    def _rename_selected(self):
        """Open the rename dialog for selected photos."""
        selected = self.grouper.selected_photos
        if not selected:
            return
        
        dialog = RenameDialog(selected, self)
        if dialog.exec():
            # Refresh the display after rename
            self._rebuild_groups()
            self._update_selection_count()
    
    def _set_location(self):
        """Open the location dialog for selected photos."""
        selected = self.grouper.selected_photos
        if not selected:
            return
        
        dialog = LocationDialog(selected, self.geocoding_service, self)
        if dialog.exec():
            # Refresh the display after location change
            self._rebuild_groups()
            self._update_selection_count()
    
    def _rotate_clockwise(self):
        """Rotate selected photos clockwise."""
        self._rotate_photos(clockwise=True)
    
    def _rotate_counterclockwise(self):
        """Rotate selected photos counterclockwise."""
        self._rotate_photos(clockwise=False)
    
    def _rotate_photos(self, clockwise: bool):
        """Rotate selected photos."""
        selected = self.grouper.selected_photos
        if not selected:
            return
        
        paths = [p.path for p in selected]
        direction = "clockwise" if clockwise else "counterclockwise"
        
        success, skipped, errors = rotate_photos(paths, clockwise=clockwise)
        
        # Refresh thumbnails for rotated photos
        for photo in selected:
            if photo.path.suffix.lower() not in {'.cr2', '.cr3', '.nef', '.arw', '.dng', '.orf', '.rw2', '.raf', '.srw', '.pef', '.raw'}:
                # Regenerate thumbnail
                photo.thumbnail_path = self.thumbnail_manager.get_thumbnail(photo.path)
        
        # Rebuild UI
        self._rebuild_groups()
        
        # Show result
        msg = f"Rotated {success} photos {direction}."
        if skipped > 0:
            msg += f"\nSkipped {skipped} RAW files (not supported)."
        if errors:
            msg += f"\n{len(errors)} errors occurred."
        
        QMessageBox.information(self, "Rotation Complete", msg)
