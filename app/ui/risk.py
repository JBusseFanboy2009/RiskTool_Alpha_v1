"""Risk analysis pages for Streamlit."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.services.risk_service import (
    compute_correlation,
    compute_drawdown,
    compute_risk_o_meter,
    compute_stress_test,
    compute_var_cvar,
    compute_volatility,
    get_stress_scenarios,
    portfolio_symbols,
)
from app.ui.charts import (
    correlation_heatmap,
    horizontal_bar,
    risk_gauge,
    stress_comparison,
    var_histogram,
)


def _parse_symbols(text: str) -> list[str]:
    return [s.strip() for s in text.split(",") if s.strip()]


def _symbols_input(db, user_id: int, key: str) -> list[str]:
    default = ", ".join(portfolio_symbols(db, user_id))
    text = st.text_input("Ticker (komma-getrennt, leer = Portfolio)", value=default, key=key)
    syms = _parse_symbols(text)
    return syms if syms else portfolio_symbols(db, user_id)


def render_risk_o_meter(db, user_id: int) -> None:
    st.header("Risiko-O-Meter")
    with st.spinner("Berechne …"):
        result = compute_risk_o_meter(db, user_id)
    score = result["score"]
    st.plotly_chart(risk_gauge(score), use_container_width=True)
    label = "Risikoarm" if score < 33 else "Moderat" if score < 66 else "Risikoreich"
    st.markdown(f"**{label}** — {result['symbol_count']} Position(en)")

    contributions = result.get("contributions") or {}
    components = result.get("components") or {}
    if contributions:
        st.subheader("Beitrag je Position")
        rows = []
        for sym, pct in sorted(contributions.items(), key=lambda x: -x[1]):
            vol = components.get(sym, 0) * 100
            rows.append({"Ticker": sym, "Risikoanteil %": pct, "Volatilität % p.a.": vol})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def render_volatility(db, user_id: int) -> None:
    st.header("Volatilität")
    syms = _symbols_input(db, user_id, "vol_syms")
    if st.button("Berechnen", key="vol_btn"):
        with st.spinner("Berechne …"):
            r = compute_volatility(db, user_id, syms)
        vol_map = r.get("annualized") or {}
        if not vol_map:
            st.warning("Keine Daten.")
            return
        labels = list(vol_map.keys())
        values = [v * 100 for v in vol_map.values()]
        st.plotly_chart(horizontal_bar(labels, values, "Annualisierte Volatilität", "Vol % p.a."), use_container_width=True)


def render_correlation(db, user_id: int) -> None:
    st.header("Korrelations-Heatmap")
    syms = _symbols_input(db, user_id, "corr_syms")
    if st.button("Berechnen", key="corr_btn"):
        with st.spinner("Berechne …"):
            r = compute_correlation(db, user_id, syms)
        labels = r.get("labels") or []
        matrix = r.get("matrix") or {}
        if not labels:
            st.warning("Keine Daten.")
            return
        st.plotly_chart(correlation_heatmap(matrix, labels), use_container_width=True)


def render_drawdown(db, user_id: int) -> None:
    st.header("Maximum Drawdown")
    syms = _symbols_input(db, user_id, "dd_syms")
    if st.button("Berechnen", key="dd_btn"):
        with st.spinner("Berechne …"):
            r = compute_drawdown(db, user_id, syms)
        summary = r.get("summary") or {}
        series = r.get("series") or {}
        for sym in series:
            st.markdown(f"**{sym}** — Max DD: {summary.get(sym, 0) * 100:.2f}%")
            s = series[sym]
            import plotly.graph_objects as go

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=s["dates"],
                    y=[v * 100 for v in s["values"]],
                    fill="tozeroy",
                    line=dict(color="#dc2626"),
                    name="Drawdown",
                )
            )
            fig.update_layout(title=sym, yaxis_title="Drawdown %", margin=dict(t=40, b=20, l=20, r=20))
            st.plotly_chart(fig, use_container_width=True)


def render_var_cvar(db, user_id: int) -> None:
    st.header("VaR & CVaR")
    syms = _symbols_input(db, user_id, "var_syms")
    confidence = st.slider("Konfidenzniveau", 0.80, 0.99, 0.95, 0.01)
    if st.button("Berechnen", key="var_btn"):
        with st.spinner("Berechne …"):
            result = compute_var_cvar(db, user_id, syms, confidence)
        for sym, data in result.items():
            st.markdown(f"### {sym}")
            c1, c2 = st.columns(2)
            c1.metric("VaR", f"{data['var'] * 100:.2f}%")
            c2.metric("CVaR", f"{data['cvar'] * 100:.2f}%")
            hist = data.get("histogram") or {}
            st.plotly_chart(
                var_histogram(hist.get("counts", []), hist.get("edges", []), "Verteilung der Tagesrenditen"),
                use_container_width=True,
            )


def render_stress(db, user_id: int) -> None:
    st.header("Stress Testing")
    scenarios = get_stress_scenarios()
    syms = _symbols_input(db, user_id, "stress_syms")

    scenario_labels = {s["id"]: s["label"] for s in scenarios}
    scenario_id = st.selectbox("Szenario", list(scenario_labels.keys()), format_func=lambda k: scenario_labels[k])
    desc = next((s["description"] for s in scenarios if s["id"] == scenario_id), "")
    if desc:
        st.caption(desc)

    intensity = st.slider("Schock-Intensität (×)", 0.5, 2.0, 1.0, 0.1)
    global_pct = st.number_input("Globaler Schock optional (%)", value=0.0, min_value=-90.0, max_value=0.0, step=1.0)
    global_shock = global_pct / 100 if global_pct != 0 else None

    if st.button("Simulation starten", type="primary"):
        with st.spinner("Simulation läuft …"):
            r = compute_stress_test(db, user_id, syms, scenario_id, intensity, global_shock)

        st.markdown(f"**{r['scenario_label']}**")
        c1, c2 = st.columns(2)
        c1.metric("Portfolio Basis", f"{r['portfolio_base_return'] * 100:+.2f}%")
        c2.metric("Portfolio gestresst", f"{r['portfolio_shocked_return'] * 100:+.2f}%")

        sim = r.get("simulation") or {}
        rows = []
        for sym, d in sim.items():
            rows.append(
                {
                    "Ticker": sym,
                    "Sektor": d["sector"],
                    "Schock": f"{d['applied_shock'] * 100:+.1f}%",
                    "Basis": f"{d['base_return'] * 100:+.2f}%",
                    "Gestresst": f"{d['shocked_return'] * 100:+.2f}%",
                }
            )
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

        labels = list(sim.keys())
        base = [sim[s]["base_return"] * 100 for s in labels]
        shocked = [sim[s]["shocked_return"] * 100 for s in labels]
        st.plotly_chart(stress_comparison(labels, base, shocked), use_container_width=True)
