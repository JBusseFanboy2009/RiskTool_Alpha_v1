"""Login / registration for Streamlit."""

from __future__ import annotations

import streamlit as st
from sqlalchemy.orm import Session

from app.models import Portfolio, User
from app.security import hash_password, verify_password


def login_user(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email.strip().lower()).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def register_user(db: Session, email: str, password: str) -> User:
    email = email.strip().lower()
    if len(password) < 8:
        raise ValueError("Passwort muss mindestens 8 Zeichen haben")
    if db.query(User).filter(User.email == email).first():
        raise ValueError("E-Mail ist bereits registriert")
    user = User(email=email, hashed_password=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    db.add(Portfolio(user_id=user.id, name="Main Portfolio"))
    db.commit()
    return user


def render_auth_page(db: Session) -> bool:
    """Returns True when user is authenticated."""
    if st.session_state.get("user_id"):
        return True

    st.title("MyShares")
    st.caption("Portfolio & Risiko-Analyse")

    tab_login, tab_register = st.tabs(["Login", "Registrieren"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("E-Mail", key="login_email")
            password = st.text_input("Passwort", type="password", key="login_password")
            if st.form_submit_button("Einloggen", type="primary", use_container_width=True):
                user = login_user(db, email, password)
                if user:
                    st.session_state.user_id = user.id
                    st.session_state.user_email = user.email
                    st.rerun()
                else:
                    st.error("Ungültige Anmeldedaten")

    with tab_register:
        with st.form("register_form"):
            email = st.text_input("E-Mail", key="reg_email")
            password = st.text_input("Passwort (min. 8 Zeichen)", type="password", key="reg_password")
            if st.form_submit_button("Registrieren", use_container_width=True):
                try:
                    user = register_user(db, email, password)
                    st.session_state.user_id = user.id
                    st.session_state.user_email = user.email
                    st.success("Registrierung erfolgreich!")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

    return False
