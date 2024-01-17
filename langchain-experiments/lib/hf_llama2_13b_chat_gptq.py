import requests
import os
from dotenv import load_dotenv
from json import JSONDecodeError
import os

load_dotenv()

API_KEY = os.getenv("HUGGINGFACEHUB_API_TOKEN")
API_URL = "https://z8afrqamxvaaitmf.us-east-1.aws.endpoints.huggingface.cloud"
headers = {
    "Accept" : "application/json",
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def query(template, model_params = None, **params):
    if model_params  is None:
        model_params = {
            "temperature": 0.1,
            "max_new_tokens": 2000
        }
    prompt = template.format_map(params)
    payload = {
        "inputs": f"<s>[INST] <<SYS>>You are a helpful assistant. No comments or explanation, just answer the question.<</SYS>>{prompt}[/INST]",
        "parameters": model_params
    }
    response = requests.post(API_URL, headers=headers, json=payload)
    response.raise_for_status()
    try:
        return response.json()[0].get("generated_text")
    except JSONDecodeError:
        with open('tmp/response.txt', "w", encoding='utf-8') as f:
            f.write(response.text)
        raise RuntimeError(f'Cannot parse response from {response.url}. See tmp/response.txt')
