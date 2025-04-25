from collections import Counter
import re
from socket import SocketIO
import traceback
from uuid import UUID
from server_types import TaskRequest
from task_updates import emit_final_error, emit_progress, emit_done, emit_error, emit_message
import time
import os
import pickle
from sentence_transformers import SentenceTransformer
import faiss
from typing import List, Union, TypedDict, Literal
from dataclasses import dataclass
import requests
from termcolor import colored


DEFAULT_DISTANCE_THRESHOLD = 1.5
DEFAULT_TEMPERATURE = 0.5
DEFAULT_TOP_P = 0.9
DEFAULT_MAX_TOKENS = None
SHORT_RESPONSE_MAX_TOKENS = 256
ULTRA_SHORT_RESPONSE_MAX_TOKENS = 32
DEFAULT_K = 50
# For a chapter to be relevant, it must have at lest this proportion of the "votes" (k nearest vectors)
CHAPTER_RELEVANCY_CUTOFF_FRACTION = 0.05
HIGH_CONFIDENCE_TEMPERATURE = 0.5

# REQUEST_URL = "http://localhost:5000/completion"
REQUEST_URL = "https://aisecure.cmihandbook.com/completion"

script_dir = os.path.dirname(os.path.realpath(__file__))

outer_dir = os.path.dirname(script_dir)

MODEL_PATH = os.path.join(
    outer_dir, "example-stories/flatland/processed/embedding-model"
)
INDEX_PATH = os.path.join(
    outer_dir, "example-stories/flatland/processed/faiss-index.index"
)
METADATA_PATH = os.path.join(
    outer_dir, "example-stories/flatland/processed/index_metadata.pkl"
)
AGGREGATED_DATA_PATH = os.path.join(
    outer_dir, "example-stories/flatland/processed/aggregated_data.pkl"
)


print("Loading metadata...", end=" ")

with open(METADATA_PATH, "rb") as fl:
    metadata = pickle.load(fl)

print("Done.")

print("Loading embedding model...", end=" ")

model = SentenceTransformer("all-MiniLM-L6-v2")
model.load(MODEL_PATH)

print("Done.")

print("Loading faiss index...", end=" ")

index = faiss.read_index(INDEX_PATH)

print("Done.")


class DialogMessage(TypedDict):
    role: Literal["system", "user", "assistant", "function"]
    content: str


Dialog = List[DialogMessage]


@dataclass
class SectionData:
    """
    Represents a section of a book.

    Attributes:
        name (str): The title or identifier for the section.
        original_text (str): The full original text of the section.
        summary_statements (List[str]): A list of summary sentences extracted from the section.
    """

    name: str
    original_text: str
    summary_statements: List[str]


print("Loading book data...")

# Load the book_data from the pickle file
with open(AGGREGATED_DATA_PATH, "rb") as f:
    book_data = pickle.load(f)

# Convert the list of dictionaries to a list of SectionData instances
book_sections = [SectionData(**section_dict) for section_dict in book_data]


def answer_question(socketio: SocketIO, task_request: TaskRequest):
    # Dummy task for now
    task_id = task_request.task_id
    for i in range(1, 11):
        time.sleep(1)
        emit_progress(socketio, task_id, i * 10, f"Step {i} complete")
    emit_done(socketio, task_id, "All done successfully")


class DialogMessage(TypedDict):
    role: Literal["system", "user", "assistant", "function"]
    content: str


Dialog = List[DialogMessage]


@dataclass
class SectionData:
    """
    Represents a section of a book.

    Attributes:
        name (str): The title or identifier for the section.
        original_text (str): The full original text of the section.
        summary_statements (List[str]): A list of summary sentences extracted from the section.
    """

    name: str
    original_text: str
    summary_statements: List[str]


