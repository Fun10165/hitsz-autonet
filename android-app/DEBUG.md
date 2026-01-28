# HITSZ AutoNet Android - Debugging Guide

## Problem: "Login failed - Retrying" notifications

This guide helps you debug login failures on the Android app.

## Quick Diagnosis Steps

### Step 1: View Logs via ADB

Connect your phone to your computer and run:

**Recommended - Use helper scripts:**
```bash
cd /Users/fun10165/hitsz-autonet/android-app

# View logs in real-time
./view-logs.sh

# OR clear old logs first, then watch
./clear-and-watch.sh

# OR save logs to a file
./save-logs.sh
```

**Alternative - Manual command:**
```bash
# View all app logs in real-time
adb logcat | grep -E "LoginManager|NetworkMonitorService|NetworkChecker"

# Save logs to a file
adb logcat | grep -E "LoginManager|NetworkMonitorService|NetworkChecker" > app_debug.log
```

**What to look for:**
- `LoginManager: ========== LOGIN ATTEMPT START ==========` - Login started
- `LoginManager: Page info:` - Shows if login page loaded correctly
- `LoginManager: Login form not found on page!` - Login page structure issue
- `LoginManager: ✓ Login successful!` or `✗ Login failed` - Final result
- `WebView error:` - Network connectivity issues

### Step 2: Common Issues & Solutions

#### Issue 1: Cannot reach login server (10.248.98.2)

**Symptoms in logs:**
```
WebView error: code=-2, description=net::ERR_NAME_NOT_RESOLVED
```

**Solution:**
- Ensure your phone is connected to HITSZ campus WiFi
- The login server `10.248.98.2` must be accessible from your device
- Try opening `http://10.248.98.2/srun_portal_pc?ac_id=1&theme=basic2` in Chrome browser on your phone
- If it doesn't load, you may not be on the correct network

#### Issue 2: Wrong credentials

**Symptoms in logs:**
```
LoginManager: ✗ Login failed - success marker not found
```

**Solution:**
- Verify username and password are correct
- Re-save credentials in the app
- Try logging in manually via browser first to confirm credentials work

#### Issue 3: Login page structure changed

**Symptoms in logs:**
```
LoginManager: Login form not found on page!
hasUsernameField: false
```

**Solution:**
- The campus login page HTML structure may have changed
- Contact developer for app update
- Check if login URL is still correct

#### Issue 4: Network check always fails

**Symptoms:**
- App keeps trying to login even when already online
- Logs show `Internet unavailable` repeatedly

**Check NetworkChecker logs:**
```bash
adb logcat -s NetworkChecker:*
```

Look for:
- `Connectivity check failed: Redirected to ...` - Still behind captive portal
- `Connectivity check error: ...` - Network request failed

#### Issue 5: WebView cleartext traffic blocked

**Symptoms in logs:**
```
WebView error: ... Cleartext HTTP traffic not permitted
```

**This is already fixed in the app manifest, but if you see this:**
- The app needs `android:usesCleartextTraffic="true"` in manifest
- HTTP (not HTTPS) is required for campus login servers

## Step 3: Manual Test Login

Add a manual login button to test without waiting:

1. Open the app
2. Make sure credentials are saved
3. Stop the service
4. Check logs while testing:
   ```bash
   adb logcat -c  # Clear old logs
   adb logcat -s LoginManager:* | grep -E "START|END|Login|success|failed"
   ```
5. Start the service and watch the logs

## Step 4: Test Network Connectivity

Test if your device can reach the login server:

```bash
# From your computer, check if phone can reach server
adb shell ping -c 3 10.248.98.2

# Check if DNS resolves
adb shell ping -c 3 www.baidu.com
```

## Step 5: Enhanced Debug Build

The updated `LoginManager.kt` now includes:

✅ **WebView console logging** - See JavaScript errors  
✅ **Detailed page info** - URL, title, form elements  
✅ **Step-by-step logging** - Each stage of login process  
✅ **HTTP error logging** - Network issues  
✅ **Credential validation** - Form submission confirmation  

