import os

# Set your API key here
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# from langchain.llms import OpenAI 
from langchain_community.llms import OpenAI
llm = OpenAI(temperature=0.9)
prompt = "What would a good company name be for a company that makes colorful socks?"

print(llm(prompt))

# print(OPENAI_API_KEY)
