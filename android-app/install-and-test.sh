#!/bin/bash

# HITSZ AutoNet - Complete Fix and Test Script
# This script installs the fixed APK and helps you test it

set -e

echo "🔧 HITSZ AutoNet - Install Fixed Version"
echo "=========================================="
echo ""

# Check device connection
echo "1️⃣ Checking device connection..."
if ! adb devices | grep -q "device$"; then
    echo "❌ No device connected!"
    echo ""
    echo "Please:"
    echo "  1. Connect your phone via USB"
    echo "  2. Enable USB debugging"
    echo "  3. Accept the USB debugging prompt on your phone"
    exit 1
fi

DEVICE=$(adb devices | grep "device$" | awk '{print $1}')
echo "✓ Device connected: $DEVICE"
echo ""

# Check if app is installed
echo "2️⃣ Checking current app status..."
if adb shell pm list packages | grep -q "com.hitsz.autonet"; then
    echo "✓ App currently installed"
    
    # Check if service is running
    if adb shell ps | grep -q "com.hitsz.autonet"; then
        echo "⚠️  Service is running - stopping it..."
        adb shell am force-stop com.hitsz.autonet
        sleep 1
        echo "✓ Service stopped"
    fi
else
    echo "✓ Fresh installation (no previous version)"
fi
echo ""

# Install new APK
echo "3️⃣ Installing fixed APK..."
APK_PATH="/Users/fun10165/hitsz-autonet/android-app/app/build/outputs/apk/debug/app-debug.apk"

if [ ! -f "$APK_PATH" ]; then
    echo "❌ APK not found at: $APK_PATH"
    echo "Please run: ./build.sh first"
    exit 1
fi

echo "APK path: $APK_PATH"
echo "Installing..."

if adb install -r "$APK_PATH" 2>&1 | grep -q "Success"; then
    echo "✓ Installation successful!"
else
    echo "⚠️  Installation may have issues, but continuing..."
fi
echo ""

# Clear old logs
echo "4️⃣ Clearing old logs..."
adb logcat -c
echo "✓ Logs cleared"
echo ""

# Instructions
echo "=========================================="
echo "✅ Installation Complete!"
echo "=========================================="
echo ""
echo "📱 Now on your phone:"
echo "   1. Open 'HITSZ AutoNet' app"
echo "   2. Verify your credentials are saved"
echo "   3. Tap 'Start Monitoring'"
echo ""
echo "💻 On this computer, run:"
echo "   ./view-logs.sh"
echo ""
echo "   Or manually:"
echo "   adb logcat | grep -E \"LoginManager|NetworkMonitorService|NetworkChecker\""
echo ""
echo "🔍 What to look for:"
echo "   ✅ 'Page loaded successfully' (not CLEARTEXT error)"
echo "   ✅ 'Page info: {...hasUsernameField:true...}'"
echo "   ✅ '✓ Login successful!'"
echo ""
echo "Press Enter to start watching logs now..."
read

echo ""
echo "📋 Starting log viewer (Press Ctrl+C to stop)..."
echo "================================================"
echo ""

# Start log viewer
adb logcat | grep -E "LoginManager|NetworkMonitorService|NetworkChecker"
