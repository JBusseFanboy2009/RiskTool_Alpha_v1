"""MyShares positions page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.services.position_service import (
    create_position,
    delete_position,
    get_position_detail,
    list_positions_for_user,
    search_market,
)
from app.ui.charts import donut_chart, horizontal_bar, line_chart


def _fmt_pct(v: float) -> str:
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.2f}%"


def render_myshares(db, user_id: int) -> None:
    st.header("MyShares")

    with st.expander("Neue Position erfassen", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            ticker = st.text_input("Ticker", placeholder="AAPL, SPY, VUSA.L …", key="new_ticker")
        with c2:
            quantity = st.number_input("Stückzahl", min_value=0.0001, value=1.0, step=0.1, key="new_qty")
        with c3:
            buy_price = st.number_input("Kaufkurs", min_value=0.0001, value=100.0, step=0.01, key="new_buy")

        if ticker and len(ticker.strip()) >= 2:
            suggestions = search_market(ticker.strip())
            if suggestions:
                st.caption("Vorschläge:")
                cols = st.columns(min(4, len(suggestions)))
                for i, s in enumerate(suggestions[:4]):
                    if cols[i].button(s["symbol"], key=f"sug_{s['symbol']}"):
                        st.session_state.new_ticker = s["symbol"]
                        st.rerun()

        if st.button("Speichern", type="primary"):
            try:
                create_position(db, user_id, ticker, quantity, buy_price)
                st.success("Position gespeichert")
                st.rerun()
            except ValueError as e:
                st.error(str(e))

    rows = list_positions_for_user(db, user_id)
    if not rows:
        st.info("Keine Positionen vorhanden.")
        return

    df = pd.DataFrame(rows)
    df["Tag %"] = df["day_change_pct"].apply(_fmt_pct)
    df["Wert EUR"] = df["value"].map(lambda v: f"{v:,.2f}")

    display = df[["ticker", "quantity", "buy_price", "current_price", "Tag %", "Wert EUR", "id"]].rename(
        columns={
            "ticker": "Ticker",
            "quantity": "Stück",
            "buy_price": "Kaufkurs",
            "current_price": "Live",
            "id": "ID",
        }
    )

    st.dataframe(
        display.drop(columns=["ID"]),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Position im Detail")
    options = {f"{r['ticker']} (ID {r['id']})": r["id"] for r in rows}
    choice = st.selectbox("Position wählen", list(options.keys()))
    pid = options[choice]
    period = st.radio("Zeitraum", ["1mo", "6mo", "1y", "3y"], horizontal=True, index=2)

    if st.button("Analyse anzeigen", type="primary"):
        st.session_state.detail_id = pid
        st.session_state.detail_period = period

    if st.session_state.get("detail_id"):
        _render_detail(db, user_id, st.session_state.detail_id, st.session_state.get("detail_period", "1y"))

    st.subheader("Position löschen")
    del_id = st.selectbox("Zu löschende Position", [r["id"] for r in rows], format_func=lambda i: next(r["ticker"] for r in rows if r["id"] == i))
    if st.button("Löschen", type="secondary"):
        delete_position(db, user_id, del_id)
        st.session_state.pop("detail_id", None)
        st.success("Gelöscht")
        st.rerun()


def _render_detail(db, user_id: int, position_id: int, period: str) -> None:
    try:
        detail = get_position_detail(db, user_id, position_id, period)
    except ValueError as e:
        st.error(str(e))
        return

    st.markdown(f"### {detail.ticker}")
    st.metric("Live-Kurs", f"{detail.latest_price:.2f}")

    if detail.history:
        dates = [p.date for p in detail.history]
        closes = [p.close for p in detail.history]
        st.plotly_chart(line_chart(dates, closes, f"Kursverlauf ({period.upper()})"), use_container_width=True)

    s = detail.structure
    st.markdown("#### Struktur-Analyse")
    st.write(f"**Sektor:** {s.sector} · **Branche:** {s.industry}")

    if s.valuation_ratios:
        st.markdown("**Fundamentale Kennzahlen**")
        ratio_df = pd.DataFrame([{"Kennzahl": k, "Wert": v} for k, v in s.valuation_ratios.items()])
        st.dataframe(ratio_df, hide_index=True, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        if s.sectors:
            labels = list(s.sectors.keys())
            values = list(s.sectors.values())
            st.plotly_chart(horizontal_bar(labels, values, "Sektorverteilung"), use_container_width=True)
    with c2:
        if s.top_holdings:
            labels = list(s.top_holdings.keys())
            values = list(s.top_holdings.values())
            st.plotly_chart(donut_chart(labels, values, "Top Holdings"), use_container_width=True)
