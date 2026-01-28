#!/bin/bash

# HITSZ AutoNet Android - Build Script for Mac
# This script sets the correct Java version and builds the APK

set -e

echo "🔨 Building HITSZ AutoNet Android App..."
echo ""

# Set JDK 17 (required for Android Gradle Plugin 8.5)
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export PATH="$JAVA_HOME/bin:$PATH"

# Set Android SDK location
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools

# Verify Java version
echo "✓ Using Java:"
java -version 2>&1 | head -1
echo ""

# Clean and build
echo "🧹 Cleaning previous builds..."
./gradlew clean --console=plain --quiet

echo "📦 Building debug APK..."
./gradlew assembleDebug --console=plain

# Check if build succeeded
if [ -f "app/build/outputs/apk/debug/app-debug.apk" ]; then
    echo ""
    echo "✅ Build successful!"
    echo ""
    echo "📱 APK Location:"
    echo "   $(pwd)/app/build/outputs/apk/debug/app-debug.apk"
    echo ""
    echo "📊 APK Size:"
    ls -lh app/build/outputs/apk/debug/app-debug.apk | awk '{print "   " $5}'
    echo ""
    echo "📲 To install on device:"
    echo "   adb install app/build/outputs/apk/debug/app-debug.apk"
    echo ""
else
    echo "❌ Build failed!"
    exit 1
fi
