const test = require("node:test");
const assert = require("node:assert/strict");
const { consumeInteractionStream } = require("./index.js");

async function* makeStream(events) {
  for (const event of events) {
    yield event;
  }
}

test("stream emits text deltas in order and preserves completion ID", async () => {
  const chunks = [];

  const originalWrite = process.stdout.write;
  process.stdout.write = function (chunk, ...args) {
    chunks.push(String(chunk));
    return true;
  };

  try {
    const result = await consumeInteractionStream(
      makeStream([
        {
          event_type: "interaction.created",
          interaction: { id: "interaction_test_1" },
        },
        {
          event_type: "step.delta",
          delta: { type: "text", text: "Hello " },
        },
        {
          event_type: "step.delta",
          delta: { type: "text", text: "world" },
        },
        {
          event_type: "interaction.completed",
          interaction: {
            id: "interaction_test_1",
            output_text: "Hello world",
            steps: [],
          },
        },
      ])
    );

    assert.equal(chunks.join("").trimEnd(), "Hello world");
    assert.equal(result.id, "interaction_test_1");
    assert.equal(result.output_text, "Hello world");
  } finally {
    process.stdout.write = originalWrite;
  }
});

test("stream errors propagate to the caller", async () => {
  async function* brokenStream() {
    yield {
      event_type: "interaction.created",
      interaction: { id: "interaction_test_2" },
    };
    throw new Error("mock stream failure");
  }

  await assert.rejects(
    consumeInteractionStream(brokenStream()),
    /mock stream failure/
  );
});



test("stream consumer collects completed function-call steps", async () => {
  const call = {
    id: "call_test_123",
    type: "function_call",
    name: "list_files",
    arguments: {}
  };

  const result = await consumeInteractionStream(
    makeStream([
      {
        event_type: "interaction.created",
        interaction: { id: "interaction_tool_test" }
      },
      {
        event_type: "step.start",
        index: 0,
        step: call
      },
      {
        event_type: "interaction.completed",
        interaction: {
          id: "interaction_tool_test",
          steps: [call]
        }
      }
    ])
  );

  assert.equal(result.id, "interaction_tool_test");
  assert.ok(Array.isArray(result.steps));
  assert.ok(
    result.steps.some(
      step => step.type === "function_call" && step.id === "call_test_123"
    ),
    "The completed function-call step should be collected"
  );
});

test("A tool call emitted in step.start is preserved when interaction.completed.steps is empty or omitted", async () => {
  const call = {
    id: "call_start_only",
    type: "function_call",
    name: "read_file",
    arguments: { filePath: "index.js" }
  };

  const result = await consumeInteractionStream(
    makeStream([
      {
        event_type: "interaction.created",
        interaction: { id: "interaction_empty_completed_steps" }
      },
      {
        event_type: "step.start",
        index: 0,
        step: call
      },
      {
        event_type: "interaction.completed",
        interaction: {
          id: "interaction_empty_completed_steps",
          steps: []
        }
      }
    ])
  );

  assert.equal(result.id, "interaction_empty_completed_steps");
  assert.ok(Array.isArray(result.steps));
  assert.equal(result.steps.length, 1);
  assert.equal(result.steps[0].id, "call_start_only");
  assert.equal(result.steps[0].name, "read_file");
  assert.deepEqual(result.steps[0].arguments, { filePath: "index.js" });
});

test("Multiple sequential tool calls retain the correct index ordering", async () => {
  const call0 = {
    id: "call_seq_0",
    type: "function_call",
    name: "list_files",
    arguments: {}
  };
  const call1 = {
    id: "call_seq_1",
    type: "function_call",
    name: "read_file",
    arguments: { filePath: "package.json" }
  };

  const result = await consumeInteractionStream(
    makeStream([
      {
        event_type: "interaction.created",
        interaction: { id: "interaction_multi_step" }
      },
      {
        event_type: "step.start",
        index: 0,
        step: call0
      },
      {
        event_type: "step.start",
        index: 1,
        step: call1
      },
      {
        event_type: "interaction.completed",
        interaction: {
          id: "interaction_multi_step",
          steps: []
        }
      }
    ])
  );

  assert.equal(result.steps.length, 2);
  assert.equal(result.steps[0].id, "call_seq_0");
  assert.equal(result.steps[1].id, "call_seq_1");
  assert.equal(result.steps[0].name, "list_files");
  assert.equal(result.steps[1].name, "read_file");
});

test("Repeated tool-call events update the existing step rather than creating duplicates", async () => {
  const initialCall = {
    id: "call_repeat_1",
    type: "function_call",
    name: "write_file",
    arguments: {}
  };
  const updatedCall = {
    id: "call_repeat_1",
    type: "function_call",
    name: "write_file",
    arguments: { filePath: "test.txt", content: "hello" }
  };

  const result = await consumeInteractionStream(
    makeStream([
      {
        event_type: "interaction.created",
        interaction: { id: "interaction_repeat_test" }
      },
      {
        event_type: "step.start",
        index: 0,
        step: initialCall
      },
      {
        event_type: "step.stop",
        index: 0,
        step: updatedCall
      },
      {
        event_type: "interaction.completed",
        interaction: {
          id: "interaction_repeat_test",
          steps: [updatedCall]
        }
      }
    ])
  );

  assert.equal(result.steps.length, 1, "Should not duplicate step across events");
  assert.equal(result.steps[0].id, "call_repeat_1");
  assert.deepEqual(result.steps[0].arguments, { filePath: "test.txt", content: "hello" });
});
