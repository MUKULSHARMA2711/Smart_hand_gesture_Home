"""AI home agent: natural language -> structured, validated action plan -> CommandService.

The LLM (or the deterministic mock) only ever *proposes* a JSON plan. Everything that
changes a device happens in backend code after validation and policy checks.
"""
