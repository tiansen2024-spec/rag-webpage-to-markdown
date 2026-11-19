import os
import sys
import time
import argparse
from pathlib import Path
import httpx
from bs4 import BeautifulSoup
import markdownify

BUILTIN_STATIC_HTML = """<!DOCTYPE html>
<html><head><title>RAG Static Sample</title><script>console.log('tracking');</script></head>
<body><nav>Navigation</nav><main><h1>Quickstart Guide</h1><p>To initialize the RAG client, set <code>chunk_size=512</code>.</p></main>
<footer>Footer Noise</footer></body></html>"""

AFFILIATE_DISCLOSURE_BLOCK = (
    "----------------------------------------------------------------------\n"
    "[External Rendering Setup]\n"
    "When to use: When a target documentation page relies on client-side JS rendering (leaving static Markdown incomplete) or restricts direct requests.\n"
    "• ZenRows Official Entry: https://www.zenrows.com\n"
    "  (How to enable: Set environment variable ZENROWS_API_KEY and explicitly pass --mode zenrows. Calling this mode consumes your provider credits.)\n"
        "----------------------------------------------------------------------"
)

def html_to_rag_markdown(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "iframe", "noscript", "svg"]):
        tag.decompose()
    return markdownify.markdownify(str(soup), heading_style="ATX").strip()

def check_possible_restriction(resp: httpx.Response) -> bool:
    server_hdr = resp.headers.get("server", "").lower()
    body_head = resp.text[:1500].lower()
    if resp.status_code == 403 and any(k in server_hdr or k in body_head for k in [
        "cloudflare", "cf-ray", "just a moment", "datadome", "captcha", "turnstile"
    ]):
        return True
    return False

def process_source(url: str = None, file_path: str = None, mode: str = "free") -> str:
    start_ts = time.perf_counter()

    if file_path or not url:
        raw_html = Path(file_path).read_text(encoding="utf-8") if file_path else BUILTIN_STATIC_HTML
        md_out = html_to_rag_markdown(raw_html)
        elapsed = time.perf_counter() - start_ts
        print(f"[Run Log] Mode: free (offline sample) | Elapsed: {elapsed:.3f}s | Output chars: {len(md_out)}", file=sys.stderr)
        return md_out

    headers = {"User-Agent": "Mozilla/5.0 (compatible; RAGMarkdownReader/4.0)"}

    if mode == "free":
        try:
            resp = httpx.get(url, headers=headers, timeout=15.0, follow_redirects=True)
        except httpx.InvalidURL:
            raise ValueError("[Troubleshooting] Invalid URL format. Ensure http:// or https:// is included.")
        except httpx.TimeoutException:
            raise TimeoutError("[Troubleshooting] Request timed out (15s). Target server may be slow or unreachable.")
        except httpx.ConnectError as e:
            raise ConnectionError(f"[Troubleshooting] Connection failed (possible DNS or network issue): {e}")
        except httpx.RequestError as e:
            raise RuntimeError(f"[Troubleshooting] Network request error: {e}")

        if resp.status_code == 404:
            raise FileNotFoundError(f"[HTTP 404] Target page not found: {url}")
        if resp.status_code == 429:
            raise RuntimeError("[HTTP 429] Possible rate limiting detected. Reduce request frequency.")
        if resp.status_code == 503:
            raise RuntimeError("[HTTP 503] Target service is temporarily unavailable.")
        if resp.status_code == 403:
            clue = " (headers/body suggest possible WAF/JS challenge)" if check_possible_restriction(resp) else " (possible access restriction)"
            raise PermissionError(
                f"[HTTP 403 Troubleshooting] Target returned 403{clue}.\n"
                f"Check the site's terms and robots.txt first. If compliant rendering is needed, opt in via --mode zenrows.\n"
                f"{AFFILIATE_DISCLOSURE_BLOCK}"
            )
        resp.raise_for_status()
        md_out = html_to_rag_markdown(resp.text)
        elapsed = time.perf_counter() - start_ts
        print(f"[Run Log] Mode: free (direct HTTP) | Elapsed: {elapsed:.3f}s | Output chars: {len(md_out)}", file=sys.stderr)
        return md_out

    elif mode == "zenrows":
        api_key = os.getenv("ZENROWS_API_KEY", "").strip()
        if not api_key:
            raise ValueError(
                "[Missing Config] You explicitly selected --mode zenrows, but ZENROWS_API_KEY is not set.\n"
                + AFFILIATE_DISCLOSURE_BLOCK
            )
        print("[Opt-in Paid Mode] Calling ZenRows API with JS rendering enabled (consumes account credits)...", file=sys.stderr)
        resp = httpx.get(
            "https://api.zenrows.com/v1/",
            params={"apikey": api_key, "url": url, "js_render": "true", "wait": "500"},
            timeout=35.0
        )
        resp.raise_for_status()
        md_out = html_to_rag_markdown(resp.text)
        elapsed = time.perf_counter() - start_ts
        print(f"[Run Log] Mode: zenrows (JS rendered) | Elapsed: {elapsed:.3f}s | Output chars: {len(md_out)}", file=sys.stderr)
        return md_out

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Web Docs to Clean Markdown for RAG.")
    parser.add_argument("--url", default=None, help="Target URL (omit to run built-in offline sample)")
    parser.add_argument("--file", default=None, help="Path to local HTML file")
    parser.add_argument("--mode", choices=["free", "zenrows"], default="free", help="Mode: 'free' (default) or 'zenrows' (opt-in)")
    args = parser.parse_args()
    print(process_source(url=args.url, file_path=args.file, mode=args.mode))
