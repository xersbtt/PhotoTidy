# Changelog

All notable changes to PhotoTidy will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-09

### Added
- **Photo Loading**
  - Support for standard formats (JPG, PNG, GIF, BMP, TIFF, WebP)
  - RAW file support (CR2, CR3, NEF, ARW, DNG, RAF, ORF, RW2)
  - HEIC/HEIF support for iPhone photos
  - Automatic thumbnail generation and caching
  - EXIF metadata extraction (date, GPS, camera info)

- **Sorting & Grouping**
  - Date-based sorting (by year, month, or day)
  - Location-based sorting with reverse geocoding
  - Camera-based sorting (by make/model)
  - Filter panel with drag-and-drop reordering
  - Ascending/descending sort order

- **View Modes**
  - Thumbnails view (large icons)
  - Tiles view (medium icons with metadata)
  - List view (compact rows)
  - Details view (table with columns)

- **Photo Management**
  - Batch rename with customizable patterns
  - Move/Copy operations with undo support
  - Lossless rotation (clockwise/counterclockwise)
  - Manual location tagging for photos without GPS

- **User Interface**
  - Dark theme
  - Collapsible photo groups
  - Full-size preview panel
  - Metadata panel with EXIF details
  - Keyboard shortcuts
  - Right-click context menu
  - Drag & drop folder/file support
  - Settings dialog
  - About dialog

### Technical
- Built with Python 3.10+ and PySide6
- Threaded photo loading for responsiveness
- Geocoding cache to reduce API calls
- macOS resource fork file filtering
