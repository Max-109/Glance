#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe Wellflow reasoning behavior across reasoning_effort values."
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
        "--prompt",
        default=(
            "A farmer has chickens and rabbits totaling 35 heads and 94 legs. "
            "How many chickens and rabbits are there? Answer in one short sentence."
        ),
        help="User prompt to send.",
    )
    parser.add_argument(
        "--efforts",
        nargs="+",
        default=["low", "medium", "high"],
        help="Reasoning effort values to compare.",
    )
    parser.add_argument(
        "--show-models",
        action="store_true",
        help="Fetch and print /models before probing completions.",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Print full JSON responses instead of summaries.",
    )
    return parser.parse_args()


def request_json(url: str, *, api_key: str, payload: dict | None = None) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def preview(text: str, limit: int = 200) -> str:
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

    base_url = args.base_url.rstrip("/")

    try:
        if args.show_models:
            models = request_json(f"{base_url}/models", api_key=args.api_key)
            print("=== models ===")
            print(json.dumps(models, indent=2))

        for effort in args.efforts:
            payload = {
                "model": args.model,
                "reasoning_effort": effort,
                "messages": [{"role": "user", "content": args.prompt}],
            }
            started_at = time.perf_counter()
            body = request_json(
                f"{base_url}/chat/completions",
                api_key=args.api_key,
                payload=payload,
            )
            elapsed_ms = round((time.perf_counter() - started_at) * 1000, 1)

            if args.raw:
                print(f"=== {effort} ({elapsed_ms} ms) ===")
                print(json.dumps(body, indent=2))
                continue

            message = body.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = body.get("usage", {})
            print(f"=== {effort} ({elapsed_ms} ms) ===")
            print(f"model: {body.get('model')}")
            print(f"usage: {json.dumps(usage, sort_keys=True)}")
            print(f"output: {preview(message)}")

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
