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
  },
  android: {
    package: "com.dailyriff.app",
  },
});
