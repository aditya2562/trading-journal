import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Optional, Dict
import streamlit as st
from core.auth import AuthEngine

auth = AuthEngine()

COOKIE_KEY = "trading_journal_session"

def _get_token() -> str:
    """Gets session token from Streamlit session state."""
    return st.session_state.get(COOKIE_KEY, "")

def _set_token(token: str) -> None:
    """Stores session token in Streamlit session state."""
    st.session_state[COOKIE_KEY] = token

def _clear_token() -> None:
    """Removes session token."""
    if COOKIE_KEY in st.session_state:
        del st.session_state[COOKIE_KEY]

def render_login_page() -> None:

    st.markdown(
        "<h1 style='text-align:center; margin-bottom:0'>📈</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<h2 style='text-align:center'>AI Trading Journal</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center; color:#64748b'>"
        "Behavioral intelligence for better trading decisions"
        "</p>",
        unsafe_allow_html=True,
    )

    st.divider()

    _, center, _ = st.columns([1, 2, 1])

    with center:
        tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

        # ── Login Tab ─────────────────────────────────────────────────────────
        with tab_login:
            
            with st.form("login_form"):
                st.markdown("#### Welcome back")
                email = st.text_input(
                    "Email",
                    placeholder="you@example.com"
                )
                password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Your password"
                )
                submitted = st.form_submit_button(
                    "Sign In",
                    use_container_width=True,
                    type="primary",
                )
            
            if submitted:
                if not email or not password:
                    st.error("Please fill in all fields.")
                else:
                    with st.spinner("Signing in..."):
                        result = auth.login(email, password)

                    if result["success"]:
                        _set_token(result["token"])
                        st.success(
                            f"Welcome back, {result['user']['name']}!"
                        )
                        st.rerun()
                    else:
                        st.error(result["error"])

        # ── Register Tab ──────────────────────────────────────────────────────
        with tab_register:
            
            with st.form("register_form"):
                st.markdown("#### Create your account")
                reg_name = st.text_input(
                    "Full Name",
                    placeholder="Your name"
                )
                reg_email = st.text_input(
                    "Email",
                    placeholder="you@example.com"
                )
                reg_password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Min 8 characters, at least 1 number"
                )
                reg_password2 = st.text_input(
                    "Confirm Password",
                    type="password",
                    placeholder="Repeat your password"
                )
                reg_submitted = st.form_submit_button(
                    "Create Account",
                    use_container_width=True,
                    type="primary",
                )
            
            if reg_submitted:
                if not all([reg_name, reg_email, reg_password, reg_password2]):
                    st.error("Please fill in all fields.")
                elif reg_password != reg_password2:
                    st.error("Passwords do not match.")
                else:
                    with st.spinner("Creating your account..."):
                        result = auth.register(
                            email=reg_email,
                            password=reg_password,
                            name=reg_name,
                        )

                    if result["success"]:
                        _set_token(result["token"])
                        st.success(
                            f"Account created! Welcome, "
                            f"{result['user']['name']}!"
                        )
                        st.rerun()
                    else:
                        st.error(result["error"])

def render_user_menu(user: Dict) -> None:

    with st.sidebar:
        st.markdown("---")
        st.markdown(f"**{user['name']}**")
        st.caption(user['email'])
        st.caption(f"Plan: {user['plan'].upper()}")

        if st.button("Sign Out", use_container_width=True):
            token = _get_token()
            if token:
                auth.logout(token)
            _clear_token()
            st.rerun()

def require_auth() -> Optional[Dict]:

    token = _get_token()

    if token:
        # Validate the existing session
        user = auth.validate_session(token)
        if user:
            return user
        else:
            # Token was invalid or expired
            _clear_token()

    # No valid session — show login page
    render_login_page()
    return None