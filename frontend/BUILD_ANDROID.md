# Building Android App

## Prerequisites
1. Install Android Studio from https://developer.android.com/studio
2. Install Java JDK 11 or higher
3. Set up Android SDK (via Android Studio)

## Setup Capacitor

### 1. Install Capacitor
```bash
cd frontend
npm install @capacitor/core @capacitor/cli
npm install @capacitor/android
```

### 2. Initialize Capacitor
```bash
npx cap init
```
When prompted:
- App name: `Reaction Game`
- App ID: `com.reactiongame.app` (or your preference)
- Web asset directory: `dist`

### 3. Build Vue App
```bash
npm run build
```

### 4. Add Android Platform
```bash
npx cap add android
```

### 5. Update capacitor.config.json
The config should include your backend server URL:
```json
{
  "appId": "com.reactiongame.app",
  "appName": "Reaction Game",
  "webDir": "dist",
  "server": {
    "url": "http://YOUR_SERVER_IP:3000",
    "cleartext": true
  }
}
```

### 6. Sync Files to Android
```bash
npx cap sync android
```

### 7. Open in Android Studio
```bash
npx cap open android
```

### 8. Build APK in Android Studio
1. Click "Build" → "Build Bundle(s) / APK(s)" → "Build APK(s)"
2. APK will be in `android/app/build/outputs/apk/debug/app-debug.apk`

## For Production Build

### 1. Build optimized Vue app
```bash
npm run build
```

### 2. Sync to Android
```bash
npx cap sync android
```

### 3. Build Signed APK
In Android Studio:
1. Build → Generate Signed Bundle / APK
2. Follow the wizard to create/use keystore
3. APK will be in `android/app/release/`

## Testing on Device
1. Enable Developer Options on Android phone
2. Enable USB Debugging
3. Connect phone via USB
4. In Android Studio, click "Run" (green play button)

## Update App After Code Changes
```bash
npm run build
npx cap sync android
```

## Common Issues

### CORS/Network Issues
- Make sure backend allows connections from Android device IP
- Use actual IP address, not localhost
- Add `cleartext: true` in capacitor.config.json for HTTP (dev only)

### WebSocket Connection
- Update WebSocket URLs to use actual server IP
- Android doesn't support `localhost` - use `10.0.2.2` for Android emulator or actual IP for device
