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

DEFAULT_DISTANCE_THRESHOLD = 1.5
DEFAULT_TEMPERATURE = 0.5
DEFAULT_TOP_P = 0.9
DEFAULT_MAX_TOKENS = None
DEFAULT_NUM_CHAPTERS_TO_ANALYZE=3

REQUEST_URL = "http://localhost:5000/completion"

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
    query: str, k: int = DEFAULT_NUM_CHAPTERS_TO_ANALYZE, distance_threshold: float = DEFAULT_DISTANCE_THRESHOLD
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


def ask() -> str:

    question = get_user_input(
        "Ask a question about 'Flatland' by Edwin Abbot, or type '!quit' to quit:\n"
    )

    if question == "!quit":
        return "!quit"

    relevant_sections = query_vector_db(
        question, k=DEFAULT_NUM_CHAPTERS_TO_ANALYZE, distance_threshold=DEFAULT_DISTANCE_THRESHOLD
    )
    
    print(f"Found {len(relevant_sections)} relevant sections.")
    
    print("\n")
    for relevant_section in relevant_sections:
        print(f"Section: {colored(relevant_section['name'], 'blue')}")
    
    print("\n")

    outline = OrderedDict()

    for section in relevant_sections:
        print(f"Thinking about: '{section['name']}'...")
        try:
            answer = get_local_llama_completion(
                [
                    {
                        "role": "system",
                        "content": f"""
    Attempt to answer the question about "Flatland" by Edwin Abbot
    in the context of the provided book chapter text.
    
    If the text is truly irrelevant, reply with !!!IRRELEVANT!!!
                    """,
                    },
                    {"role": "user", "content": f"[Question to Address]: {question}"},
                    {
                        "role": "user",
                        "content": f"""
    [Chapter Title]: '{section['name']}'
    [Chapter Text]:

    {section['original_text'].strip()}
                    """.strip(),
                    },
                ]
            )

            if not (
                "!!!IRRELEVANT!!!" in answer.upper()
                or "!!IRRELEVANT!!" in answer.upper()
            ):
                print("Full chapter text analysis successful.")
                outline[section["name"]] = answer
            else:
                    print(f"""
On second thought, durring full chapter text analysis,
LLM thought '{section['name']}' was irrelevant.
                          """.strip())
        except Exception as e:
            print(
                f"Could not analyze entire chapter text, going to try with pre-baked summary statements: {e}"
            )

            try:
                answer = get_local_llama_completion(
                    [
                        {
                            "role": "system",
                            "content": f"""
    Attempt to answer the question about "Flatland" by Edwin Abbot in the context
    of the provided summary statements.
    
    If the statements are truly irrelevant, reply with !!!IRRELEVANT!!!
                    """,
                        },
                        {
                            "role": "user",
                            "content": f"[Question to Address]: {question}",
                        },
                        {
                            "role": "user",
                            "content": f"""
    [Chapter Title]: '{section['name']}'
    [Summary Statements]:

    {format_summary_sentences(section['summary_statements']).strip()}
                    """.strip(),
                        },
                    ]
                )

                if not (
                    "!!!IRRELEVANT!!!" in answer.upper()
                    or "!!IRRELEVANT!!" in answer.upper()
                ):
                    outline[section["name"]] = answer
                    print("Summary statement analysis successful.")
                else:
                    print(f"""
On second thought, durring summary statement analysis,
LLM thought '{section['name']}' was irrelevant.
                          """.strip())

            except Exception as e:
                print(f"Error occurred while making the LLM completion request: {e}")

    essay_skeleton = f"\n\n{'='*10}\n\n".join(
        [
            f"""
        
Chapter: {section_name}

Observations:

{answer}
        
        """.strip()
            for section_name, answer in outline.items()
        ]
    )

    print(f"""
Finished creating essay skeleton from {len(outline)} relevant sections.
{len(relevant_sections)-len(outline)} of the initial sections were irrelevant.
""".strip())
    
    print("Writing essay...")
    
    essay = get_local_llama_completion(
        [
            {
                "role":"system",
                "content":f"""
Please write a cohesive essay essay about "Flatland" by Edwin Abbot
that attempts to answer a given question (thesis) using the provided outline.
                """
            },
            {
                "role":"user",
                "content":f"[Question to Address]: {question}"
            },
            {
                "role":"user",
                "content":f"""
[Essay Outline]:

{essay_skeleton.strip()}                
                
                """.strip()
            }
        ]
    )
    
    print(colored(essay, "green", attrs=["bold"]) + "\n")

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
