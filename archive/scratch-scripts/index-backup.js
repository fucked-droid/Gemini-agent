const { GoogleGenAI } = require("@google/genai");
const fs = require("fs/promises");
const path = require("path");
const { execFile } = require("child_process");
const readline = require("readline");

const ai = new GoogleGenAI({
  apiKey: process.env.GEMINI_API_KEY,
});

const MODEL = "gemini-3.5-flash-lite";

const MAX_STEPS = 20;
const MAX_REPAIR_ATTEMPTS = 5;

const tools = [
  {
    type: "function",
    name: "list_files",
    description: "List files and folders in the current project directory.",
    parameters: {
      type: "object",
      properties: {},
    },
  },
  {
    type: "function",
    name: "read_file",
    description: "Read a text file from the project.",
    parameters: {
      type: "object",
      properties: {
        filePath: {
          type: "string",
        },
      },
      required: ["filePath"],
    },
  },
  {
    type: "function",
    name: "write_file",
    description: "Create or completely replace a text file.",
    parameters: {
      type: "object",
      properties: {
        filePath: {
          type: "string",
        },
        content: {
          type: "string",
        },
      },
      required: ["filePath", "content"],
    },
  },
  {
    type: "function",
    name: "run_command",
    description:
      "Run a development command in the current Windows project. Always inspect the command result. A non-zero exit code means the command failed and the error should be diagnosed and repaired.",
    parameters: {
      type: "object",
      properties: {
        command: {
          type: "string",
        },
      },
      required: ["command"],
    },
  },
];

async function listFiles() {
  const entries = await fs.readdir(process.cwd(), {
    withFileTypes: true,
  });

  return entries
    .map((entry) =>
      entry.isDirectory() ? `${entry.name}/` : entry.name
    )
    .join("\n");
}

async function readFile(filePath) {
  const fullPath = path.resolve(process.cwd(), filePath);

  console.log("Reading:", fullPath);

  return await fs.readFile(fullPath, "utf8");
}

async function writeFile(filePath, content) {
  const fullPath = path.resolve(process.cwd(), filePath);

  console.log("Writing:", fullPath);

  await fs.writeFile(fullPath, content, "utf8");

  return `Successfully wrote ${fullPath}`;
}

function runCommand(command) {
  return new Promise((resolve) => {
    console.log("Running:", command);

    execFile(
      "cmd.exe",
      ["/d", "/s", "/c", command],
      {
        cwd: process.cwd(),
        timeout: 30000,
        maxBuffer: 1024 * 1024,
      },
      (error, stdout, stderr) => {
        const output = [];

        if (stdout) {
          output.push(`STDOUT:\n${stdout}`);
        }

        if (stderr) {
          output.push(`STDERR:\n${stderr}`);
        }

        if (error) {
          output.push(`EXIT CODE: ${error.code ?? "unknown"}`);
          output.push(`COMMAND FAILED: ${command}`);

          resolve({
            success: false,
            command,
            output: output.join("\n"),
          });

          return;
        }

        resolve({
          success: true,
          command,
          output:
            output.length > 0
              ? output.join("\n")
              : "Command completed successfully.",
        });
      }
    );
  });
}

async function executeTool(functionCall) {
  const args = functionCall.arguments || {};

  console.log("\n================================");
  console.log("TOOL:", functionCall.name);
  console.log("ARGUMENTS:", args);
  console.log("================================");

  try {
    if (functionCall.name === "list_files") {
      return {
        success: true,
        result: await listFiles(),
      };
    }

    if (functionCall.name === "read_file") {
      return {
        success: true,
        result: await readFile(args.filePath),
      };
    }

    if (functionCall.name === "write_file") {
      return {
        success: true,
        result: await writeFile(
          args.filePath,
          args.content
        ),
      };
    }

    if (functionCall.name === "run_command") {
      const command = args.command;
      const lowerCommand = command.toLowerCase().trim();

      const blockedCommands = [
        "del ",
        "erase ",
        "rmdir ",
        "rd ",
        "format ",
        "shutdown",
        "restart",
        "taskkill",
        "diskpart",
      ];

      if (
        blockedCommands.some(
          (blocked) =>
            lowerCommand === blocked.trim() ||
            lowerCommand.startsWith(blocked)
        )
      ) {
        return {
          success: false,
          blocked: true,
          result: `Command blocked for safety: ${command}`,
        };
      }

      return await runCommand(command);
    }

    return {
      success: false,
      result: `Unknown tool: ${functionCall.name}`,
    };
  } catch (error) {
    return {
      success: false,
      result: `TOOL ERROR: ${error.message}`,
    };
  }
}

function ask(question) {
  return new Promise((resolve) => {
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
    });

    rl.question(question, (answer) => {
      rl.close();
      resolve(answer.trim());
    });
  });
}

