"""Gemini calls: retries, model fallback, plain-text and JSON responses."""
import json
import re
import sys
import time

from google import genai
from google.genai import errors as genai_errors

import config

RETRYABLE_CODES = {429, 500, 502, 503, 504}
BACKOFF = [5, 15, 45]  # seconds between attempts, per model

_client = None
_down = None  # set once every model has failed this run; later calls fail fast


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


def generate(prompt, json_mode=False):
    """Return model text. Retries busy/rate-limit errors, then tries the next model.

    If every model was already exhausted earlier in this run, fail immediately
    instead of repeating the whole retry cycle.
    """
    global _down
    if _down is not None:
        raise RuntimeError(f"Gemini unavailable this run (skipping retries): {_down}")

    cfg = {"temperature": 0.2}
    if json_mode:
        cfg["response_mime_type"] = "application/json"
    last_err = None
    attempts = len(BACKOFF) + 1

    for model in config.GEMINI_MODELS:
        for i in range(attempts):
            try:
                resp = _get_client().models.generate_content(
                    model=model, contents=prompt, config=cfg
                )
                if resp.text:
                    return resp.text
                raise RuntimeError(f"{model}: empty response")
            except genai_errors.APIError as e:
                last_err = e
                if e.code not in RETRYABLE_CODES:
                    raise  # bad key / bad request: retrying won't help
                if i < attempts - 1:
                    wait = BACKOFF[i]
                    print(f"{model}: {e.code}, retry {i + 1}/{attempts - 1} in {wait}s",
                          file=sys.stderr)
                    time.sleep(wait)
        print(f"{model}: giving up, trying next model", file=sys.stderr)

    _down = last_err
    raise last_err or RuntimeError("no models configured")


def generate_json(prompt):
    """Like generate(), but parses the reply as JSON."""
    text = generate(prompt, json_mode=True).strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)  # tolerate code fences
    return json.loads(text)
