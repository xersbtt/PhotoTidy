# Changelog

All notable changes to PhotoTidy will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0]

### Added
- **Batch Processing Pipeline** - Chain multiple operations in a single workflow:
  - Add steps: Resize, Rotate, Rename, Text Watermark, Image Watermark, WebP
  - Reorder steps with ↑↓ buttons
  - Live preview of the entire pipeline
  - Output saved to "Batch Processed/" folder
- **Mass Resize** - Batch resize photos by percentage, max dimension, or exact size
- **Text Watermark** - Add custom text watermarks with system fonts, color, and opacity
- **Image Watermark** - Use any image file as a watermark (logos, signatures)
- **WebP Conversion** - Convert photos to WebP format for optimized web uploads
  - Quality slider for lossy compression
  - Lossless compression option
  - Shows estimated file size savings

### Technical
- New `core/batch_pipeline.py` module for chaining operations
- New `core/image_processing.py` module for image transformations
- All processed images save to subfolders (`Batch Processed/`, `Resized/`, `Watermarked/`, `WebP/`)
- EXIF metadata preserved in all output files

### Improved
- **Toolbar Layout** - Reorganized with dropdown menus (File, Edit, Organize) for cleaner UI

## [1.1.0]

### Added
- **Open Files** - Open individual image files instead of entire folders
- **Add Folder** - Append folder contents to current view (cumulative loading)
- **Configurable Location Format** - Choose from 5 display formats:
  - Suburb/Locality only
  - City only
  - Suburb + Country
  - City + Country
  - Full (City, State, Country)
- **Image Dimensions** - Photo Details panel now shows width × height
- **Delete to Recycle Bin** - Delete photos safely (can restore from Recycle Bin)
- **Remove from View** - Hide photos from app without deleting files
- **Settings Persistence** - All settings now save and restore across sessions

### Improved
- **Smart Drag & Drop** - Dropping files adds only those files; dropping folders replaces view
- **Suburb Support** - Australian suburbs now correctly detected in location data

### Fixed
- **GPS Extraction Bug** - Fixed issue where GPS coordinates weren't extracted from some photos (IFD pointer handling)
- **Drag & Drop Files** - Fixed TypeError when dropping individual files

### Dependencies
- Added `send2trash>=1.8.0` for Recycle Bin support

## [1.0.0] 

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
