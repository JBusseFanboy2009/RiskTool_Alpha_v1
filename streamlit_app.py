"""
MyShares — Streamlit App (Haupt-Einstiegspunkt für share.streamlit.io)

Lokal starten:
    streamlit run streamlit_app.py
"""

from __future__ import annotations

import streamlit as st

from app.ui.auth import render_auth_page
from app.ui.dashboard import render_dashboard
from app.ui.db import get_session, init_database
from app.ui.positions import render_myshares
from app.ui.risk import (
    render_correlation,
    render_drawdown,
    render_risk_o_meter,
    render_stress,
    render_var_cvar,
    render_volatility,
)

st.set_page_config(
    page_title="MyShares",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_database()

PAGES = {
    "Portfolio Overview": render_dashboard,
    "MyShares": render_myshares,
    "Risiko-O-Meter": render_risk_o_meter,
    "Volatilität": render_volatility,
    "Korrelation": render_correlation,
    "Maximum Drawdown": render_drawdown,
    "VaR & CVaR": render_var_cvar,
    "Stress Testing": render_stress,
}


def main() -> None:
    with get_session() as db:
        if not render_auth_page(db):
            return

        with st.sidebar:
            st.title("MyShares")
            st.caption(st.session_state.get("user_email", ""))
            page = st.radio("Navigation", list(PAGES.keys()), label_visibility="collapsed")
            st.divider()
            if st.button("Logout", use_container_width=True):
                for key in ("user_id", "user_email", "detail_id", "detail_period"):
                    st.session_state.pop(key, None)
                st.rerun()

        PAGES[page](db, st.session_state.user_id)


if __name__ == "__main__":
    main()
