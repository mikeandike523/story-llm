import pickle
from dataclasses import dataclass
from typing import List, Union
from openai import OpenAI
from typing import List, Literal, TypedDict

from termcolor import colored

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


def validate_and_extract_section_names(completion: str) -> List[str]:
    """
    Validate the completion response and extract section names.

    Each non-empty line must follow a similar format to:
    !!![SECTION_NAME]!!! or !!! SECTION_NAME !!! or even !!! [ SECTION_NAME ] !!!
    with optional square brackets and extra whitespace allowed.
    
    The function trims whitespace and any leading/trailing square brackets
    from the resulting section name.
    
    Args:
        completion: The completion string from the AI

    Returns:
        A list of section names if all lines are valid

    Raises:
        AIResponseInvalidFormat: If any line doesn't match the expected format
    """
    import re

    # Trim whitespace at the beginning and end of the whole response
    completion = completion.strip()

    # Split the completion into lines and filter out empty ones
    lines = [line.strip() for line in completion.splitlines() if line.strip()]

    if not lines:
        raise AIResponseInvalidFormat(
            "AI response is empty or contains only whitespace", completion
        )

    # Updated pattern that allows optional square brackets and extra whitespace:
    # ^!!!\s*\[?\s*(.*?)\s*\]?\s*!!!$
    pattern = r"^!!!\s*\[?\s*(.*?)\s*\]?\s*!!!$"

    section_names = []
    for i, line in enumerate(lines):
        match = re.match(pattern, line)
        if not match:
            raise AIResponseInvalidFormat(
                f"Line {i+1} doesn't match the expected format. Got: '{line}'",
                completion,
            )
        # Extract the section name, trim extra whitespace, and remove any stray square brackets.
        section_name = match.group(1).strip().strip("[]")
        section_names.append(section_name)

    return section_names

def get_completion_0(dialog: Dialog, temperature=0.5, max_tokens=None):
    response = client.chat.completions.create(
        model="gpt-4o", temperature=temperature, max_tokens=max_tokens, messages=dialog
    )
    return response.choices[0].message.content.strip()


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


def main():
    question = get_user_input(
        'Ask a question about "Flatland" by Edwin Abbot, or type "!quit" to quit: ',
        ["!quit"],
    )
    if question is None:
        print("Goodbye!")
        return
    dialog = []
    dialog.append(
        {
            "role": "system",
            "content": """
You will receive a question about the book 'Flatland' by Edwin Abbot.

Your will be given a list of sections, and a list of summary statements for each section.

Your goal is to decide which section or sections is most likely to answer the user's question.

You should try to cite only a single section. Use multiple sections sparingly.

Format your response as follows:

!!![SECTION_NAME]!!!

If you want to cite multiple sections, put one on each line, e.g.:

!!![SECTION_NAME_1]!!!
!!![SECTION_NAME_2]!!!
!!![SECTION_NAME_3]!!!

""".strip(),
        }
    )

    dialog.extend(
        [
            {
                "role": "function",
                "name": "section_summary_retriever",
                "content": f"""
Section Name: {section.name}
Summary Statements:
{"\n".join(map(lambda statement: f" - {statement}", section.summary_statements))}
""".strip(),
            }
            for section in book_sections
        ]
    )

    dialog.append({"role": "user", "content": question})

    print("GPT is thinking...")

    completion = get_completion_0(dialog)

    try:

        selected_section_names = validate_and_extract_section_names(completion)

    except AIResponseInvalidFormat:
        print(colored("GPT couldn't figure out which parts of the book were relevant.", "red"))

    available_section_names = [section.name for section in book_sections]

    if any(
        selected_section_name not in available_section_names
        for selected_section_name in selected_section_names
    ):
        print(
            colored(
                """
GPT could not find any book sections that can help answer your question.
Try asking again or asking another question.
                      """.strip(),
                "yellow",
            )
        )

    selected_section_objects = []

    for selected_section_name in selected_section_names:
        # find first matching section by name
        for section in book_sections:
            if section.name == selected_section_name:
                selected_section_objects.append(section)
                break

    # have to implement the rest of this later
    # as a placeholder/debug
    print(colored("GPT thought that the following sections are relevant:", "green"))
    for section in selected_section_objects:
        print(colored(f" - {section.name}", "blue"))


if __name__ == "__main__":
    main()
