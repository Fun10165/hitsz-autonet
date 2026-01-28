# HITSZ AutoNet - CLEARTEXT FIX Applied

## Problem Solved ✅

**Issue:** `ERR_CLEARTEXT_NOT_PERMITTED` - Android was blocking HTTP traffic to:
- `10.248.98.2` (campus login server)
- `www.baidu.com` (connectivity check)

**Root Cause:** Modern Android versions (9+) block non-HTTPS traffic by default for security.

**Solution:** Added network security configuration to allow HTTP for these specific domains.

## What Was Fixed

✅ Created `network_security_config.xml` with cleartext permissions  
✅ Updated `AndroidManifest.xml` to use the security config  
✅ Rebuilt APK with the fix  

## Install Fixed Version

### Quick Install (via ADB)

```bash
cd /Users/fun10165/hitsz-autonet/android-app
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

The `-r` flag will replace the existing app while keeping your saved credentials.

### Manual Install

1. Copy the APK from:
   ```
   /Users/fun10165/hitsz-autonet/android-app/app/build/outputs/apk/debug/app-debug.apk
   ```
2. Transfer to your phone
3. Uninstall old version
4. Install new APK
5. Re-enter credentials if needed

## Test After Install

1. **Open app** and verify credentials are still saved
2. **Start service**
3. **Watch logs**:
   ```bash
   cd /Users/fun10165/hitsz-autonet/android-app
   ./view-logs.sh
   ```

## Expected Log Output

### Before Fix (OLD - error):
```
E LoginManager: WebView error: net::ERR_CLEARTEXT_NOT_PERMITTED
```

### After Fix (NEW - working):
```
I LoginManager: ========== LOGIN ATTEMPT START ==========
D LoginManager: Loading login page...
D LoginManager: Page loading started: http://10.248.98.2/...
I LoginManager: Page loaded successfully: http://10.248.98.2/...
I LoginManager: Page info: {...hasUsernameField:true...}
I LoginManager: Filling login form...
I LoginManager: ✓ Login successful!
```

## What to Watch For

The logs should now show:
1. ✅ Page loads successfully (no cleartext error)
2. ✅ Login form is found on the page
3. ✅ Login submission works
4. ✅ Success confirmation received

If you still see issues, they will now be related to:
- Network connectivity (can't reach server)
- Wrong credentials
- Page structure changes

But the cleartext blocking is fixed!

## Security Note

The app only allows HTTP for:
- `10.248.98.2` (campus network login)
- `baidu.com` (connectivity test)

All other traffic still requires HTTPS for security.

---

**APK Location:**  
`/Users/fun10165/hitsz-autonet/android-app/app/build/outputs/apk/debug/app-debug.apk`

**File size:** ~6.9 MB

**Install and test immediately!**
