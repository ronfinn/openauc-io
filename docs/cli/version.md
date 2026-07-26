# `openauc version`

Print the installed version.

## Syntax

```bash
openauc version
```

No arguments or options.

## Example

```bash
uv run openauc version
```

```text
0.1.0a1
```

## Exit codes

| Code | When |
|------|------|
| 0 | Always |

## Use it to

Confirm which build you are running — the first thing to check when a command
is missing or behaves unexpectedly.

```bash
uv run openauc version && uv run openauc --help
```
