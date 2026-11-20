"""Month-end variance commentary with its facts and the number check."""
import streamlit as st

from app.common import commentary, footer, setup
from fpacopilot.commentary import check

setup("Commentary")
st.title("Variance commentary", icon=":material/edit_note:")
f, out = commentary()
st.caption(f"Source: {out['source']}")
with st.container(border=True):
    st.markdown(out["text"])

bad = check(out["text"], f)
if bad:
    st.error(f"Figures not found in the facts: {bad}", icon=":material/error:")
else:
    st.success("Number check passed: every figure in the text appears in the facts below.", icon=":material/verified:")

st.subheader("How it is produced")
st.markdown(
    "1. The pipeline computes the **facts**: every figure the commentary may use, already rounded and formatted.\n"
    "2. A language model (Claude) drafts the text from those facts only. Without an API key, a deterministic "
    "template writes it instead. Drafts are cached, so this app never calls the API.\n"
    "3. A **number check** extracts every figure from the draft and rejects it if one is not in the facts: the "
    "model can explain the numbers but cannot invent or recompute them."
)
with st.expander("Facts (JSON)"):
    st.json(f)
footer()
