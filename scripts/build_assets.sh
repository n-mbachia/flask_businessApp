#!/bin/bash

# Ensure we're in the project root
dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$dir/.." || exit 1

# Create necessary directories
mkdir -p app/static/dist/js/lib
mkdir -p app/static/dist/js/pages
mkdir -p app/static/dist/css

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing Node.js dependencies..."
    npm install
fi

# Build assets
echo "Building frontend assets..."

# Copy required files
cp -r app/static/js/pages/*.js app/static/dist/js/pages/
cp -r app/static/js/components/**/*.js app/static/dist/js/

# Minify and bundle JavaScript
echo "Bundling JavaScript..."
esbuild app/static/js/app.js \
    --bundle \
    --minify \
    --sourcemap \
    --target=es2015 \
    --outfile=app/static/dist/js/app.js

echo "Build complete!"

echo "Making scripts executable..."
chmod +x scripts/build_assets.sh
chmod +x restructure_static.sh
