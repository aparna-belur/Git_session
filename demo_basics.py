from datetime import datetime

import streamlit as st

st.set_page_config(page_title="Streamlit basics")
st.title("Streamlit basics")

st.header("1. Rerun model")
name = st.text_input("Your name", "world")
st.write(f"Hello, {name}!")

st.header("2. Plain variables reset, session_state remembers")
plain = 0
if st.button("Add 1 (plain variable)"):
    plain += 1
st.write("plain variable:", plain)

if "count" not in st.session_state:
    st.session_state.count = 0
if st.button("Add 1 (session_state)"):
    st.session_state.count += 1
st.write("session_state count:", st.session_state.count)

st.header("3. Widgets return values")
age = st.slider("Age", 0, 100, 25)
color = st.selectbox("Colour", ["red", "green", "blue"])
agree = st.checkbox("I agree")
st.write({"age": age, "colour": color, "agree": agree})

st.header("4. Form (reruns only on submit)")
with st.form("my_form"):
    city = st.text_input("City")
    days = st.number_input("Days", min_value=1, max_value=30, value=3)
    submitted = st.form_submit_button("Submit")
if submitted:
    st.success(f"Trip to {city or '?'} for {days} days")

st.header("5. Fragment: only this part refreshes")


@st.fragment(run_every="3s")
def clock() -> None:
    st.write("Time now:", datetime.now().strftime("%H:%M:%S"))


clock()