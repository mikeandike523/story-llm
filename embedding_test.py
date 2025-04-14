import pickle
from typing import List, TypedDict,  Literal
from dataclasses import dataclass

import numpy as np
from sentence_transformers import SentenceTransformer
import faiss



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

# Initialize your model for computing embeddings.
# 'all-MiniLM-L6-v2' is an efficient model that works well for many tasks.
model = SentenceTransformer('all-MiniLM-L6-v2')

model.save("example-stories/flatland/processed/embedding-model")



embeddings = []
metadata = []  # This will store additional info, such as section name and text
for section in book_sections:
    # Compute an embedding for the full section text (or a specific summary if that's your focus)
    embed = model.encode(section.original_text, convert_to_numpy=True)
    embeddings.append(embed)
    metadata.append({
        "name": section.name,
        "summary_statements": section.summary_statements,
        "original_text": section.original_text
    })


# Create a numpy array of embeddings. Note that FAISS requires float32.
embeddings = np.vstack(embeddings).astype("float32")

# Create a FAISS index. Here, we use a flat (brute-force) index with L2 distance.
dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)

print("Indexing complete: {} sections indexed.".format(index.ntotal))

faiss.write_index(index, "example-stories/flatland/processed/faiss-index.index")

with open("example-stories/flatland/processed/index_metadata.pkl", "wb") as fl:
    pickle.dump(metadata, fl)
    

D, I = index.search(embeddings, 2)  # top-2 because 1st result is itself
mean_distance_to_nearest = np.mean(D[:, 1])
print("Average nearest neighbor distance:", mean_distance_to_nearest)