# Examples

Static samples for the project watchlist (`config/watchlist.yaml`):

| Asset class | Tickers |
|-------------|---------|
| ETFs | AIAI.MI, SMH.MI, IWQU.MI, QOMP.DE, 36BZ.DE |
| Stocks | ISP.MI |

## Briefings

All tracked samples in [`briefings/`](briefings/) (newest first). Session charts are in [`briefings/charts/`](briefings/charts/).

| Language | Date | Session | File |
|----------|------|---------|------|
| Italian | 2026-06-25 | `close` | [watchlist_2026-06-25_close.md](briefings/watchlist_2026-06-25_close.md) |
| Italian | 2026-06-25 | `midday` | [watchlist_2026-06-25_midday.md](briefings/watchlist_2026-06-25_midday.md) |
| Italian | 2026-06-25 | `pre_open` | [watchlist_2026-06-25_pre_open.md](briefings/watchlist_2026-06-25_pre_open.md) |
| Italian | 2026-06-24 | `close` | [watchlist_2026-06-24_close.md](briefings/watchlist_2026-06-24_close.md) |
| Italian | 2026-06-24 | `midday` | [watchlist_2026-06-24_midday.md](briefings/watchlist_2026-06-24_midday.md) |
| Italian | 2026-06-24 | `pre_open` | [watchlist_2026-06-24_pre_open.md](briefings/watchlist_2026-06-24_pre_open.md) |
| Italian | 2026-06-23 | `close` | [watchlist_2026-06-23_close.md](briefings/watchlist_2026-06-23_close.md) |
| Italian | 2026-06-23 | `midday` | [watchlist_2026-06-23_midday.md](briefings/watchlist_2026-06-23_midday.md) |
| Italian | 2026-06-23 | `post_open` | [watchlist_2026-06-23_post_open.md](briefings/watchlist_2026-06-23_post_open.md) |
| Italian | 2026-06-23 | `pre_open` | [watchlist_2026-06-23_pre_open.md](briefings/watchlist_2026-06-23_pre_open.md) |
| Italian | 2026-06-22 | `close` | [watchlist_2026-06-22_close.md](briefings/watchlist_2026-06-22_close.md) |
| Italian | 2026-06-22 | `midday` | [watchlist_2026-06-22_midday.md](briefings/watchlist_2026-06-22_midday.md) |
| Italian | 2026-06-19 | `close` | [watchlist_2026-06-19_close.md](briefings/watchlist_2026-06-19_close.md) |
| Italian | 2026-06-19 | `pre_open` | [watchlist_2026-06-19_pre_open.md](briefings/watchlist_2026-06-19_pre_open.md) |
| Italian | 2026-06-18 | `close` | [watchlist_2026-06-18_close.md](briefings/watchlist_2026-06-18_close.md) |
| Italian | 2026-06-18 | `midday` | [watchlist_2026-06-18_midday.md](briefings/watchlist_2026-06-18_midday.md) |
| Italian | 2026-06-18 | `post_open` | [watchlist_2026-06-18_post_open.md](briefings/watchlist_2026-06-18_post_open.md) |
| Italian | 2026-06-18 | `pre_open` | [watchlist_2026-06-18_pre_open.md](briefings/watchlist_2026-06-18_pre_open.md) |
| Italian | 2026-06-17 | `close` | [watchlist_2026-06-17_close.md](briefings/watchlist_2026-06-17_close.md) |
| Italian | 2026-06-17 | `midday` | [watchlist_2026-06-17_midday.md](briefings/watchlist_2026-06-17_midday.md) |
| Italian | 2026-06-17 | `post_open` | [watchlist_2026-06-17_post_open.md](briefings/watchlist_2026-06-17_post_open.md) |
| Italian | 2026-06-16 | `close` | [watchlist_2026-06-16_close.md](briefings/watchlist_2026-06-16_close.md) |
| Italian | 2026-06-16 | `post_open` | [watchlist_2026-06-16_post_open.md](briefings/watchlist_2026-06-16_post_open.md) |
| Italian | 2026-06-15 | `close` | [watchlist_2026-06-15_close.md](briefings/watchlist_2026-06-15_close.md) |
| Italian | 2026-06-15 | `post_open` | [watchlist_2026-06-15_post_open.md](briefings/watchlist_2026-06-15_post_open.md) |
| Italian | 2026-06-15 | `pre_open` | [watchlist_2026-06-15_pre_open.md](briefings/watchlist_2026-06-15_pre_open.md) |
| Italian | 2026-06-13 | `close` | [watchlist_2026-06-13_close.md](briefings/watchlist_2026-06-13_close.md) |
| Italian | 2026-06-12 | `close` | [watchlist_2026-06-12_close.md](briefings/watchlist_2026-06-12_close.md) |
| English | 2026-06-12 | `close` | [watchlist_2026-06-12_close_en.md](briefings/watchlist_2026-06-12_close_en.md) |
| Italian | 2026-06-12 | `midday` | [watchlist_2026-06-12_midday.md](briefings/watchlist_2026-06-12_midday.md) |
| Italian | 2026-06-12 | `post_open` | [watchlist_2026-06-12_post_open.md](briefings/watchlist_2026-06-12_post_open.md) |
| Italian | 2026-06-11 | `close` | [watchlist_2026-06-11_close.md](briefings/watchlist_2026-06-11_close.md) |
| Italian | 2026-06-10 | `close` | [watchlist_2026-06-10_close.md](briefings/watchlist_2026-06-10_close.md) |
| Italian | 2026-06-09 | `close` | [watchlist_2026-06-09_close.md](briefings/watchlist_2026-06-09_close.md) |

The CLI writes new briefings to `output/briefings/`, which is not tracked by git.

See the [Sample briefings](../README.md#sample-briefings) section in the project README.

## Watchlist

Use [`config/watchlist.yaml`](../config/watchlist.yaml) or copy from [`config/watchlist.yaml.example`](../config/watchlist.yaml.example).

## Regenerate

```bash
uv run briefing --watchlist config/watchlist.yaml --session close --language Italian --force
cp output/briefings/watchlist_$(date +%Y-%m-%d)_close.md examples/briefings/

uv run briefing --watchlist config/watchlist.yaml --session close --language English --force
cp output/briefings/watchlist_$(date +%Y-%m-%d)_close.md examples/briefings/watchlist_$(date +%Y-%m-%d)_close_en.md
```
