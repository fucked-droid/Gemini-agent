const { GoogleGenAI } = require("@google/genai");
const fs = require("fs/promises");
const path = require("path");

const ai = new GoogleGenAI({
  apiKey: process.env.GEMINI_API_KEY,
});

async function readFile(filePath) {
  const fullPath = path.resolve(process.cwd(), filePath);

  console.log("Reading:", fullPath);

  return await fs.readFile(fullPath, "utf8");
}

async function main() {
  console.log("Starting agent...");

  const interaction = await ai.interactions.create({
    model: "gemini-3.5-flash-lite",

    input: "Read the file index.js and tell me what it does.",

    tools: [
      {
        type: "function",
        name: "read_file",
        description: "Read a file from the project.",
        parameters: {
          type: "object",
          properties: {
            filePath: {
              type: "string",
              description: "Path of the file to read.",
            },
          },
          required: ["filePath"],
        },
      },
    ],
  });

  console.log("Interaction created.");

  const functionCall = interaction.steps.find(
    (step) => step.type === "function_call"
  );

  if (!functionCall) {
    console.log("No function call requested.");
    return;
  }

  console.log("Gemini requested:", functionCall.name);
  console.log("Arguments:", functionCall.arguments);

  if (functionCall.name === "read_file") {
    const result = await readFile(functionCall.arguments.filePath);

    console.log("\n--- FILE CONTENT ---");
    console.log(result);
    console.log("--- END FILE ---");
     const finalInteraction = await ai.interactions.create({
      model: "gemini-3.5-flash-lite",
      previous_interaction_id: interaction.id,
      input: [
        {
          type: "function_result",
          call_id: functionCall.id,
          result: result,
        },
      ],
    });

    console.log("\n--- GEMINI FINAL ANSWER ---");
    console.log(JSON.stringify(finalInteraction, null, 2));

    const finalInteraction = await ai.interactions.create({
      model: "gemini-3.5-flash-lite",
      previous_interaction_id: interaction.id,
      input: [
        {
          type: "function_result",
          call_id: functionCall.id,
          result: result,
        },
      ],
    });

    console.log("\n--- GEMINI FINAL ANSWER ---");
    console.log(JSON.stringify(finalInteraction, null, 2));
  }
}

main().catch((error) => {
  console.error("ERROR:", error);
});