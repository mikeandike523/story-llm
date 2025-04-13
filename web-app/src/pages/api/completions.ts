// Next.js API route support: https://nextjs.org/docs/api-routes/introduction
import type { NextApiRequest, NextApiResponse } from "next";
import { z } from "zod";
import { toSerializableObject } from "@/utils/serialization";

// Default values for optional fields.
const DEFAULT_TEMPERATURE = 0.5;
const DEFAULT_MAX_TOKENS = null;

const MODEL = "gpt-4o";

// Define the DialogMessage type (as a TypeScript union) for clarity.
// Zod will be used for runtime validation.
type DialogMessage =
  | {
      role: "system";
      content: string;
    }
  | {
      role: "assistant";
      content: string;
    }
  | {
      role: "user";
      content: string;
    }
  | {
      role: "function";
      content: string;
      name: string;
    };

// Define the overall API input type.
type APIInput = {
  temperature?: number;
  maxTokens?: number | null;
  dialog: DialogMessage[];
};

// Define the API output as a string.
type APIOutput = string;

// Define error causes as an enumeration.
enum APIErrorCause {
  InternalError = "INTERNAL_ERROR",
  InvalidInput = "INVALID_INPUT",
  Unauthorized = "UNAUTHORIZED",
  Forbidden = "FORBIDDEN",
  NotFound = "NOT_FOUND",
  GPTApiError = "GPT_API_ERROR",
}

// Define the API error type.
type APIError = {
  cause: APIErrorCause;
  message: string;
  data?: ReturnType<typeof toSerializableObject>;
};

// --- Zod schemas for runtime validation ---

// First, define schemas for each type of dialog message.
const systemMessageSchema = z.object({
  role: z.literal("system"),
  content: z.string(),
});

const assistantMessageSchema = z.object({
  role: z.literal("assistant"),
  content: z.string(),
});

const userMessageSchema = z.object({
  role: z.literal("user"),
  content: z.string(),
});

const functionMessageSchema = z.object({
  role: z.literal("function"),
  content: z.string(),
  name: z.string(),
});

// Combine the message schemas into a union type.
const dialogMessageSchema = z.union([
  systemMessageSchema,
  assistantMessageSchema,
  userMessageSchema,
  functionMessageSchema,
]);

// Define the main API input schema.
const apiInputSchema = z.object({
  // temperature is optional with a default value.
  temperature: z.number().optional().default(DEFAULT_TEMPERATURE),
  // maxTokens can be a number or null and is optional with a default.
  maxTokens: z
    .union([z.number(), z.null()])
    .optional()
    .default(DEFAULT_MAX_TOKENS),
  // dialog must be an array of dialog messages.
  dialog: z.array(dialogMessageSchema),
});

// --- API Route Handler ---

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<APIOutput>
) {
  // Only allow POST requests.
  if (req.method !== "POST") {
    res.status(405).send("Method Not Allowed");
    return;
  }

  try {
    // Validate and parse the request body using the defined schema.
    const apiInput: APIInput = apiInputSchema.parse(req.body);

    const {
      temperature = DEFAULT_TEMPERATURE,
      maxTokens = DEFAULT_MAX_TOKENS,
      dialog,
    } = apiInput;

    // Call GPT completions api

    // We can safely assume the role of the completion will be "assistant".
    // So we send back only the content

    const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
    if (!OPENAI_API_KEY) {
      console.error("Missing OPENAI_API_KEY environment variable.");
      const apiError: APIError = {
        cause: APIErrorCause.InternalError,
        message: "A system error occurred.",
      };
      res.status(401).send(JSON.stringify(apiError));
      return;
    }

    // Prepare the payload for the GPT API.
    const payload: {
      model: string;
      messages: DialogMessage[];
      temperature: number;
      max_tokens?: number;
    } = {
      model: MODEL,
      messages: dialog,
      temperature,
    };

    // Only include max_tokens if maxTokens is not null.
    if (maxTokens !== null) {
      payload.max_tokens = maxTokens;
    }

    // Call the OpenAI GPT completions API.
    const response = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${OPENAI_API_KEY}`,
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorData = await response.json();
      const errorMessage =
        errorData.error?.message || "Error communicating with GPT API";

      let cause = APIErrorCause.GPTApiError;
      let isDueToInsufficientFunds = false;

      if (response.status === 402) {
        cause = APIErrorCause.GPTApiError;
        isDueToInsufficientFunds = true;
      } else if (response.status === 429) {
        if (
          errorMessage.toLowerCase().includes("quota") ||
          errorMessage.toLowerCase().includes("insufficient")
        ) {
          cause = APIErrorCause.GPTApiError;
          isDueToInsufficientFunds = true;
        }
      }

      const apiError: APIError = {
        cause,
        message: isDueToInsufficientFunds
          ? "This organization ran out of funding to offer our services for free. We are working on creating a donation portal. Stay tuned!"
          : errorMessage,
      };

      res.status(response.status).send(JSON.stringify(apiError));
      return;
    }

    // Parse the JSON response from the GPT API.
    const data = await response.json();

    // Extract the assistant's reply from the response. We assume that the first choice is what we need.
    const assistantReply = data.choices[0]?.message?.content;
    if (typeof assistantReply !== "string") {
      const apiError: APIError = {
        cause: APIErrorCause.InternalError,
        message: "Invalid response from GPT API",
      };
      res.status(500).send(JSON.stringify(apiError));
      return;
    }

    // Send the assistant's response content back to the client.
    res.status(200).send(assistantReply);
  } catch (err) {
    // If the error is a ZodError, it means validation failed.
    if (err instanceof z.ZodError) {
      const apiError: APIError = {
        cause: APIErrorCause.InvalidInput,
        message: "Validation failed",
        data: toSerializableObject(err.issues, {
          enumerableOnly: true,
          circularMode: "ignore",
          nonPrimitivesMode: "reportType",
          undefinedMode: "ignore",
        }),
      };
      res.status(400).send(JSON.stringify(apiError));
    } else {
      // Any other errors are considered internal server errors.
      const apiError: APIError = {
        cause: APIErrorCause.InternalError,
        message: "Internal server error",
      };
      res.status(500).send(JSON.stringify(apiError));
    }
  }
}
