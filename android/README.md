# PixelCut Android (On-Device AI Background Remover)

A standalone native Android application that runs **100% on-device AI background removal** powered by **ONNX Runtime Mobile** and **Jetpack Compose (Material 3)**.

---

## Highlights

- **100% Offline & Private:** Inference runs entirely locally on your smartphone using ONNX Runtime Mobile (`u2netp.onnx`). Zero photos or data ever leave the device.
- **Modern Jetpack Compose UI:** Premium dark theme, interactive Before/After comparison slider, live transparency checkerboard canvas, and Material 3 controls.
- **Background Replacement:**
  - **Transparent:** Pristine PNG alpha cutout.
  - **Curated Solid Colors:** White, Black, Slate, Indigo, Red, Emerald, Cyan, Amber, Pink.
  - **Curated Gradients:** Sunset Glow, Cyberpunk, Royal Violet, Ocean Breeze, Clean Studio, Midnight Slate.
  - **Custom Background Photo:** Pick any image from your gallery as a backdrop.
- **Social Media Aspect Ratios:** 1:1 (Square), 4:5 (Instagram Portrait), 9:16 (Stories/Reels), 16:9 (Landscape), and Original.
- **Effects:** One-tap Drop Shadow and White Subject Outline.
- **Export & Share:** Direct save to Android MediaStore (`Pictures/PixelCut`) and system share sheet (`ACTION_SEND`).

---

## Pre-Built APK

The ready-to-install debug APK is located at:
```
dist/android/PixelCut-v1.0-debug.apk
```
*(Also built at `android/app/build/outputs/apk/debug/app-debug.apk`)*

### Installing on Device via ADB

1. Enable **USB Debugging** on your Android device (Settings > Developer options).
2. Connect your phone via USB or WiFi.
3. Install the APK:
   ```bash
   adb install -r dist/android/PixelCut-v1.0-debug.apk
   ```

---

## Project Structure

```
android/
├── app/
│   ├── build.gradle.kts           # App-level dependencies & ONNX packaging configuration
│   └── src/main/
│       ├── AndroidManifest.xml    # Permissions, Camera, MediaStore, and FileProvider
│       ├── assets/
│       │   └── models/
│       │       └── u2netp.onnx    # Bundled 4.5 MB lightweight neural network
│       ├── java/com/example/pixelcut/
│       │   ├── MainActivity.kt    # Entry activity with edge-to-edge Compose
│       │   ├── Navigation.kt      # Modern navigation setup
│       │   ├── core/
│       │   │   ├── SegmentationEngine.kt # ONNX Runtime Mobile inference & mask extraction
│       │   │   ├── CompositionEngine.kt  # Solid/gradient/image composition & framing
│       │   │   ├── ExportManager.kt      # MediaStore gallery saving & intent sharing
│       │   │   └── ImageUtils.kt         # Bitmap downsampling & EXIF rotation correction
│       │   ├── ui/
│       │   │   ├── components/
│       │   │   │   ├── BeforeAfterSlider.kt   # Interactive draggable split slider
│       │   │   │   ├── CheckerboardCanvas.kt  # Repeating transparency grid canvas
│       │   │   │   ├── BackgroundSelector.kt  # Color, gradient, & photo selector
│       │   │   │   └── PresetSelector.kt      # Aspect ratios & effect toggles
│       │   │   └── main/
│       │   │       ├── MainScreen.kt          # Full Material 3 Compose screen
│       │   │       └── MainScreenViewModel.kt # Reactive StateFlow view model
│       │   └── theme/             # Dark Material 3 theme palette
│       └── res/                   # Drawables, mipmaps, strings, and file_paths.xml
├── gradle/
│   └── libs.versions.toml         # Gradle Version Catalog
├── build.gradle.kts               # Root Gradle project configuration
├── settings.gradle.kts
└── gradlew.bat                    # Gradle Wrapper
```

---

## Building from Source

### Prerequisites
- JDK 17 or higher
- Android SDK (API 34 or API 36)

### Build Debug APK
```bash
cd android
./gradlew assembleDebug
```
The output APK will be placed in `android/app/build/outputs/apk/debug/app-debug.apk`.

### Opening in Android Studio
1. Launch **Android Studio**.
2. Select **Open** and choose the `android` folder within this repository.
3. Allow Gradle sync to complete and press **Run 'app'** (`Shift + F10`).
