plugins {
    id("com.android.application")
    id("com.chaquo.python")
    id("org.jetbrains.kotlin.android")
}
android {
 namespace = "com.thetechguy.wolfcoin"
 compileSdk = 35
 defaultConfig {
  ndk { abiFilters += listOf("x86_64","arm64-v8a") }
  applicationId = "com.thetechguy.wolfcoin"
  minSdk = 26
  targetSdk = 35
  versionCode = 20
  versionName = "0.9.8-dev"
 }
 buildTypes { getByName("debug") { if (System.getenv("WOLF_QA_INSTALL") == "1") applicationIdSuffix = ".qa" }; getByName("release") { isMinifyEnabled = false } }
 compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
 kotlinOptions { jvmTarget = "17" }
}
dependencies { implementation("androidx.webkit:webkit:1.13.0") }



chaquopy {
 defaultConfig {
  version = "3.11"
  buildPython(System.getenv("WOLF_BUILD_PYTHON") ?: "python3.11")
 }
}
