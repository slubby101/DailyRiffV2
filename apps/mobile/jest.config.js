/** @type {import('jest').Config} */
module.exports = {
  preset: "jest-expo",
  collectCoverageFrom: ["src/stores/**/*.{ts,tsx}"],
  coverageThreshold: {
    global: {
      branches: 90,
      functions: 90,
      lines: 90,
      statements: 90,
    },
  },
  // Override jest-expo's default transformIgnorePatterns to handle pnpm's
  // virtual store layout. Default pattern assumes node_modules/react-native
  // but pnpm installs to node_modules/.pnpm/react-native@<ver>/node_modules/react-native.
  // Without this override, react-native's Flow-typed jest/setup.js slips
  // through untransformed and jest errors on `type ErrorHandler = ...`.
  transformIgnorePatterns: [
    "node_modules/(?!(\\.pnpm/)?((jest-)?react-native|@react-native|@react-navigation|expo(nent)?|@expo(nent)?/.*|@unimodules/.*|unimodules|sentry-expo|native-base|react-clone-referenced-element))",
  ],
};
