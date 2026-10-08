import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

llm = ChatGroq(
    model=os.getenv("MODEL_NAME", "openai/gpt-oss-120b"),
    api_key=os.getenv("API_KEY"),
    temperature=0
)