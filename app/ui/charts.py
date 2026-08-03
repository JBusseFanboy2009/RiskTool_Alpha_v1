"""Plotly chart helpers for Streamlit."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def risk_color(score: float) -> str:
    s = max(0.0, min(100.0, float(score)))
    if s < 33:
        return "#22c55e"
    if s < 66:
        return "#eab308"
    return "#ef4444"


def pie_chart(labels: list, values: list, title: str = "") -> go.Figure:
    fig = px.pie(names=labels, values=values, title=title, hole=0)
    fig.update_layout(margin=dict(t=40, b=20, l=20, r=20))
    return fig


def donut_chart(labels: list, values: list, title: str = "") -> go.Figure:
    fig = px.pie(names=labels, values=values, title=title, hole=0.45)
    fig.update_layout(margin=dict(t=40, b=20, l=20, r=20))
    return fig


def horizontal_bar(labels: list, values: list, title: str, x_title: str = "%") -> go.Figure:
    df = pd.DataFrame({"label": labels, "value": values})
    fig = px.bar(df, x="value", y="label", orientation="h", title=title, labels={"value": x_title, "label": ""})
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, margin=dict(t=40, b=20, l=20, r=20))
    return fig


def line_chart(dates: list, values: list, title: str, y_title: str = "") -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=values, mode="lines", line=dict(color="#0f172a")))
    fig.update_layout(title=title, yaxis_title=y_title, margin=dict(t=40, b=20, l=20, r=20))
    return fig


def correlation_heatmap(matrix: dict, labels: list) -> go.Figure:
    if not labels:
        return go.Figure()
    z = [[float(matrix.get(r, {}).get(c, 1.0 if r == c else 0.0)) for c in labels] for r in labels]
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=labels,
            y=labels,
            colorscale="RdYlGn_r",
            zmin=-1,
            zmax=1,
            text=[[f"{v:.2f}" for v in row] for row in z],
            texttemplate="%{text}",
        )
    )
    fig.update_layout(title="Korrelations-Matrix", margin=dict(t=40, b=20, l=20, r=20))
    return fig


def risk_gauge(score: float) -> go.Figure:
    s = max(0.0, min(100.0, float(score)))
    color = risk_color(s)
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=s,
            number={"suffix": " / 100"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": color},
                "steps": [
                    {"range": [0, 33], "color": "#dcfce7"},
                    {"range": [33, 66], "color": "#fef9c3"},
                    {"range": [66, 100], "color": "#fee2e2"},
                ],
            },
            title={"text": "Risiko-Score"},
        )
    )
    fig.update_layout(margin=dict(t=60, b=20, l=30, r=30), height=280)
    return fig


def var_histogram(counts: list, edges: list, title: str) -> go.Figure:
    if not counts or not edges:
        return go.Figure()
    mids = [(edges[i] + edges[i + 1]) / 2 * 100 for i in range(len(counts))]
    fig = px.bar(x=mids, y=counts, labels={"x": "Tagesrendite %", "y": "Häufigkeit"}, title=title)
    fig.update_layout(margin=dict(t=40, b=20, l=20, r=20))
    return fig


def stress_comparison(labels: list, base: list, shocked: list) -> go.Figure:
    df = pd.DataFrame({"Ticker": labels * 2, "Rendite %": base + shocked, "Szenario": ["Basis"] * len(labels) + ["Gestresst"] * len(labels)})
    fig = px.bar(df, x="Ticker", y="Rendite %", color="Szenario", barmode="group", title="Stress-Test Vergleich")
    fig.update_layout(margin=dict(t=40, b=20, l=20, r=20))
    return fig
