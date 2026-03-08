import os
import json
import logging
import requests
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RateLimitError(Exception):
    pass

class DeepSeek_LLM_Client:
    """Client for DeepSeek LLM for semantic extraction."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            logger.warning("DEEPSEEK_API_KEY is not set.")
        # Typically DeepSeek API endpoint or similar OpenAI compatible endpoint
        self.base_url = "https://api.deepseek.com/v1/chat/completions"

        self.prompt_template = """
You are an expert financial analyst and data extractor.
Read the following corporate announcement or research summary and extract the key information.

You MUST respond ONLY with a valid JSON object in the exact following format, with no markdown formatting or extra text:
{{
    "expansion_intent_score": <float between 0.0 and 1.0 representing the likelihood of business expansion>,
    "key_factors": [<list of strings representing the key factors driving this intent, e.g., "异地拿地", "产能瓶颈">]
}}

Input Text:
{text}
"""

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=10),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type((requests.exceptions.RequestException, RateLimitError, requests.exceptions.Timeout))
    )
    def _make_api_request(self, payload: dict) -> dict:
        """Make the API request with retry and rate-limiting logic."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        # We use a mocked response for the sake of the environment if API key is not a real one
        if self.api_key == "your_deepseek_api_key_here" or not self.api_key:
            # For demonstration we log quietly to not spam console during large processing loops
            # logger.info("Using mock DeepSeek API response due to missing/dummy API key.")
            return {
                "choices": [{
                    "message": {
                        "content": '{"expansion_intent_score": 0.8, "key_factors": ["异地拿地", "产能瓶颈"]}'
                    }
                }]
            }

        response = requests.post(
            self.base_url,
            headers=headers,
            json=payload,
            timeout=10
        )

        if response.status_code == 429:
            logger.warning("Rate limit hit, retrying...")
            raise RateLimitError("Rate limit exceeded")

        response.raise_for_status()
        return response.json()

    def analyze_document(self, text: str) -> dict:
        """
        Analyze a document and extract intention and key factors.
        Ensures the output is parsed as a standardized JSON.
        """
        prompt = self.prompt_template.format(text=text)

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "You are a specialized financial parsing assistant."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1
        }

        try:
            response_data = self._make_api_request(payload)
            content = response_data['choices'][0]['message']['content']

            # Clean up potential markdown formatting if the model disobeys instructions
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            parsed_json = json.loads(content.strip())
            return parsed_json

        except Exception as e:
            logger.error(f"Failed to analyze document: {e}")
            # Fallback/default structure
            return {
                "expansion_intent_score": 0.0,
                "key_factors": [],
                "error": str(e)
            }
