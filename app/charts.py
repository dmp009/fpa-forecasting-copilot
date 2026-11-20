"""Pure plotly figure builders (no Streamlit imports)."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def k(x: float) -> str:
    return f"{'-' if x < 0 else '+'}£{abs(x) / 1e3:,.0f}k"


# Sober portfolio palette, shared with .streamlit/config.toml (validated with the dataviz palette checker).
BLUE, GOLD, GREEN, RED, GREY, INK, GRID = "#2558A8", "#B7791F", "#1F9D55", "#C2362B", "#9AA5B4", "#0B0D10", "#E5E7EB"
_LAYOUT = {
    "margin": {"l": 10, "r": 10, "t": 50, "b": 10},
    "template": "plotly_white",
    "colorway": [BLUE, GOLD, GREEN, "#7C3AED", RED, "#0E9AA7", "#E8590C", "#DB2777"],
    "font": {"family": "Inter, Arial, sans-serif", "color": INK, "size": 13},
    "title_x": 0, "title_xanchor": "left", "title_font_size": 16,
    "legend": {"orientation": "h", "y": -0.12, "yanchor": "top", "x": 0, "xanchor": "left"},
    "xaxis": {"gridcolor": GRID, "zeroline": False},
    "yaxis": {"gridcolor": GRID, "zeroline": False, "tickprefix": "£"},
    "paper_bgcolor": "rgba(0,0,0,0)", "plot_bgcolor": "rgba(0,0,0,0)",
}


def bridge(steps: list[tuple[str, float]], title: str) -> go.Figure:
    """Budget -> volume, mix, price, returns, shipping -> actual."""
    names, values = zip(*steps, strict=True)
    measure = ["absolute"] + ["relative"] * (len(steps) - 2) + ["total"]
    fig = go.Figure(go.Waterfall(
        x=list(names), y=list(values), measure=measure,
        text=[k(x) if m == "relative" else f"£{x / 1e6:,.2f}m" for x, m in zip(values, measure, strict=True)],
        textposition="outside", connector={"line": {"color": GREY, "width": 1}},
        increasing={"marker": {"color": GREEN}}, decreasing={"marker": {"color": RED}},
        totals={"marker": {"color": BLUE}}, hovertemplate="%{x}: £%{y:,.0f}<extra></extra>",
    ))
    lo = min(values[0], values[-1])
    fig.update_layout(title=title, showlegend=False, **_LAYOUT)
    fig.update_yaxes(range=[lo * 0.8, max(values[0], values[-1]) * 1.06])
    return fig


def monthly_vs_budget(m: pd.DataFrame, title: str) -> go.Figure:
    """m: month_start, actual, budget."""
    fig = go.Figure()
    fig.add_trace(go.Bar(x=m["month_start"], y=m["actual"], name="Actual", marker_color=BLUE,
                         hovertemplate="%{x|%b %Y}: £%{y:,.0f}<extra>Actual</extra>"))
    fig.add_trace(go.Scatter(x=m["month_start"], y=m["budget"], name="Budget", mode="lines+markers",
                             line={"color": GOLD, "width": 2}, marker={"size": 8},
                             hovertemplate="%{x|%b %Y}: £%{y:,.0f}<extra>Budget</extra>"))
    fig.update_layout(title=title, **_LAYOUT)
    fig.update_xaxes(dtick="M1", tickformat="%b")
    return fig


def variance_bars(df: pd.DataFrame, label: str, title: str) -> go.Figure:
    """Horizontal bars of variance (df: label, variance), sorted."""
    d = df.sort_values("variance")
    fig = go.Figure(go.Bar(
        y=d[label], x=d["variance"], orientation="h", marker_color=[GREEN if x >= 0 else RED for x in d["variance"]],
        text=[k(x) for x in d["variance"]], textposition="auto",
        hovertemplate="%{y}: £%{x:,.0f}<extra></extra>",
    ))
    fig.update_layout(title=title, showlegend=False, **_LAYOUT)
    fig.update_xaxes(tickprefix="£")
    fig.update_yaxes(tickprefix="")
    return fig


def backtest(tot: pd.DataFrame, labels: dict[str, str], title: str) -> go.Figure:
    """tot: month, actual and one column per method."""
    fig = go.Figure()
    fig.add_trace(go.Bar(x=tot["month"], y=tot["actual"], name="Actual", marker_color=GREY,
                         hovertemplate="%{x}: £%{y:,.0f}<extra>Actual</extra>"))
    for col, colour in zip(labels, [BLUE, GOLD, RED], strict=False):
        fig.add_trace(go.Scatter(x=tot["month"], y=tot[col], name=labels[col], mode="lines+markers",
                                 line={"color": colour, "width": 2}, marker={"size": 8},
                                 hovertemplate="%{x}: £%{y:,.0f}<extra>" + labels[col] + "</extra>"))
    fig.update_layout(title=title, **_LAYOUT)
    return fig


def landing(ytd: float, dec: float, budget: float, title: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["Landing"], y=[ytd], name="Jan-Nov actual", marker_color=BLUE,
                         hovertemplate="Jan-Nov actual: £%{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Bar(x=["Landing"], y=[dec], name="December forecast", marker_color="#8FAACF",
                         hovertemplate="December forecast: £%{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Bar(x=["Budget"], y=[budget], name="Full-year budget", marker_color=GOLD,
                         hovertemplate="Budget: £%{y:,.0f}<extra></extra>"))
    fig.update_layout(title=title, barmode="stack", **_LAYOUT)
    return fig
