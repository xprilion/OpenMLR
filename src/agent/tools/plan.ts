import type { ToolSpec } from "../types.js";

let currentPlan: Array<{ id: string; content: string; status: string }> = [];

async function planToolHandler(args: Record<string, any>): Promise<[string, boolean]> {
  const todos = args.todos || [];

  if (!Array.isArray(todos)) {
    return ["Error: todos must be an array.", false];
  }

  for (const todo of todos) {
    if (!todo || typeof todo !== "object") {
      return ["Error: Each todo must be an object.", false];
    }
    for (const field of ["id", "content", "status"]) {
      if (!(field in todo)) {
        return [`Error: Todo missing required field '${field}'.", false`];
      }
    }
    if (!["pending", "in_progress", "completed"].includes(todo.status)) {
      return [`Error: Invalid status '${todo.status}'. Must be one of: pending, in_progress, completed.`, false];
    }
  }

  currentPlan = todos;

  const lines = todos.map((t: any) => {
    const icon = t.status === "completed" ? "[x]" : t.status === "in_progress" ? "[~]" : "[ ]";
    return `${icon} ${t.id}: ${t.content}`;
  });

  return [lines.join("\n"), true];
}

export const planToolSpec: ToolSpec = {
  name: "plan_tool",
  description:
    "Track progress on multi-step tasks with a todo list (pending/in_progress/completed).\n\n" +
    "Use for tasks with 3+ steps. Each call replaces the entire plan (send full list).\n\n" +
    "Rules: exactly ONE task in_progress at a time. Mark completed immediately after finishing. " +
    "Only mark completed when the task fully succeeded. Update frequently so the user sees progress.",
  parameters: {
    type: "object",
    required: ["todos"],
    additionalProperties: false,
    properties: {
      todos: {
        type: "array",
        description: "List of todo items",
        items: {
          type: "object",
          properties: {
            id: { type: "string", description: "Unique identifier" },
            content: { type: "string", description: "Task description" },
            status: { type: "string", enum: ["pending", "in_progress", "completed"], description: "Status" },
          },
          required: ["id", "content", "status"],
        },
      },
    },
  },
  handler: planToolHandler,
};

export function getCurrentPlan() {
  return currentPlan;
}
