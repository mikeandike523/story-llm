import {
  createColorPalette,
  parseAnsiSequences,
  ParseToken,
} from "ansi-sequence-parser";
import {
  ChangeEvent,
  CSSProperties,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { Button, Div, H1, H2, Textarea } from "style-props-html";
import { v4 as uuidv4 } from "uuid";
import decorationsToCSS from "./utils/decorationsToCss";

import "./App.css";

const MAX_LOGS = 50;

const colorPalette = createColorPalette();

type AugmentedToken = ParseToken & {
  style: CSSProperties;
};

function App() {
  const [question, setQuestion] = useState("");
  const numLines = question.split("\n").length;
  const logsContainerRef = useRef<HTMLDivElement>(null);

  const [logs, setLogs] = useState<[string, AugmentedToken[]][]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fancyLog = useCallback(
    (message: string) => {
      const tokens = parseAnsiSequences(message);
      const existingLogs = [...logs];
      while (existingLogs.length >= MAX_LOGS) {
        existingLogs.shift();
      }
      existingLogs.push([
        uuidv4(),
        tokens.map((token) => {
          return {
            ...token,
            style: decorationsToCSS(new Set(token.decorations)),
          };
        }),
      ]);
      setLogs(existingLogs);
    },
    [logs]
  );

  const clearLogs = () => {
    setLogs([]);
  };

  useEffect(() => {
    const logsContainer = logsContainerRef.current;
    if (logsContainer) {
      logsContainer.scrollTo({
        top: logsContainer.scrollHeight,
        left: 0,
        behavior: "smooth",
      });
    }
  }, [logs]);

  async function fetchAnswer() {
    setIsProcessing(true);
    try {
      // todo
    } catch (error) {
      setIsProcessing(false);
      setError(
        error instanceof Error
          ? error.message
          : "Unknown error. You can check the browser console for more details."
      );
    }
    clearLogs();
  }

  return (
    <Div
      width="100dvw"
      height="100dvh"
      display="grid"
      gridTemplateRows="1fr"
      gridTemplateColumns="1fr 1.5fr"
    >
      <Div
        display="grid"
        gridTemplateColumns="1fr"
        gridTemplateRows="auto auto 1.75fr"
        borderRight="2px solid black"
      >
        <H1 padding="0.5rem" fontSize="1.5rem" width="100%" textAlign="center">
          Flatland Librarian
        </H1>
        <Div
          display="flex"
          flexDirection="column"
          padding="0.5rem"
          gap="0.5rem"
          borderBottom="2px solid black"
          alignItems="center"
        >
          <H2 width="100%" textAlign="center" fontSize="1rem">
            Ask a question about "Flatland" by Edwin Abbot.
          </H2>
          <Textarea
            width="100%"
            fontSize="1rem"
            lineHeight="1.5"
            resize="none"
            rows={numLines + 1}
            value={question}
            onChange={(e: ChangeEvent<HTMLTextAreaElement>) => {
              setQuestion(e.target.value);
            }}
          ></Textarea>
          <Button fontSize="1rem" padding="0.25rem" onClick={fetchAnswer}>
            Go!
          </Button>
        </Div>
        <Div
          ref={logsContainerRef}
          height="50dvh"
          borderBottom="2px solid black"
          overflowX="hidden"
          overflowY="auto"
        >
          {logs.map(([u, tokens]) => (
            <div
              key={u}
              style={{
                fontSize: "1rem",
                width: "100%",
              }}
            >
              {tokens.map((token, tokenIndex) => (
                <span
                  key={tokenIndex}
                  // backgroundColor={colorPalette.value(
                  //   token.background ?? { type: "rgb", rgb: [255, 255, 255] }
                  // )}
                  // color={colorPalette.value(
                  //   token.foreground ?? { type: "rgb", rgb: [0, 0, 0] }
                  // )}
                  style={{
                    backgroundColor: colorPalette.value(
                      token.background ?? { type: "rgb", rgb: [255, 255, 255] }
                    ),
                    color: colorPalette.value(
                      token.foreground ?? { type: "rgb", rgb: [0, 0, 0] }
                    ),
                    fontFamily: "monospace",
                    whiteSpace: "pre-wrap",
                    ...token.style,
                  }}
                >
                  {token.value}
                </span>
              ))}
            </div>
          ))}
        </Div>
      </Div>
      <Div></Div>
    </Div>
  );
}

export default App;
