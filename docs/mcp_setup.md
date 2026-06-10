# MCP setup

The project ships an [MCP](https://modelcontextprotocol.io/) server that
exposes the wiki as a set of tools any MCP-aware client can call. The
goal is to make the architecture's intended workflow real:

> **Agents maintain the wiki. Humans inspect the markdown wiki. Raw
> evidence stays immutable. Schema rules control updates. Linting
> catches unsupported claims.**

## What the server exposes

| Tool | What it does |
|---|---|
| `list_cases` | Cases visible in `raw_sources/` and `wiki/cases/`. |
| `get_case_summary` | The case `index.md` plus the list of available pages. |
| `list_wiki_pages` | Markdown pages present on disk for the case. |
| `read_wiki_page` | Read a single page. Path-traversal protected; `.fw/` is off-limits. |
| `ingest_case_sources` | Compile evidence into the wiki (`changed-only` / `force` / `apply`, `dry_run`, `review`). |
| `query_case` | Wiki-first answer with `claim_NNNN` evidence and citations. |
| `lint_case` | Structured findings, four severity tiers. |
| `generate_report` | Returns the report body and whether it was queued for human review. |
| `compare_all_methods` | All four answer providers in one response. |
| `get_hypothesis_history` | Per-step confidence trajectory. |
| `get_contradictions` | Both the markdown and the structured contradicting evidence. |
| `get_open_questions` | Parses `open_questions.md` into a list. |
| `graph_query` | GraphRAG-lite relationship walk. |

## Install

```bash
pip install -e ".[dev,mcp]"   # adds the optional `mcp` SDK
```

The MCP SDK is **only** required to run the server. The tool functions
in `mcp_server/tools.py` import cleanly without it; tests cover them
directly.

## Run

```bash
python -m mcp_server.server
```

The server speaks MCP over stdio. Any MCP-aware client (Claude Desktop,
mcp-cli, a custom agent) can point at it.

## Generic client configuration

Drop something like this into your MCP client's config. Adjust the
absolute path:

```json
{
  "mcpServers": {
    "forensic-llm-wiki": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/absolute/path/to/forensic-llm-wiki"
    }
  }
}
```

If you have a virtualenv, point `command` at its Python:

```json
{
  "mcpServers": {
    "forensic-llm-wiki": {
      "command": "/absolute/path/to/forensic-llm-wiki/.venv/bin/python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/absolute/path/to/forensic-llm-wiki"
    }
  }
}
```

## What the agent demo looks like

See `docs/agent_demo.md` for example tool-call traces, including the
flagship *"Is this confirmed malware?"* question and the
*"What should I investigate next?"* follow-up.

## Limitations

- Mock LLM mode is used by default. Set `FORENSIC_WIKI_LLM=live` and
  install the `live` extra to call Claude during `ingest_case_sources`.
- No authentication. The server trusts its stdio client. Run it in user
  space, not as a network-exposed daemon.
- Path traversal is blocked in `read_wiki_page`, but mutating tools
  (`ingest_case_sources`, `generate_report`) trust their `case_id`.
  Restrict the working directory to the project root.
- Long-running flows (full ingest, evolve) take seconds. Clients may
  need a larger response timeout.
