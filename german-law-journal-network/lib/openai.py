# written with help from ChatGPT-4

import requests
import json
import os
import time
import re
from dotenv import load_dotenv

load_dotenv()


def query_openai_api(model, instruction, user_input, max_tokens=1000,
                     temperature=1, top_p=1, frequency_penalty=0,
                     presence_penalty=0, timeout=60, max_retries=3, retry_delay=5, verbose=False):
    """
    Send a request to the OpenAI API with automatic message composition.

    Args:
        model (str): The model to use for the request (e.g., 'gpt-3.5-turbo').
        instruction (str): The instruction or context for the system message.
        user_input (str): The user's input message.
        max_tokens (int, optional): The maximum number of tokens to generate. Defaults to 8192.
        temperature (float, optional): The sampling temperature to use. Defaults to 1.
        top_p (float, optional): The nucleus sampling (top-p) parameter. Defaults to 1.
        frequency_penalty (float, optional): The frequency penalty parameter. Defaults to 0.
        presence_penalty (float, optional): The presence penalty parameter. Defaults to 0.
        timeout (int, optional): The maximum number of seconds to wait for an answer from the API. Defaults to 60
        max_retries (int, optional): The maximum number of retry attempts. Defaults to 3.
        retry_delay (int, optional): The delay in seconds before retrying a request. Defaults to 5.

    Returns:
        str: The response from the model

    Throws:
        ValueError: If the no API key has been set in the environment variables or any of the parameters are of the wrong type
        RuntimeError if the request fails after the given number of retries or a different GPT-4 related error occurred
    """
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("API key not found. Please check your .env file.")

    if not model.lower().startswith("gpt"):
        raise ValueError("The provided model is not compatible with the OpenAI chat API.")

    if type(instruction) is not str or type(user_input) is not str:
        raise ValueError("Instruction and user input must be a string")

    if model == "gpt-4":
        url = "https://api.openai.com/v1/chat/completions"
        messages = [
            {"role": "system", "content": instruction},
            {"role": "user", "content": user_input}
        ]
        data = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty
        }
    elif model.startswith("gpt-3.5-"):
        url = "https://api.openai.com/v1/engines/" + model + "/completions"  # Modify this URL if needed
        prompt = f"{instruction}\n\n{user_input}"
        data = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty
        }
    else:
        raise ValueError("Unsupported model. Please use 'gpt-4' or a model starting with 'gpt-3.5-'.")

    json_data = json.dumps(data)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, data=json_data, headers=headers, timeout=timeout)

            if response.status_code == 200:
                content = response.json()
                if model == "gpt-4":
                    message = content['choices'][0]['message']
                    return message['content']
                elif model.startswith("gpt-3.5-"):
                    return content['choices'][0]['text']
            else:
                error_info = response.json().get('error', {})

                if response.status_code == 429 and error_info.get('code') == 'rate_limit_exceeded':
                    retry_after_match = re.search(r"Please try again in (\d+(\.\d+)?)s", error_info['message'])
                    if retry_after_match:
                        retry_after = float(retry_after_match.group(1))
                        if verbose:
                            print(f"Rate limit exceeded. Retrying after {retry_after} seconds.")
                        time.sleep(retry_after)
                        continue  # Continue the loop to retry the request

                # Check if token budget is exhausted
                if response.status_code == 429 and error_info.get('code') == "insufficient_quota":
                    raise RuntimeError("OpenAI token budget has been exhausted.")

                # Other error
                raise RuntimeError(f"Error response from OpenAI: {response.text}")

        except requests.exceptions.RequestException:
            if verbose:
                print(f"Request timeout or other error. Attempt {attempt} of {max_retries}")

        if attempt < max_retries:
            time.sleep(retry_delay)

    raise RuntimeError("Too many retries.")
