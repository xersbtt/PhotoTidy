# PhotoTidy

![PhotoTidy Banner](assets/banner.png)

A modern photo organization tool for sorting, grouping, and managing your photo library.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![PySide6](https://img.shields.io/badge/PySide6-6.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Features

### 📁 Smart Photo Organization
- **Date Sorting** - Group photos by year, month, or day
- **Location Sorting** - Automatic GPS-based grouping with reverse geocoding
- **Camera Sorting** - Organize by camera make/model
- **Manual Location Tagging** - Tag photos without GPS data

### 🎨 Multiple View Modes
- **Thumbnails** - Large preview icons
- **Tiles** - Medium icons with metadata
- **List** - Compact rows
- **Details** - Table view with columns

### 🛠️ Photo Management
- **Batch Rename** - Custom patterns (date, location, sequence)
- **Move/Copy** - Organize into folders with undo support
- **Rotate** - Lossless EXIF-based rotation
- **Preview** - Full-size preview with metadata panel

### 📷 Format Support
- **Standard**: JPG, PNG, GIF, BMP, TIFF, WebP
- **RAW**: CR2, CR3, NEF, ARW, DNG, RAF, ORF, RW2
- **HEIC/HEIF**: iPhone photos

## Installation

### Requirements
- Python 3.10 or higher
- Windows 10/11 (primary), Linux/macOS (experimental)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/xersbtt/PhotoTidy.git
cd PhotoTidy

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## Usage

### Opening Photos
- Click **📁 Open Folder** or press `Ctrl+O`
- **Drag & drop** a folder or images onto the window

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Open folder |
| `Ctrl+A` | Select all |
| `Ctrl+D` | Deselect all |
| `Ctrl+Z` | Undo |
| `Ctrl+1/2/3/4` | Switch view mode |
| `F2` | Rename selected |
| `F5` | Refresh |
| `F1` | About |
| `Ctrl+,` | Settings |

### Right-Click Menu
Right-click any photo for quick actions:
- Open File / Show in Explorer
- Select/Deselect
- Rename / Set Location
- Delete

## Project Structure

```
PhotoTidy/
├── main.py              # Application entry point
├── config.py            # Configuration and constants
├── requirements.txt     # Python dependencies
├── core/                # Core functionality
│   ├── photo.py         # Photo data model
│   ├── metadata.py      # EXIF extraction
│   ├── thumbnail.py     # Thumbnail generation
│   ├── geocoding.py     # Reverse geocoding
│   └── operations.py    # File operations
├── sorting/             # Sorting strategies
│   ├── base.py          # Base strategy interface
│   ├── date_sorter.py   # Date-based sorting
│   ├── location_sorter.py
│   ├── camera_sorter.py
│   └── grouped.py       # Photo grouping
├── ui/                  # User interface
│   ├── main_window.py   # Main application window
│   ├── toolbar.py       # Toolbar with actions
│   ├── filter_panel.py  # Filter/sort controls
│   ├── group_widget.py  # Photo group display
│   └── ...
└── utils/               # Utilities
    ├── renamer.py       # Batch renaming
    └── rotate.py        # Image rotation
```

## Dependencies

- **PySide6** - Qt-based GUI framework
- **Pillow** - Image processing
- **pillow-heif** - HEIC/HEIF support
- **exifread** - EXIF metadata extraction
- **rawpy** - RAW file processing
- **geopy** - Reverse geocoding

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- [Nominatim](https://nominatim.org/) for geocoding services
- [Qt/PySide6](https://www.qt.io/) for the GUI framework
