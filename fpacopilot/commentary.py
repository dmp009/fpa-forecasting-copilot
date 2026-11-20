"""Month-end variance commentary: facts -> text -> number check.

1. `facts()` computes every figure the commentary may use, already formatted ("£8.80m", "-7.1%").
2. The text comes from Claude (`llm`) when an API key is configured, or from a deterministic template.
   LLM text is cached in data/ai_cache/ keyed by a hash of the facts, so the app and CI never call
   the API: they read the cache, or fall back to the template when the facts changed.
3. `check()` rejects any text that states a figure not in the facts. A rejected LLM draft is not used.
"""
from __future__ import annotations

import hashlib
import json
import re

from fpacopilot import variance as v
from fpacopilot.config import AI_CACHE, SNAPSHOT, settings
from fpacopilot.forecast import LABELS
from fpacopilot.warehouse import connect

MODEL = "claude-opus-5-5"
CACHE = AI_CACHE / "commentary.json"


def money(x: float) -> str:
    sign = "-" if x < 0 else ""
    x = abs(x)
    return f"{sign}£{x / 1e6:.2f}m" if x >= 1e6 else f"{sign}£{x / 1e3:.0f}k"


def pct(x: float) -> str:
    return f"{x:+.1%}"


def facts() -> dict:
    s = settings()
    con = connect()
    start, end = f"{s['budget_year']}-01-01", s["close_date"]
    act, bud = v.actuals(con, start, end), v.budget(con, start, end)
    br = v.bridge(act, bud)
    reg = v.pnl(act, bud, "region")
    seg = v.pvm(act, bud).groupby("category")[["variance", "volume", "mix", "price"]].sum()
    fc = json.loads((SNAPSHOT / "forecast_summary.json").read_text())
    land, scores = fc["landing"], fc["scores"]
    total_wape = {m: scores[m]["Total"] for m in scores}
    worst, best = seg["variance"].idxmin(), seg["variance"].idxmax()
    return {
        "period": f"January to November {s['budget_year']} (year to date at the {end} close)",
        "currency": s["currency"],
        "ytd": {
            "net_revenue_actual": money(br.actual_net), "net_revenue_budget": money(br.budget_net),
            "variance": money(br.actual_net - br.budget_net), "variance_pct": pct(br.actual_net / br.budget_net - 1),
        },
        "bridge": {k: money(x) for k, x in
                   {"volume": br.volume, "mix": br.mix, "price": br.price, "returns": br.returns,
                    "shipping": br.shipping}.items()},
        "regions": {r: {"actual": money(reg.loc[r, ("actual", "net_revenue")]),
                        "budget": money(reg.loc[r, ("budget", "net_revenue")]),
                        "variance": money(reg.loc[r, ("variance", "net_revenue")]),
                        "variance_pct": pct(reg.loc[r, ("variance_pct", "net_revenue")])} for r in reg.index},
        "categories": {
            "largest_shortfall": {"category": worst, "variance": money(seg.loc[worst, "variance"]),
                                  "volume": money(seg.loc[worst, "volume"])},
            "largest_beat": {"category": best, "variance": money(seg.loc[best, "variance"]),
                             "mix": money(seg.loc[best, "mix"]), "price": money(seg.loc[best, "price"])},
        },
        "landing": {
            "method": LABELS[land["best_method"]], "december_forecast": money(land["december_forecast"]),
            "december_budget": money(land["december_budget"]), "full_year_landing": money(land["full_year_landing"]),
            "full_year_budget": money(land["full_year_budget"]),
            "full_year_gap": money(land["full_year_landing"] - land["full_year_budget"]),
            "full_year_gap_pct": pct(land["full_year_landing"] / land["full_year_budget"] - 1),
        },
        "forecast_accuracy_wape": {LABELS[m]: f"{w:.1%}" for m, w in total_wape.items()},
    }


