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
            "temperature": 0.1
        }
    prompt = template.format_map(params)
    payload = {
        "inputs": f"<s>[INST] <<SYS>>You are a helpful assistant. You keep your answers short. When asked to provide data such as CSV data or JSON as response, do not return additional comments or notes.<</SYS>>{prompt}[/INST]",
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
