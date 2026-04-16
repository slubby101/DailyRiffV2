import { ExpoConfig, ConfigContext } from "expo/config";

const ENVIRONMENT = process.env.EXPO_PUBLIC_ENVIRONMENT ?? "development";

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: ENVIRONMENT === "production" ? "DailyRiff" : `DailyRiff (${ENVIRONMENT})`,
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
  extra: {
    supabaseUrl: process.env.EXPO_PUBLIC_SUPABASE_URL ?? "http://localhost:54321",
    supabaseAnonKey: process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY ?? "",
    apiUrl: process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000",
    environment: ENVIRONMENT,
  },
  experiments: {
    typedRoutes: true,
  },
});
