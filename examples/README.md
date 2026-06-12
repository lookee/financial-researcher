# Examples

Static samples for the **example watchlist** (`config/watchlist.yaml.example`):

| Asset class | Tickers |
|-------------|---------|
| ETFs | SMH.MI, WTAI.MI |
| Stocks | 1NVDA.MI (NVIDIA, GEM), STMMI.MI |

## Briefings

All tracked samples in [`briefings/`](briefings/):

| Language | Date | Session | File |
|----------|------|---------|------|
| Italian | 2026-06-09 | `close` | [watchlist_2026-06-09_close.md](briefings/watchlist_2026-06-09_close.md) |
| Italian | 2026-06-10 | `close` | [watchlist_2026-06-10_close.md](briefings/watchlist_2026-06-10_close.md) |
| Italian | 2026-06-11 | `close` | [watchlist_2026-06-11_close.md](briefings/watchlist_2026-06-11_close.md) |
| Italian | 2026-06-12 | `post_open` | [watchlist_2026-06-12_post_open.md](briefings/watchlist_2026-06-12_post_open.md) |
| Italian | 2026-06-12 | `midday` | [watchlist_2026-06-12_midday.md](briefings/watchlist_2026-06-12_midday.md) |
| Italian | 2026-06-12 | `close` | [watchlist_2026-06-12_close.md](briefings/watchlist_2026-06-12_close.md) |

The CLI writes new briefings to `output/briefings/`, which is not tracked by git.

See the [Sample briefings](../README.md#sample-briefings) section in the project README.

## Watchlist

Use [`config/watchlist.yaml.example`](../config/watchlist.yaml.example) — copy to `config/watchlist.yaml`.

## Regenerate

```bash
uv run briefing --watchlist config/watchlist.yaml.example --session close --language English --force
cp output/briefings/watchlist_$(date +%Y-%m-%d)_close.md examples/briefings/

uv run briefing --watchlist config/watchlist.yaml.example --session close --language Italian --force
cp output/briefings/watchlist_$(date +%Y-%m-%d)_close.md examples/briefings/watchlist_$(date +%Y-%m-%d)_close.md
```
