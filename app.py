
import os
import uuid
import difflib
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from langchain.messages import HumanMessage
from langgraph.types import Command

from agent import agent
from history import (
    create_conversation,
    list_conversations,
    conversation_exists,
    rename_conversation,
    save_message,
    load_messages,
    save_activity,
    load_activity,
    delete_conversation,
)

load_dotenv()

WORK_DIR = Path(os.environ["WORK_DIR"]).expanduser().resolve()

st.set_page_config(
    page_title="Coding Companion AI",
    page_icon="💻",
    layout="wide",
)

st.markdown("""
<style>
    .block-container {
        padding-top: 0.7rem !important;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# SESSION STATE
# ==========================================
if "chat_id" not in st.session_state:
    saved_chats = list_conversations()

    if saved_chats:
        st.session_state.chat_id = saved_chats[0]["id"]
    else:
        st.session_state.chat_id = create_conversation()


if "selected_file" not in st.session_state:
    st.session_state.selected_file = None

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "tool_activity" not in st.session_state:
    st.session_state.tool_activity = []

if "pending_actions" not in st.session_state:
    st.session_state.pending_actions = []

if "agent_busy" not in st.session_state:
    st.session_state.agent_busy = False


# ==========================================
# AGENT CHECKPOINT HELPERS
# ==========================================

def agent_config():
    return {
        "configurable": {
            "thread_id": st.session_state.chat_id
        },
        "recursion_limit": 30,
    }


def get_pending_actions():
    """Read unresolved human approval requests from LangGraph."""
    snapshot = agent.get_state(agent_config())
    actions = []

    for task in snapshot.tasks:
        for interruption in task.interrupts:
            value = interruption.value

            if isinstance(value, dict):
                actions.extend(
                    value.get("action_requests", [])
                )

    return actions


# ==========================================
# CHAT MANAGEMENT
# ==========================================

def open_conversation(chat_id):
    if not conversation_exists(chat_id):
        st.error("Conversation not found.")
        return

    st.session_state.chat_id = chat_id
    st.session_state.messages = load_messages(chat_id)
    st.session_state.tool_activity = load_activity(chat_id)

    st.session_state.pending_actions = get_pending_actions()
    st.session_state.agent_busy = bool(
        st.session_state.pending_actions
    )
    st.session_state.pending_prompt = None


def new_chat():
    chat_id = create_conversation()
    open_conversation(chat_id)


# Load current chat on initial page load
if "loaded_chat_id" not in st.session_state:
    open_conversation(st.session_state.chat_id)
    st.session_state.loaded_chat_id = st.session_state.chat_id


# ==========================================
# FILE HELPERS
# ==========================================

def safe_file(path):
    target = (WORK_DIR / path).resolve()
    target.relative_to(WORK_DIR)
    return target


def get_language(path):
    extensions = {
        ".py": "python",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "cpp",
        ".hpp": "cpp",
        ".java": "java",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".html": "html",
        ".css": "css",
        ".php": "php",
        ".sql": "sql",
        ".json": "json",
        ".md": "markdown",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".sh": "bash",
        ".txt": "text",
    }
    return extensions.get(path.suffix.lower(), "text")


def show_explorer(folder, depth=0):
    if depth > 10:
        return

    try:
        entries = sorted(
            folder.iterdir(),
            key=lambda p: (not p.is_dir(), p.name.lower())
        )
    except OSError:
        st.warning("Unable to access folder.")
        return

    for item in entries:
        if item.is_symlink():
            continue

        relative = item.relative_to(WORK_DIR).as_posix()

        if item.is_dir():
            with st.expander(
                f"📁 {item.name}",
                expanded=False
            ):
                show_explorer(item, depth + 1)

        elif item.is_file():
            selected = (
                st.session_state.selected_file == relative
            )

            if st.button(
                f"📄 {item.name}",
                key=f"file_{relative}",
                use_container_width=True,
                type="primary" if selected else "secondary"
            ):
                st.session_state.selected_file = relative
                st.rerun()


# ==========================================
# TOOL ACTIVITY
# ==========================================

def extract_tool_activity(messages):
    activity = []
    pending = {}

    for message in messages:
        for call in getattr(message, "tool_calls", []) or []:
            item = {
                "tool": call.get("name", "unknown"),
                "args": call.get("args", {}),
                "result": None,
                "status": "pending",
            }

            activity.append(item)

            if call.get("id"):
                pending[call["id"]] = item

        if getattr(message, "type", None) == "tool":
            call_id = getattr(
                message, "tool_call_id", None
            )

            if call_id in pending:
                item = pending[call_id]
                item["result"] = message.content
                item["status"] = (
                    "error"
                    if getattr(message, "status", None) == "error"
                    else "completed"
                )

    return activity


def refresh_tool_activity():
    snapshot = agent.get_state(agent_config())
    messages = snapshot.values.get("messages", [])

    st.session_state.tool_activity = (
        extract_tool_activity(messages)
    )

    save_activity(
        st.session_state.chat_id,
        st.session_state.tool_activity
    )


# ==========================================
# AGENT COMMUNICATION
# ==========================================

def save_visible_message(role, content):
    message = {
        "role": role,
        "content": str(content),
    }

    st.session_state.messages.append(message)

    save_message(
        st.session_state.chat_id,
        role,
        message["content"]
    )


def process_result(result):
    interrupts = result.get("__interrupt__", [])

    if interrupts:
        st.session_state.pending_actions = (
            get_pending_actions()
        )
        st.session_state.agent_busy = True

    else:
        st.session_state.pending_actions = []
        st.session_state.agent_busy = False

        messages = result.get("messages", [])

        if messages:
            response = messages[-1].content

            if not isinstance(response, str):
                response = str(response)

            save_visible_message("assistant", response)

    refresh_tool_activity()


def ask_agent(prompt):
    save_visible_message("user", prompt)

    result = agent.invoke(
        {"messages": [HumanMessage(content=prompt)]},
        config=agent_config()
    )

    process_result(result)


def resume_agent(decisions):
    result = agent.invoke(
        Command(resume={"decisions": decisions}),
        config=agent_config()
    )

    process_result(result)


# ==========================================
# HUMAN APPROVAL PANEL
# ==========================================

def show_approval_panel():
    actions = st.session_state.pending_actions

    if not actions:
        return

    st.warning("Agent paused — review pending actions.")

    with st.form("approval_form"):
        decisions = []

        for index, action in enumerate(actions):
            name = action.get("name", "unknown")
            args = action.get("args", {})

            st.markdown(f"**Action {index + 1}: {name}**")

            if name == "write_file":
                path = args.get("path", "")
                proposed = str(args.get("content", ""))

                st.caption(f"File: {path}")

                try:
                    target = safe_file(path)

                    original = (
                        target.read_text(encoding="utf-8")
                        if target.is_file()
                        else ""
                    )

                    left, right = st.columns(2)

                    with left:
                        st.markdown("Original")
                        st.code(
                            original or "(New file)",
                            language=get_language(target),
                            line_numbers=True,
                        )

                    with right:
                        st.markdown("Proposed")
                        st.code(
                            proposed,
                            language=get_language(target),
                            line_numbers=True,
                        )

                    diff = "".join(
                        difflib.unified_diff(
                            original.splitlines(keepends=True),
                            proposed.splitlines(keepends=True),
                            fromfile="Original",
                            tofile="Proposed",
                        )
                    )

                    with st.expander("View Diff"):
                        st.code(
                            diff or "No changes",
                            language="diff",
                        )

                except (OSError, ValueError, UnicodeError):
                    st.error("Unable to preview file safely.")

            elif name == "delete_file":
                st.error(
                    f"Delete: {args.get('path', '')}"
                )

            elif name == "run_file":
                st.info(
                    f"Execute: {args.get('path', '')}"
                )

            else:
                st.json(args)

            choice = st.radio(
                f"Decision for action {index + 1}",
                ["Reject", "Approve"],
                horizontal=True,
                key=f"approval_{st.session_state.chat_id}_{index}",
            )

            decisions.append(
                {"type": "approve"}
                if choice == "Approve"
                else {
                    "type": "reject",
                    "message": "User rejected the action."
                }
            )

            st.divider()

        submitted = st.form_submit_button(
            "Submit Decisions & Continue",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        with st.spinner("Resuming agent..."):
            try:
                resume_agent(decisions)
                st.rerun()
            except Exception as e:
                st.error(f"Resume failed: {e}")


# ==========================================
# SIDEBAR: SAVED CONVERSATIONS
# ==========================================

with st.sidebar:
    st.title("💬 Chat History")

    if st.button(
        "➕ New Chat",
        use_container_width=True,
        type="primary"
    ):
        new_chat()
        st.rerun()

    st.divider()

    conversations = list_conversations()

    for conversation in conversations:
        chat_id = conversation["id"]
        title = conversation["title"]

        is_active = chat_id == st.session_state.chat_id

        if st.button(
            f"{'🟢' if is_active else '💬'} {title}",
            key=f"open_{chat_id}",
            use_container_width=True,
        ):
            open_conversation(chat_id)
            st.rerun()

    st.divider()
    st.subheader("Manage Current Chat")

    current = next(
        (
            item for item in conversations
            if item["id"] == st.session_state.chat_id
        ),
        None
    )

    current_title = (
        current["title"] if current else "New Chat"
    )

    new_title = st.text_input(
        "Conversation name",
        value=current_title,
        key=f"title_{st.session_state.chat_id}",
    )

    if st.button(
        "✏️ Rename",
        use_container_width=True
    ):
        rename_conversation(
            st.session_state.chat_id,
            new_title
        )
        st.rerun()

    confirm_delete = st.checkbox(
        "Confirm conversation deletion",
        key=f"confirm_{st.session_state.chat_id}"
    )

    if st.button(
        "🗑️ Delete Conversation",
        disabled=not confirm_delete,
        use_container_width=True,
    ):
        delete_conversation(st.session_state.chat_id)
        new_chat()
        st.rerun()


# ==========================================
# HEADER
# ==========================================

st.title("💻 Coding Companion AI")
st.caption(
    "Explore • Understand • Debug • Optimize • Test"
)

explorer, editor, chat = st.columns(
    [1.1, 2.1, 1.8],
    gap="medium"
)


# ==========================================
# FILE EXPLORER
# ==========================================

with explorer:
    st.subheader("📁 Explorer")

    if st.button(
        "🔄 Refresh Files",
        use_container_width=True
    ):
        st.rerun()

    with st.expander(
        f"📁 {WORK_DIR.name}",
        expanded=True
    ):
        show_explorer(WORK_DIR)


# ==========================================
# FILE VIEWER
# ==========================================

with editor:
    st.subheader("📄 File Viewer")

    selected = st.session_state.selected_file

    if selected is None:
        st.info("Select a file from the explorer.")

    else:
        try:
            target = safe_file(selected)

            if not target.is_file():
                st.warning("File no longer exists.")

            elif target.stat().st_size > 1_000_000:
                st.warning("File exceeds the 1 MB preview limit.")

            else:
                content = target.read_text(encoding="utf-8")
                language = get_language(target)

                st.markdown(f"**{selected}**")

                st.caption(
                    f"Language: {language} | "
                    f"Size: {target.stat().st_size} bytes | "
                    f"Lines: {len(content.splitlines())}"
                )

                st.code(
                    content,
                    language=language,
                    line_numbers=True,
                )

                st.divider()
                st.markdown("**Quick AI Actions**")

                col1, col2, col3 = st.columns(3)

                with col1:
                    if st.button(
                        "Explain",
                        use_container_width=True
                    ):
                        st.session_state.pending_prompt = (
                            f"Read {selected} and explain the code."
                        )
                        st.rerun()

                with col2:
                    if st.button(
                        "Debug",
                        use_container_width=True
                    ):
                        st.session_state.pending_prompt = (
                            f"Read {selected}, find possible bugs "
                            "and suggest fixes. Do not modify it."
                        )
                        st.rerun()

                with col3:
                    if st.button(
                        "Optimize",
                        use_container_width=True
                    ):
                        st.session_state.pending_prompt = (
                            f"Read {selected}, analyze complexity "
                            "and suggest optimizations. "
                            "Do not modify it."
                        )
                        st.rerun()

        except (OSError, ValueError, UnicodeError):
            st.error("Unable to preview this file.")


# ==========================================
# AI CHAT
# ==========================================

with chat:
    st.markdown("""
    <style>
        div[data-testid="stColumn"]:last-child {
            transform: translateY(-120px);
        }
    </style>
    """, unsafe_allow_html=True)

    st.subheader("🤖 AI Assistant")

    chat_container = st.container(height=440)

    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if st.session_state.pending_actions:
        show_approval_panel()

    user_prompt = st.chat_input(
        "Ask about your project...",
        disabled=st.session_state.agent_busy,
    )

    pending = st.session_state.pending_prompt

    if pending and not st.session_state.agent_busy:
        st.session_state.pending_prompt = None
        user_prompt = pending

    if user_prompt:
        with st.spinner("Agent is working..."):
            try:
                ask_agent(user_prompt)

                # Name new chats from the first user prompt
                current_messages = st.session_state.messages

                user_messages = [
                    m for m in current_messages
                    if m["role"] == "user"
                ]

                if len(user_messages) == 1:
                    rename_conversation(
                        st.session_state.chat_id,
                        user_prompt[:45]
                    )

                st.rerun()

            except Exception as e:
                st.error(f"Agent error: {e}")

    st.divider()
    st.subheader("⚙️ Agent Activity")

    activity = st.session_state.tool_activity

    if not activity:
        st.caption("Tool calls will appear here.")

    else:
        for index, item in enumerate(reversed(activity)):
            status = item["status"]

            symbol = {
                "completed": "✅",
                "error": "❌",
                "pending": "⏳",
            }.get(status, "⚙️")

            with st.expander(
                f"{symbol} {item['tool']}",
                expanded=False
            ):
                st.markdown("**Arguments**")
                st.json(item["args"])

                st.markdown("**Result**")

                if item["result"] is not None:
                    st.code(str(item["result"]))
                else:
                    st.caption("No result recorded.")
