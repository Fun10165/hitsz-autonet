# Building HITSZ AutoNet Android App

This guide explains how to build the Android app on a Mac without Android Studio.

## Prerequisites Check

The following are already installed on your Mac:
- ✅ Java (OpenJDK 25.0.1)
- ✅ Gradle (via Homebrew)
- ✅ Android Command Line Tools (via Homebrew)

## Environment Setup

### 1. Set Android Environment Variables

Add these to your `~/.zshrc` or `~/.bash_profile`:

```bash
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin
export PATH=$PATH:$ANDROID_HOME/platform-tools
```

Then reload:
```bash
source ~/.zshrc  # or source ~/.bash_profile
```

### 2. Accept Android SDK Licenses

```bash
sdkmanager --licenses
```

Press 'y' to accept all licenses.

### 3. Install Required Android SDK Components

```bash
# Install platform tools
sdkmanager "platform-tools"

# Install Android SDK Platform 34 (for compileSdk 34)
sdkmanager "platforms;android-34"

# Install Build Tools
sdkmanager "build-tools;34.0.0"

# Verify installations
sdkmanager --list_installed
```

## Building the App

### Navigate to Project

```bash
cd /Users/fun10165/hitsz-autonet/android-app
```

### Build Commands

```bash
# Make gradlew executable (first time only)
chmod +x gradlew

# Clean build
./gradlew clean

# Build debug APK
./gradlew assembleDebug

# Build release APK (unsigned)
./gradlew assembleRelease
```

### Build Output Locations

- Debug APK: `app/build/outputs/apk/debug/app-debug.apk`
- Release APK: `app/build/outputs/apk/release/app-release-unsigned.apk`

### Common Build Issues

**Issue**: "SDK location not found"
```bash
# Create local.properties file
echo "sdk.dir=/opt/homebrew/share/android-commandlinetools" > local.properties
```

**Issue**: "Failed to find target with hash string 'android-34'"
```bash
# Install the platform
sdkmanager "platforms;android-34"
```

**Issue**: "Could not determine java version"
```bash
# Check Java version
java -version  # Should show OpenJDK 25 or compatible
```

## Installing on Android Device

### Via USB (with ADB)

1. Enable Developer Options on your Android device
2. Enable USB Debugging
3. Connect device via USB
4. Install ADB if not already:
   ```bash
   sdkmanager "platform-tools"
   ```
5. Install the APK:
   ```bash
   adb install app/build/outputs/apk/debug/app-debug.apk
   ```

### Via File Transfer

1. Build the APK (see above)
2. Transfer APK to your device (email, cloud, USB)
3. On device: Enable "Install from Unknown Sources"
4. Open APK file on device and tap Install

## Signing Release APK (Optional)

For production release, sign the APK:

```bash
# Generate keystore (first time only)
keytool -genkey -v -keystore hitsz-autonet.keystore -alias hitsz -keyalg RSA -keysize 2048 -validity 10000

# Sign the release APK
jarsigner -verbose -sigalg SHA256withRSA -digestalg SHA-256 -keystore hitsz-autonet.keystore app/build/outputs/apk/release/app-release-unsigned.apk hitsz

# Optimize with zipalign (optional but recommended)
zipalign -v 4 app/build/outputs/apk/release/app-release-unsigned.apk app/build/outputs/apk/release/app-release.apk
```

## Gradle Wrapper

The project includes a Gradle wrapper, so you don't need to install Gradle globally. The wrapper downloads the correct Gradle version automatically.

If `gradlew` is missing, create it:

```bash
gradle wrapper --gradle-version 8.2
```

## Troubleshooting

### Build is slow
- First build downloads many dependencies, this is normal
- Subsequent builds will be much faster
- Enable Gradle daemon in `gradle.properties` (already configured)

### Out of memory errors
```bash
# Increase Gradle JVM memory in gradle.properties
org.gradle.jvmargs=-Xmx4096m -Dfile.encoding=UTF-8
```

### Permission denied on gradlew
```bash
chmod +x gradlew
```

## Next Steps

After successful build:
1. Install the APK on your Android device
2. Open the app and configure credentials
3. Start the monitoring service
4. Check the main README.md for usage instructions
