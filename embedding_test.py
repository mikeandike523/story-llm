import pickle
from typing import List, TypedDict, Literal
from dataclasses import dataclass

import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from tqdm import tqdm


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

print("Loading embedding model...")

# Initialize your model for computing embeddings.
# 'all-MiniLM-L6-v2' is an efficient model that works well for many tasks.
model = SentenceTransformer("all-MiniLM-L6-v2")

print("Arranging metadata...")

metadata = []
for section in book_sections:
    section_name = section.name.replace("\r\n", "\n").strip()
    section_text_paragraphs = [
        para.strip()
        for para in section.original_text.replace("\r\n", "\n").strip().split("\n\n")
        if para.strip()
    ]

    for i, paragraph in enumerate(section_text_paragraphs):
        subsection = {
            "chapter_name": section_name,
            "text": paragraph,
            "number": i + 1,  # 1-indexed
        }
        metadata.append(subsection)

embeddings = []

print("Computing embeddings...")

for item in tqdm(metadata, desc="Encoding paragraphs"):
    # Encode the paragraph text into a vector
    vector = model.encode(item["text"])
    embeddings.append(vector)

print("Saving embedding model...")

model.save("example-stories/flatland/processed/embedding-model")

embeddings = np.vstack(embeddings).astype("float32")


print("Constructing FAISS index...")

dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)

print("Indexing complete: {} sections indexed.".format(index.ntotal))

print("Saving FAISS index...")
faiss.write_index(index, "example-stories/flatland/processed/faiss-index.index")


print("Saving metadata...")
with open("example-stories/flatland/processed/index_metadata.pkl", "wb") as fl:
    pickle.dump(metadata, fl)

print("Computing index metrics...")

D, I = index.search(embeddings, 2)  # top-2 because 1st result is itself
mean_distance_to_nearest = np.mean(D[:, 1])
median_distance_to_nearest = np.median(D[:, 1])
min_distance_to_nearest = np.min(D[:, 1])
max_distance_to_nearest = np.max(D[:, 1])

print("Average nearest neighbor distance:", mean_distance_to_nearest)
print("Median nearest neighbor distance:", median_distance_to_nearest)
print("Minimum nearest neighbor distance:", min_distance_to_nearest)
print("Maximum nearest neighbor distance:", max_distance_to_nearest)