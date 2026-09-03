---
name: zotero-agent
description: Use the registered zotero-agent MCP to search, inspect, and—only when explicitly requested—manage the user's local Zotero library. Trigger for Zotero collections, items, PDFs, notes, tags, metadata, duplicates, bibliography export, or Zotero MCP diagnostics.
---

# Zotero Agent MCP

Use the registered `zotero-agent` MCP server as the interface to the user's Zotero desktop library.

## Preconditions

- Prefer the MCP tools exposed by `zotero-agent`; do not read or modify `zotero.sqlite` directly.
- Zotero desktop and its local API/bridge must be available. If the MCP server is unavailable, report the failed prerequisite instead of silently switching to Zotero Cloud or direct database access.
- Never reveal bridge tokens, API keys, configuration secrets, or Zotero user identifiers.
- Do not enable or request the MCP server's unrestricted JavaScript execution mode (`--allow-exec`).

## Read operations

For read-only requests, use the narrowest relevant MCP tool, such as collection listing, item search/retrieval, library statistics, PDF-path/outline inspection, author search, duplicate detection, missing-field checks, or bibliography export.

When the user explicitly says “只读” or otherwise prohibits changes, call only read-oriented tools. Treat exports as read-only only when they do not alter Zotero records.

## Write operations

Create, update, attach, tag, move, merge, enrich, or add notes only when the user explicitly asks for that mutation.

- Confirm the intended scope before broad changes whose target is ambiguous.
- Preview affected items when the MCP tool supports a preview or dry-run mode.
- Treat duplicate merging as non-reversible and require an explicit merge request.
- Prefer reversible, narrowly scoped changes and report what changed.

## Project citation boundary

Within this repository, `reference/literature/zotero_library.bib` remains the only allowed citation source. Zotero MCP results may support discovery and inspection, but an item must be imported into that file by a human before it is cited in modeling deliverables. Do not modify `reference/`.

## Runtime contract

- Upstream: `alex-roc/zotero-agent`
- CLI/runtime version: `zotero-agent==0.8.2`
- Compatible MCP dependency: `mcp==1.12.0`
- Transport: stdio via `zot mcp`
- License: AGPL-3.0-or-later for the upstream runtime; this project Skill is a local integration wrapper.

If the installed runtime no longer matches this contract, use the project's `skill-maintenance` workflow to diagnose and update it rather than changing dependencies ad hoc.