### Rebuild with Enhanced Logging

```bash
cd /Users/fun10165/hitsz-autonet/android-app
./build.sh
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

## Step 6: Export and Share Logs

If you need help from the developer:

```bash
# Capture comprehensive logs
adb logcat -d > full_debug.log

# Filter relevant logs
grep -E "LoginManager|NetworkMonitor|NetworkChecker" full_debug.log > filtered_debug.log

# Share filtered_debug.log
```

## Understanding Log Output

### Successful Login

```
LoginManager: ========== LOGIN ATTEMPT START ==========
LoginManager: Username: 2021******
LoginManager: Login URL: http://10.248.98.2/srun_portal_pc?ac_id=1&theme=basic2
LoginManager: Page loaded successfully: http://10.248.98.2/srun_portal_pc?ac_id=1&theme=basic2
LoginManager: Page info: {"url":"...","hasUsernameField":true,"hasPasswordField":true,...}
LoginManager: Filling login form...
LoginManager: Login submit result: {"status":"SUBMITTED","message":"Login form submitted"}
LoginManager: Waiting 3000ms for login to process...
LoginManager: Verifying login result...
LoginManager: Verification result: {...,"page":"success",...}
LoginManager: ✓ Login successful!
LoginManager: ========== LOGIN ATTEMPT END ==========
```

### Failed Login (Form Not Found)

```
LoginManager: ========== LOGIN ATTEMPT START ==========
LoginManager: Page loaded successfully: http://10.248.98.2/...
LoginManager: Page info: {"hasUsernameField":false,...}
LoginManager: Login form not found on page!
LoginManager: Page might be redirecting or login URL is incorrect
LoginManager: ========== LOGIN ATTEMPT END ==========
```

### Failed Login (Wrong Credentials)

```
LoginManager: Login submit result: {"status":"SUBMITTED",...}
LoginManager: Verifying login result...
LoginManager: Verification result: {...} (no "page":"success")
LoginManager: ✗ Login failed - success marker not found
LoginManager: Check if credentials are correct and login page URL is accessible
```

## Network Troubleshooting

### Test connectivity from app perspective:

```bash
# Check if app can access internet
adb shell am start -a android.intent.action.VIEW -d "http://www.baidu.com"

# Check if app can access login server
adb shell am start -a android.intent.action.VIEW -d "http://10.248.98.2"
```

## Advanced: Enable WebView Debugging

If you need to inspect the login page in Chrome DevTools:

1. Add to `AndroidManifest.xml`:
   ```xml
   android:debuggable="true"
   ```

2. In `LoginManager.kt`, add:
   ```kotlin
   WebView.setWebContentsDebuggingEnabled(true)
   ```

3. Rebuild and install
4. Open Chrome on your computer: `chrome://inspect`
5. Find your device and click "inspect" on the WebView

## Still Having Issues?

1. **Verify network access**: Try manual login via phone browser
2. **Check app permissions**: Settings → Apps → HITSZ AutoNet → Permissions
3. **Clear app data**: Settings → Apps → HITSZ AutoNet → Storage → Clear Data
4. **Reinstall app**: Uninstall and install fresh APK
5. **Share logs**: Run diagnostics and share filtered logs

## Quick Command Reference

```bash
# Real-time filtered logs (use helper scripts)
cd android-app && ./view-logs.sh

# Clear and watch fresh logs
./clear-and-watch.sh

# Save logs to timestamped file
./save-logs.sh

# Manual commands (alternative)
adb logcat | grep -E "LoginManager|NetworkMonitorService|NetworkChecker"
adb logcat -c  # Clear logs
adb logcat | grep -E "LoginManager|NetworkMonitorService|NetworkChecker" > debug.log

# Reinstall debug build
cd android-app && ./build.sh && adb install -r app/build/outputs/apk/debug/app-debug.apk

# Restart app service
adb shell am force-stop com.hitsz.autonet
# Then manually start service in app
```
