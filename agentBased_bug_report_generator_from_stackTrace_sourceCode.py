from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, Tool
from langchain.tools import tool
import json
from langchain_core.runnables.utils import AddableDict
from langchain import PromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
import os
import javalang
import subprocess


# Get the commit version before a specific timestamp
def get_commit_version(creation_time, repo_path, git_branch):
    command = f'git rev-list -n 1 --before="{creation_time}" {git_branch}'
    result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=repo_path)
    commit_version = result.stdout.strip()
    return commit_version

# Checkout to the specific commit version
def checkout_to_commit(commit_version, repo_path, git_branch):
    # Ensure working directory is clean (optional)
    subprocess.run('git stash --include-untracked', shell=True, cwd=repo_path)
    reset_command = f'git checkout {git_branch}'
    subprocess.run(reset_command, shell=True, cwd=repo_path)
    checkout_command = f'git checkout {commit_version}'
    subprocess.run(checkout_command, shell=True, cwd=repo_path)



# Define tools (as before)
@tool
def parse_stack_trace(stack_trace):
    """Parse stack traces directly provided in the input JSON."""
    # print("------- Parse Stack Trace (start) ----------")
    # print("input stack trace:", stack_trace)
    # print(json.dumps(stack_trace))
    # print("------- Parse Stack Trace (end) ----------")
    return json.dumps(stack_trace)




def find_method_with_javalang(full_identifier, codebase_dirs):
    """
    Locate the file corresponding to the full identifier, parse it, and extract the method.
    """
    # Check if the method is already in the cache
    if full_identifier in method_cache:
        return method_cache[full_identifier]
    
    # Validate the full_identifier format
    if not full_identifier or full_identifier.count('.') < 2:
        return "Invalid format. Please request a method using the fully qualified format: {package}.{class}.{method}"

    # Split the full identifier into class path and method name
    *class_path, method_name = full_identifier.split('.')
    class_name = class_path[-1] + ".java"
    class_dir = os.path.join(*class_path[:-1])  # Exclude the class name

    # Traverse through codebase directories to find the class file
    for dir_path in codebase_dirs:
        file_path = os.path.join(dir_path, class_dir, class_name)
        print("------- find_method_with_javalang (start) ----------")
        print("File Path:", file_path)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    if "(" in full_identifier:
                        method_cache[full_identifier] = content
                        return content
                    # Parse the Java file with javalang
                    tree = javalang.parse.parse(content)
                    # print("Javalang Tree:", tree)
                    for _, method in tree.filter(javalang.tree.MethodDeclaration):
                        # Check if this is the requested method
                        if method.name == method_name:
                            print("method.name:", method.name)
                            print("method.position:", method.position)
                            # Extract full method code
                            method_code = extract_method_code(content, method.position)
                            # Cache the result for future lookups
                            method_cache[full_identifier] = method_code
                            # print("method_cache:", method_cache)
                            print("------- find_method_with_javalang (end) ----------")
                            return method_code
            except Exception as e:
                print(f"Error parsing file {file_path}: {e}")
    
    # If not found, cache and return a default response
    method_cache[full_identifier] = "[Method not found in codebase]"
    return "[Method not found in codebase]"

def extract_method_code(file_content, position):
    """
    Extract the full method code using the position provided by javalang.
    """
    lines = file_content.splitlines()
    start_line = position.line - 1  # javalang position is 1-indexed
    method_lines = []
    open_braces = 0
    found_method_start = False  # To track when the method body starts

    for i in range(start_line, len(lines)):
        line = lines[i]
        method_lines.append(line)

        # Update brace counts
        open_braces += line.count('{')
        open_braces -= line.count('}')

        # Check if we are inside the method body
        if '{' in line and not found_method_start:
            found_method_start = True

        # Stop when all braces are balanced after method body starts
        if found_method_start and open_braces == 0:
            break

    print("------- extract_method_code (start) ----------")
    print("start_line:", start_line)
    print("------- extract_method_code (end) ----------")
    return "\n".join(method_lines)




