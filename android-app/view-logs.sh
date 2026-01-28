#!/bin/bash

# HITSZ AutoNet Android - Log Viewer Script
# This script displays filtered logs from the app for debugging

echo "📱 HITSZ AutoNet - Debug Log Viewer"
echo "===================================="
echo ""
echo "Showing logs for: LoginManager, NetworkMonitorService, NetworkChecker"
echo "Press Ctrl+C to stop"
echo ""
echo "Waiting for device..."

# Check if device is connected
if ! adb devices | grep -q "device$"; then
    echo "❌ No device connected!"
    echo ""
    echo "Please connect your Android device via USB and:"
    echo "1. Enable USB debugging in Developer Options"
    echo "2. Accept the USB debugging prompt on your phone"
    exit 1
fi

echo "✓ Device connected"
echo ""
echo "--- Log Output ---"
echo ""

# Use grep for cross-shell compatibility
adb logcat | grep -E "LoginManager|NetworkMonitorService|NetworkChecker"
