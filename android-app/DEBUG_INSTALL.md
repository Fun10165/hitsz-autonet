# HITSZ AutoNet Android - Debug Installation Guide

## New Build Available

A new debug build with **comprehensive logging** has been created to help diagnose login failures.

## What's Improved

✅ **Detailed step-by-step logging** of the entire login process  
✅ **WebView console output** - See JavaScript errors  
✅ **Page structure validation** - Verifies login form exists  
✅ **Network error detection** - Identifies connectivity issues  
✅ **Credential submission tracking** - Confirms form was filled  
✅ **Success verification** - Multiple checks for login status  

## Installation Steps

### 1. Transfer New APK to Phone

**Option A - Via ADB (if phone is connected):**
```bash
cd /Users/fun10165/hitsz-autonet/android-app
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

**Option B - Manual Transfer:**
1. Copy `app/build/outputs/apk/debug/app-debug.apk` to your phone
2. Install (you may need to uninstall the old version first)

### 2. Set Up Logging on Your Computer

Connect your phone via USB and run one of these:

**Option A - Use helper script (recommended):**
```bash
cd /Users/fun10165/hitsz-autonet/android-app
./view-logs.sh
```

**Option B - Manual command:**
```bash
adb logcat | grep -E "LoginManager|NetworkMonitorService|NetworkChecker"
```

**Option C - Clear old logs first:**
```bash
./clear-and-watch.sh
```

**Option D - Save logs to file:**
```bash
./save-logs.sh
```

Keep the terminal window open to see what's happening.

### 3. Test the App

1. Open HITSZ AutoNet on your phone
2. Verify credentials are saved
3. Start the monitoring service
4. Watch the logs on your computer

## What to Look For

### Successful Login Pattern:
```
LoginManager: ========== LOGIN ATTEMPT START ==========
LoginManager: Page loaded successfully
LoginManager: Page info: {...hasUsernameField:true...}
LoginManager: Filling login form...
LoginManager: Login submit result: SUBMITTED
LoginManager: ✓ Login successful!
```

### Common Failure Patterns:

**Cannot reach server:**
```
WebView error: code=-2, description=net::ERR_NAME_NOT_RESOLVED
```
→ **Fix:** Ensure phone is on HITSZ WiFi

**Login form not found:**
```
LoginManager: Login form not found on page!
```
→ **Fix:** Login page URL or structure changed

**Wrong credentials:**
```
LoginManager: ✗ Login failed - success marker not found
```
→ **Fix:** Verify username/password are correct

## Quick Diagnostics

```bash
# Check if phone can reach login server
adb shell ping -c 3 10.248.98.2

# Test connectivity to Baidu (for internet check)
adb shell ping -c 3 www.baidu.com

# Save logs to file for analysis
adb logcat -d -s LoginManager:* NetworkMonitorService:* > debug_output.txt
```

## Next Steps After Installing

1. **Clear old data** (optional): Settings → Apps → HITSZ AutoNet → Storage → Clear Data
2. **Re-enter credentials** in the app
3. **Start monitoring service**
4. **Watch logs** for detailed information
5. **Share log output** if you need help troubleshooting

## If Login Still Fails

The enhanced logs will tell us exactly what's going wrong:

1. **Network issue** - Can't reach `10.248.98.2`
2. **Page structure issue** - Login form elements missing
3. **Authentication issue** - Credentials rejected
4. **Timeout issue** - Login takes too long

See **DEBUG.md** for complete troubleshooting guide.

---

**Location of new APK:**  
`/Users/fun10165/hitsz-autonet/android-app/app/build/outputs/apk/debug/app-debug.apk`

**File size:** ~6.8 MB
