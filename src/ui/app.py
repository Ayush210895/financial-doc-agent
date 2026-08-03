import requests
import streamlit as st

API_URL = "http://localhost:8000/query"

st.set_page_config(page_title="Financial Document Intelligence Agent", layout="wide")
st.title("Financial Document Intelligence Agent")
st.caption("JPM · GS · BAC · WFC · UBS — ask about filings, risk factors, or financials")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("tool_calls"):
            with st.expander("Tool calls used"):
                for tc in msg["tool_calls"]:
                    st.code(f"{tc['tool']}: {tc['input']}", language="python")

question = st.chat_input("Ask a question about JPM, GS, BAC, WFC, or UBS...")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = requests.post(API_URL, json={"question": question}, timeout=120)
                response.raise_for_status()
                data = response.json()
                answer = data["answer"]
                tool_calls = data.get("tool_calls", [])
            except Exception as e:
                answer = f"Error calling API: {e}\n\nMake sure the FastAPI service is running (`uvicorn src.api.main:app --reload`) or the Docker container is up on port 8000."
                tool_calls = []

        st.markdown(answer)
        if tool_calls:
            with st.expander("Tool calls used"):
                for tc in tool_calls:
                    st.code(f"{tc['tool']}: {tc['input']}", language="python")

    st.session_state.messages.append({"role": "assistant", "content": answer, "tool_calls": tool_calls})