async function runAgent(
  userTask,
  previousInteractionId = null
) {
  const instructions = `
You are an autonomous coding agent.

Current project:
${process.cwd()}

Your job is to COMPLETE the user's coding task, not merely explain how to do it.

You have access to these tools:
- list_files
- read_file
- write_file
- run_command

WORKFLOW:

1. Understand the user's task.
2. Inspect the existing project before making unrelated changes.
3. Read relevant source files.
4. Plan the smallest appropriate implementation.
5. Modify or create files.
6. Run the appropriate tests, build commands, or programs.
7. Carefully inspect command results.
8. If a command fails:
   - identify the actual cause
   - inspect relevant files
   - make a targeted correction
   - run the failed command again
9. Continue repairing until the task is verified or you reach a genuine blocker.
10. Do not claim success without verification.

IMPORTANT SELF-CORRECTION RULE:

A failed command is NOT the end of the task.

When run_command reports:
- COMMAND FAILED
- a non-zero EXIT CODE
- test failures
- syntax errors
- runtime errors
- build errors

you must treat the result as debugging information.

Diagnose the failure and attempt a repair.

Do not repeatedly make random changes.
Use the error output to determine what should change.

Keep track of what you have already tried.

Do not modify unrelated files.

Maximum repair attempts:
${MAX_REPAIR_ATTEMPTS}

If the task cannot be completed safely or correctly after reasonable repair attempts,
stop and clearly explain the remaining blocker.

Before finalizing:
- verify the implementation
- run relevant tests
- report what was changed
- report verification results
`;

  let interaction;

  if (previousInteractionId) {
    interaction = await ai.interactions.create({
      model: MODEL,
      previous_interaction_id: previousInteractionId,
      tools,
      input: `${instructions}

User's next request:
${userTask}`,
    });
  } else {
    interaction = await ai.interactions.create({
      model: MODEL,
      tools,
      input: `${instructions}

User's request:
${userTask}`,
    });
  }

  let repairAttempts = 0;

  for (let step = 1; step <= MAX_STEPS; step++) {
    console.log(
      `\n========== AGENT STEP ${step}/${MAX_STEPS} ==========`
    );

    const functionCalls = interaction.steps.filter(
      (item) => item.type === "function_call"
    );

    if (functionCalls.length === 0) {
      console.log("\n--- GEMINI ---");
      console.log(
        interaction.output_text || "No response returned."
      );

      return interaction.id;
    }

    const functionResults = [];

    for (const functionCall of functionCalls) {
      const toolResult = await executeTool(functionCall);

      console.log("\n--- TOOL RESULT ---");

      if (typeof toolResult === "object") {
        console.log(
          JSON.stringify(toolResult, null, 2)
        );
      } else {
        console.log(toolResult);
      }

      console.log("--- END TOOL RESULT ---");

      if (
        functionCall.name === "run_command" &&
        toolResult.success === false
      ) {
        repairAttempts++;

        console.log(
          `\n⚠️ COMMAND FAILED`
        );

        console.log(
          `Repair attempt: ${repairAttempts}/${MAX_REPAIR_ATTEMPTS}`
        );

        if (repairAttempts > MAX_REPAIR_ATTEMPTS) {
          console.log(
            "\n🛑 Maximum repair attempts reached."
          );

          return interaction.id;
        }
      }

      functionResults.push({
        type: "function_result",
        name: functionCall.name,
        call_id: functionCall.id,
        result: [
          {
            type: "text",
            text: JSON.stringify(toolResult),
          },
        ],
      });
    }

    interaction = await ai.interactions.create({
      model: MODEL,
      previous_interaction_id: interaction.id,
      tools,
      input: functionResults,
    });
  }

  console.log(
    "\n🛑 Maximum agent steps reached."
  );

  return interaction.id;
}

async function main() {
  console.log("========================================");
  console.log("       GEMINI CODING AGENT");
  console.log("       SELF-CORRECTING MODE");
  console.log("========================================");

  console.log(`Project: ${process.cwd()}`);
  console.log(`Model: ${MODEL}`);
  console.log(`Max steps: ${MAX_STEPS}`);
  console.log(
    `Max repair attempts: ${MAX_REPAIR_ATTEMPTS}`
  );

  let interactionId = null;

  while (true) {
    const userTask = await ask("\nYou > ");

    if (!userTask) {
      continue;
    }

    if (
      userTask.toLowerCase() === "exit" ||
      userTask.toLowerCase() === "quit"
    ) {
      console.log("\nGoodbye bro.");
      break;
    }

    console.log("\nStarting task...");

    try {
      interactionId = await runAgent(
        userTask,
        interactionId
      );
    } catch (error) {
      console.error("\nERROR:");
      console.error(error);
    }
  }
}

main().catch((error) => {
  console.error("\nFATAL ERROR:");
  console.error(error);
});