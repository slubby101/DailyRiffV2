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
};
