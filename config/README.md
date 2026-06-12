# User configuration

This directory holds **your** runtime data — not application defaults (those live in [`src/financial_researcher/defaults/`](../src/financial_researcher/defaults/)).

| File | Purpose |
|------|---------|
| `watchlist.yaml` | Your ISIN watchlist (created on first `uv run briefing` if missing) |
| `watchlist.yaml.example` | Committed template — copy to `watchlist.yaml` to start |

```bash
cp config/watchlist.yaml.example config/watchlist.yaml
```

Override location with `WATCHLIST_PATH` or `--watchlist`.
