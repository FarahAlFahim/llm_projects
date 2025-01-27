import os
import javalang

# Set your API key here
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# from langchain.llms import OpenAI 
from langchain_community.llms import OpenAI
llm = OpenAI(temperature=0.9)
prompt = "What would a good company name be for a company that makes colorful socks?"

# print(llm(prompt))

# print(OPENAI_API_KEY)


file_path = "/Users/fahim/Desktop/PhD/Projects/zookeeper/src/java/main/org/apache/zookeeper/server/quorum/QuorumPeer.java"
with open(file_path, 'r') as f:
    content = f.read()
tree = javalang.parse.parse(content)
# print("Javalang Tree:", tree)

# Define the file path to save the result
output_file_path = "javalang_tree_output.txt"

# Write the result to the file
with open(output_file_path, 'w') as output_file:
    output_file.write("Javalang Tree:\n")
    output_file.write(str(tree))

print(f"Javalang Tree output saved to: {output_file_path}")
