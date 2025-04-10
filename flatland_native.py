from bs4 import BeautifulSoup
from termcolor import colored
import re
from collections import OrderedDict
import pickle


def extract_structure_from_html(html_path):
    # Read and parse the HTML file.
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    soup = BeautifulSoup(html_content, "lxml")

    # Use the <body> if available; otherwise the whole document.
    container = soup.find("body") or soup
    # Get all headings (h1-h6) and paragraphs (<p>) in their document order.
    all_elements = container.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p"])

    # Step 1. Aggregate <p> content into header prior
    flat_sections = []

    for elem in all_elements:
        if elem.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            text = elem.get_text(strip=True)
            if not text:
                continue
            flat_sections.append((text, []))
        elif elem.name == "p":
            if len(flat_sections) == 0:
                print(
                    colored("Warning: got some content before first heading", "yellow")
                )
            else:
                working_flat_section = flat_sections[-1]
                text = elem.get_text(strip=True)
                if not text:
                    continue
                working_flat_section[1].append(text)

    # skip until table of contents is over

    skip_pointer = 0
    skipped_count = 0
    while skipped_count < 2:
        next_name_upper = flat_sections[skip_pointer][0].upper()
        if next_name_upper.startswith("PART I") or next_name_upper.startswith(
            "PART II"
        ):
            skipped_count += 1
        skip_pointer += 1

    flat_sections = flat_sections[skip_pointer:]

    parts = []

    for name, paragraphs in flat_sections:
        if name.upper().startswith("PART I") or name.upper().startswith("PART II"):
            parts.append((name, []))
        else:
            if not re.match(r"^Section \d+\.", name):
                continue
            if len(parts) == 0:
                print(
                    colored(
                        "Warning: got some content before first part, this should not occur for the flatland ebook.",
                        "yellow",
                    )
                )
            else:
                working_part = parts[-1]
                working_part[1].append([name, paragraphs])

    return parts


parts = extract_structure_from_html("example-stories/flatland/pg201-images.html")

# debug

for part_name, part_sections in parts:
    print(("    " * 0) + colored(part_name, "red", attrs=["bold"]))
    for section_name, section_paragraphs in part_sections:
        print(("    " * 1) + colored(section_name, "green") + " " + f"({len(section_paragraphs)} paragraphs)")
        

with open("example-stories/flatland/processed/native_structure.pkl" , "wb") as f:
    pickle.dump(parts, f)
