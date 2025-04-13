import Head from "next/head";
import { useState } from "react";
import { Div, H1, Nav } from "style-props-html";

const CONVERSATION_CONTEXT_MAX_LENGTH_CHARACTERS = 10_000;
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

/**
 * Truncates a conversation to the last N messages (user, assistant, function, system, etc.)
 * whose total character count is strictly less than or equal to the provided maximum length.
 */
function snipConversationToCharacterLength(
  conversation: DialogMessage[],
  maxChars: number
): DialogMessage[] {
  // Edge cases
  if (conversation.length === 0) {
    return [];
  }
  let accChars = 0;
  let pointer = conversation.length - 1;
  const snippedConversation: DialogMessage[] = [];
  while (pointer >= 0) {
    const message = conversation[pointer];
    const nextCharCount = accChars + message.content.length;
    if (nextCharCount > maxChars) {
      break;
    }
    accChars = nextCharCount;
    pointer -= 1;
    snippedConversation.unshift(message);
  }
  return snippedConversation;
}

export default function Home() {
  const [conversation, setConversation] = useState<DialogMessage[]>([]);
  const addToConversation = (...messages: DialogMessage[]) => {
    setConversation([...conversation, ...messages]);
  };

  return (
    <>
      <Head>
        <title>Flatland Explorer</title>
        <meta name="description" content="Explore 'Flatland' by Edwin Abbot" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      <Div
        width="100dvw"
        height="100dvh"
        overflowY="auto"
        overflowX="hidden"
        display="grid"
        gridTemplateRows="auto 1fr"
        gridTemplateColumns="1fr"
      >
        <Nav
          width="100%"
          display="flex"
          flexDirection="row"
          alignItems="center"
          justifyContent="center"
          padding="0.25rem"
          background=""
        >
          <H1 fontSize="1.25rem" fontWeight="bold" padding=""></H1>
        </Nav>
      </Div>
    </>
  );
}
