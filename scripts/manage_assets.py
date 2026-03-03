#!/usr/bin/env python3
"""
Static Asset Management Script

This script provides commands to manage static assets including:
- Building production assets
- Cleaning build artifacts
- Optimizing images
- Generating asset manifests
- Validating asset configuration
"""

import os
import sys
import json
import shutil
import hashlib
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent
STATIC_DIR = PROJECT_ROOT / 'app' / 'static'
CONFIG_DIR = PROJECT_ROOT / 'config'
CONFIG_FILE = CONFIG_DIR / 'static_assets.json'

# Ensure config directory exists
CONFIG_DIR.mkdir(exist_ok=True)

class AssetManager:
    def __init__(self):
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load the asset configuration from config.json"""
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Config file not found at {CONFIG_FILE}")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in config file at {CONFIG_FILE}")
            sys.exit(1)
    
    def clean(self):
        """Clean build artifacts and temporary files"""
        build_dirs = [
            STATIC_DIR / 'dist',
            STATIC_DIR / '.webassets-cache',
            STATIC_DIR / '.sass-cache'
        ]
        
        for dir_path in build_dirs:
            if dir_path.exists():
                print(f"Removing {dir_path}")
                shutil.rmtree(dir_path)
        
        print("Clean complete!")
    
    def build(self, env: str = 'production'):
        """Build static assets for the specified environment"""
        print(f"Building assets for {env} environment...")
        
        # Create necessary directories
        self._ensure_directories()
        
        # Process CSS
        self._process_css(env)
        
        # Process JavaScript
        self._process_js(env)
        
        # Process images
        if env == 'production':
            self._process_images()
        
        # Generate manifest
        self._generate_manifest(env)
        
        print("Build complete!")
    
    def _ensure_directories(self):
        """Ensure all required directories exist"""
        dirs = [
            STATIC_DIR / 'dist' / 'css',
            STATIC_DIR / 'dist' / 'js',
            STATIC_DIR / 'dist' / 'img',
            STATIC_DIR / 'dist' / 'fonts'
        ]
        
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def _process_css(self, env: str):
        """Process CSS files"""
        print("Processing CSS...")
        # TODO: Implement CSS processing with PostCSS, Autoprefixer, etc.
        # For now, just copy the files
        css_src = STATIC_DIR / 'css'
        css_dest = STATIC_DIR / 'dist' / 'css'
        
        if css_src.exists():
            self._copy_files(css_src, css_dest, '*.css')
    
    def _process_js(self, env: str):
        """Process JavaScript files"""
        print("Processing JavaScript...")
        # TODO: Implement JS bundling with webpack/rollup/esbuild
        # For now, just copy the files
        js_src = STATIC_DIR / 'js'
        js_dest = STATIC_DIR / 'dist' / 'js'
        
        if js_src.exists():
            self._copy_files(js_src, js_dest, '*.js')
    
    def _process_images(self):
        """Process and optimize images"""
        print("Processing images...")
        # TODO: Implement image optimization with Pillow
        # For now, just copy the files
        img_src = STATIC_DIR / 'img'
        img_dest = STATIC_DIR / 'dist' / 'img'
        
        if img_src.exists():
            self._copy_files(img_src, img_dest, '*.*')
    
    def _copy_files(self, src_dir: Path, dest_dir: Path, pattern: str):
        """Copy files matching pattern from src_dir to dest_dir"""
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        for src_file in src_dir.glob('**/' + pattern):
            if src_file.is_file():
                rel_path = src_file.relative_to(src_dir)
                dest_file = dest_dir / rel_path
                
                # Create parent directories if they don't exist
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                shutil.copy2(src_file, dest_file)
    
    def _generate_manifest(self, env: str):
        """Generate asset manifest with hashed filenames"""
        print("Generating asset manifest...")
        manifest = {}
        dist_dir = STATIC_DIR / 'dist'
        
        for file_path in dist_dir.glob('**/*'):
            if file_path.is_file():
                rel_path = str(file_path.relative_to(dist_dir))
                file_hash = self._get_file_hash(file_path)
                manifest[rel_path] = f"{rel_path}?v={file_hash}"
        
        # Save manifest
        manifest_path = dist_dir / 'manifest.json'
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of a file"""
        hash_md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()[:8]
    
    def validate(self):
        """Validate asset configuration and structure"""
        print("Validating asset configuration...")
        
        # Check required directories
        required_dirs = [
            'css',
            'js',
            'img',
            'fonts'
        ]
        
        for dir_name in required_dirs:
            dir_path = STATIC_DIR / dir_name
            if not dir_path.exists():
                print(f"Warning: Missing directory: {dir_path}")
        
        print("Validation complete!")


def main():
    parser = argparse.ArgumentParser(description='Manage static assets')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Build command
    build_parser = subparsers.add_parser('build', help='Build assets')
    build_parser.add_argument(
        '--env',
        choices=['development', 'production'],
        default='production',
        help='Build environment (default: production)'
    )
    
    # Clean command
    subparsers.add_parser('clean', help='Clean build artifacts')
    
    # Validate command
    subparsers.add_parser('validate', help='Validate asset configuration')
    
    args = parser.parse_args()
    manager = AssetManager()
    
    if args.command == 'build':
        manager.build(env=args.env)
    elif args.command == 'clean':
        manager.clean()
    elif args.command == 'validate':
        manager.validate()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
