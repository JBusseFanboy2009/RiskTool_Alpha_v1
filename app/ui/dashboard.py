"""Portfolio overview page."""

from __future__ import annotations

import streamlit as st

from app.services.position_service import portfolio_overview
from app.ui.charts import pie_chart


def render_dashboard(db, user_id: int) -> None:
    st.header("Portfolio Overview")
    data = portfolio_overview(db, user_id)
    total = data["total_value"]
    slices = data["slices"]

    st.metric("Gesamtwert", f"{total:,.2f} EUR")

    if not slices:
        st.info("Noch keine Positionen im Depot. Füge welche unter **MyShares** hinzu.")
        return

    labels = [s["ticker"] for s in slices]
    values = [s["value"] for s in slices]
    st.plotly_chart(pie_chart(labels, values, "Allokation"), use_container_width=True)

    st.subheader("Positionen")
    for s in slices:
        st.write(f"**{s['ticker']}** — {s['value']:,.2f} EUR ({s['weight'] * 100:.1f}%)")
