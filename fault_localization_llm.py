from langchain import OpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, Tool
import os

# Initialize OpenAI LLM
llm = OpenAI(temperature=0)

# Step 1: Stack Trace Parsing Tool
def parse_stack_trace(stack_trace):
    """Parse the stack trace to extract file-level details."""
    parsed_files = []
    for line in stack_trace.split("\n"):
        if "at" in line and ".java:" in line:
            try:
                file_path = line.split("(")[1].split(".java")[0] + ".java"
                parsed_files.append(file_path)
            except IndexError:
                continue
    return list(set(parsed_files))

def parse_tool(input_text):
    return parse_stack_trace(input_text)

# Step 2: Repository Context Tool
class GitRepositoryManager:
    def __init__(self, repo_list):
        """Initialize with a list of repository configurations."""
        self.repos = repo_list  # List of dictionaries with 'path' and 'name'

    def checkout_commit(self, repo_name, commit_hash):
        """Checkout a specific commit in the specified repository."""
        repo_path = self._get_repo_path(repo_name)
        if repo_path:
            os.system(f"git -C {repo_path} checkout {commit_hash}")
        else:
            raise ValueError(f"Repository {repo_name} not found.")

    def read_file(self, repo_name, file_path):
        """Read a file from a specific repository."""
        repo_path = self._get_repo_path(repo_name)
        if repo_path:
            full_path = os.path.join(repo_path, file_path)
            if os.path.exists(full_path):
                with open(full_path, "r") as file:
                    return file.read()
        return None

    def _get_repo_path(self, repo_name):
        """Get the file path for a repository by name."""
        for repo in self.repos:
            if repo['name'] == repo_name:
                return repo['path']
        return None

# Step 3: File Suspiciousness Scoring (with LLM)
def suspiciousness_reasoning_tool(stack_trace, source_code):
    """Use an LLM to assess suspiciousness based on stack trace and file content."""
    
    template="""
    You are a fault localization assistant. Based on the following stack trace:
    {stack_trace}
    and the provided source code:
    {source_code}
    Identify how likely this file is to contain a bug. Provide a score between 0 and 1 and explain your reasoning.
    """
    
    prompt = PromptTemplate.from_template(template)
    llm = ChatOpenAI(model='gpt-4o-mini', temperature = 0)
    chain = LLMChain(llm=llm, prompt=prompt)
    return chain.run({"stack_trace": stack_trace, "source_code": source_code})

# Initialize Repository Manager
repositories = [
    {"name": "zookeeper", "path": "/path/to/zookeeper/repository"},
    {"name": "hadoop", "path": "/path/to/hadoop/repository"}
]
git_manager = GitRepositoryManager(repositories)

# Define Agent Tools
parse_tool_instance = Tool(
    name="Parse Stack Trace",
    func=parse_tool,
    description="Extract file paths from a stack trace."
)

def git_tool(input_text):
    repo_name, file_path = input_text.split(",", 1)
    return git_manager.read_file(repo_name.strip(), file_path.strip())

git_tool_instance = Tool(
    name="Git Tool",
    func=git_tool,
    description="Read files from a repository. Provide input in the format 'repo_name, file_path'."
)

# Initialize the Agent
tools = [parse_tool_instance, git_tool_instance]
agent = initialize_agent(tools, llm, agent="zero-shot-react-description", verbose=True)

# Step 4: Running the Agent
stack_trace = """Exception in thread "main" java.lang.NullPointerException
    at org.apache.zookeeper.server.quorum.QuorumPeer$LearnerCnxAcceptor.run(QuorumPeer.java:999)
    at org.apache.zookeeper.server.quorum.Follower.processPacket(Follower.java:204)
"""

# Parse Stack Trace
parsed_files = agent.run(stack_trace)
print("Parsed Files:", parsed_files)

# Score Suspiciousness for Each File
for parsed_file in parsed_files:
    repo_name, file_path = "zookeeper", parsed_file  # Update logic for repo selection if needed
    source_code = git_manager.read_file(repo_name, file_path)
    if source_code:
        score_and_reasoning = suspiciousness_reasoning_tool(stack_trace, source_code)
        print(f"File: {file_path}\nScore and Reasoning:\n{score_and_reasoning}\n")
    else:
        print(f"File: {file_path} not found in the repository.")
