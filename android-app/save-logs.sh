#!/bin/bash

# HITSZ AutoNet Android - Save Logs to File
# Captures logs for later analysis

FILENAME="hitsz_autonet_debug_$(date +%Y%m%d_%H%M%S).log"

echo "💾 Saving logs to: $FILENAME"
echo ""
echo "Capturing for 2 minutes (or press Ctrl+C to stop early)..."
echo ""

# Capture logs with timeout
timeout 120 adb logcat | grep -E "LoginManager|NetworkMonitorService|NetworkChecker" > "$FILENAME"

if [ -f "$FILENAME" ]; then
    LINES=$(wc -l < "$FILENAME")
    SIZE=$(ls -lh "$FILENAME" | awk '{print $5}')
    
    echo ""
    echo "✓ Logs saved!"
    echo "  File: $FILENAME"
    echo "  Lines: $LINES"
    echo "  Size: $SIZE"
    echo ""
    echo "You can view the file with: less $FILENAME"
else
    echo "❌ Failed to save logs"
fi
