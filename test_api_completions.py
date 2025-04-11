import requests
import json

def test_api_completions():
    # Define the URL to your API endpoint running locally on port 3000.
    url = "http://localhost:3000/api/completions"

    # Construct the JSON payload.
    # Make sure to provide a valid list of dialog messages.
    payload = {
        "temperature": 0.5,
        "maxTokens": 50,  # Use an integer or null (if supported)
        "dialog": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the capital of France?"}
        ]
    }

    try:
        # Send a POST request with the JSON payload.
        response = requests.post(url, json=payload)

        # Output the response status and content.
        print("Status Code:", response.status_code)
        print("Response:")
        try:
            # Attempt to decode the response as JSON.
            print(json.dumps(response.json(), indent=2))
        except ValueError:
            # Fallback to raw text output if response isn't JSON.
            print(response.text)
    except requests.RequestException as e:
        print("Error while connecting to the API:", e)

if __name__ == "__main__":
    test_api_completions()
