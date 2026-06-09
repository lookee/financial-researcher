"""
Session profiles for the watchlist briefing crew.

Maps each Milan trading-session phase to the four placeholder values consumed by
the agents (agents_briefing_*.yaml):

    {session_orientation} -> market_analyst, outlook_analyst, chief_strategist
    {valid_metrics}       -> market_analyst
    {news_window}         -> news_analyst
    {calendar_split}      -> calendar_analyst

USAGE (sketch — adapt to how your crew assembles the kickoff inputs):

    from session_profiles import resolve_session_profile

    phase = resolve_session_profile(session_label, current_time)  # returns a dict
    inputs = {
        ...existing inputs...,
        "session_orientation": phase["session_orientation"],
        "valid_metrics":       phase["valid_metrics"],
        "news_window":         phase["news_window"],
        "calendar_split":      phase["calendar_split"],
    }

NOTE: the pre-market / opening profiles assume your fetch pipeline can supply
previous-close, index futures and overnight (Asia close / US futures) data in
watchlist_context. Without those, the forward-looking orientation has nothing to
stand on and the agent will either stay vague or fabricate — add that data first.

Borsa Italiana continuous session is roughly 09:00–17:30 Europe/Rome (auction
phases around it). Tune the cutoffs below to your venue if needed.
"""

PRE_MARKET = {
    "session_orientation": (
        "forward-looking pre-market briefing: today's continuous session has NOT "
        "happened yet. Focus on what the day faces — overnight moves, index "
        "futures, and scheduled catalysts — not on a recap of today's price action."
    ),
    "valid_metrics": (
        "previous-session close and its 1W/1M/YTD context; index futures and "
        "overnight signals (Asia close, US futures) where available in "
        "watchlist_context. DO NOT report today's intraday/1D performance — it does "
        "not exist yet and must not be inferred."
    ),
    "news_window": (
        "the last 12–16 hours (overnight and after-hours): Asia close, US futures, "
        "and post-close company/regulatory releases take priority over older stories"
    ),
    "calendar_split": (
        "every scheduled event for today is still AHEAD — list today's catalysts as "
        "upcoming, with exact times where confirmed, ahead of later-week events"
    ),
}

OPENING = {
    "session_orientation": (
        "opening briefing (first ~30–60 minutes): prices exist but are noisy and "
        "thin. Emphasise the GAP versus the previous close and the reaction to "
        "overnight news, not nascent intraday performance."
    ),
    "valid_metrics": (
        "gap vs previous close (primary); previous-session 1W/1M/YTD for context. "
        "Today's 1D is present but noisy — report it only with an explicit caveat "
        "that the session has just opened and volumes are auction-concentrated."
    ),
    "news_window": (
        "the last 16–24 hours, with overnight and pre-open releases prioritised as "
        "the drivers of the opening gap"
    ),
    "calendar_split": (
        "separate intraday catalysts already passed (e.g. the open itself) from "
        "those still ahead today; most of the day is still AHEAD"
    ),
}

MIDDAY = {
    "session_orientation": (
        "mid-session briefing: the session is IN PROGRESS. Treat all of today's "
        "figures as partial and clearly say so; balance what has happened this "
        "morning with what the afternoon still holds."
    ),
    "valid_metrics": (
        "today's PARTIAL 1D (label it 'parziale, sessione in corso'); previous "
        "1W/1M/YTD complete. Do not present the partial 1D as a final session move."
    ),
    "news_window": (
        "the last 7 calendar days (primary), extendable to 14 days, with this "
        "morning's headlines prioritised for explaining the partial 1D move"
    ),
    "calendar_split": (
        "split clearly: events already occurred earlier TODAY vs events still ahead "
        "this afternoon/this session; then later-week events"
    ),
}

CLOSE = {
    "session_orientation": (
        "session-close briefing: the session is COMPLETE. Recap the full day's "
        "action and set up the next sessions — this is the native, fully "
        "backward-then-forward format."
    ),
    "valid_metrics": (
        "full and final 1D / 1W / 1M / YTD for every instrument; all standard "
        "metrics apply"
    ),
    "news_window": (
        "the last 7 calendar days (primary), extendable to 14 days if nothing "
        "recent explains the moves"
    ),
    "calendar_split": (
        "today's events are concluded — focus the calendar on the upcoming sessions "
        "(next 2–4 weeks)"
    ),
}

# Map common session labels to a profile. Adjust the label strings to whatever
# your CLI actually passes as {session_label}.
# Order matters: longer / more specific keys (e.g. pre-open) before bare "open".
_LABEL_MAP = {
    "pre-open": PRE_MARKET,
    "pre-market": PRE_MARKET,
    "preopen": PRE_MARKET,
    "pre-apertura": PRE_MARKET,
    "post-open": OPENING,
    "opening": OPENING,
    "apertura": OPENING,
    "open": OPENING,
    "midday": MIDDAY,
    "mid-session": MIDDAY,
    "mezza-giornata": MIDDAY,
    "lunch": MIDDAY,
    "close": CLOSE,
    "closing": CLOSE,
    "chiusura": CLOSE,
}


def resolve_session_profile(session_label: str, current_time=None) -> dict:
    """
    Resolve a profile from an explicit session_label first; if unrecognised, fall
    back to wall-clock time (Europe/Rome) so the crew still adapts sensibly.

    current_time: a datetime in Europe/Rome, or None to skip the time fallback.
    """
    if session_label:
        key = session_label.strip().lower().replace("_", "-").replace(" ", "-")
        for k, prof in _LABEL_MAP.items():
            if k in key:
                return prof

    if current_time is not None:
        h, m = current_time.hour, current_time.minute
        t = h * 60 + m
        if t < 9 * 60:                 # before 09:00
            return PRE_MARKET
        if t < 9 * 60 + 60:            # 09:00–10:00
            return OPENING
        if t < 17 * 60 + 30:           # 10:00–17:30
            return MIDDAY
        return CLOSE                   # 17:30 onwards

    # Safe default: the format the briefing was originally designed for.
    return CLOSE
