#!/usr/bin/env python3
"""
Build script for PhotoTidy
Creates a standalone Windows executable using PyInstaller
"""

import subprocess
import sys
import shutil
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
ASSETS_DIR = PROJECT_ROOT / "assets"
ICON_PATH = ASSETS_DIR / "icon.png"

def check_pyinstaller():
    """Check if PyInstaller is installed, install if not."""
    try:
        import PyInstaller
        print(f"✓ PyInstaller {PyInstaller.__version__} found")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✓ PyInstaller installed")

def clean_build():
    """Clean previous build artifacts."""
    print("\nCleaning previous builds...")
    for folder in [DIST_DIR, BUILD_DIR]:
        if folder.exists():
            shutil.rmtree(folder)
            print(f"  Removed {folder}")
    print("✓ Clean complete")

def build_executable():
    """Build the executable using PyInstaller."""
    print("\nBuilding PhotoTidy executable...")
    
    # Hidden imports that PyInstaller might miss
    hidden_imports = [
        "PySide6.QtCore",
        "PySide6.QtGui", 
        "PySide6.QtWidgets",
        "PIL",
        "PIL.Image",
        "PIL.ExifTags",
        "pillow_heif",
        "rawpy",
        "exifread",
        "geopy",
        "geopy.geocoders",
    ]
    
    # Build the PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=PhotoTidy",
        "--windowed",  # No console window
        "--noconfirm",  # Overwrite without asking
        "--clean",  # Clean cache before building
        f"--icon={ICON_PATH}",
        f"--add-data={ASSETS_DIR};assets",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        f"--specpath={BUILD_DIR}",
    ]
    
    # Add hidden imports
    for imp in hidden_imports:
        cmd.append(f"--hidden-import={imp}")
    
    # Exclude unnecessary modules
    excludes = ["tkinter", "matplotlib", "numpy.testing", "scipy", "pandas"]
    for exc in excludes:
        cmd.append(f"--exclude-module={exc}")
    
    # Add the main script
    cmd.append(str(PROJECT_ROOT / "main.py"))
    
    print(f"  Command: {' '.join(cmd[:5])}...")
    
    # Run PyInstaller
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    
    if result.returncode == 0:
        print("✓ Build complete!")
        output_path = DIST_DIR / "PhotoTidy"
        print(f"\n📁 Executable location: {output_path}")
        print(f"   Main executable: {output_path / 'PhotoTidy.exe'}")
        return True
    else:
        print("✗ Build failed!")
        return False

def create_portable_zip():
    """Create a portable ZIP distribution."""
    print("\nCreating portable ZIP distribution...")
    output_folder = DIST_DIR / "PhotoTidy"
    
    if not output_folder.exists():
        print("✗ Build folder not found. Run build first.")
        return False
    
    zip_path = DIST_DIR / "PhotoTidy-portable"
    shutil.make_archive(str(zip_path), 'zip', DIST_DIR, "PhotoTidy")
    print(f"✓ Created: {zip_path}.zip")
    return True

def main():
    """Main build process."""
    print("=" * 50)
    print(" PhotoTidy Build Script")
    print("=" * 50)
    
    # Check requirements
    check_pyinstaller()
    
    # Clean previous builds
    clean_build()
    
    # Build executable
    if not build_executable():
        sys.exit(1)
    
    # Create portable ZIP
    create_portable_zip()
    
    print("\n" + "=" * 50)
    print(" Build Complete!")
    print("=" * 50)
    print("\nTo share PhotoTidy:")
    print("  1. Share the 'dist/PhotoTidy' folder, or")
    print("  2. Share the 'dist/PhotoTidy-portable.zip' file")
    print("\nUsers can run PhotoTidy.exe directly - no Python installation required!")

if __name__ == "__main__":
    main()
