#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request


DEFAULT_PROMPT = (
    "Solve this carefully. Find the smallest positive integer n such that n leaves remainder 1 "
    "when divided by 2, remainder 2 when divided by 3, remainder 3 when divided by 4, remainder 4 "
    "when divided by 5, remainder 5 when divided by 6, and is divisible by 7. Explain briefly and "
    "end with FINAL: <number>."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe Wellflow behavior while varying max_tokens."
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("WELLFLOW_BASE_URL", "https://api.wellflow.dev/v1"),
        help="OpenAI-compatible base URL.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("WELLFLOW_API_KEY", ""),
        help="API key. Defaults to WELLFLOW_API_KEY.",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("WELLFLOW_MODEL", "claude-opus-4.6"),
        help="Model id to test.",
    )
    parser.add_argument(
        "--reasoning-effort",
        default=os.environ.get("WELLFLOW_REASONING_EFFORT", "high"),
        help="reasoning_effort value to keep fixed while varying max_tokens.",
    )
    parser.add_argument(
        "--max-tokens",
        nargs="+",
        type=int,
        default=[5, 500, 2000],
        help="List of max_tokens values to compare.",
    )
    parser.add_argument(
        "--prompt",
        default=DEFAULT_PROMPT,
        help="Prompt to send.",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Print full JSON responses instead of a compact summary.",
    )
    return parser.parse_args()


def request_json(url: str, *, api_key: str, payload: dict) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.loads(response.read().decode("utf-8"))


def preview(text: str, limit: int = 260) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def main() -> int:
    args = parse_args()
    if not args.api_key:
        print(
            "Missing API key. Pass --api-key or set WELLFLOW_API_KEY.", file=sys.stderr
        )
        return 2

    endpoint = args.base_url.rstrip("/") + "/chat/completions"

    try:
        print(f"model: {args.model}")
        print(f"reasoning_effort: {args.reasoning_effort}")
        print(f"max_tokens values: {args.max_tokens}")
        print(f"prompt: {args.prompt}")
        print()

        for max_tokens in args.max_tokens:
            payload = {
                "model": args.model,
                "reasoning_effort": args.reasoning_effort,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": args.prompt}],
            }
            started_at = time.perf_counter()
            body = request_json(endpoint, api_key=args.api_key, payload=payload)
            elapsed_ms = round((time.perf_counter() - started_at) * 1000, 1)

            if args.raw:
                print(f"=== max_tokens={max_tokens} ({elapsed_ms} ms) ===")
                print(json.dumps(body, indent=2))
                print()
                continue

            choice = body.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content", "")
            finish_reason = choice.get("finish_reason")
            usage = body.get("usage", {})

            print(f"=== max_tokens={max_tokens} ({elapsed_ms} ms) ===")
            print(f"finish_reason: {finish_reason}")
            print(f"usage: {json.dumps(usage, sort_keys=True)}")
            print(f"output: {preview(content)}")
            print()

    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code}: {error_body}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
