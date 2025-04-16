from dataclasses import dataclass
import os
import pickle
import re
import sys
import traceback
from collections import Counter
from typing import List, Literal, TypedDict, Union

import faiss
import prompt_toolkit as pt
import requests
from sentence_transformers import SentenceTransformer
from termcolor import colored

MODEL_PATH = os.path.realpath("example-stories/flatland/processed/embedding-model")
INDEX_PATH = os.path.realpath("example-stories/flatland/processed/faiss-index.index")
METADATA_PATH = os.path.realpath(
    "example-stories/flatland/processed/index_metadata.pkl"
)

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

REQUEST_URL = "https://aisecure.cmihandbook.com/completion"

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
with open("example-stories/flatland/processed/aggregated_data.pkl", "rb") as f:
    book_data = pickle.load(f)

# Convert the list of dictionaries to a list of SectionData instances
book_sections = [SectionData(**section_dict) for section_dict in book_data]


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


def get_user_input(
    prompt: str, cancel_strings: Union[str, List[str], None] = None
) -> Union[str, None]:
    user_input = None
    if cancel_strings is None:
        cancel_strings = []
    if isinstance(cancel_strings, str):
        cancel_strings = [cancel_strings]
    while user_input is None:
        user_input = pt.prompt(prompt)
        if not user_input.strip():
            print("Please enter a valid response.")
            user_input = None
            continue
        if user_input.strip() in cancel_strings:
            return None

    return user_input.strip()


def format_summary_statements(summary_statements: List[str]) -> str:
    return "\n".join(
        f"{i+1}. {sentence}" for i, sentence in enumerate(summary_statements)
    )


def get_local_llama_completion(
    dialog: Dialog,
    temperature=DEFAULT_TEMPERATURE,
    top_p=DEFAULT_TOP_P,
    max_tokens=DEFAULT_MAX_TOKENS,
):

    # Note: max_tokens, if None, should be encoded as null in the json

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

        return completion["content"]

    except requests.RequestException as e:
        print(
            colored(
                f"Network error.\n{e}\nHowever sometimes this can occur when chapter text is too long. Attempting backup strategy",
                "red",
            )
        )
        return None


def attempt_answer_question_by_chapter(question, chapter_name, chapter_text):

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

    reply = get_local_llama_completion(dialog, max_tokens=SHORT_RESPONSE_MAX_TOKENS)

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
    question, chapter_name, summary_statements
):

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

    reply = get_local_llama_completion(dialog, max_tokens=SHORT_RESPONSE_MAX_TOKENS)

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


def parse_command(command_text):
    items = re.split(r"\s+", command_text.strip())
    return items[0], items[1:] if len(items) > 1 else []


def run_command(command, *args):
    if command == "!quit" or command == "!bye" or command == "!exit":
        print(colored("Goodbye!", "green"))
        sys.exit(0)
    elif command == "!help":
        print("Help text under construction...")
        return

    # Fallthrough is when no command matches
    print(colored(f"Invalid command: {command}", "red"))


def LLM_classify_input(
    input_text: str,
) -> Literal["sensible", "accidental", "command", "unsure"]:
    return "sensible"
    dialog = [
        {
            "role": "system",
            "content": """
Judge whether the user input is a sensible question or statement, or it is likely to be accidental typing or an incomplete thought.

The user also has some special commands that begin with a "!", such as:

!exit
!quit
!bye
!help

If sensible, reply "sensible"

If accidental, reply "accidental"

If a command, reply "command"

If unsure, reply "unsure"
""".strip(),
        },
        {
            "role": "user",
            "content": input_text,
        },
    ]
    reply = (
        get_local_llama_completion(
            dialog,
            max_tokens=ULTRA_SHORT_RESPONSE_MAX_TOKENS,
            temperature=HIGH_CONFIDENCE_TEMPERATURE,
        )
        .strip()
        .lower()
    )

    if reply == "sensible":
        return "sensible"
    elif reply == "accidental":
        return "accidental"
    elif reply == "command":
        return "command"
    elif reply == "unsure":
        return "unsure"
    else:
        return "unsure"


def ask() -> str:

    question = get_user_input("Ask a question about 'Flatland' by Edwin Abbot:\n")
    input_class = LLM_classify_input(question)

    while input_class != "sensible":

        if input_class == "accidental":
            print("Your question has a typo or is incomplete. Please try again.")
        elif input_class == "command":
            command, args = parse_command(question)
            run_command(command, *args)
        elif input_class == "unsure":
            print("I cannot understand your question. Please try another one.")

        question = get_user_input("Ask a question about 'Flatland' by Edwin Abbot:\n")
        input_class = LLM_classify_input(question)

    relevant_paragraphs = query_vector_db(
        question, k=DEFAULT_K, distance_threshold=DEFAULT_DISTANCE_THRESHOLD
    )

    print(f"Found {len(relevant_paragraphs)} relevant paragraphs.")

    if len(relevant_paragraphs) == 0:

        print("Cannot find relevant information, sorry. Please ask another question.")

        return None

    counts = Counter()

    for paragraph_metadata in relevant_paragraphs:
        chapter_name = paragraph_metadata["chapter_name"]
        counts.update([chapter_name])

    total_counts = sum(counts.values())
    proportions = {chapter: count / total_counts for chapter, count in counts.items()}

    print("Chapter search metrics:")

    for chapter_name, count in counts.items():
        percent = count / total_counts * 100
        print(
            f"{colored(chapter_name, 'blue', attrs=['bold'])}:  {percent:.2f}% ({count})"
        )

    winner_chapters = []

    for chapter, proportion in proportions.items():
        if proportion >= CHAPTER_RELEVANCY_CUTOFF_FRACTION:
            winner_chapters.append(chapter)

    print(
        f"Chapters with at least {CHAPTER_RELEVANCY_CUTOFF_FRACTION * 100:.0f}% relevance:"
    )

    for chapter in winner_chapters:
        print(f"{colored(chapter, 'blue', attrs=['bold'])}")

    observations = {}

    for chapter_name in winner_chapters:

        print(f"Thinking about chapter '{chapter_name}'...")

        chapter = [
            section for section in book_sections if section.name == chapter_name
        ][0]
        chapter_text = chapter.original_text
        answer = attempt_answer_question_by_chapter(
            question, chapter_name, chapter_text
        )
        if answer == "!!!IRRELEVANT!!!":
            print(
                f"After LLM reconsidered, chapter {chapter_name} is not really relevant."
            )
        elif answer is None:
            print(f"Full chapter text analysis failed. Trying summary statement analysis...")
            summary_answer = attempt_answer_question_by_summary_statements(question, chapter_name, chapter.summary_statements)
            if summary_answer == "!!!IRRELEVANT!!!":
                print(
                    f"After LLM reconsidered, chapter {chapter_name} is not really relevant."
                )
            elif summary_answer is None:
                print(f"Network or other error when analyzing with summary statements.")
            else:
                observations[chapter_name] = summary_answer
        else:
            observations[chapter_name] = answer

    print("Putting it all together...")

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

    final_answer = get_local_llama_completion(final_answer_dialog)

    print("\n" + colored(final_answer, "green", attrs=["bold"]) + "\n")

    return None


def main():

    retval = None

    while retval != "!quit":
        try:
            retval = ask()
        except Exception as e:
            print(
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
    print("Goodbye!")


if __name__ == "__main__":
    main()
