#!/bin/bash

# NetworkEyes Plugin Build Script
# This script creates a tar.gz file ready for GitHub releases

PLUGIN_NAME="NetworkEyes"
VERSION="1.0.0"
BUILD_DIR="PluginBuild"
PLUGIN_DIR="$BUILD_DIR/$PLUGIN_NAME"
OUTPUT_DIR="releases"

echo "Building $PLUGIN_NAME v$VERSION..."

# Create releases directory
mkdir -p "$OUTPUT_DIR"

# Create the tar.gz file
cd "$BUILD_DIR"
tar -czf "../$OUTPUT_DIR/${PLUGIN_NAME}-v${VERSION}.tar.gz" "$PLUGIN_NAME"
cd ..

echo "✅ Plugin package created: $OUTPUT_DIR/${PLUGIN_NAME}-v${VERSION}.tar.gz"

# Show contents
echo ""
echo "📦 Package contents:"
tar -tzf "$OUTPUT_DIR/${PLUGIN_NAME}-v${VERSION}.tar.gz" | head -20

echo ""
echo "🚀 Ready for GitHub release!"
echo "Upload this file to: https://github.com/DJJones66/NetworkEyes/releases"