def query_vector_db(
    query: str,
    k: int = DEFAULT_K,
    distance_threshold: float = DEFAULT_DISTANCE_THRESHOLD,
):
    """
    Performs a vector search on the FAISS index and returns only the results with distance under the threshold.

    Args:
        query (str): The user's query.
        k (int): The maximum number of results to return.
        distance_threshold (float): Maximum allowed L2 distance for results to be considered relevant.

    Returns:
        List[dict]: Filtered list of relevant section metadata.
    """
    query_embedding = model.encode(query, convert_to_numpy=True).astype("float32")
    distances, indices = index.search(query_embedding.reshape(1, -1), k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if dist < distance_threshold:
            results.append(metadata[idx])
        else:
            break  # Since L2 distances are sorted, we can break early

    return results


def format_summary_statements(summary_statements: List[str]) -> str:
    return "\n".join(
        f"{i+1}. {sentence}" for i, sentence in enumerate(summary_statements)
    )


def get_local_llama_completion(
    dialog: Dialog,
    socketio,
    task_id,
    temperature=DEFAULT_TEMPERATURE,
    top_p=DEFAULT_TOP_P,
    max_tokens=DEFAULT_MAX_TOKENS,
    
):
    

    # Note: max_tokens, if None, should be encoded as null in the json

    report = lambda message: emit_message(socketio, task_id, message)

    request_data = {
        "messages": dialog,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens if max_tokens is not None else None,
    }

    #  Do the post request here ...
    try:
        response = requests.post(REQUEST_URL, json=request_data)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Parse the JSON response
        completion = response.json()

        report("Done.")

        return completion["content"]

    except requests.RequestException as e:
        emit_error(socketio, task_id,
            colored(
                f"Network error.\n{e}\nHowever sometimes this can occur when chapter text is too long. Attempting backup strategy",
                "red",
            )
        )
        return None


def attempt_answer_question_by_chapter(question, chapter_name, chapter_text, socketio, task_id):

    report = lambda message: emit_message(socketio, task_id, message)
    
    report("Attempting to answer question by chapter...")

    dialog = [
        {
            "role": "system",
            "content": """
Concisely answer the user's question in the context of the provided chapter.

If the chapter is truly not relevant to question, reply !!!IRRELEVANT!!!

""".strip(),
        },
        {
            "role": "user",
            "content": f"[Question to Address]: {question.strip()}".strip(),
        },
        {
            "role": "user",
            "content": f"""

[Chapter Name]: "{chapter_name.strip()}"

[Chapter Text]:

{chapter_text.strip()}
""".strip(),
        },
    ]


    reply = get_local_llama_completion(dialog, socketio, task_id, max_tokens=SHORT_RESPONSE_MAX_TOKENS)

    if reply is None:
        return None

    flag_pattern = re.compile(
        r"(?:(?<=^)|(?<=\s))!{1,3}IRRELEVANT!{1,3}(?:(?=\s)|(?=$))",
        re.IGNORECASE | re.MULTILINE,
    )

    is_irrelevant = flag_pattern.search(reply)

    if is_irrelevant:
        return "!!!IRRELEVANT!!!"

    return reply


def attempt_answer_question_by_summary_statements(
    question, chapter_name, summary_statements, socketio, task_id
):
    
    report = lambda message: emit_message(socketio, task_id, message)
    
    report("Attempting to answer question by summary statements...")

    dialog = [
        {
            "role": "system",
            "content": """
Concisely answer the user's question in the context of the provided chapter summary statements.

If the chapter is truly not relevant to question, reply !!!IRRELEVANT!!!

""".strip(),
        },
        {
            "role": "user",
            "content": f"[Question to Address]: {question.strip()}".strip(),
        },
        {
            "role": "user",
            "content": f"""

[Chapter Name]: "{chapter_name.strip()}"

[Summary Statements]:

{format_summary_statements(summary_statements)}
""".strip(),
        },
    ]

    reply = get_local_llama_completion(dialog, socketio, task_id, max_tokens=SHORT_RESPONSE_MAX_TOKENS)

    if reply is None:
        return None

    flag_pattern = re.compile(
        r"(?:(?<=^)|(?<=\s))!{1,3}IRRELEVANT!{1,3}(?:(?=\s)|(?=$))",
        re.IGNORECASE | re.MULTILINE,
    )

    is_irrelevant = flag_pattern.search(reply)

    if is_irrelevant:
        return "!!!IRRELEVANT!!!"

    return reply



def ask(question, socketio, task_id) -> str:
    
    report = lambda message: emit_message(socketio, task_id, message)

    relevant_paragraphs = query_vector_db(
        question, k=DEFAULT_K, distance_threshold=DEFAULT_DISTANCE_THRESHOLD
    )

    report(f"Found {len(relevant_paragraphs)} relevant paragraphs.")

    if len(relevant_paragraphs) == 0:

        report("Cannot find relevant information, sorry. Please ask another question.")

        return None

    counts = Counter()

    for paragraph_metadata in relevant_paragraphs:
        chapter_name = paragraph_metadata["chapter_name"]
        counts.update([chapter_name])

    total_counts = sum(counts.values())
    proportions = {chapter: count / total_counts for chapter, count in counts.items()}

    report("Chapter search metrics:")

    for chapter_name, count in counts.items():
        percent = count / total_counts * 100
        report(
            f"{colored(chapter_name, 'blue', attrs=['bold'])}:  {percent:.2f}% ({count})"
        )

    winner_chapters = []

    for chapter, proportion in proportions.items():
        if proportion >= CHAPTER_RELEVANCY_CUTOFF_FRACTION:
            winner_chapters.append(chapter)

    report(
        f"Chapters with at least {CHAPTER_RELEVANCY_CUTOFF_FRACTION * 100:.0f}% relevance:"
    )

    for chapter in winner_chapters:
        report(f"{colored(chapter, 'blue', attrs=['bold'])}")

    observations = {}

    for chapter_name in winner_chapters:

        report(f"Thinking about chapter '{chapter_name}'...")

        chapter = [
            section for section in book_sections if section.name == chapter_name
        ][0]
        chapter_text = chapter.original_text
                
        answer = attempt_answer_question_by_chapter(
            question, chapter_name, chapter_text, socketio, task_id
        )
        if answer == "!!!IRRELEVANT!!!":
            report(
                f"After LLM reconsidered, chapter {chapter_name} is not really relevant."
            )
            report(
                f"Full chapter text analysis failed. Trying summary statement analysis..."
            )
            summary_answer = attempt_answer_question_by_summary_statements(
                question, chapter_name, chapter.summary_statements, socketio, task_id
            )
            if summary_answer == "!!!IRRELEVANT!!!":
                report(
                    f"After LLM reconsidered, chapter {chapter_name} is not really relevant."
                )
            elif summary_answer is None:
                report(f"Network or other error when analyzing with summary statements.")
            else:
                observations[chapter_name] = summary_answer
        elif answer is None:
            report("Failed to analyze full chapter text, trying summary statement analysis...")
        else:
            observations[chapter_name] = answer

    report("Putting it all together...")

    final_answer_dialog = (
        [
            {
                "role": "system",
                "content": """
Please answer the user's question based on observations about individual chapters.

Write your answer in an essay format and avoid self-referential statements such as "Based on the observations in each chapter...".

""".strip(),
            },
            {
                "role": "user",
                "content": f"[Question to Address]: {question.strip()}".strip(),
            },
        ]
        + [
            {
                "role": "user",
                "content": (
                    f"\n\n{'='*40}\n\n".join(
                        [
                            f"""
[Chapter Name]: '{chapter_name.strip()}'

[Chapter Observations]:

{observation.strip()}

""".strip()
                            for chapter_name, observation in observations.items()
                        ]
                    )
                ),
            }
        ]
    )

    final_answer = get_local_llama_completion(final_answer_dialog, socketio, task_id)

    return final_answer

def answer_question(socketio: SocketIO, task_request: TaskRequest):

    task_id = task_request.task_id
    
    question = task_request.payload

    try:
        emit_done(socketio, task_id, ask(question, socketio, task_id))
    except Exception as e:
        emit_final_error(socketio, task_id,
            colored(
                f"""
All primary and backup analysis methods failed.

This may be due to internal token limits, or other server errors.

Please try asking the question again, or try again later if it is a network issue.

Contact michaelsohnenacademic@gmail.com for assistance.                        

Error:

{str(e)}

Traceback:

{traceback.format_exc()}
                        """.strip(),
                "red",
            )
        )
