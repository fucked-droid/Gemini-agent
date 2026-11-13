const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");
const { editFile, isProtectedFile } = require("./index.js");

function createTempFixtureDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "gemini-edit-test-"));
}

function cleanupTempDir(dirPath) {
  try {
    fs.rmSync(dirPath, { recursive: true, force: true });
  } catch {
    // Ignore cleanup errors
  }
}

test("editFile successfully replaces unambiguous targeted text block and returns success message", async () => {
  const tempDir = createTempFixtureDir();
  try {
    const filePath = path.join(tempDir, "sample.js");
    const initialContent = [
      "function greet() {",
      '  console.log("Hello old world");',
      "}",
      "",
      "module.exports = { greet };",
    ].join("\n");
    fs.writeFileSync(filePath, initialContent, "utf8");

    const target = '  console.log("Hello old world");';
    const replacement = '  console.log("Hello new world");';

    const result = await editFile("sample.js", target, replacement, tempDir);

    assert.equal(typeof result, "string");
    assert.ok(result.includes("Successfully replaced target text in sample.js"));

    const updatedContent = fs.readFileSync(filePath, "utf8");
    assert.ok(updatedContent.includes('console.log("Hello new world");'));
    assert.ok(!updatedContent.includes('console.log("Hello old world");'));
    assert.ok(updatedContent.includes("module.exports = { greet };"));
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("editFile preserves unrelated content, surrounding lines, and indentation", async () => {
  const tempDir = createTempFixtureDir();
  try {
    const filePath = path.join(tempDir, "complex.js");
    const initialContent = [
      "// Top comment header",
      "const a = 10;",
      "",
      "function calculate() {",
      "  const x = 5;",
      "  const y = 10;",
      "  return x + y;",
      "}",
      "",
      "function unrelated() {",
      "  return true;",
      "}",
      "",
      "// Bottom comment",
    ].join("\n");
    fs.writeFileSync(filePath, initialContent, "utf8");

    const target = [
      "function calculate() {",
      "  const x = 5;",
      "  const y = 10;",
      "  return x + y;",
      "}",
    ].join("\n");

    const replacement = [
      "function calculate() {",
      "  const x = 20;",
      "  const y = 30;",
      "  return x * y;",
      "}",
    ].join("\n");

    await editFile("complex.js", target, replacement, tempDir);

    const updatedContent = fs.readFileSync(filePath, "utf8");

    assert.ok(updatedContent.startsWith("// Top comment header\nconst a = 10;\n\n"));
    assert.ok(updatedContent.endsWith("\n\nfunction unrelated() {\n  return true;\n}\n\n// Bottom comment"));
    assert.ok(updatedContent.includes("return x * y;"));
    assert.ok(!updatedContent.includes("return x + y;"));
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("editFile preserves Windows CRLF line endings in unaffected regions", async () => {
  const tempDir = createTempFixtureDir();
  try {
    const filePath = path.join(tempDir, "crlf_file.txt");
    const initialContent = "First line\r\nTARGET_LINE\r\nThird line\r\nFourth line\r\n";
    fs.writeFileSync(filePath, initialContent, "utf8");

    await editFile("crlf_file.txt", "TARGET_LINE", "REPLACED_LINE", tempDir);

    const updatedContent = fs.readFileSync(filePath, "utf8");
    assert.equal(updatedContent, "First line\r\nREPLACED_LINE\r\nThird line\r\nFourth line\r\n");
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("editFile rejects replacement when target text is missing without modifying file", async () => {
  const tempDir = createTempFixtureDir();
  try {
    const filePath = path.join(tempDir, "untouched.txt");
    const initialContent = "Alpha\nBeta\nGamma\n";
    fs.writeFileSync(filePath, initialContent, "utf8");

    await assert.rejects(
      async () => {
        await editFile("untouched.txt", "NON_EXISTENT_TARGET", "REPLACEMENT", tempDir);
      },
      {
        name: "Error",
        message: "Target text not found in untouched.txt.",
      }
    );

    const currentContent = fs.readFileSync(filePath, "utf8");
    assert.equal(currentContent, initialContent, "File content must remain completely unchanged");
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("editFile rejects ambiguous target text with multiple matches without modifying file", async () => {
  const tempDir = createTempFixtureDir();
  try {
    const filePath = path.join(tempDir, "ambiguous.txt");
    const initialContent = "Line 1: DUPLICATE_KEY\nLine 2: unique\nLine 3: DUPLICATE_KEY\nLine 4: DUPLICATE_KEY\n";
    fs.writeFileSync(filePath, initialContent, "utf8");

    await assert.rejects(
      async () => {
        await editFile("ambiguous.txt", "DUPLICATE_KEY", "REPLACEMENT", tempDir);
      },
      {
        name: "Error",
        message: "Ambiguous target text: found 3 matches in ambiguous.txt. Target text must match exactly once.",
      }
    );

    const currentContent = fs.readFileSync(filePath, "utf8");
    assert.equal(currentContent, initialContent, "File content must not be modified when ambiguous");
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("editFile safely fails when target file does not exist and does not create it", async () => {
  const tempDir = createTempFixtureDir();
  try {
    const nonExistent = path.join(tempDir, "does_not_exist.txt");
    assert.equal(fs.existsSync(nonExistent), false);

    await assert.rejects(
      async () => {
        await editFile("does_not_exist.txt", "TARGET", "REPLACEMENT", tempDir);
      },
      {
        name: "Error",
        message: "File not found: does_not_exist.txt",
      }
    );

    assert.equal(fs.existsSync(nonExistent), false, "File must not be silently created");
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("editFile safely fails when target path is a directory", async () => {
  const tempDir = createTempFixtureDir();
  try {
    const subDir = path.join(tempDir, "some_dir");
    fs.mkdirSync(subDir);

    await assert.rejects(
      async () => {
        await editFile("some_dir", "TARGET", "REPLACEMENT", tempDir);
      },
      {
        name: "Error",
        message: "Cannot edit directory: some_dir",
      }
    );
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("editFile blocks edits to protected secret and session files", async () => {
  const tempDir = createTempFixtureDir();
  try {
    // Create mock protected files
    fs.writeFileSync(path.join(tempDir, ".env"), "GEMINI_API_KEY=mock_key\n", "utf8");
    fs.writeFileSync(path.join(tempDir, ".env.local"), "SECRET=val\n", "utf8");
    fs.writeFileSync(path.join(tempDir, ".gemini_sessions.json"), "{}", "utf8");
    fs.writeFileSync(path.join(tempDir, ".gemini_sessions.backup.json"), "{}", "utf8");

    const protectedTargets = [
      ".env",
      "./.env",
      ".env.local",
      ".gemini_sessions.json",
      ".gemini_sessions.backup.json",
    ];

    for (const targetFile of protectedTargets) {
      await assert.rejects(
        async () => {
          await editFile(targetFile, "mock", "new_val", tempDir);
        },
        /Access denied: editing protected file is forbidden/,
        `Should reject editing ${targetFile}`
      );
    }

    // Verify helper isProtectedFile
    assert.equal(isProtectedFile(".env", tempDir), true);
    assert.equal(isProtectedFile(".env.production", tempDir), true);
    assert.equal(isProtectedFile(".gemini_sessions.json", tempDir), true);
    assert.equal(isProtectedFile(".gemini_sessions.test.json", tempDir), true);
    assert.equal(isProtectedFile("safe_file.js", tempDir), false);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("editFile validates required arguments safely", async () => {
  const tempDir = createTempFixtureDir();
  try {
    const filePath = path.join(tempDir, "valid.txt");
    fs.writeFileSync(filePath, "content", "utf8");

    // Invalid filePath
    await assert.rejects(async () => await editFile("", "t", "r", tempDir), /Invalid file path/);
    await assert.rejects(async () => await editFile(null, "t", "r", tempDir), /Invalid file path/);

    // Invalid target
    await assert.rejects(async () => await editFile("valid.txt", "", "r", tempDir), /Target text cannot be empty/);
    await assert.rejects(async () => await editFile("valid.txt", null, "r", tempDir), /Target text cannot be empty/);
    await assert.rejects(async () => await editFile("valid.txt", undefined, "r", tempDir), /Target text cannot be empty/);

    // Invalid replacement
    await assert.rejects(async () => await editFile("valid.txt", "content", null, tempDir), /Replacement text must be a string/);
    await assert.rejects(async () => await editFile("valid.txt", "content", undefined, tempDir), /Replacement text must be a string/);
  } finally {
    cleanupTempDir(tempDir);
  }
});

test("editFile supports replacing target with empty string (targeted deletion)", async () => {
  const tempDir = createTempFixtureDir();
  try {
    const filePath = path.join(tempDir, "deletion.txt");
    const initialContent = "Keep this prefix. DELETE_THIS_TEXT Keep this suffix.";
    fs.writeFileSync(filePath, initialContent, "utf8");

    const result = await editFile("deletion.txt", "DELETE_THIS_TEXT ", "", tempDir);
    assert.ok(result.includes("Successfully replaced target text in deletion.txt"));

    const updatedContent = fs.readFileSync(filePath, "utf8");
    assert.equal(updatedContent, "Keep this prefix. Keep this suffix.");
  } finally {
    cleanupTempDir(tempDir);
  }
});