@tool
def provide_method(full_identifier_data):
    """
    Provide the source code for a specific method given its full identifier.
    Note:
        Always request method names in the fully qualified format: {package}.{class}.{method}.
    """
    full_identifier = full_identifier_data.strip().replace("'","").replace('"', '').replace("`","")
    method_code = find_method_with_javalang(full_identifier, codebase_dirs)
    print("------- provide_method (start) ----------")
    print(f"Method '{full_identifier}' provided.")
    # print(method_code)
    print("------- provide_method (end) ----------")
    return method_code



@tool
def analyze_method_and_request_next(input_data):
    """
    Analyze the provided method and determine if further methods are required.
    Returns the next method to request or observations so far if no further methods are needed.
    Note:
        Always request method names in the fully qualified format: {package}.{class}.{method}.
    """
    # Normalize input_data
    input_data = input_data.strip().replace("'","").replace('"', '').replace("`","")
    
    # Retrieve the method source code using the cache-aware dynamic retrieval
    method_body = find_method_with_javalang(input_data, codebase_dirs)
    print("------- analyze_method_and_request_next (start) ----------")
    print(f"Method '{input_data}' provided.")
    # print(method_body)
    # print("------- analyze_method_and_request_next (end) ----------")
    
    # Construct the LLM prompt
    template = """
    You are analyzing a call graph for a bug report. The current method is:

    Method: {input_data}
    Source Code:
    {method_body}

    If this method calls any other methods not in the stack trace, identify one such method and return its name.
    Always request method names in the fully qualified format: 
    {{package}}.{{class}}.{{method}}

    If no further methods are needed, respond with observations so far based on analyzed methods.
    """
    prompt = PromptTemplate.from_template(template)
    
    # Configure the LLM
    llm = ChatOpenAI(model='gpt-4o-mini', temperature=0)
    chain = LLMChain(llm=llm, prompt=prompt)

    try:
        # Run the LLM chain
        response = chain.run({'input_data': input_data, 'method_body': method_body})
        print("response:", response)
        print("------- analyze_method_and_request_next (end) ----------")
        return response
    except Exception as e:
        # Log or handle errors gracefully
        print(f"Error during LLM chain execution: {e}")
        return "Error occurred during method analysis. Please try again."







