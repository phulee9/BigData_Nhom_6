import json
import os
import time

import requests
from dotenv import load_dotenv


load_dotenv(override=True)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def get_groq_api_keys():
    # Lấy danh sách Groq keys
    keys = []

    for index in range(1, 10):
        key = os.getenv(f"GROQ_API_KEY_{index}")

        if key and key.strip():
            keys.append(key.strip())

    keys = list(dict.fromkeys(keys))

    if not keys:
        raise ValueError("Missing GROQ_API_KEY_1, GROQ_API_KEY_2, ... in .env")

    return keys


def parse_json_response(response_json):
    # Parse JSON từ response
    content = response_json["choices"][0]["message"]["content"]

    if isinstance(content, dict):
        return content

    return json.loads(content)


def call_groq_json(prompt, temperature=0, timeout=120):
    # Gọi Groq, tự chuyển key nếu lỗi
    api_keys = get_groq_api_keys()
    last_error = None

    for key_index, api_key in enumerate(api_keys, start=1):
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": temperature,
            "response_format": {
                "type": "json_object",
            },
        }

        try:
            response = requests.post(
                GROQ_API_URL,
                headers=headers,
                json=payload,
                timeout=timeout,
            )

            response.raise_for_status()

            return parse_json_response(response.json())

        except Exception as error:
            last_error = error
            print(f"Groq error key {key_index}/{len(api_keys)}: {error}")
            time.sleep(2)

    raise RuntimeError(f"All Groq keys failed. Last error: {last_error}")