import os
from fastapi import HTTPException

API_KEYS = {}

def load_api_keys():
    # Load API keys from environment variables
    api_keys_str = os.getenv('API_KEYS', '')
    for key_value in api_keys_str.split(','):
        if ':' in key_value:
            key, value = key_value.split(':')
            API_KEYS[key.strip()] = int(value.strip())

def validate_api_key(api_key: str):
    if api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")

def get_credits(api_key: str) -> int:
    return API_KEYS.get(api_key, 0)

def deduct_credits(api_key: str, amount: int):
    if API_KEYS[api_key] < amount:
        raise HTTPException(status_code=402, detail="Insufficient credits")
    API_KEYS[api_key] -= amount

# Load API keys when the module is imported
load_api_keys()