def generate_final_bug_report(agent_based_source_code_analysis, dev_written_bug_report):
    """Generate the final bug report based on analyzed methods."""
    # print("------------------- generate final bug report (start) --------------")
    # print("bug report:", dev_written_bug_report)
    # print("analyzed method:", agent_based_source_code_analysis)
    # print("current_source_code_dict:", current_source_code_dict)
    # print("------------------- generate final bug report (end) --------------")

    template = """
    Generate a bug report with the goal of diagnosing the root cause, based on provided stack traces and agent-based analysis of source code methods.

    # Guidelines
    - Use stack traces to extract key details such as error type, location, and involved methods or files.
    - Leverage insights from agent-based analysis to identify root causes, including any interdependent method calls or contributing factors.
    - Clearly describe the issue and provide actionable debugging steps for resolution.
    - Ensure the report is detailed, accurate, and presented in JSON format.

    # Steps
    1. **Parse Stack Traces**:
    - Extract and analyze critical elements like error messages, line numbers, and method calls.
    - Identify the initial point of failure and trace subsequent calls.
    2. **Incorporate Agent-Based Analysis**:
    - Add details about relevant methods, their roles, and dependencies in the source code.
    - Highlight specific methods or lines contributing to the issue.
    3. **Diagnose the Root Cause**:
    - Combine stack trace data and agent insights to deduce the root cause of the error.
    - Provide reasoning that connects observed behavior to the diagnosed issue.
    4. **Construct the Bug Report**:
    - Summarize the issue with a clear title and description.
    - Detail steps to reproduce, expected behavior, observed behavior, and actionable suggestions for resolution.
    5. **Format the Output**:
    - Compile the bug report into a well-structured JSON format.

    # Output Format
    Output the bug report in the following JSON structure:
    ```json
    {{
        "Title": "string",
        "Description": "string",
        "StackTrace": "string or array of stack trace lines",
        "RootCause": "string or null",
        "StepsToReproduce": ["string", "..."] or null,
        "ExpectedBehavior": "string",
        "ObservedBehavior": "string",
        "Suggestions": "string or null"
    }}


    # You are given the stack traces below:
    {stack_trace}



    # You are given the insights derived from agent-based analysis of source code methods below:
    {agent_based_source_code_analysis}

    """

    # template = """
    # Generate a bug report with the goal of diagnosing the root cause, using the provided stack traces, agent-based analysis of source code methods, and the analyzed source code methods themselves.

    # # Guidelines
    # - **Understand the Inputs**:
    # - Analyze the stack traces to extract key error details, such as error type, affected methods, and line numbers.
    # - Utilize insights from the agent-based analysis, including identified methods, lines of code, and their relationships to the error.
    # - Reference the source code methods analyzed to provide additional context and validate findings.
    # - **Focus on Diagnosing the Root Cause**:
    # - Clearly identify the root cause of the issue by synthesizing information from stack traces, agent analysis, and source code.
    # - Describe how the identified code or methods contribute to the error.
    # - **Create a Detailed Bug Report**:
    # - Include actionable details such as error description, affected methods, and steps for resolution.
    # - Maintain a clear and structured JSON format.

    # # Steps
    # 1. **Analyze the Stack Traces**:
    # - Extract relevant details, including error type, error message, file names, and line numbers.
    # - Identify the sequence of method calls leading to the error.
    # 2. **Incorporate Agent-Based Analysis**:
    # - Use the agent’s findings to correlate stack trace information with analyzed methods.
    # - Highlight relationships between methods, dependencies, and any specific issues identified by the agent.
    # 3. **Diagnose the Root Cause**:
    # - Determine the most likely cause of the error based on the combined data.
    # - Provide a concise explanation of the root cause and its context within the codebase.
    # 4. **Format the Bug Report**:
    # - Structure the bug report in a clear JSON format, including key details such as error description, analyzed methods, and suggested resolutions.

    # # Output Format
    # Output the bug report in the following JSON structure:
    # ```json
    # {{
    #     "Title": "string",
    #     "Description": "string",
    #     "StackTrace": "string or array of stack trace lines",
    #     "RootCause": "string or null",
    #     "StepsToReproduce": ["string", "..."] or null,
    #     "ExpectedBehavior": "string",
    #     "ObservedBehavior": "string",
    #     "Suggestions": "string or null"
    # }}


    # # You are given the stack traces below:
    # {stack_trace}



    # # You are given the insights derived from agent-based analysis of source code methods below:
    # {agent_based_source_code_analysis}



    # # You are given the source code methods analyzed by agent-based approach below:
    # {method_cache}

    # """

    
    prompt = PromptTemplate.from_template(template)
    llm = ChatOpenAI(model='gpt-4o-mini', temperature = 0)

    chain = LLMChain(llm=llm, prompt=prompt)
    return chain.run({'stack_trace': stack_trace, 'agent_based_source_code_analysis': agent_based_source_code_analysis})

# Tools for the agent
tools = [
    Tool(name="Parse Stack Trace", func=parse_stack_trace, description="Extract stack traces from the input JSON."),
    Tool(name="Provide Method", func=provide_method, description="Provide the source code for a specific method."),
    Tool(name="Analyze and Request Next", func=analyze_method_and_request_next, description="Analyze the method and request the next one if needed.")
    # Tool(name="Generate Final Bug Report", func=generate_final_bug_report, description="Generate the final bug report using analyzed methods.")
]

# Initialize LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Initialize the agent
agent_executor = initialize_agent(
    tools=tools,
    llm=llm,
    agent="zero-shot-react-description",  
    verbose=True,
)


# Read input and prepare output data
# input_file = "test.json"
# output_file = "test_output.json"
input_file = "source_code_data/Hadoop.json"
output_file = "agentBased_bug_report_from_stackTrace_sourceCode/Hadoop.json"

# Path to source code and Git repository
# repo_path = "/Users/fahim/Desktop/PhD/Projects/zookeeper"
# codebase_dirs = ["/Users/fahim/Desktop/PhD/Projects/zookeeper/src/java/main", "/Users/fahim/Desktop/PhD/Projects/zookeeper/src/java/test"]
# git_branch = "master"

