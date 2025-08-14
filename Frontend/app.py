import streamlit as st
from agents import graph
from langchain_core.messages import HumanMessage

st.title("Hotel Chatbot")

# Initialize chat history and state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_confirmation" not in st.session_state:
    st.session_state.pending_confirmation = None

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message("user" if isinstance(message, HumanMessage) else "assistant"):
        st.markdown(message.content)

# Handle confirmation if pending
if st.session_state.pending_confirmation:
    options = [f"{c[0]}, {c[1]}" for c in st.session_state.pending_confirmation["options"]]
    selected = st.radio("Select a location:", options, key="location_select")
    if st.button("Confirm"):
        lat, lon = map(float, selected.replace(" ", "").split(","))
        st.session_state.messages.append(HumanMessage(content=f"Selected: {lat}, {lon}"))
        st.session_state.pending_confirmation = None
        state = graph.invoke({"messages": st.session_state.messages})
        st.session_state.messages = state.messages
        st.experimental_rerun()

# User input
if prompt := st.chat_input("Ask about hotels..."):
    st.session_state.messages.append(HumanMessage(content=prompt))
    with st.chat_message("user"):
        st.markdown(prompt)

    # Process with LangGraph
    state = graph.invoke({"messages": st.session_state.messages, "pending_confirmation": st.session_state.pending_confirmation})
    st.session_state.messages = state.messages
    st.session_state.pending_confirmation = state.pending_confirmation

    with st.chat_message("assistant"):
        st.markdown(state.messages[-1].content)