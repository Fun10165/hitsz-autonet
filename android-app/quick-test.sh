#!/bin/bash

# Quick test script - Start service and immediately show logs

echo "🔄 Starting fresh test..."
echo ""

# Stop app
echo "Stopping app..."
adb shell am force-stop com.hitsz.autonet

# Clear logs
echo "Clearing logs..."
adb logcat -c

echo ""
echo "=========================================="
echo "NOW: Open HITSZ AutoNet on your phone and tap 'Start Monitoring'"
echo "=========================================="
echo ""
echo "Waiting 3 seconds for you to start the service..."
sleep 3

echo ""
echo "📋 Showing logs (Press Ctrl+C to stop):"
echo "=========================================="
echo ""

# Show logs
adb logcat | grep -E "LoginManager|NetworkMonitorService|NetworkChecker"