# repo_path = "/Users/fahim/Desktop/PhD/Projects/activemq"
# codebase_dirs = ["/Users/fahim/Desktop/PhD/Projects/activemq/activemq-client/src/main/java", "/Users/fahim/Desktop/PhD/Projects/activemq/activemq-core/src/main/java", "/Users/fahim/Desktop/PhD/Projects/activemq/activemq-broker/src/main/java", "/Users/fahim/Desktop/PhD/Projects/activemq/activemq-karaf/src/main/java", "/Users/fahim/Desktop/PhD/Projects/activemq/activemq-kahadb-store/src/main/java", "/Users/fahim/Desktop/PhD/Projects/activemq/activemq-optional/src/main/java"]
# git_branch = "main"

repo_path = "/Users/fahim/Desktop/PhD/Projects/hadoop"
codebase_dirs = ["/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-common/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-common/src/test/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/src/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/src/test/core", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-common/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-hdfs-project/hadoop-hdfs/src/main/java","/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-tools/hadoop-distcp/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-tools/hadoop-azure/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-nfs/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-auth/src/main/java"]
git_branch = "trunk"

with open(input_file, "r") as file:
    source_code_data = json.load(file)

# Prepare output data
output_data = []

for entry in source_code_data:
    filename = entry['filename']
    creation_time = entry['creation_time']
    stack_trace = entry['stack_trace']
    source_code_dict = entry['source_code']


    # Switch to the appropriate commit
    commit_version = get_commit_version(creation_time, repo_path, git_branch)
    print("Commit Version:", commit_version)
    checkout_to_commit(commit_version, repo_path, git_branch)

    # Cache for storing method definitions
    method_cache = {}

    # Step 1: Parse the stack trace
    current_source_code_dict = {}
    parsed_stack_traces = agent_executor.stream({"input": stack_trace})
    # print("================ parsed_stack_traces (start) ====================")
    # print(f"parsed_stack_traces: {parsed_stack_traces} (type: {type(parsed_stack_traces)})")

    # Ensure parsed_stack_traces is iterable and extract traces
    if isinstance(parsed_stack_traces, dict) or hasattr(parsed_stack_traces, "items"):
        parsed_stack_traces = list(parsed_stack_traces.values())
        print("parsed stack traces list:", parsed_stack_traces)
    # parsed_stack_traces = list(parsed_stack_traces)  # Fully consume the generator
    # print("================ parsed_stack_traces (end) ====================")


    # Step 2: Sequentially request and analyze methods
    analyzed_methods = {}
    for trace in parsed_stack_traces:
        # print("================ trace in parsed_stack_traces (start) ====================")
        # print(f"Trace: {trace}, Type: {type(trace)}, length: {len(trace)}")
        # print(isinstance(trace, AddableDict))
        # print("================ trace in parsed_stack_traces (end) ====================")
        if isinstance(trace, dict) or isinstance(trace, AddableDict):
            if 'output' in trace:
                agent_based_source_code_analysis = trace['output']
                # print("####################################")
                # print("agent_based_source_code_analysis:", agent_based_source_code_analysis)
                # print("####################################")

            
        else:
            print(f"Unexpected trace format: {trace}")
            continue
        


    # Step 3: Generate the final bug report
    try:
        # Manually trigger the final bug report generation
        final_bug_report = generate_final_bug_report(agent_based_source_code_analysis, stack_trace)
        print("####################################")
        print("Final bug report called manually:", final_bug_report)
        # print("method_cache:", method_cache)
        print("####################################")

        # Parse and include the generated bug report
        bug_report = json.loads(final_bug_report.replace("```json\n", "").replace("\n```", ""))

    except Exception as e:
        print(f"Error generating final bug report: {e}")



    # # Parse the bug report JSON from the generated string
    # try:
    #     # Remove any markdown-style code block indicators (` ```json `) if present
    #     bug_report = json.loads(final_bug_report.replace("```json\n", "").replace("\n```", ""))
    # except json.JSONDecodeError:
    #     print(f"Failed to parse JSON for filename: {filename}")
    #     continue  # Skip this entry if JSON parsing fails



    # Add to output data
    output_data.append({
        "filename": filename,
        "creation_time": creation_time,
        "analyzed_methods": method_cache,
        "bug_report": bug_report
    })


# Write output JSON file
with open(output_file, "w") as outfile:
    json.dump(output_data, outfile, indent=4)


print(f"Bug reports have been generated and saved to '{output_file}'")
