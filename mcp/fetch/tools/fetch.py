import urllib.error
import urllib.request

TOOL = {
    "name": "fetch",
    "description": "Fetch a URL over HTTP(S) and return the response body as text.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "http(s):// URL to fetch"},
            "max_chars": {"type": "integer", "description": "Optional cap on returned characters (default 20000)"},
        },
        "required": ["url"],
    },
}


def call(arguments: dict) -> str:
    url = arguments["url"]
    if not url.startswith(("http://", "https://")):
        raise ValueError("only http(s) URLs are supported")

    max_chars = int(arguments.get("max_chars", 20000))
    request = urllib.request.Request(url, headers={"User-Agent": "domus-ai-fetch/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read(max_chars + 1).decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        raise RuntimeError(f"fetch failed for {url}: {e}") from e

    if len(body) > max_chars:
        body = body[:max_chars] + "\n... (truncated)"
    return body
