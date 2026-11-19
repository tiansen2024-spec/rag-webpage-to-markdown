# Webpage to Clean Markdown for RAG Pipelines

A lightweight Python utility that strips HTML boilerplate and converts documentation pages into clean Markdown for LLM RAG ingestion.

## 1. Offline Zero-Key Quickstart (Static HTML)

```bash
pip install -r requirements.txt
python rag_markdown_reader.py
```

**Output:**
```markdown
RAG Static Sample

# Quickstart Guide
To initialize the RAG client, set `chunk_size=512`.
```

---

## 2. Real-World Comparison: Static Fetching vs. JS Rendering on the Exact Same URL

Modern developer portals (React/Vue SPAs) inject API specifications and rate-limit tables dynamically via JavaScript. Below is a side-by-side test against our hosted dynamic documentation page:
**Test Target URL:** `https://tiansen2024-spec.github.io/rag-webpage-to-markdown/sample_dynamic_doc.html`

### Test A: Default Free Static Mode (`--mode free`)
Command:
```bash
python rag_markdown_reader.py --url "https://tiansen2024-spec.github.io/rag-webpage-to-markdown/sample_dynamic_doc.html" --mode free
```
**Actual Output A (393 chars, 0.69s — Missing All JS-Injected Specs & Tables):**
```markdown
CloudRAG API Reference (Client-Side Rendered Demo)

# Retrieval API v2 — Endpoint Specifications

This page demonstrates a typical Single-Page Application (SPA) documentation page where core technical tables are injected dynamically via client-side JavaScript.

*[Loading dynamic API specifications via JavaScript... Static HTTP clients without JS rendering will only see this placeholder.]*
```
> **Why it failed for RAG:** Standard HTTP clients (`httpx`/`requests`) only download the initial HTML shell without executing `<script>` tags. Feeding this into a vector database results in empty knowledge chunks.

### Test B: Opt-in External JS Rendering Mode (`--mode zenrows`)
Command (requires `ZENROWS_API_KEY` with headless JS rendering enabled):
```bash
export ZENROWS_API_KEY="your_key"
python rag_markdown_reader.py --url "https://tiansen2024-spec.github.io/rag-webpage-to-markdown/sample_dynamic_doc.html" --mode zenrows
```
**Actual Output B (719 chars, 2.86s — Full API Headers, Rate Limit Table & Retry Policy Recovered):**
```markdown
CloudRAG API Reference (Client-Side Rendered Demo)

# Retrieval API v2 — Endpoint Specifications

This page demonstrates a typical Single-Page Application (SPA) documentation page where core technical tables are injected dynamically via client-side JavaScript.

## 1. Authentication Header
All retrieval requests must include the `X-RAG-Token` header using a workspace bearer key.

## 2. Production Rate Limits & Quotas
| Tier | Requests / Min | Max Chunk Tokens | Concurrent Streams |
| --- | --- | --- | --- |
| Standard | 60 RPM | 4,096 tokens | 5 |
| Enterprise | 600 RPM | 32,768 tokens | 50 |

## 3. Error Retry Policy
When receiving HTTP 429, clients must implement exponential backoff starting at `1000ms`.
```

### Test Conditions & Cost Basis Comparison

| Mode | Test Condition | Output Completeness | Cost & Billing Basis |
| :--- | :--- | :--- | :--- |
| `--mode free` (Default) | Google Colab (Python 3), direct `httpx` GET (15s timeout), no JS execution | **Incomplete on SPA docs** (misses dynamically rendered DOM nodes) | **$0 (Free)** |
| `--mode zenrows` (Explicit Opt-in) | Headless browser `js_render=true` + `wait=500ms` via ZenRows API | **Complete** (executes JS and recovers full tables/specs) | **Paid / Trial Quota** (billed per API request with JS rendering weight per official pricing page) |

---

## 3. How to Enable External Rendering (Optional & Explicit Opt-in)

Paid third-party API calls are **never** triggered automatically. If your RAG ingestion pipeline is missing body text on JS-rendered documentation sites, you can opt in:

1. Get an API key from [ZenRows Official Page](https://www.zenrows.com).
   2. Run with `--mode zenrows` explicitly enabled.
