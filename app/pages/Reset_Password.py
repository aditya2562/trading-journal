import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from core.auth import AuthEngine

st.set_page_config(
    page_title="Reset Password — AI Trading Journal",
    page_icon="🔑",
    layout="centered",
)

auth = AuthEngine()

st.markdown(
    "<h2 style='text-align:center'>🔑 Reset Your Password</h2>",
    unsafe_allow_html=True,
)

query_params = st.query_params
token = query_params.get("token", "")

if not token:
    st.error(
        "No reset token found. Please use the link from your reset email, or request a new reset link from the login page."
    )
    st.stop()

# Center the form
_, center, _ = st.columns([1, 2, 1])

with center:
    with st.form("reset_password_form"):
        st.caption("Enter your new password below.")
        new_password = st.text_input(
            "New Password",
            type="password",
            placeholder="Min 8 characters, at least 1 number"
        )
        confirm_password = st.text_input(
            "Confirm New Password",
            type="password",
            placeholder="Repeat your new password"
        )
        submitted = st.form_submit_button(
            "Reset Password",
            use_container_width=True,
            type="primary",
        )

    if submitted:
        if not new_password or not confirm_password:
            st.error("Please fill in both fields.")
        elif new_password != confirm_password:
            st.error("Passwords do not match.")
        else:
            with st.spinner("Resetting your password..."):
                result = auth.reset_password(token, new_password)

            if result["success"]:
                st.success(
                    "Your password has been reset! "
                    "You can now sign in with your new password."
                )
                st.info("Go to the main page to sign in.")
            else:
                st.error(result["error"])