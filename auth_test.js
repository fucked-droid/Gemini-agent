const test = require("node:test");
const assert = require("node:assert");
const { runAgent, isAuthenticationError } = require("./index.js");

test("Authentication error classification", () => {
  assert.strictEqual(isAuthenticationError({ status: 400, message: "API_KEY_INVALID" }), true);
  assert.strictEqual(isAuthenticationError({ statusCode: 401, message: "Unauthorized" }), true);
  assert.strictEqual(isAuthenticationError({ response: { status: 403 }, message: "Forbidden" }), true);
  assert.strictEqual(isAuthenticationError({ message: "API key not valid. Please pass a valid API key." }), true);
  assert.strictEqual(isAuthenticationError({ status: 500, message: "Internal Server Error" }), false);
  assert.strictEqual(isAuthenticationError({ status: 429, message: "Rate limit exceeded" }), false);
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