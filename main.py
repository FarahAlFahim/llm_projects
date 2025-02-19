import os
import javalang

# Set your API key here
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")


# from langchain.llms import OpenAI 
from langchain_community.llms import OpenAI
llm = OpenAI(temperature=0.9)
prompt = "What would a good company name be for a company that makes colorful socks?"

# print(llm(prompt))

# print(OPENAI_API_KEY)
# print(DEEPSEEK_API_KEY)


# file_path = "/Users/fahim/Desktop/PhD/Projects/zookeeper/src/java/main/org/apache/zookeeper/server/quorum/QuorumPeer.java"
# with open(file_path, 'r') as f:
#     content = f.read()
# tree = javalang.parse.parse(content)
# # print("Javalang Tree:", tree)

# # Define the file path to save the result
# output_file_path = "javalang_tree_output.txt"

# # Write the result to the file
# with open(output_file_path, 'w') as output_file:
#     output_file.write("Javalang Tree:\n")
#     output_file.write(str(tree))

# print(f"Javalang Tree output saved to: {output_file_path}")



def find_correct_codebase_path(requested_file, codebase_dirs):
    """
    Removes incorrect codebase_dir prefix from the requested file 
    and checks which codebase_dir contains the actual file.
    """
    for codebase_dir in codebase_dirs:
        if requested_file.startswith(codebase_dir):
            relative_path = requested_file[len(codebase_dir):].lstrip("/")
            print('relative path:', relative_path)
            break
    else:
        relative_path = requested_file  # If no prefix matches, use the original file name

    # Check in all codebase_dirs to find where the file actually exists
    for codebase_dir in codebase_dirs:
        corrected_path = os.path.join(codebase_dir, relative_path)
        if os.path.exists(corrected_path):
            return corrected_path  # Return the correct path if found

    return None  # File not found in any codebase_dir

new_file = "/Users/fahim/Desktop/PhD/Projects/zookeeper/src/java/farah/org/apache/zookeeper/server/quorum/QuorumPeer.java"
if os.path.exists(new_file):
    print("already exist")
else:
    codebase_dirs = ["/Users/fahim/Desktop/PhD/Projects/zookeeper/src/java/main", "/Users/fahim/Desktop/PhD/Projects/zookeeper/src/java/test"]
    correct_path = find_correct_codebase_path(new_file, codebase_dirs)
    if correct_path:
        print(correct_path)
    else:
        print("not found")