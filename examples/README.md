# Examples

Static samples for the **example watchlist** (`config/watchlist.yaml.example`):

| Asset class | Tickers |
|-------------|---------|
| ETFs | AIAI.MI, SMH.MI, IWQU.MI |
| Italian stocks | STMMI.MI, ENI.MI, RACE.MI, 1AAPL.MI (Apple, GEM) |

## Briefings

| Language | Session | File |
|----------|---------|------|
| English | Close, 2026-06-10 | [watchlist_2026-06-10_close.md](briefings/watchlist_2026-06-10_close.md) |
| Italian | Close, 2026-06-09 | [watchlist_2026-06-09_close_it.md](briefings/watchlist_2026-06-09_close_it.md) |

The CLI writes new briefings to `output/briefings/`, which is not tracked by git.

See the [Sample briefings](../README.md) section in the project README.

## Watchlist

[`watchlist.example.yaml`](watchlist.example.yaml) mirrors `config/watchlist.yaml.example`.

## Regenerate

```bash
uv run briefing --watchlist config/watchlist.yaml.example --session close --language English --force
cp output/briefings/watchlist_$(date +%Y-%m-%d)_close.md examples/briefings/

uv run briefing --watchlist config/watchlist.yaml.example --session close --language Italian --force
cp output/briefings/watchlist_$(date +%Y-%m-%d)_close.md examples/briefings/watchlist_$(date +%Y-%m-%d)_close_it.md
```
