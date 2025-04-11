import pickle
import json
import os
import argparse

parser = argparse.ArgumentParser(description="Convert a pickle file to JSON.")
parser.add_argument("input_pickle", help="Path to the pickle file.")

def main():
    args = parser.parse_args()

    input_pickle = args.input_pickle

    if not os.path.isfile(input_pickle):
        print(f"Error: '{input_pickle}' does not exist.")
        return

    with open(input_pickle, "rb") as f:
        data = pickle.load(f)

    output_json = json.dumps(data, indent=4)

    output_filename = os.path.splitext(os.path.basename(input_pickle))[0] + ".json"
    output_path = os.path.join(os.path.dirname(input_pickle), output_filename)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output_json)

    print(f"Converted '{input_pickle}' to '{output_path}'.")


if __name__ == "__main__":
    main()