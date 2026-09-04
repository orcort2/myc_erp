#!/usr/bin/env node

/**
 * Discovers every "*.test.ts"/"*.test.tsx" file under src/ and prints their
 * paths (relative to the repo root, one per line) so package.json's "test"
 * script can pass the full, always-up-to-date list to `tsx --test` via
 * shell command substitution ($(...) is portable POSIX, unlike bash's `**`
 * globstar, which isn't enabled by default and doesn't exist in dash/sh --
 * npm scripts run through `sh -c`, so relying on it would silently under-run
 * tests on some shells/CI images). A hand-maintained explicit file list
 * requires remembering to add every new test file; this makes that
 * automatic while staying strictly scoped to files that actually match the
 * project's test-file naming convention (never anything else under src/).
 */

const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const SRC = path.join(ROOT, "src");
const TEST_FILE_PATTERN = /\.test\.tsx?$/;

function collectTestFiles(dir, results) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      collectTestFiles(fullPath, results);
    } else if (entry.isFile() && TEST_FILE_PATTERN.test(entry.name)) {
      results.push(path.relative(ROOT, fullPath).split(path.sep).join("/"));
    }
  }
  return results;
}

const files = collectTestFiles(SRC, []).sort();

if (files.length === 0) {
  console.error("list-test-files: no *.test.ts(x) files found under src/ -- refusing to run an empty test suite");
  process.exit(1);
}

process.stdout.write(files.join("\n") + "\n");
