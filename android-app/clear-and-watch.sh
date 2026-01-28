#!/bin/bash

# HITSZ AutoNet Android - Clear Logs and Start Fresh
# Clears old logs and starts watching new ones

echo "🧹 Clearing old logs..."
adb logcat -c

echo "✓ Logs cleared"
echo ""
echo "📱 Starting fresh log capture..."
echo "Press Ctrl+C to stop"
echo ""

# Watch new logs only
adb logcat | grep -E "LoginManager|NetworkMonitorService|NetworkChecker"
