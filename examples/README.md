# Examples

Static samples for the **example watchlist** (`config/watchlist.yaml.example`):

| Asset class | Tickers |
|-------------|---------|
| ETFs | AIAI.MI, SMH.MI, IWQU.MI |
| Italian stocks | STMMI.MI, ENI.MI, RACE.MI, 1AAPL.MI (Apple, GEM) |

## Briefing

| Session | File |
|---------|------|
| Close, 2026-06-09 (English) | [watchlist_2026-06-09_close.md](briefings/watchlist_2026-06-09_close.md) |

The CLI writes new briefings to `output/briefings/`, which is not tracked by git.

See the [Sample briefing](../README.md#sample-briefing) section in the project README.

## Watchlist

[`watchlist.example.yaml`](watchlist.example.yaml) mirrors `config/watchlist.yaml.example`.

## Regenerate

```bash
uv run briefing --watchlist config/watchlist.yaml.example --session close --language English --force
cp output/briefings/watchlist_$(date +%Y-%m-%d)_close.md examples/briefings/
```
