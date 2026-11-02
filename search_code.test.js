const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");
const { searchCode } = require("./index.js");

function createTempFixtureDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "gemini-search-test-"));
}

function cleanupTempDir(dirPath) {
  try {
    fs.rmSync(dirPath, { recursive: true, force: true });
  } catch {
    // Ignore cleanup errors
  }
}

test("searchCode terminates recursion early and caps results at exactly 100 matches", async () => {
  const tempDir = createTempFixtureDir();
  try {
    // Create nested subdirectories: dir_a, dir_b, dir_c
    const dirA = path.join(tempDir, "dir_a");
    const dirB = path.join(tempDir, "dir_b");
    const dirC = path.join(tempDir, "dir_c");
    fs.mkdirSync(dirA, { recursive: true });
    fs.mkdirSync(dirB, { recursive: true });
    fs.mkdirSync(dirC, { recursive: true });

    // dir_a has 60 matches
    const linesA = Array.from({ length: 60 }, (_, i) => `TARGET_TOKEN line in A ${i + 1}`).join("\n");
    fs.writeFileSync(path.join(dirA, "file_a.txt"), linesA, "utf8");

    // dir_b has 60 matches (60 + 60 = 120 potential matches)
    const linesB = Array.from({ length: 60 }, (_, i) => `TARGET_TOKEN line in B ${i + 1}`).join("\n");
    fs.writeFileSync(path.join(dirB, "file_b.txt"), linesB, "utf8");

    // dir_c has 40 matches plus a unique canary line that must never be reached
    const linesC = Array.from({ length: 40 }, (_, i) => `TARGET_TOKEN line in C ${i + 1}`).join("\n") + "\nCANARY_SHOULD_NEVER_BE_COLLECTED TARGET_TOKEN";
    fs.writeFileSync(path.join(dirC, "file_c.txt"), linesC, "utf8");

    const result = await searchCode("TARGET_TOKEN", false, tempDir);

    assert.equal(typeof result, "string", "Result should be a string");
    const matchedLines = result.split("\n");

    // Must be capped at exactly 100 matches
    assert.equal(matchedLines.length, 100, "Results must be capped at exactly 100 matches");

    // Canary in dir_c must not have been reached / collected due to early-exit recursion termination
    assert.equal(result.includes("CANARY_SHOULD_NEVER_BE_COLLECTED"), false, "Later directories must not be traversed after reaching 100 matches");
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("searchCode normal search returns all matches when total is fewer than 100", async () => {
  const tempDir = createTempFixtureDir();
  try {
    const subDir = path.join(tempDir, "sub");
    fs.mkdirSync(subDir, { recursive: true });

    const content1 = "First line\nFind this unique_keyword here\nThird line";
    const content2 = "Another unique_keyword line\nNo match\nFinal unique_keyword line";
    fs.writeFileSync(path.join(tempDir, "file1.txt"), content1, "utf8");
    fs.writeFileSync(path.join(subDir, "file2.txt"), content2, "utf8");

    const result = await searchCode("unique_keyword", false, tempDir);
    assert.equal(typeof result, "string");

    const lines = result.split("\n");
    assert.equal(lines.length, 3, "Should return all 3 matching lines");

    // Verify format: relPath:lineNum: lineText
    assert.ok(lines.some((l) => l.includes("file1.txt:2: Find this unique_keyword here")));
    assert.ok(lines.some((l) => l.includes("file2.txt:1: Another unique_keyword line")));
    assert.ok(lines.some((l) => l.includes("file2.txt:3: Final unique_keyword line")));
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("searchCode returns descriptive message when no matches are found", async () => {
  const tempDir = createTempFixtureDir();
  try {
    fs.writeFileSync(path.join(tempDir, "sample.txt"), "hello world", "utf8");
    const result = await searchCode("nonexistent_pattern_12345", false, tempDir);
    assert.equal(result, 'No matches found for query: "nonexistent_pattern_12345"');
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("searchCode supports regex search with pattern matching", async () => {
  const tempDir = createTempFixtureDir();
  try {
    fs.writeFileSync(
      path.join(tempDir, "data.txt"),
      "alpha 100\nbeta 200\ngamma text\ndelta 999",
      "utf8"
    );

    const result = await searchCode("[a-z]+ \\d{3}", true, tempDir);
    const lines = result.split("\n");
    assert.equal(lines.length, 3, "Regex should match 3 lines with 3-digit numbers");
    assert.ok(lines.some((l) => l.includes("alpha 100")));
    assert.ok(lines.some((l) => l.includes("beta 200")));
    assert.ok(lines.some((l) => l.includes("delta 999")));
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("searchCode skips excluded directories and binary file extensions", async () => {
  const tempDir = createTempFixtureDir();
  try {
    const nodeModulesDir = path.join(tempDir, "node_modules");
    const gitDir = path.join(tempDir, ".git");
    fs.mkdirSync(nodeModulesDir, { recursive: true });
    fs.mkdirSync(gitDir, { recursive: true });

    // Excluded directory files containing search target
    fs.writeFileSync(path.join(nodeModulesDir, "dep.js"), "EXCLUDE_TARGET match in node_modules", "utf8");
    fs.writeFileSync(path.join(gitDir, "config"), "EXCLUDE_TARGET match in git", "utf8");

    // Binary extension file containing search target
    fs.writeFileSync(path.join(tempDir, "image.png"), "EXCLUDE_TARGET match in png", "utf8");

    // Valid file containing search target
    fs.writeFileSync(path.join(tempDir, "valid.js"), "EXCLUDE_TARGET match in valid file", "utf8");

    const result = await searchCode("EXCLUDE_TARGET", false, tempDir);
    const lines = result.split("\n");

    assert.equal(lines.length, 1, "Only the valid file match should be included");
    assert.ok(lines[0].includes("valid.js:1: EXCLUDE_TARGET match in valid file"));
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("searchCode input validation handles empty query and invalid regex", async () => {
  assert.equal(await searchCode(""), "Search query cannot be empty.");
  assert.equal(await searchCode(null), "Search query cannot be empty.");
  assert.equal(await searchCode(undefined), "Search query cannot be empty.");

  const invalidRegexResult = await searchCode("[unclosed-group", true);
  assert.ok(invalidRegexResult.startsWith("Invalid regular expression:"));
});
