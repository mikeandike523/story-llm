import pickle
from openai import OpenAI
import re
import shutil
import os
from sanitize_filename import sanitize

# Clear out the debug folder if it exists
if os.path.isdir("example-stories/flatland/processed/summaries"):
    shutil.rmtree("example-stories/flatland/processed/summaries")

os.makedirs("example-stories/flatland/processed/summaries")

OPENAI_API_KEY = None
with open("OPENAI_API_KEY.txt", "r") as f:
    OPENAI_API_KEY = f.read().strip()

client = OpenAI(api_key=OPENAI_API_KEY)

# Load native structure from pickle file.
with open("example-stories/flatland/processed/native_structure.pkl", "rb") as f:
    native_structure = pickle.load(f)

total_sections = 0
total_errors = 0

# Iterate over parts and sections.
for part_name, part_sections in native_structure:
    print(f"Processing Part: \"{part_name}\"")
    for section_name, section_paragraphs in part_sections:
        print(f"Processing Section: \"{section_name}\"")
        section_summary = ""

        system_prompt = """
        Please summarize each paragraph into a single sentence.
        Format the response as a numbered list (1., 2., 3., etc.) followed by the sentence.
        """

        # Join the section paragraphs with double newline
        user_prompt = "\n\n".join(section_paragraphs)

        original_text_path = f"example-stories/flatland/processed/summaries/{sanitize(part_name)}/{sanitize(section_name)}/original_text.txt"
        summary_path = f"example-stories/flatland/processed/summaries/{sanitize(part_name)}/{sanitize(section_name)}/summary.txt"

        os.makedirs(os.path.dirname(original_text_path), exist_ok=True)

        with open(original_text_path, "w", encoding="utf-8") as f:
            f.write(user_prompt)

        try:
            # Call the OpenAI ChatCompletion API (Switch model to "gpt-3.5-turbo" if preferred)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5,
                max_tokens=None
            )

            # Extract the output content.
            section_summary = response.choices[0].message.content.strip()

            os.makedirs(os.path.dirname(summary_path), exist_ok=True)

  

            # Split response into non-empty lines and trim spaces.
            numbered_list = [
                line.strip() for line in section_summary.split("\n")
                if line.strip() != ""
            ]

            for line in numbered_list:
                if not re.match(r"^\d+\.\s", line):
                    raise ValueError(
                        f"Invalid format for summary line: '{line}'. Expected format: 'number. summary sentence.'"
                    )
                
            section_summary = "\n".join(numbered_list)

            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(section_summary)

            total_sections += 1

        except Exception as e:
            print(f"An error occurred while processing section \"{section_name}\": {str(e)}")
            total_errors += 1

print(f"Total sections processed: {total_sections}")
print(f"Total errors encountered: {total_errors}")