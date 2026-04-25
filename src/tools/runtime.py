from __future__ import annotations

import base64
import html
import json
import mimetypes
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote_plus, urlparse
from urllib.request import Request, urlopen

from src.agents.screen_capture_agent import ScreenCaptureAgent
from src.exceptions.app_exceptions import GlanceError, ValidationError
from src.models.interactions import ToolCallRecord
from src.models.settings import AppSettings


@dataclass(frozen=True)
class ToolImage:
    path: str
    mime_type: str = "image/png"


@dataclass(frozen=True)
class ToolResult:
    content: str
    result_path: str = ""
    artifact_paths: list[str] = field(default_factory=list)
    images: list[ToolImage] = field(default_factory=list)


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters_schema: dict[str, Any]
    pre_speech_notice: str
    timeout_seconds: float
    executor: Callable[[dict[str, Any]], ToolResult]

    def provider_payload(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            },
        }


@dataclass(frozen=True)
class ToolCallRequest:
    call_id: str
    name: str
    arguments: dict[str, Any]


class ToolExecutionError(GlanceError):
    """Raised when a runtime tool cannot complete safely."""


class RuntimeToolRegistry:
    def __init__(
        self,
        settings: AppSettings,
        *,
        screen_capture_agent: ScreenCaptureAgent | None = None,
    ) -> None:
        self._settings = settings
        self._screen_capture_agent = screen_capture_agent
        self._definitions = self._build_definitions()

    @property
    def enabled_definitions(self) -> list[ToolDefinition]:
        if not self._settings.tools_enabled:
            return []
        return [
            definition
            for name, definition in self._definitions.items()
            if self._policy_for_tool(name) == "allow"
        ]

    def get(self, name: str) -> ToolDefinition | None:
        if not self._settings.tools_enabled:
            return None
        definition = self._definitions.get(name)
        if definition is None or self._policy_for_tool(name) != "allow":
            return None
        return definition

    def _policy_for_tool(self, name: str) -> str:
        if name == "take_screenshot":
            return self._settings.tool_take_screenshot_policy
        if name == "web_search":
            return self._settings.tool_web_search_policy
        if name == "web_fetch":
            return self._settings.tool_web_fetch_policy
        return "deny"

    def _build_definitions(self) -> dict[str, ToolDefinition]:
        return {
            "take_screenshot": ToolDefinition(
                name="take_screenshot",
                description=(
                    "Capture the user's current screen when visual context is needed "
                    "to answer the live request."
                ),
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "Brief reason the screenshot is needed.",
                        }
                    },
                    "additionalProperties": False,
                },
                pre_speech_notice="I'll take a quick screenshot.",
                timeout_seconds=6,
                executor=self._take_screenshot,
            ),
            "web_search": ToolDefinition(
                name="web_search",
                description=(
                    "Search the web for current public information. Use this when "
                    "the answer depends on recent facts, pricing, schedules, or other "
                    "details likely to change."
                ),
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The exact search query.",
                        },
                        "max_results": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 8,
                            "description": "Maximum number of results to return.",
                        },
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
                pre_speech_notice="I'll search the web for that.",
                timeout_seconds=12,
                executor=_web_search,
            ),
            "web_fetch": ToolDefinition(
                name="web_fetch",
                description=(
                    "Read a specific public http or https page and return concise "
                    "page text for reasoning."
                ),
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The http or https URL to read.",
                        }
                    },
                    "required": ["url"],
                    "additionalProperties": False,
                },
                pre_speech_notice="I'll read that page.",
                timeout_seconds=12,
                executor=_web_fetch,
            ),
        }

    def _take_screenshot(self, arguments: dict[str, Any]) -> ToolResult:
        del arguments
        if self._screen_capture_agent is None:
            raise ToolExecutionError("Screen capture is not available in this runtime.")
        temp_file = tempfile.NamedTemporaryFile(
            prefix="glance-tool-screenshot-",
            suffix=".png",
            delete=False,
        )
        temp_file.close()
        screenshot_path = self._screen_capture_agent.run(output_path=temp_file.name)
        return ToolResult(
            content=(
                "Screenshot captured. Use the attached image as visual context for "
                "the user's request."
            ),
            artifact_paths=[screenshot_path],
            images=[ToolImage(path=screenshot_path, mime_type="image/png")],
        )


