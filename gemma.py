"""Gemma 4 31B (Gemini API / Google AI Studio) client."""

import argparse
import os
import sys
import time

from google import genai
from google.genai import errors, types

MODEL_ID = "gemma-4-31b-it"
FALLBACK_MODEL_ID = "gemma-4-26b-a4b-it"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
RETRY_INTERVAL = 10.0  # fixed seconds between retries


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
    model: str = MODEL_ID,
    max_attempts: int | None = None,
) -> str:
    """Call the API, retrying 429/5xx forever by default (TPM is small; wait it out)."""
    client = get_client()
    attempt = 0
    while True:
        attempt += 1
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    thinking_config=types.ThinkingConfig(thinking_level=thinking_level),
                ),
            )
            return response.text
        except errors.APIError as e:
            if e.code not in RETRYABLE_STATUS:
                raise
            if max_attempts is not None and attempt >= max_attempts:
                raise
            print(
                f"API error {e.code} (attempt {attempt}), "
                f"retrying in {RETRY_INTERVAL:.0f}s: {str(e.message)[:120]}",
                file=sys.stderr,
            )
            time.sleep(RETRY_INTERVAL)


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
    parser.add_argument("--model", default=MODEL_ID, help="Model ID to use")
    parser.add_argument(
        "--fallback-model",
        default=FALLBACK_MODEL_ID,
        help="Model to try when the primary model keeps returning 429/503",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=None,
        help="Retry attempts per model (default: unlimited)",
    )
    args = parser.parse_args()

    try:
        try:
            print(
                generate(
                    args.prompt,
                    system_instruction=args.system,
                    thinking_level=args.thinking,
                    model=args.model,
                    max_attempts=args.max_attempts,
                )
            )
        except errors.APIError as e:
            if (
                args.fallback_model
                and args.fallback_model != args.model
                and e.code in RETRYABLE_STATUS
            ):
                print(
                    f"{args.model} unavailable (error {e.code}); "
                    f"falling back to {args.fallback_model}",
                    file=sys.stderr,
                )
                print(
                    generate(
                        args.prompt,
                        system_instruction=args.system,
                        thinking_level=args.thinking,
                        model=args.fallback_model,
                        max_attempts=args.max_attempts,
                    )
                )
            else:
                raise
    except errors.APIError as e:
        print(f"ERROR: API error {e.code}: {str(e.message)[:300]}", file=sys.stderr)
        sys.exit(1)
    except SystemExit as e:
        print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
