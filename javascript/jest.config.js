/*
 * Copyright (c) Jupyter Development Team.
 * Distributed under the terms of the Modified BSD License.
 */

import path from "path";

const esModules = [
  "lib0",
  "y-protocols",
  "y-websocket",
  "yjs",
].join("|");

module.exports = {
  preset: "ts-jest/presets/js-with-babel",
  testTimeout: 10000,
  testPathIgnorePatterns: ["/lib/", "/node_modules/"],
  moduleFileExtensions: [
    "ts",
    "tsx",
    "js",
    "jsx",
    "json",
    "node",
    "mjs",
    "cjs",
  ],
  transformIgnorePatterns: [`/node_modules/(?!${esModules}).+`],
  reporters: ["default", "jest-junit"],
  coverageReporters: ["json", "lcov", "text", "html"],
  coverageDirectory: path.join(__dirname, "coverage"),
  testRegex: "/test/.*.spec.ts[x]?$",
  globals: {
    "ts-jest": {
      tsconfig: `./tsconfig.test.json`,
    },
  },
};
