#!/usr/bin/env python3
"""
Build script for creating Monopoly executable.

This script uses PyInstaller to create a standalone executable
that can be distributed without requiring Python to be installed.

Requirements:
    pip install pyinstaller

Usage:
    python build_app.py                  # Build with defaults
    python build_app.py --onefile        # Single executable file
    python build_app.py --clean          # Clean build artifacts first
    python build_app.py --debug          # Include console for debugging

Output:
    dist/Monopoly.exe    (Windows)
    dist/Monopoly.app    (macOS)
    dist/Monopoly        (Linux)
"""

import subprocess
import sys
import os
import shutil
import argparse
from pathlib import Path


def check_pyinstaller():
    """Check if PyInstaller is installed."""
    try:
        import PyInstaller
        print(f"[OK] PyInstaller {PyInstaller.__version__} found")
        return True
    except ImportError:
        print("[X] PyInstaller not found")
        print("\nInstall it with:")
        print("  pip install pyinstaller")
        return False


def check_dependencies():
    """Check if required dependencies are installed."""
    required = ['PyQt6', 'qasync', 'websockets']
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg)
            print(f"[OK] {pkg} found")
        except ImportError:
            print(f"[X] {pkg} missing")
            missing.append(pkg)
    
    if missing:
        print(f"\nInstall missing packages:")
        print(f"  pip install {' '.join(missing)}")
        return False
    return True


def clean_build():
    """Remove previous build artifacts."""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    files_to_clean = ['Monopoly.spec']
    
    for d in dirs_to_clean:
        if os.path.exists(d):
            print(f"Removing {d}/")
            shutil.rmtree(d)
    
    for f in files_to_clean:
        if os.path.exists(f):
            print(f"Removing {f}")
            os.remove(f)


def build_executable(onefile=True, debug=False):
    """Build the executable using PyInstaller."""
    
    # Base PyInstaller command
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name=Monopoly',
        '--noconfirm',  # Replace output without asking
    ]
    
    # Single file or folder?
    # Note: On macOS, --onefile + --windowed is deprecated (a .app bundle is inherently a folder)
    # PyInstaller 7.0 will make this an error, so we use --onedir on macOS for .app bundles
    if sys.platform == 'darwin' and not debug:
        # macOS .app bundle requires onedir
        cmd.append('--onedir')
        print("Building as .app bundle (macOS requires onedir for windowed apps)")
    elif onefile:
        cmd.append('--onefile')
        print("Building as single file (slower startup, easier distribution)")
    else:
        cmd.append('--onedir')
        print("Building as folder (faster startup, more files)")
    
    # GUI or console?
    if debug:
        cmd.append('--console')
        print("Console window will be shown (debug mode)")
    else:
        cmd.append('--windowed')
        print("Console window hidden (release mode)")
    
    # Add data files (shared constants, etc.)
    # PyInstaller needs to know about non-Python files
    cmd.extend([
        '--add-data', f'shared{os.pathsep}shared',
        '--add-data', f'client{os.pathsep}client',
    ])
    
    # Hidden imports that PyInstaller might miss
    cmd.extend([
        '--hidden-import=PyQt6.QtCore',
        '--hidden-import=PyQt6.QtGui',
        '--hidden-import=PyQt6.QtWidgets',
        '--hidden-import=qasync',
        '--hidden-import=websockets',
        '--hidden-import=websockets.client',
        '--hidden-import=asyncio',
        '--hidden-import=json',
        '--hidden-import=uuid',
    ])
    
    # Exclude conflicting/unnecessary packages
    cmd.extend([
        '--exclude-module=PyQt5',        # We use PyQt6, not PyQt5
        '--exclude-module=PySide2',      # Exclude other Qt bindings
        '--exclude-module=PySide6',      # Exclude other Qt bindings
        '--exclude-module=tkinter',      # Not used
        '--exclude-module=matplotlib',   # Not used
        '--exclude-module=numpy',        # Not used
        '--exclude-module=pandas',       # Not used
        '--exclude-module=scipy',        # Not used
        '--exclude-module=PIL',          # Not used
        '--exclude-module=cv2',          # Not used
        '--exclude-module=test',         # Test modules
        '--exclude-module=unittest',     # Test modules
    ])
    
    # Platform-specific options
    if sys.platform == 'darwin':
        # macOS: Create .app bundle
        cmd.extend([
            '--osx-bundle-identifier=com.monopoly.game',
        ])
    elif sys.platform == 'win32':
        # Windows: Could add icon here
        # cmd.extend(['--icon=assets/icon.ico'])
        pass
    
    # The main script to package
    cmd.append('client/main.py')
    
    print("\nRunning PyInstaller...")
    print(f"Command: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd)
    
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Build Monopoly executable")
    parser.add_argument('--onefile', action='store_true', default=True,
                        help='Create single executable (default)')
    parser.add_argument('--onedir', action='store_true',
                        help='Create folder with executable')
    parser.add_argument('--clean', action='store_true',
                        help='Clean build artifacts before building')
    parser.add_argument('--debug', action='store_true',
                        help='Show console window for debugging')
    parser.add_argument('--check-only', action='store_true',
                        help='Only check dependencies, do not build')
    args = parser.parse_args()
    
    print("=" * 60)
    print(" MONOPOLY BUILD SCRIPT")
    print("=" * 60)
    
    # Change to script directory
    os.chdir(Path(__file__).parent)
    print(f"\nWorking directory: {os.getcwd()}")
    
    # Check dependencies
    print("\n--- Checking Dependencies ---\n")
    if not check_pyinstaller():
        return 1
    if not check_dependencies():
        return 1
    
    if args.check_only:
        print("\n[OK] All dependencies satisfied")
        return 0
    
    # Clean if requested
    if args.clean:
        print("\n--- Cleaning Build Artifacts ---\n")
        clean_build()
    
    # Build
    print("\n--- Building Executable ---\n")
    onefile = not args.onedir
    success = build_executable(onefile=onefile, debug=args.debug)
    
    if success:
        print("\n" + "=" * 60)
        print(" BUILD SUCCESSFUL")
        print("=" * 60)
        
        if onefile:
            if sys.platform == 'win32':
                print("\nOutput: dist/Monopoly.exe")
            elif sys.platform == 'darwin':
                print("\nOutput: dist/Monopoly.app")
            else:
                print("\nOutput: dist/Monopoly")
        else:
            print("\nOutput: dist/Monopoly/")
        
        print("\nTo run:")
        if sys.platform == 'win32':
            print("  dist\\Monopoly.exe")
        elif sys.platform == 'darwin':
            print("  open dist/Monopoly.app")
            print("  # or: dist/Monopoly.app/Contents/MacOS/Monopoly")
        else:
            print("  ./dist/Monopoly")
        
        return 0
    else:
        print("\n" + "=" * 60)
        print(" BUILD FAILED")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    sys.exit(main())

