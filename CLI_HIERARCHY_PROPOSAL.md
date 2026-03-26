# CLI Hierarchy and Naming Convention Proposal

## 1. Goal
Simplify the current long, flat CLI commands into a hierarchical and concise structure for better usability and extensibility.

## 2. Core Prefix Strategy
Use 2-letter prefixes as the primary command groups:
- **`ri` (Read-it):** Core services for fetching, summarizing, and storing reading materials (URLs).
- **`ei` (Eval-it):** Infrastructure for evaluating the quality of summaries and data.

## 3. Hierarchical Structure

### `ri` (Read-it) Command Group
- `ri fetch <URL>`: Fetch raw data from a URL.
- `ri sum <fetch_result>`: Summarize the fetched content.
- `ri push <target>`: Send data to specific destinations.
    - `ri push p`: Send to personal storage (GitHub Discussions).
    - `ri push q`: Send to processing/evaluation queue.

### `ei` (Eval-it) Command Group
- `ei add <summary>`: Add a summary to the evaluation queue.
- `ei check <URL>`: Verify if a URL already exists in the evaluation queue.
- `ei run`: (Future) Trigger evaluation pipeline.

## 4. `pyproject.toml` Mapping (Example)

Instead of multiple flat entries, we will use `Click`'s grouping feature:

```toml
[project.scripts]
ri = "endpoint.readit.cli:ri"
ei = "endpoint.evalit.cli:ei"
```

## 5. Benefits
1. **Conciseness:** `endpoint-readit-fetch` (21 chars) → `ri fetch` (8 chars).
2. **Discoverability:** `ri --help` shows all related subcommands in one place.
3. **Pipelining:** Encourages usage like `ri fetch URL | ri sum | ri push p`.
4. **Scalability:** New features can be added as subcommands (e.g., `ei report`, `ri list`) without cluttering the global command namespace.