class ToolExecutor:
    def __init__(self, registry: RuntimeToolRegistry) -> None:
        self._registry = registry

    def execute(self, call: ToolCallRequest) -> tuple[ToolCallRecord, ToolResult]:
        started_at = _utc_now()
        definition = self._registry.get(call.name)
        if definition is None:
            return _error_execution(
                call,
                started_at,
                "Tool is unavailable or disabled.",
            )

        try:
            _validate_arguments(definition.parameters_schema, call.arguments)
            result = _run_with_timeout(
                definition.executor,
                call.arguments,
                timeout_seconds=definition.timeout_seconds,
                tool_name=definition.name,
            )
        except Exception as exc:
            return _error_execution(call, started_at, _safe_error_message(exc))

        record = ToolCallRecord(
            call_id=call.call_id,
            tool_name=call.name,
            status="success",
            arguments_summary=_arguments_summary(call.name, call.arguments),
            result_preview=_preview(result.content),
            result_path=result.result_path,
            artifact_paths=list(result.artifact_paths),
            started_at=started_at,
            finished_at=_utc_now(),
        )
        return record, result


def file_to_data_url(path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(path.name)
    if not mime_type:
        mime_type = "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _run_with_timeout(
    executor: Callable[[dict[str, Any]], ToolResult],
    arguments: dict[str, Any],
    *,
    timeout_seconds: float,
    tool_name: str,
) -> ToolResult:
    pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"glance-{tool_name}")
    future = pool.submit(executor, arguments)
    try:
        return future.result(timeout=timeout_seconds)
    except TimeoutError as exc:
        future.cancel()
        raise ToolExecutionError(f"{tool_name} timed out.") from exc
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


def _error_execution(
    call: ToolCallRequest,
    started_at: str,
    message: str,
) -> tuple[ToolCallRecord, ToolResult]:
    result = ToolResult(content=f"{call.name} failed: {message}")
    record = ToolCallRecord(
        call_id=call.call_id,
        tool_name=call.name,
        status="error",
        arguments_summary=_arguments_summary(call.name, call.arguments),
        result_preview=_preview(result.content),
        error=message,
        started_at=started_at,
        finished_at=_utc_now(),
    )
    return record, result


def _validate_arguments(schema: dict[str, Any], arguments: dict[str, Any]) -> None:
    if not isinstance(arguments, dict):
        raise ValidationError("Tool arguments must be an object.")
    required = schema.get("required", [])
    for field_name in required:
        if field_name not in arguments:
            raise ValidationError(f"Missing required argument: {field_name}.")
    properties = schema.get("properties", {})
    if schema.get("additionalProperties") is False:
        unexpected = set(arguments) - set(properties)
        if unexpected:
            raise ValidationError(
                f"Unexpected argument: {sorted(unexpected)[0]}."
            )
    for field_name, value in arguments.items():
        field_schema = properties.get(field_name, {})
        expected_type = field_schema.get("type")
        if expected_type == "string" and not isinstance(value, str):
            raise ValidationError(f"{field_name} must be text.")
        if expected_type == "integer" and (
            not isinstance(value, int) or isinstance(value, bool)
        ):
            raise ValidationError(f"{field_name} must be a whole number.")
        if "minimum" in field_schema and value < field_schema["minimum"]:
            raise ValidationError(f"{field_name} is below the minimum.")
        if "maximum" in field_schema and value > field_schema["maximum"]:
            raise ValidationError(f"{field_name} is above the maximum.")
        if "enum" in field_schema and value not in field_schema["enum"]:
            raise ValidationError(f"{field_name} is not allowed.")


def _web_search(arguments: dict[str, Any]) -> ToolResult:
    query = str(arguments.get("query", "")).strip()
    if not query:
        raise ValidationError("Search query cannot be empty.")
    max_results = int(arguments.get("max_results", 5))
    search_url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    body = _read_url(search_url, timeout_seconds=10, max_bytes=800_000)
    results = _parse_duckduckgo_results(body)[:max_results]
    if not results:
        raise ToolExecutionError("Search returned no readable results.")

    text_lines = [f"Search query: {query}", ""]
    for index, result in enumerate(results, start=1):
        text_lines.append(f"{index}. {result['title']}")
        text_lines.append(f"   {result['url']}")
        if result.get("snippet"):
            text_lines.append(f"   {result['snippet']}")
    content = "\n".join(text_lines)
    return ToolResult(
        content=content,
        result_path=_write_temp_result(
            "glance-web-search-",
            ".json",
            json.dumps({"query": query, "results": results}, indent=2),
        ),
    )


