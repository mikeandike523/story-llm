import pickle
from dataclasses import dataclass
from typing import List, Union
from openai import OpenAI
from typing import List, Literal, TypedDict
from termcolor import colored
import requests
from time import sleep
import re
import prompt_toolkit as pt


# Note to self
# If the api rejects the "function" role (i.e. not supported by a model or api)
# Use the "user" role and have a consistent prefix
# e.g role="user", content="[external-data]: ...."
# you can even engineer things more carefully by adding an additional system or user message to explain the meaning of the prefix format
# You can try user or system for this
# Using the user role may be a more conversational way to introduce the system and better groups it with the follwing messages
# You can also try adding this to the initial "system" message (most models are designed to take only one system message at the start)
# You can observe if this leads to more consistent understanding of the custom prefix, but this also
# adds to the cognitive load of the system prompt
# it may be wise to try both approaches and see which one works best


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


# Load the book_data from the pickle file
with open("example-stories/flatland/processed/aggregated_data.pkl", "rb") as f:
    book_data = pickle.load(f)

# Assuming book_data is structured as below:
# book_data = [
#     {
#         "name": "...",
#         "original_text": "...",
#         "summary_statements": ["..."]  # list of strings
#     },
#     ...
# ]

# Convert the list of dictionaries to a list of SectionData instances
book_sections = [SectionData(**section_dict) for section_dict in book_data]

OPENAI_API_KEY = None
with open("OPENAI_API_KEY.txt", "r", encoding="utf-8") as f:
    OPENAI_API_KEY = f.read().strip()

client = OpenAI(api_key=OPENAI_API_KEY)


class AIResponseInvalidFormat(Exception):
    """Exception raised when the AI response doesn't follow the expected format."""

    def __init__(self, message="AI response format is invalid", raw_response=None):
        self.message = message
        self.raw_response = raw_response
        super().__init__(self.message)


def get_completion_0(dialog: Dialog, temperature=0.5, max_tokens=None):
    response = None
    while response is None:
        response = requests.post(
            "https://aisecure.cmihandbook.com/completion", json=dialog
        )
        if response.status_code == 503:
            print(
                colored(
                    "Local LLM server is full up, please wait a few seconds and try again.",
                    "yellow",
                )
            )
            sleep(5)
            response = None
            continue
        if response.status_code != 200:
            print(response.text)
            raise Exception(f"Unexpected status code: {response.status_code}")
    response_json = response.json()
    return response_json["content"].strip()


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



def validate_and_get_rank(completion: str) -> float:
    
    
    if not completion.strip():
        raise AIResponseInvalidFormat("Completion is empty or contains only whitespace")

    # Prepare the string by stripping and padding with a whitespace on each end.
    padded = " " + completion.strip() + " "

    # Regex explanation:
    #   \s+         - one or more whitespace characters
    #   (\d+(?:\.\d+)?) - one or more digits, optionally followed by a dot and one or more digits (the percentage value)
    #   %           - a literal percent sign
    #   \s+         - one or more whitespace characters
    pattern = r'\s+(\d+(?:\.\d+)?)%\s+'

    match = re.search(pattern, padded)
    if not match:
        raise AIResponseInvalidFormat(
            f"Invalid completion format: '{completion}'. Expected a percentage with whitespace on both sides."
        )

    try:
        value = float(match.group(1))
        return value / 100
    except ValueError as e:
        raise AIResponseInvalidFormat(
            f"Invalid percentage found: '{match.group(1)}%'."
        ) from e


def ask(conversation):
    question = get_user_input(
        'Ask a question about "Flatland" by Edwin Abbot, or type "!quit" to quit:\n',
        ["!quit"],
    )
    if question is None:
        print("Goodbye!")
        return "!quit"

    print(f"Getting rankings...")

    rankings = {}

    for section in book_sections:
        print(f"Ranking section: {section.name}")
        completion = get_completion_0(
            [
                {
                    "role": "system",
                    "content": """
Rank the relevancy on a scale of 0% to 100% of the given book chapter given a list of summary statements.

Format your output as a number followed by a percent sign.
Only state the number and percent sign and nothing else.

""".strip(),
                },
                {"role": "user", "content": f"[Question to Address]: {question}"},
                {
                    "role": "user",
                    "content": f'[Section Name]: "{section.name}"',
                },
                {
                    "role": "user",
                    "content": f"[Summary Statements]:\n\n{'\n'.join(
                        map(lambda statement: ' - ' + statement, section.summary_statements)
                    )}",
                },
            ]
        )
        rankings[section.name] = validate_and_get_rank(completion)

    # find top ranked section and get the object from book_sections

    top_ranked_section = max(rankings, key=rankings.get)
    top_ranked_section_object = next(
        section for section in book_sections if section.name == top_ranked_section
    )

    print(colored(f"Top Ranked Section: {top_ranked_section}", "blue"))

    answer = get_completion_0(
        [
            {
                "role": "system",
                "content": """
Answer the question with respect to the summary statements of the chapter.

""".strip(),
            },
            {"role": "user", "content": f"[Question to Address]: {question}"},
            {
                "role": "user",
                "content": f'[Section Name]: "{top_ranked_section_object.name}"',
            },
            {
                "role": "user",
                "content": f"[Summary Statements]:\n\n{'\n'.join(
                        map(lambda statement: ' - ' + statement, top_ranked_section_object.summary_statements)
                    )}",
            },
        ]
    )

    print(colored(answer, "green"))

    return "!continue"


def main():
    retval = None
    conversation = []
    while retval != "!quit":
        retval = ask(conversation)


if __name__ == "__main__":
    main()
