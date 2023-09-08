import os
from typing import Any, List, Tuple
import streamlit as st
import time
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from dotenv import load_dotenv
from datetime import datetime
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory, ConversationBufferWindowMemory
from langchain.memory.chat_message_histories import StreamlitChatMessageHistory
from langchain.callbacks.base import BaseCallbackHandler
from langchain.chains import ConversationalRetrievalChain, ConversationChain

def log_it(message: str) -> None: print(f"[{datetime.now()}]: {message}")

if st.session_state.get("env") is None:
    log_it(f"loaded .env: {load_dotenv()}")
    st.session_state["env"] = True

llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo")


def update_state(update: dict) -> None:
    for key, value in update.items():
        st.session_state[key] = value

def get_auth() -> Tuple[str]:
    user = os.getenv("AUTH_USER")
    pswd = os.getenv("AUTH_PASS")
    return (user, pswd)


class StreamHandler(BaseCallbackHandler):
    def __init__(self, container: st.delta_generator.DeltaGenerator, inital_text: str = ""):
        self.container = container
        self.text = inital_text
        self.run_id_ignore_token = None
    
    def on_llm_start(self, serialized: dict, prompts: List[str], **kwargs) -> Any:
        if prompts[0].startswith("Human: "):
            self.run_id_ignore_token = kwargs.get("run_id")
        
    def on_llm_new_token(self, token: str, **kwargs) -> Any:
        if self.run_id_ignore_token == kwargs.get("run_id"):
            return
        self.text += token
        self.container.markdown(self.text)
    
class PrintRetreival(BaseCallbackHandler):
    def __init__(self, container: st.delta_generator.DeltaGenerator):
        self.status = container.status("**Retrieval**")
    
    def on_retriever_start(self, serialized: dict, query: str, **kwargs):
        self.status.write(f"**Question:** {query}")
        self.status.update(label=f"**Retrieval:** {query}")

    def on_retriever_end(self, documents, **kwargs):
        for idx, doc in enumerate(documents):
            source = os.path.basename(doc.metadata["source"])
            self.status.write(f"**Documents {idx} from {source}**")
            self.status.markdown(doc.page_content)
        self.status.update(state="complete")

auth = get_auth()

msgs = StreamlitChatMessageHistory()

memory = ConversationBufferWindowMemory(
    memory_key="history",
    chat_memory=msgs,
    return_messages=True,
    k=2
)

chain = ConversationChain(
    llm=llm,
    memory=memory,
    verbose=True
)

if st.session_state.get("auth_expand_flag") is None:
    update_state({"auth_expand_flag":True})
if st.session_state.get("rr_check") is None:
    update_state({"rr_check":False})

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

if len(msgs.messages) == 0 or st.sidebar.button("Clear Messages"):
    msgs.clear()
    msgs.add_ai_message("How can I help you today?")

avatars = {"human": "user", "ai": "assistant"}

for msg in msgs.messages:
    st.chat_message(avatars[msg.type]).write(msg.content)

if user_query := st.chat_input(placeholder="Enter message", disabled=not st.session_state.get("authenticated")):
    st.chat_message("user").write(user_query)

    with st.chat_message("assistant"):
        response = None
        with st.spinner("Thinking . . ."):
            message_placeholder = st.empty()
            full_response = ""
            response = chain.run(user_query)

        if response:
            for word in response.split(" "):
                full_response += word + " "
                time.sleep(0.05)
                message_placeholder.markdown(full_response + "█ ")
        
        message_placeholder.markdown(full_response)