def _web_fetch(arguments: dict[str, Any]) -> ToolResult:
    url = str(arguments.get("url", "")).strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValidationError("URL must start with http:// or https://.")
    body = _read_url(url, timeout_seconds=10, max_bytes=1_200_000)
    text = _html_to_text(body)
    if not text:
        raise ToolExecutionError("Page returned no readable text.")
    title = _extract_title(body) or parsed.netloc
    content = f"Fetched page: {title}\nURL: {url}\n\n{text[:12000]}"
    return ToolResult(
        content=content,
        result_path=_write_temp_result("glance-web-fetch-", ".md", content),
    )


def _read_url(url: str, *, timeout_seconds: float, max_bytes: int) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 Glance/1.0"
            )
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ToolExecutionError("Response was too large to read safely.")
        content_type = response.headers.get_content_charset() or "utf-8"
    return data.decode(content_type, errors="replace")


class _SearchResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._current_link: str = ""
        self._current_text: list[str] = []
        self._capture_link = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attr_map = {name: value or "" for name, value in attrs}
        href = attr_map.get("href", "")
        css_class = attr_map.get("class", "")
        if "result__a" in css_class or href.startswith("http"):
            self._current_link = href
            self._current_text = []
            self._capture_link = True

    def handle_data(self, data: str) -> None:
        if self._capture_link:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or not self._capture_link:
            return
        title = html.unescape(" ".join(self._current_text)).strip()
        if title and self._current_link:
            self.results.append(
                {
                    "title": _squash_whitespace(title),
                    "url": _normalize_duckduckgo_url(self._current_link),
                    "snippet": "",
                }
            )
        self._capture_link = False
        self._current_link = ""
        self._current_text = []


def _parse_duckduckgo_results(body: str) -> list[dict[str, str]]:
    parser = _SearchResultParser()
    parser.feed(body)
    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for result in parser.results:
        url = result["url"]
        if not url.startswith("http") or url in seen:
            continue
        seen.add(url)
        deduped.append(result)
    return deduped


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if tag in {"p", "br", "li", "h1", "h2", "h3", "h4", "article", "section"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if tag in {"p", "li", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)


def _html_to_text(body: str) -> str:
    extractor = _TextExtractor()
    extractor.feed(body)
    return _squash_whitespace("\n".join(extractor.parts))


def _extract_title(body: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", body, flags=re.IGNORECASE | re.S)
    if match is None:
        return ""
    return _squash_whitespace(html.unescape(match.group(1)))


def _normalize_duckduckgo_url(url: str) -> str:
    if url.startswith("//"):
        return f"https:{url}"
    return html.unescape(url)


def _write_temp_result(prefix: str, suffix: str, content: str) -> str:
    temp_file = tempfile.NamedTemporaryFile(
        prefix=prefix,
        suffix=suffix,
        mode="w",
        encoding="utf-8",
        delete=False,
    )
    try:
        temp_file.write(content)
    finally:
        temp_file.close()
    return temp_file.name


def _arguments_summary(tool_name: str, arguments: dict[str, Any]) -> str:
    if tool_name == "take_screenshot":
        reason = str(arguments.get("reason", "")).strip()
        return f"reason: {_preview(reason, limit=80)}" if reason else "screen context"
    if tool_name == "web_search":
        return f"query: {_preview(str(arguments.get('query', '')), limit=80)}"
    if tool_name == "web_fetch":
        parsed = urlparse(str(arguments.get("url", "")))
        return parsed.netloc or _preview(str(arguments.get("url", "")), limit=80)
    return _preview(json.dumps(arguments, ensure_ascii=False), limit=120)


def _preview(value: str, *, limit: int = 260) -> str:
    text = _squash_whitespace(value)
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rstrip()}..."


def _squash_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _safe_error_message(exc: Exception) -> str:
    if isinstance(exc, GlanceError):
        return str(exc)
    return f"{exc.__class__.__name__}: {exc}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
