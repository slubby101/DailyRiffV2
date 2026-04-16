import { ExpoConfig, ConfigContext } from "expo/config";

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: "DailyRiff",
  slug: "dailyriff",
  version: "0.0.1",
  orientation: "portrait",
  scheme: "dailyriff",
  platforms: ["ios", "android"],
  ios: {
    bundleIdentifier: "com.dailyriff.app",
    supportsTablet: false,
    infoPlist: {
      NSMicrophoneUsageDescription:
        "DailyRiff needs microphone access to record practice sessions.",
      UIBackgroundModes: ["audio"],
    },
  },
  android: {
    package: "com.dailyriff.app",
    permissions: [
      "android.permission.RECORD_AUDIO",
      "android.permission.WRITE_EXTERNAL_STORAGE",
    ],
  },
  plugins: ["expo-router", "expo-secure-store", "expo-notifications"],
  experiments: {
    typedRoutes: true,
  },
});
