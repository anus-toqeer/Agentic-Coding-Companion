# 💻 Coding Companion AI

### An Agentic AI-Powered Coding Assistant

An intelligent coding companion built using **LangChain, LangGraph, Groq, Tavily, and Streamlit** that can explore project files, understand code, suggest improvements, execute programs, and assist with debugging.

The project began as an **Artificial Intelligence Lab activity**, where the challenge was to brainstorm useful features, design AI tools, and implement them with the help of AI.

The goal was not simply to generate code, but to explore how **human creativity, problem-solving, and decision-making can work alongside artificial intelligence** to build something useful.

## ✨ Features

### 🤖 Agentic AI Assistant
- Understands natural-language coding requests.
- Selects appropriate tools based on the task.
- Performs multi-step operations using LangChain agents.
- Maintains conversation context across interactions.

### 📁 Interactive File Explorer
- Explore the configured coding workspace.
- Expand and collapse folders.
- Select files to inspect their contents.
- View file information and syntax-highlighted source code.

### 🛠️ Coding Tools
- **List Files:** Explore files and directories.
- **Read Files:** Retrieve source code.
- **Write Files:** Create or modify files.
- **Search in Files:** Locate keywords and code patterns.
- **Run Files:** Execute supported programs.
- **Detect Language:** Identify programming languages.
- **Compare Files:** Examine differences between files.
- **Delete Files:** Remove files with approval.
- **Web Search:** Retrieve information through Tavily.

### ⚡ Quick AI Actions
Select a file and instantly request:
- Code explanation
- Bug analysis
- Optimization suggestions

### 🔍 Agent Activity Tracking
Inspect the tools selected by the agent, their arguments, and the returned results.

### 📝 Code Diff Viewer
Compare original and proposed source code side by side before accepting modifications.

### 🛡️ Human-in-the-Loop Approval
The agent pauses before configured sensitive operations, including:
- Writing or modifying files
- Deleting files
- Executing code

Users can approve or reject proposed actions before execution.

### 💬 Persistent Chat History
- Save conversations locally using SQLite.
- Create and switch between conversations.
- Rename or delete conversations.
- Reopen previous conversations after restarting the application.

### 🧠 Persistent Agent Memory
LangGraph SQLite checkpointing preserves agent conversation state across application restarts.

## 🧰 Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core development |
| LangChain | Agent creation and tool integration |
| LangGraph | Agent state and human-in-the-loop workflows |
| Groq | LLM inference |
| gpt-oss-120b | Language model |
| Tavily | Web search |
| Streamlit | Interactive web interface |
| SQLite | Persistent chat history and agent checkpoints |
| difflib | Code difference visualization |

## 📂 Project Structure

```text
CodingCompanion/
├── app.py
├── agent.py
├── llm.py
├── tools.py
├── history.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── data/                 # Generated locally, excluded from Git
```

The coding workspace is configured separately through the `WORK_DIR` environment variable.

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/anus-toqeer/Agentic-Coding-Companion
cd Coding-Companion-AI
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate on Windows:

```powershell
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key
MODEL_NAME=openai/gpt-oss-120b
WORK_DIR=C:\path\to\your\coding_workspace
```

Create the working directory if it doesn't already exist.

### 5. Run the application

```bash
streamlit run app.py
```

Open the local URL displayed by Streamlit.

## 🔄 How It Works

1. The user submits a coding request through Streamlit.
2. The LangChain agent interprets the request using the configured LLM.
3. The agent chooses the appropriate coding tools.
4. Tools interact with files inside the configured workspace.
5. Sensitive tool calls pause for human approval.
6. The agent processes tool results and responds to the user.
7. Conversation history and agent checkpoints are saved locally.

## 🔐 Safety and Limitations

This project is intended for **local development and educational experimentation**.

- File operations are intended to remain inside the configured workspace.
- Human approval is required for configured sensitive tool calls.
- Code execution is not fully sandboxed and may access resources outside the workspace.
- The application is not designed for untrusted public multi-user hosting.
- API keys, local conversations, and checkpoints should not be committed to GitHub.

## 🎓 Learning Outcomes

This project provided hands-on experience with:

- Agentic AI architecture
- LLM tool calling
- Designing custom AI tools
- Prompt engineering
- LangChain and LangGraph
- Human-in-the-loop workflows
- Agent observability
- Persistent agent state
- AI-assisted software development

## 💡 Inspiration

This project grew out of an AI lab activity that encouraged students to brainstorm features, design tools, and use AI meaningfully to implement their ideas.

It demonstrated that AI can be more than a shortcut for writing code. When used thoughtfully, it can support creativity, experimentation, problem-solving, and practical learning.

## 👨‍💻 Author

**Anus Toqeer**

BS Computer Science — PUCIT, University of the Punjab

---

*Built as an Artificial Intelligence Lab activity and expanded through further experimentation and learning.*