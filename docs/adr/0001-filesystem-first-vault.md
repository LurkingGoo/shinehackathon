---
type: adr
diataxis: reference
title: Filesystem-first vault + vault-search wiring
status: accepted
date: 2026-07-01
tags: [adr, vault, tooling]
---

# 0001. Filesystem-first vault + vault-search wiring

- Status: Accepted
- Date: 2026-07-01

## Context
Scaffolding a new hackathon codebase project inside the Obsidian vault and wiring
it to vault tooling. The vault has **no** obsidian MCP server defined
(`claude mcp list` returns zero). A prior project (trading-desk) drifted by
assuming obsidian-rest was a precondition.

## Decision
Author the project **filesystem-first**: filesystem `Read` is the canonical
transport; obsidian-rest is an optional accelerator, never a precondition.
Register the project as an **indexed root** of the shared `_tools/vault-search`
(BM25 v0) engine, queried via a thin `scripts/search.ps1` wrapper. Codebase
project, `antigravity: false`, no credentials.

## Consequences
- No session ever blocks waiting on an MCP server.
- Cross-project retrieval works from day one via the established shared-engine
  pattern; re-index is event-driven (`_tools/vault-search/index.py`), not
  scheduled — must be re-run after notes/docs change.
- Repeats no obsidian-rest assumption, avoiding the trading-desk drift.
