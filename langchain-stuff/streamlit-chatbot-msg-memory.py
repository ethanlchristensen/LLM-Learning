import os
import time
from typing import Tuple
import streamlit as st
from dotenv import load_dotenv
from datetime import datetime
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
from langchain.memory.chat_message_histories import StreamlitChatMessageHistory
from langchain.chains import ConversationChain


def log_it(message: str) -> None:
    """
    Function to log messages with datetime
    """

    print(f"[{datetime.now()}]: {message}")

def load_env() -> None:
    """
    Function to check and load the .env file.
    Update the streamlit session_state dict
    """

    if st.session_state.get("env") is None:
        log_it(f"loaded .env: {load_dotenv()}")
        st.session_state["env"] = True


def update_state(update: dict) -> None:
    """
    Function to update the streamlit session_state dict
    :param update: dict of keys/values to add/update
    """

    for key, value in update.items():
        st.session_state[key] = value

def get_auth() -> Tuple[str]:
    """
    Function to get the auth credentials from env
    """

    user = os.getenv("AUTH_USER")
    pswd = os.getenv("AUTH_PASS")
    return (user, pswd)


# create the llm instance
llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo")

# get the auth credentials tuple
auth = get_auth()

# create an instance of the chat history
msgs = StreamlitChatMessageHistory()

# create memory for the langchain conversation chain
memory = ConversationBufferWindowMemory(
    memory_key="history",
    chat_memory=msgs,
    return_messages=True,
    k=2
)

# create the ConversationChain
chain = ConversationChain(
    llm=llm,
    memory=memory,
    verbose=True
)

# initialize the auth_expand_flag and rr_check
if st.session_state.get("auth_expand_flag") is None:
    update_state({"auth_expand_flag":True})
if st.session_state.get("rr_check") is None:
    update_state({"rr_check":False})

# create the side bar to login
with st.sidebar:
    with st.expander(label="Login", expanded=st.session_state.get("auth_expand_flag")):
        st.title("Login")
        username = st.text_input(label="Enter Username:")
        password = st.text_input(label="Enter Password:", type="password")

        if not (username and password):
            st.warning("Please enter the credentials!")
            update_state({"authenticated":False, "auth_expand_flag":True, "rr_check":False})
            msgs.clear()
        elif not (username, password) == auth:
            st.warning("The credentials were not valid!")
            update_state({"authenticated":False, "auth_expand_flag":True, "rr_check":False})
            msgs.clear()
        else:
            st.success("Get to chatting!")
            update_state({"authenticated":True, "auth_expand_flag":False})
            if not st.session_state.get("rr_check"):
                update_state({"rr_check":True})
                st.experimental_rerun()

# initialize the chat with an AI message
if len(msgs.messages) == 0 or st.sidebar.button("Clear Messages"):
    msgs.clear()
    msgs.add_ai_message("How can I help you today?")

# keep track of the avatars. i.e. what langchain uses to identify AI/Human and
# how that maps to streamlit
avatars = {"human": "user", "ai": "assistant"}

# display the messages
for msg in msgs.messages:
    st.chat_message(avatars[msg.type]).write(msg.content)

# text input for user to enter query if logged in
if user_query := st.chat_input(placeholder="Enter message", disabled=not st.session_state.get("authenticated")):
    # write the message to the screen
    st.chat_message("user").write(user_query)

    # have agent get response
    with st.chat_message("assistant"):
        response = None
        # make a spinner while we make the openai call
        with st.spinner("Thinking . . ."):
            message_placeholder = st.empty()
            full_response = ""
            response = chain.run(user_query)

        # build the response and write to the screen one word at a time
        if response:
            for word in response.split(" "):
                full_response += word + " "
                time.sleep(0.05)
                message_placeholder.markdown(full_response + "█ ")
        
        message_placeholder.markdown(full_response)

