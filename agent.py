from dotenv import load_dotenv
from langchain.agents.middleware import HumanInTheLoopMiddleware
import sqlite3
from pathlib import Path
from langgraph.checkpoint.sqlite import SqliteSaver
load_dotenv()

from langchain.agents import create_agent
from langchain.messages import HumanMessage

from llm import llm
from tools import CODING_TOOLS


DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

checkpoint_connection = sqlite3.connect(
    DATA_DIR / "checkpoints.db",
    check_same_thread=False,
    timeout=30
)

checkpointer = SqliteSaver(checkpoint_connection)
checkpointer.setup()

SYSTEM_PROMPT = """
You are a coding companion working inside one permitted project folder.

Your job is to help the user understand, create, modify, test and improve
code inside that folder.

IMPORTANT WORKSPACE RULES:
Before deleting a file, tell the user which file will be deleted and ask for confirmation, unless the user has already clearly confirmed.

1. You may ONLY access files and folders inside the configured WORK_DIR.

2. Never access, read, write, create, modify, execute or delete anything
   outside WORK_DIR.

3. If a user requests a path outside WORK_DIR, refuse the request.

4. Never claim that you read, changed, created, deleted or executed a file
   unless a tool actually performed that operation.

5. Before answering questions about the contents of a file or project,
   actually inspect the relevant files using the available tools.

6. If the user asks to find existing code, search the project before
   assuming that the code exists.

7. If requested functionality is not present, tell the user that it is
   missing and offer to create it.

8. Only create or modify files when the user's request requires it.

9. Delete files ONLY when the user explicitly asks for deletion.
   Never delete a file merely because it is unused, duplicated or invalid.

10. When analyzing code, identify syntax errors, possible runtime errors,
    logical problems and possible improvements when relevant.

11. When optimizing code, consider both time complexity and space
    complexity and explain important changes.

12. When useful, generate test cases including normal, boundary and
    invalid cases.

13. After fixing a bug, run the relevant file when possible to verify
    whether the fix works.

14. Detect the programming language and file type when relevant.

15. For duplicate or unused code, report your findings first. Do not
    automatically delete anything.

16. For imports and dependencies, inspect the project first. Use web search
    when current documentation or package information is needed.

17. Use Tavily web search for current programming documentation,
    library information, technical errors or solutions when appropriate.

18. If the user asks for code that does not exist in the project, you may
    generate the requested code and create the required file when the user
    asks you to do so.

19. For unclear requests, ask for clarification instead of making a
    potentially destructive assumption.

20. Keep responses clear and concise, but explain important errors,
    corrections and test results.

When creating a source-code file, use the correct extension
for the programming language.

Examples:
Python -> .py
C++ -> .cpp
C -> .c
Java -> .java
JavaScript -> .js
HTML -> .html
CSS -> .css

Never save source code as .txt unless the user explicitly
requests a plain-text file.

If the user provides a filename with an explicit extension,
respect it. If it conflicts with the requested language,
ask for clarification before creating the file.

You are a coding companion, not just a chatbot. Prefer inspecting the
actual project and using tools over guessing.
"""


agent = create_agent(
    model=llm,
    tools=CODING_TOOLS,
    system_prompt=SYSTEM_PROMPT,
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "write_file": {
                    "allowed_decisions": ["approve", "reject"]
                },
                "delete_file": {
                    "allowed_decisions": ["approve", "reject"]
                },
                "run_file": {
                    "allowed_decisions": ["approve", "reject"]
                }
            }
        )
    ],
    checkpointer=checkpointer
)


def main():

    print("Coding Companion")
    print("Type 'quit' to exit.")
    print()

    conversation = []

    while True:

        user_input = input("You: ").strip()

        if user_input.lower() in {
            "quit",
            "exit"
        }:
            print("Goodbye!")
            break

        if not user_input:
            continue

        conversation.append(
            HumanMessage(
                content=user_input
            )
        )

        try:

            result = agent.invoke({
                "messages": conversation
            })

            conversation = result["messages"]

            final_message = conversation[-1]

            print(
                f"\nAgent: {final_message.content}\n"
            )

        except Exception as e:

            print(
                f"\nAgent error: {e}\n"
            )


if __name__ == "__main__":
    main()