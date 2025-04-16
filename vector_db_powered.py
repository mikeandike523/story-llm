from collections import Counter
import pickle
import traceback
from typing import List, Literal, OrderedDict, TypedDict, Union
from dataclasses import dataclass
import os

import prompt_toolkit as pt
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import requests
from termcolor import colored


MODEL_PATH = os.path.realpath("example-stories/flatland/processed/embedding-model")
INDEX_PATH = os.path.realpath("example-stories/flatland/processed/faiss-index.index")
METADATA_PATH = os.path.realpath(
    "example-stories/flatland/processed/index_metadata.pkl"
)

DEFAULT_DISTANCE_THRESHOLD = 1.25
DEFAULT_TEMPERATURE = 0.5
DEFAULT_TOP_P = 0.9
DEFAULT_MAX_TOKENS = None
DEFAULT_K = 20
# For a chapter to be relevant, it must have at lest this proportion of the "votes" (k nearest vectors)
CHAPTER_RELEVANCY_CUTOFF_FRACTION = 0.75

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


def query_vector_db(
    query: str, k: int = DEFAULT_K, distance_threshold: float = DEFAULT_DISTANCE_THRESHOLD
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
        user_input = input(prompt)
        if not user_input.strip():
            print("Please enter a valid response.")
            user_input = None
            continue
        if user_input.strip() in cancel_strings:
            return None

    return user_input.strip()


def format_summary_sentences(summary_statements: List[str]) -> str:
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
        print(f"Error occurred while making the request: {e}")
        return None
    
def attempt_answer_question_by_chapter(chapter_name, chapter_text):

    dialog = [

        {
            "role":"system",
            "content": """
You will answer the user's question in the context of the provided chapter.

If the chapter is truly not relevant to question, reply !!!IRRELEVANT!!!

""".strip()
        },
        {
            "role":"user",
            "content":f"""


""".strip()
        },

    ]


def ask() -> str:

    question = get_user_input(
        "Ask a question about 'Flatland' by Edwin Abbot, or type '!quit' to quit:\n"
    )

    if question == "!quit":
        return "!quit"

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

    print("Chapter hit frequencies:")

    for chapter_name, count in counts.items():
        print(f"{colored(chapter_name, 'blue', attrs=['bold'])}: {count}")

    total_counts = sum(counts.values())
    proportions = {chapter: count / total_counts for chapter, count in counts.items()}

    winner_chapters = []

    for chapter, proportion in proportions.items():
        if proportion >= CHAPTER_RELEVANCY_CUTOFF_FRACTION:
            winner_chapters.append(chapter)

    print(f"Chapters with at least {CHAPTER_RELEVANCY_CUTOFF_FRACTION * 100:.0f}% relevance:")

    for chapter in winner_chapters:
        print(f"{colored(chapter, 'blue', attrs=['bold'])}")


    return None


def main():
    
    
    retval = None
    while retval != "!quit":
        try:
            retval = ask()
        except Exception as e:
            print(colored(f"""
All primary and backup analysis methods failed.

This may be due to internal token limits, or other server errors.

Please try asking the question again, or try again later if it is a network issue.

Contact michaelsohnenacademic@gmail.com for assistance.                        

Error:

{str(e)}

Traceback:

{traceback.format_exc()}
                          """.strip(), "red"))
    print("Goodbye!")


if __name__ == "__main__":
    main()
