#!/bin/bash

echo "🔄 Testing Login Fix..."
echo ""
echo "Stopping app and clearing logs..."

adb shell am force-stop com.hitsz.autonet
adb logcat -c

sleep 1

echo ""
echo "✅ Ready!"
echo ""
echo "📱 NOW: On your phone, open HITSZ AutoNet and tap 'Start Monitoring'"
echo ""
echo "⏳ Waiting 5 seconds for you to start..."
sleep 5

echo ""
echo "📋 Showing logs - Look for:"
echo "   ✅ 'Page loaded successfully'"
echo "   ✅ 'Dynamic content should be ready'"
echo "   ✅ 'hasUsernameField:true, hasPasswordField:true'"
echo "   ✅ 'Login submit result: SUBMITTED'"
echo "   ✅ '✓ Login successful!'"
echo ""
echo "=========================================="
echo ""

adb logcat | grep -E "LoginManager|NetworkMonitorService|NetworkChecker"
