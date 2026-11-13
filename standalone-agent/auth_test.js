const test = require("node:test");
const assert = require("node:assert");
const {
  runAgent,
  isAuthenticationError,
  validateApiKey,
  isPlaceholderApiKey,
  extractApiErrorMessage,
} = require("./index.js");

test("Authentication error classification", () => {
  assert.strictEqual(isAuthenticationError({ status: 400, message: "API_KEY_INVALID" }), true);
  assert.strictEqual(isAuthenticationError({ statusCode: 401, message: "Unauthorized" }), true);
  assert.strictEqual(isAuthenticationError({ response: { status: 403 }, message: "Forbidden" }), true);
  assert.strictEqual(isAuthenticationError({ message: "API key not valid. Please pass a valid API key." }), true);
  assert.strictEqual(isAuthenticationError({ status: 500, message: "Internal Server Error" }), false);
  assert.strictEqual(isAuthenticationError({ status: 429, message: "Rate limit exceeded" }), false);

  // Speakeasy / GoogleGenAI 400 BadRequestError with hidden message in body
  assert.strictEqual(
    isAuthenticationError({
      status: 400,
      message: '400 API error occurred: {"httpMeta":{"response":{},"request":{}}}',
      body: JSON.stringify({
        error: {
          code: 400,
          message: "API key not valid. Please pass a valid API key.",
          status: "INVALID_ARGUMENT",
        },
      }),
    }),
    true
  );

  // Speakeasy / GoogleGenAI 400 BadRequestError with placeholder key
  const prevKey = process.env.GEMINI_API_KEY;
  try {
    process.env.GEMINI_API_KEY = "YOUR_GEMINI_API_KEY";
    assert.strictEqual(
      isAuthenticationError({
        status: 400,
        message: '400 API error occurred: {"httpMeta":{"response":{},"request":{}}}',
      }),
      true
    );
  } finally {
    process.env.GEMINI_API_KEY = prevKey;
  }
});

test("API key validation and placeholder detection", () => {
  assert.strictEqual(isPlaceholderApiKey("YOUR_GEMINI_API_KEY"), true);
  assert.strictEqual(isPlaceholderApiKey("YOUR_API_KEY"), true);
  assert.strictEqual(isPlaceholderApiKey("<YOUR_API_KEY>"), true);
  assert.strictEqual(isPlaceholderApiKey(""), true);
  assert.strictEqual(isPlaceholderApiKey(null), true);
  assert.strictEqual(isPlaceholderApiKey("AIzaSyD-valid-mock-key-1234567890"), false);

  assert.strictEqual(validateApiKey("").valid, false);
  assert.strictEqual(validateApiKey("   ").valid, false);
  assert.strictEqual(validateApiKey("YOUR_GEMINI_API_KEY").valid, false);
  assert.strictEqual(validateApiKey("AIzaSyD-valid-mock-key-1234567890").valid, true);
});

test("extractApiErrorMessage extracts nested Google error details", () => {
  const sdkError = {
    status: 400,
    message: '400 API error occurred: {"httpMeta":{"response":{},"request":{}}}',
    body: JSON.stringify({
      error: {
        code: 400,
        message: "API key not valid. Please pass a valid API key.",
        status: "INVALID_ARGUMENT",
      },
    }),
  };
  assert.strictEqual(extractApiErrorMessage(sdkError), "API key not valid. Please pass a valid API key.");

  const emptyMetaError = {
    status: 400,
    message: '400 API error occurred: {"httpMeta":{"response":{},"request":{}}}',
  };
  assert.ok(extractApiErrorMessage(emptyMetaError).includes("rejected the request payload"));
});

test("Invalid API key does not trigger interaction recovery and throws immediately", async () => {
  let createCalls = 0;
  const mockClient = {
    interactions: {
      create: async () => {
        createCalls++;
        const err = new Error("API_KEY_INVALID: API key not valid");
        err.status = 400;
        throw err;
      }
    }
  };

  let errorThrown = null;
  try {
    await runAgent("Test task", null, mockClient);
  } catch (err) {
    errorThrown = err;
  }

  assert.ok(errorThrown !== null, "An error should be thrown");
  assert.strictEqual(errorThrown.status, 400);
  assert.ok(errorThrown.message.includes("API_KEY_INVALID"));
  assert.strictEqual(createCalls, 1, "Should not retry or attempt recovery on authentication error");
});

test("Expired interaction recovery works for genuine expired interaction errors", async () => {
  let createCalls = 0;

  const mockClient = {
    interactions: {
      create: async (params) => {
        createCalls++;

        if (createCalls === 1) {
          const err = new Error(
            "Interaction previous_interaction_id expired or not found"
          );
          err.status = 400;
          throw err;
        }

        // Simulate the actual SDK's async-iterable streaming response.
        return (async function* () {
          yield {
            event_type: "interaction.created",
            interaction: {
              id: "new_interaction_123"
            }
          };

          yield {
            event_type: "interaction.completed",
            interaction: {
              id: "new_interaction_123",
              output_text: "Recovered successfully",
              steps: []
            }
          };
        })();
      }
    }
  };

  const resultId = await runAgent("Test task", "expired_id_999", mockClient);

  assert.strictEqual(resultId, "new_interaction_123");
  assert.strictEqual(createCalls, 2);
});