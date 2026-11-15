"""Gemma 4 31B (Gemini API / Google AI Studio) client."""

import argparse
import os
import sys

from google import genai
from google.genai import types

MODEL_ID = "gemma-4-31b-it"


def get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit(
            "Environment variable GEMINI_API_KEY is not set. "
            "Set it from a GitHub Secret or a local .env file."
        )
    return genai.Client(api_key=api_key)


def generate(
    prompt: str,
    system_instruction: str | None = None,
    thinking_level: str = "minimal",
) -> str:
    client = get_client()
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            thinking_config=types.ThinkingConfig(thinking_level=thinking_level),
        ),
    )
    return response.text


def main() -> None:
    parser = argparse.ArgumentParser(description=f"Chat with {MODEL_ID} via the Gemini API")
    parser.add_argument("prompt", help="Prompt text")
    parser.add_argument("--system", default=None, help="System instruction")
    parser.add_argument(
        "--thinking",
        choices=["high", "minimal"],
        default="minimal",
        help="Thinking level: 'high' enables reasoning, 'minimal' disables it",
    )
    args = parser.parse_args()

    try:
        print(generate(args.prompt, system_instruction=args.system, thinking_level=args.thinking))
    except SystemExit as e:
        print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
