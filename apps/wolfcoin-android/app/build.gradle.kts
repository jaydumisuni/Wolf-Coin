plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}
android {
 namespace = "com.thetechguy.wolfcoin"
 compileSdk = 35
 defaultConfig {
  applicationId = "com.thetechguy.wolfcoin"
  minSdk = 26
  targetSdk = 35
  versionCode = 10
  versionName = "0.8.0-dev"
 }
 buildTypes { getByName("release") { isMinifyEnabled = false } }
 compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
 kotlinOptions { jvmTarget = "17" }
}
dependencies { implementation("androidx.webkit:webkit:1.13.0") }

