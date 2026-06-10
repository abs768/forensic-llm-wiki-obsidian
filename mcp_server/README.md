# Forensic LLM Wiki — MCP server

This package exposes the project's CLI capabilities as
[Model Context Protocol](https://modelcontextprotocol.io/) tools so any
MCP-aware client (Claude Desktop, mcp-cli, custom agents) can:

- list cases,
- read wiki pages safely (path-traversal blocked),
- ingest raw evidence (with `--review` semantics),
- query the compiled wiki,
- run lint and compose reports,
- compare all four answer methods,
- inspect contradictions, open questions, and hypothesis history,
- walk the GraphRAG-lite relationship graph.

## Installation

The `mcp` SDK is an **optional** dependency. Install it with the dev
extras:

```bash
pip install -e ".[dev,mcp]"
```

If you don't need the MCP runtime (e.g. just running tests or the CLI),
you don't need the SDK. The tools themselves live in
`mcp_server/tools.py` and import cleanly without it.

## Run

```bash
python -m mcp_server.server
```

The server speaks MCP over stdio. Point any MCP client at it.

## Generic client configuration

Most MCP clients accept a JSON configuration along these lines. Paths
will need to match your local checkout:

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

For Claude Desktop specifically, see `docs/mcp_setup.md`. The project
does **not** assume Claude Desktop is installed.

## Tools

| Tool | Inputs | Notes |
|---|---|---|
| `list_cases` | — | Cases visible under `raw_sources/` and `wiki/cases/`. |
| `get_case_summary` | `case_id` | Returns the index page and available wiki pages. |
| `list_wiki_pages` | `case_id` | Lists markdown pages on disk for the case. |
| `read_wiki_page` | `case_id, page` | Path-traversal protected; the `.fw/` sidecar is off-limits. |
| `ingest_case_sources` | `case_id, mode={changed-only\|force\|apply}, dry_run, review` | Wraps `fw.py ingest`. |
| `query_case` | `case_id, question` | Wiki-first answer with `claim_NNNN` evidence and citations. |
| `lint_case` | `case_id` | Structured findings with four severity tiers. |
| `generate_report` | `case_id, review` | Returns the report body + whether it was queued for review. |
| `compare_all_methods` | `case_id, question` | All four providers in one response. |
| `get_hypothesis_history` | `case_id` | Per-step confidence trajectory. |
| `get_contradictions` | `case_id` | Both the markdown and the structured contradicting evidence. |
| `get_open_questions` | `case_id` | Parses `open_questions.md` into a list. |
| `graph_query` | `case_id, question` | GraphRAG-lite relationship walk. |

## Limitations

- The server uses the mock LLM mode by default. To use a live LLM,
  install the `anthropic` extra and set `FORENSIC_WIKI_LLM=live` in
  the environment before launching.
- No authentication. The MCP transport is stdio; the server trusts its
  client. Run it in user space, not as a network-exposed daemon.
- `read_wiki_page` blocks path traversal and the sidecar, but tools
  that mutate state (`ingest_case_sources`, `generate_report`) trust
  their `case_id`. Restrict the working directory to the project root.
- The MCP layer is a thin wrapper. Long-running workflows (ingest,
  evolve) take seconds, not milliseconds — the client may need a
  larger response timeout.