def template(f: dict) -> str:
    y, b, ld, c = f["ytd"], f["bridge"], f["landing"], f["categories"]
    regions = "; ".join(f"{r} {d['actual']} vs {d['budget']} ({d['variance_pct']})" for r, d in f["regions"].items())
    return "\n\n".join([
        (f"**Headline.** Net revenue for {f['period']} was {y['net_revenue_actual']} against a budget of "
        f"{y['net_revenue_budget']}, a variance of {y['variance']} ({y['variance_pct']})."),
        (f"**Drivers.** Volume explains {b['volume']}: fewer units were sold than budgeted. Mix added {b['mix']} "
        f"and price added {b['price']}. Returns moved by {b['returns']} and shipping income by {b['shipping']}."),
        f"**Regions.** {regions}.",
        (f"**Categories.** {c['largest_shortfall']['category']} has the largest shortfall ({c['largest_shortfall']['variance']}, "
        f"of which volume {c['largest_shortfall']['volume']}). {c['largest_beat']['category']} beat budget by "
        f"{c['largest_beat']['variance']} (mix {c['largest_beat']['mix']}, price {c['largest_beat']['price']})."),
        (f"**Full-year landing.** With December forecast at {ld['december_forecast']} ({ld['method']}, budget "
        f"{ld['december_budget']}), the year lands at {ld['full_year_landing']} against a budget of "
        f"{ld['full_year_budget']}: a gap of {ld['full_year_gap']} ({ld['full_year_gap_pct']})."),
    ])


NUMBER = re.compile(r"-?£?\d[\d,]*(?:\.\d+)?[mk%]?")


def allowed(f: dict) -> set[str]:
    out: set[str] = set()

    def walk(x):
        if isinstance(x, dict):
            for val in x.values():
                walk(val)
        elif isinstance(x, str):
            out.update(NUMBER.findall(x.replace("−", "-")))

    walk(f)
    out.update({t.lstrip("+") for t in set(out)})
    return out | {t.lstrip("-") for t in out}


def check(text: str, f: dict) -> list[str]:
    """Figures in the text that are not in the facts (years, day numbers and list counts are allowed)."""
    ok = allowed(f)
    bad = []
    for tok in NUMBER.findall(text.replace("−", "-").replace("+", "")):
        plain = tok.lstrip("-")
        if tok in ok or plain in ok:
            continue
        if re.fullmatch(r"\d{1,2}|20\d\d", plain):  # day of month, counts, years
            continue
        bad.append(tok)
    return bad


SYSTEM = (
    "You are an FP&A analyst writing the month-end revenue commentary for the finance director of a UK online "
    "retailer of gifts and homeware. Write in British English, five short paragraphs with bold lead-ins: Headline, "
    "Drivers, Regions, Categories, Full-year landing. Use only figures that appear in the facts, copied exactly as "
    "written there (same rounding, sign and unit); do not compute new figures, totals or percentages. Explain what "
    "the variance means for the business in plain words, and end with one recommended action. No more than 220 words."
)


def llm(f: dict) -> str:
    import anthropic

    client = anthropic.Anthropic()
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=4000,
        output_config={"effort": "medium"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=SYSTEM,
        messages=[{"role": "user", "content": "Facts (JSON):\n" + json.dumps(f, indent=2)}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("the model declined to write the commentary")
    return "".join(b.text for b in response.content if b.type == "text").strip()


def fact_hash(f: dict) -> str:
    return hashlib.sha256(json.dumps(f, sort_keys=True).encode()).hexdigest()[:16]


def get(f: dict | None = None) -> dict:
    """{'text', 'source', 'rejected'} from the cache when it matches these facts, else the template."""
    f = f or facts()
    if CACHE.exists():
        c = json.loads(CACHE.read_text())
        if c.get("facts_hash") == fact_hash(f) and not check(c["text"], f):
            return {"text": c["text"], "source": f"Claude ({c['model']}), cached", "rejected": []}
    return {"text": template(f), "source": "Deterministic template", "rejected": []}


def run(use_llm: bool | None = None) -> dict:
    """Write data/ai_cache/commentary.json with an LLM draft that passes the check (when a key is set)."""
    import os

    f = facts()
    (SNAPSHOT / "commentary_facts.json").write_text(json.dumps(f, indent=2))
    if use_llm is None:
        use_llm = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("FPA_USE_LLM"))
    if use_llm:
        text = llm(f)
        bad = check(text, f)
        if bad:
            print(f"LLM draft rejected, figures not in the facts: {bad}")
        else:
            AI_CACHE.mkdir(parents=True, exist_ok=True)
            CACHE.write_text(json.dumps({"facts_hash": fact_hash(f), "model": MODEL, "text": text}, indent=2))
    out = get(f)
    assert not check(out["text"], f), check(out["text"], f)
    print(out["source"])
    print(out["text"])
    return out
