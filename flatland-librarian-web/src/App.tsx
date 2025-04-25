import { css } from "@emotion/react";
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
import { MdError } from "react-icons/md";
import { io, Socket } from "socket.io-client";
import { Button, Div, H1, H2, Span, Textarea } from "style-props-html";
import { v4 as uuidv4 } from "uuid";

import "./App.css";

import LoadingSpinner from "./components/LoadingSpinner";
import useMeasureElement from "./hooks/useMeasureElement";
import {
  ProgressUpdate,
  TaskDone,
  TaskError,
  TaskMessage,
} from "./types/server-messages";
import decorationsToCSS from "./utils/decorationsToCss";

const BASE_URL = "http://localhost:8080";
const MAX_LOGS = 50;

const colorPalette = createColorPalette();

type AugmentedToken = ParseToken & {
  style: CSSProperties;
};

function App() {
  const [question, setQuestion] = useState("");
  const numLines = question.split("\n").length;
  const socketRef = useRef<Socket | null>(null);
  const questionContainerRef = useRef<HTMLDivElement>(null);
  const logsContainerRef = useRef<HTMLDivElement>(null);
  const qcHeight = useMeasureElement<HTMLDivElement, number>(
    questionContainerRef,
    (element) => element.clientHeight
  );

  const [logs, setLogs] = useState<[string, AugmentedToken[]][]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answer, setAnswer] = useState<string | null>(null);
  // const fancyLog = useCallback(
  //   (message: string) => {
  //     console.log(message);
  //     const tokens = parseAnsiSequences(message);
  //     const existingLogs = [...logs];
  //     while (existingLogs.length >= MAX_LOGS) {
  //       existingLogs.shift();
  //     }
  //     existingLogs.push([
  //       uuidv4(),
  //       tokens.map((token) => {
  //         return {
  //           ...token,
  //           style: decorationsToCSS(new Set(token.decorations)),
  //         };
  //       }),
  //     ]);
  //     setLogs(existingLogs);
  //   },
  //   [logs]
  // );

  const fancyLog = useCallback((message: string) => {
    setLogs((prevLogs) => {
      const existingLogs = [...prevLogs];
      while (existingLogs.length >= MAX_LOGS) {
        existingLogs.shift();
      }
      existingLogs.push([
        uuidv4(),
        parseAnsiSequences(message).map((token) => {
          return {
           ...token,
            style: decorationsToCSS(new Set(token.decorations)),
          };
        }),
      ]);
      return existingLogs;
    })
  },[])

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

  const fetchAnswer = useCallback(
    async function fetchAnswer() {
      clearLogs();
      setAnswer(null);
      setIsProcessing(true);
      try {
        // 1) Begin task
        const beginRes = await fetch(`${BASE_URL}/begin`);
        if (!beginRes.ok)
          throw new Error(`Begin failed: ${beginRes.statusText}`);
        const { task_id: taskId } = await beginRes.json();
        if (!taskId) throw new Error("No task_id in /begin response");

        // 2) Connect socket
        const socket = io(BASE_URL, { transports: ["websocket"] });
        socketRef.current = socket;

        socket.on("connect", () => {
          fancyLog("[SocketIO] connected");
          socket.emit("join", { task_id: taskId });
          fancyLog(`[SocketIO] joined room: ${taskId}`);

          // 3) send question
          fetch(`${BASE_URL}/ask`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ task_id: taskId, payload: question }),
          }).catch((err) => {
            fancyLog(`[Error] failed to /ask: ${err.message}`);
            socket.disconnect();
          });
        });

        socket.on("progress", (data: ProgressUpdate) => {
          fancyLog(`[Progress] ${data.progress}% - ${data.message}`);
        });

        socket.on("message", (data: TaskMessage) => {
          fancyLog(data.message);
        });

        socket.on("done", (data: TaskDone) => {
          fancyLog("[Done]");
          setAnswer(data.result);
          setIsProcessing(false);
          socket.disconnect();
        });

        socket.on("final_error", (data: TaskError) => {
          fancyLog(`[Fatal Error] ${data.message}`);
          setError(data.message);
          setIsProcessing(false);
          socket.disconnect();
        });

        socket.on("error", (data: TaskError) => {
          fancyLog(`[Error] ${data.message}`);
        });

        socket.on("disconnect", () => {
          fancyLog("[SocketIO] disconnected");
          setIsProcessing(false);
        });
      } catch (error) {
        setError(
          error instanceof Error
            ? error.message
            : "Unknown error. You can check the browser console for more details."
        );
        setIsProcessing(false);
      }
    },
    [fancyLog, question]
  );

  return (
    <Div
      width="100dvw"
      height="100dvh"
      display="grid"
      gridTemplateRows="1fr"
      gridTemplateColumns="1fr 1fr"
    >
      <Div
        display="grid"
        gridTemplateColumns="1fr"
        gridTemplateRows="auto 1fr"
        borderRight="2px solid black"
      >
        <Div
          display="flex"
          flexDirection="column"
          padding="0.5rem"
          gap="0.5rem"
          borderBottom="2px solid black"
          alignItems="center"
          ref={questionContainerRef}
        >
          <H1
            padding="0.5rem"
            fontSize="1.5rem"
            width="100%"
            textAlign="center"
          >
            Flatland Librarian
          </H1>
          <H2 width="100%" textAlign="center" fontSize="1rem">
            Ask a question about "Flatland" by Edwin Abbot.
          </H2>
          <Textarea
            disabled={isProcessing}
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
          <Button
            position="relative"
            fontSize="1.25rem"
            padding="0.25rem"
            onClick={fetchAnswer}
            userSelect="none"
            transformOrigin="center"
            display="flex"
            alignItems="center"
            justifyContent="center"
            borderRadius="0.25rem"
            minWidth="5rem"
            disabled={isProcessing || question.trim().length === 0}
            css={css`
              border: none;
              background-color: hsl(210, 100%, 90%);
              cursor: pointer;
              color: hsl(150, 75%, 25%);
              transform: scale(1);
              &:disabled {
                opacity: 0.65;
                cursor: ${isProcessing ? "progress" : "auto"};
                transform: scale(0.95);
              }
              &:hover:not(:disabled) {
                background-color: hsl(210, 100%, 55%);
                transform: scale(1.05);
                color: hsl(150, 80%, 80%);
              }
              &:active:not(:disabled) {
                background-color: hsl(210, 100%, 40%);
                transform: scale(0.95);
                color: hsl(150, 90%, 90%);
              }
              transition: transform 0.1s ease-in-out, opacity 0.1 ease-in-out,
                background-color 0.1s ease-in-out;
            `}
          >
            <Span
              color="inherit"
              fontWeight="bold"
              opacity={isProcessing ? 0.0 : 1.0}
              transition="opacity 0.1s ease-in-out"
            >
              Go!
            </Span>
            <LoadingSpinner
              position="absolute"
              top="0"
              right="0"
              left="0"
              bottom="0"
              show={isProcessing}
              spinnerPrimaryColor="hsl(150, 75%, 25%)"
              spinnerSecondaryColor="transparent"
              size="1rem"
              thickness={3}
              spinnerBackgroundColor="transparent"
              periodSeconds={1}
              fadeSeconds={0.1}
            />
          </Button>
          {error && (
            <Div
              padding="0.25rem"
              fontSize="1rem"
              color="black"
              border="2px solid hsl(0, 100%, 50%)"
              borderRadius="0.25rem"
              display="flex"
              flexDirection="row"
              alignItems="flex-start"
              flex-wrap="wrap"
              gap="0.5rem"
            >
              <MdError size="1rem" />
              <Span whiteSpace="pre-wrap">{error}</Span>
            </Div>
          )}
        </Div>
        <Div
          ref={logsContainerRef}
          height={`calc(100dvh - ${qcHeight}px - 2px)`}
          overflowX="hidden"
          overflowY="auto"
          display="flex"
          flexDirection="column"
        >
          {logs.map(([u, tokens]) => (
            <div
              key={u}
              style={{
                fontSize: "1rem",
                width: "100%",
                whiteSpace: "pre-wrap",
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
                    whiteSpace: "pre-wrap",
                    backgroundColor: colorPalette.value(
                      token.background ?? { type: "rgb", rgb: [255, 255, 255] }
                    ),
                    color: colorPalette.value(
                      token.foreground ?? { type: "rgb", rgb: [0, 0, 0] }
                    ),
                    fontFamily: "monospace",
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
      <Div
        width="100%"
        height="100dvh"
        whiteSpace="pre-wrap"
        padding="0.5rem"
        fontSize="1rem"
        overflowX="hidden"
        overflowY="auto"
        opacity={answer ? 1.0 : 0.0}
      >
        {answer ?? ""}
      </Div>
    </Div>
  );
}

export default App;
