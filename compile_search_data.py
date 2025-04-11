from sanitize_filename import sanitize
import pickle
import re

def get_path_to_summary(part_name, section_name):
    return f"example-stories/flatland/processed/summaries/{sanitize(part_name)}/{sanitize(section_name)}/summary.txt"

def get_path_to_original_text(part_name, section_name):
    return f"example-stories/flatland/processed/summaries/{sanitize(part_name)}/{sanitize(section_name)}/original_text.txt"

book = None

with open("example-stories/flatland/processed/native_structure.pkl", "rb") as f:
    book = pickle.load(f)

aggregated_data = []

for part_name, part_sections in book:
    print(f"Processing Part: {part_name}")
    for section_name, section_paragraphs in part_sections:
        print(f"Processing Section: {section_name}")
        summary_path = get_path_to_summary(part_name, section_name)
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = f.read().strip()
        section_aggregate_data = {}

        # We attempt to use re to remove a prefix "Section <digits>.<one or more whitespace>" from the section name.

        section_name_no_prefix = re.sub(r"^Section \d+\.\s+", "", section_name)

        section_aggregate_data["name"] = section_name_no_prefix

        summary_lines = summary.split("\n")

        cleaned_lines = []

        for line in summary_lines:
            stripped = line.strip()
            if not stripped:
                continue
            cleaned_lines.append(stripped)

        # Data validation 1:
        # ensure each clean line begins with "<digits>.<one or more whitespace>"
        for line in cleaned_lines:
            if not re.match(r"^\d+\.\s", line):
                raise ValueError(f"Invalid format for summary line: '{line}'. Expected format: 'number. summary sentence.'")
            
        # remove the leading digit, dot and whitespace from each line
        cleaned_lines = [
            re.sub(r"^\d+\.\s+", "", line) for line in cleaned_lines
        ]

        section_aggregate_data["summary_statements"] = cleaned_lines

        original_text_path = get_path_to_original_text(part_name, section_name)

        with open(original_text_path, "r", encoding="utf-8") as f:
            original_text = f.read().strip()

        section_aggregate_data["original_text"] = original_text

        aggregated_data.append(section_aggregate_data)

with open("example-stories/flatland/processed/aggregated_data.pkl", "wb") as f:
    pickle.dump(aggregated_data, f)


        