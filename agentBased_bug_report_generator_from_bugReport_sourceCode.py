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
    # Handle extra information
    if " " in full_identifier:
      if full_identifier.split(" ")[0].count('.') > 2:
        full_identifier = full_identifier.split(" ")[0].strip()

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
        print(f"full_identifier: #######{full_identifier}#########")
        print("File Path:", file_path)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
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
        else:
            # Search full class
            prev_class_name = class_name.split(".")[0].strip()
            new_class_name = method_name.strip() + ".java"
            file_path = os.path.join(dir_path, class_dir, prev_class_name, new_class_name)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        # full_identifier = full_identifier + "(source code of the class)"
                        method_cache[full_identifier] = [content]
                        return content
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
    
    if "Invalid format" in method_body or "[Method not found in codebase]" in method_body:
        return method_body
    # print(method_body)
    # print("------- analyze_method_and_request_next (end) ----------")
    
    # Construct the LLM prompt
    # template = """
    # You are analyzing a method from the call dependency of stack traces of bug report with the goal of diagnosing the root cause. 


    # # You are given the stack traces of the bug report below:
    # {stack_trace}


    # # You are given the agent based chat history below:
    # {chat_history}
    
    
    
    # # You are given the current method below to analyze with the goal of diagnosing the root cause:
    # Method: {input_data}
    # Source Code:
    # {method_body}

    
    # If this method calls any other methods not in the stack trace, identify one such method and return its name.
    # Always request method names in the fully qualified format: 
    # {{package}}.{{class}}.{{method}}

    # If no further methods are needed, respond with observations so far based on analyzed methods.
    # """

    template = """
    Analyze the source code of a method from the call dependency of stack traces and request the next methods that are reachable from the call dependency or provide observations based on the analysis.

    # Guidelines
    - **Understand the Input**:
    - Inputs include:
        - Source code of a method from the call dependency of the stack trace.
        - Stack trace data.
        - Chat history from the agent-based system.
    - Use these inputs to analyze the current method, trace dependencies, and identify further methods to analyze.
    - **Analyze the Method**:
    - Examine the source code to determine its role in the stack trace.
    - Identify its dependencies and analyze its contribution to the issue.
    - **Request Next Methods**:
    - Based on the current method’s call dependency, request the next methods to analyze in fully qualified format: `{{package}}.{{class}}.{{method}}`.
    - If no further methods are required, summarize the observations from the analyzed methods and provide a diagnosis of the root cause.
    - **Clarity and Relevance**:
    - Focus on the relevant parts of the method and dependencies.
    - Avoid unnecessary details or irrelevant method requests.

    # Steps
    1. **Input Analysis**:
    - Parse the stack trace, source code, and chat history for relevant details.
    - Identify the context of the current method in the call dependency.
    2. **Method Analysis**:
    - Analyze the current method for its role and potential issues contributing to the root cause.
    3. **Request Next Methods**:
    - Determine the next methods reachable from the call dependency.
    - Request fully qualified method names if further analysis is required.
    4. **Summarize Observations**:
    - If no additional methods are needed, summarize observations so far based on the analyzed methods.
    - Provide reasoning and diagnosis of the root cause.

    # Output Format
    Output should either be a request for the next method in the call dependency or a summary of observations, formatted as follows:
    1. **Method Request**:
    {{package}}.{{class}}.{{method}}

    2. **Observations Summary**:
    Observations: "Summary of findings and insights based on analyzed methods."



    # You are given the stack traces of the bug report below:
    {stack_trace}


    # You are given the agent based chat history below:
    {chat_history}
    
    
    
    # You are given the current method below to analyze with the goal of diagnosing the root cause:
    Method: {input_data}
    Source Code:
    {method_body}

    """

    
    prompt = PromptTemplate.from_template(template)
    
    # Configure the LLM
    llm = ChatOpenAI(model='gpt-4o-mini', temperature=0)
    chain = LLMChain(llm=llm, prompt=prompt)

    try:
        # Run the LLM chain
        response = chain.run({'stack_trace': stack_trace, 'chat_history': chat_history, 'input_data': input_data, 'method_body': method_body})
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
    Generate or enhance a bug report with the goal of diagnosing the root cause, based on the provided bug report and agent-based analysis of source code methods.

    # Guidelines
    - Use the existing bug report to extract key information such as error type, description, and affected methods.
    - Incorporate insights from the agent-based analysis of the source code to pinpoint the methods or lines responsible for the issue.
    - Ensure that the bug report clearly states the root cause and provides steps for resolution.
    - The output should be in JSON format, structured for clarity and comprehensiveness.

    # Steps
    1. **Analyze Existing Bug Report**:
    - Extract key details from the provided bug report, including the error message, stack trace, and affected components.
    - Review the provided information for accuracy and completeness.
    2. **Incorporate Agent-Based Insights**:
    - Add any insights from the agent-based analysis that identify relevant methods or code areas contributing to the bug.
    - Describe how these insights connect to the error in the report.
    3. **Diagnose the Root Cause**:
    - Use the bug report and analysis to deduce the root cause of the issue.
    - Focus on the interaction between methods, their parameters, and their dependencies.
    4. **Enhance the Bug Report**:
    - Update the bug report with additional details that help in diagnosing the root cause.
    - Ensure that the report includes clear, actionable steps for reproduction, expected behavior, observed behavior, and possible resolutions.
    5. **Format the Output**:
    - Ensure the final bug report is presented in a well-structured JSON format.

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


    # You are given the bug report below:
    {bug_report}



    # You are given the insights derived from agent-based analysis of source code methods below:
    {agent_based_source_code_analysis}

    """

    

    prompt = PromptTemplate.from_template(template)
    llm = ChatOpenAI(model='gpt-4o-mini', temperature = 0)

    chain = LLMChain(llm=llm, prompt=prompt)
    return chain.run({'bug_report': dev_written_bug_report, 'agent_based_source_code_analysis': agent_based_source_code_analysis})

# Tools for the agent
tools = [
    # Tool(name="Parse Stack Trace", func=parse_stack_trace, description="Extract stack traces from the input JSON."),
    Tool(name="Provide Method", func=provide_method, description="Use this to request specific methods from the source code."),
    Tool(name="Analyze and Request Next", func=analyze_method_and_request_next, description="Use this to analyze the provided method and determine if more methods are needed.")
    # Tool(name="Generate Final Bug Report", func=generate_final_bug_report, description="Generate the final bug report using analyzed methods.")
]

# Initialize LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Define the system prompt
# system_prompt = """
# You are an intelligent assistant specialized in analyzing stack traces and source code to generate improved bug reports. You have access to three tools:

# 1. **parse_stack_trace**: Use this tool to parse and extract information from stack traces.
# 2. **provide_method**: Use this tool to request specific methods from the source code based on the stack trace or other analysis.
# 3. **analyze_method_and_request_next**: Use this tool to analyze a provided method. If further methods are needed, explicitly request them using this tool.

# ### Instructions
# Always follow this workflow:

# 1. **Parsing**: Start by invoking `parse_stack_trace` if stack trace analysis is needed.
# 2. **Method Requests**:
#    - Use the `provide_method` tool to obtain a specific method from the source code.
#    - Once a method is provided, **immediately pass it to the `analyze_method_and_request_next` tool** for analysis.
# 3. **Analysis and Alternation**:
#    - After analyzing the method with `analyze_method_and_request_next`, determine if additional methods are needed:
#      - If more methods are required, return to step 2 and invoke `provide_method` again.
#      - If no further methods are needed, complete the analysis and provide a conclusion.
# 4. **No Consecutive Usage**: Do not invoke `provide_method` consecutively without analyzing the last provided method. Similarly, do not repeatedly invoke `analyze_method_and_request_next` without requesting the next method if more analysis is required.

# ### Key Behaviors
# - Alternate between `provide_method` and `analyze_method_and_request_next` until the analysis is complete.
# - Use logical reasoning to decide when to conclude the process, ensuring all necessary methods have been analyzed.
# - Strictly adhere to the workflow to ensure a systematic and efficient analysis process.

# """

# System Prompt for two tools
system_prompt = """
Analyze stack traces using an agent-based system and iteratively request and analyze methods from the source code until a clear diagnosis of the root cause is achieved.

# Guidelines
- **Tools Available**:
  - `provide_method`: Retrieves methods from the source code based on the call dependency of stack traces.
  - `analyze_method_and_request_next`: Analyzes a method and requests additional methods from the call dependency if needed.
- **Iterative Process**:
  1. Start by analyzing the stack traces to identify the first method to request.
  2. Use `provide_method` to obtain the required method in fully qualified format (`{{package}}.{{class}}.{{method}}`).
  3. Analyze the retrieved method using `analyze_method_and_request_next`.
  4. Based on the analysis, request additional methods from the call dependency if needed.
  5. Repeat this process until enough information is gathered to diagnose the root cause.
- **Focus on the Root Cause**:
  - While analyzing methods, look for patterns, errors, or interactions contributing to the issue.
  - Ensure all relevant methods in the call dependency are considered before concluding.
- **Output Requirements**:
  - Provide a detailed and structured analysis summarizing the diagnostic process.
  - Include the reasoning for requesting each method and how it contributed to identifying the root cause.

# Steps
1. **Initial Analysis**:
   - Parse the stack traces to identify the initial method for analysis.
   - Request this method using the `provide_method` tool.
2. **Iterative Analysis**:
   - For each method:
     - Use `analyze_method_and_request_next` to examine its role in the stack trace.
     - Request additional methods from the call dependency if necessary.
   - Repeat until no further methods are required or the root cause is identified.
3. **Final Diagnosis**:
   - Summarize the analysis process, including key observations and conclusions.
   - Provide a clear explanation of the root cause, supported by evidence from the analyzed methods.

# Output Format
- A detailed analysis should include:
  1. A summary of the stack trace and initial method.
  2. The methods requested and analyzed, including their fully qualified names.
  3. Key observations and reasoning at each step.
  4. A conclusive diagnosis of the root cause.

"""

# Initialize the agent
agent_executor = initialize_agent(
    tools=tools,
    llm=llm,
    agent="zero-shot-react-description",  
    verbose=True,
    system_prompt=system_prompt
)


# Read input and prepare output data
# input_file = "test.json"
output_file = "test_output.json"
input_file = "source_code_data/Hadoop.json"
# output_file = "agentBased_bug_report_from_bugReport_sourceCode/ActiveMQ.json"

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
    bug_report = entry['bug_report']
    stack_trace = entry['stack_trace']
    source_code_dict = entry['source_code']


    # Switch to the appropriate commit
    commit_version = get_commit_version(creation_time, repo_path, git_branch)
    print("Commit Version:", commit_version)
    checkout_to_commit(commit_version, repo_path, git_branch)

    # Cache for storing method definitions
    method_cache = {}

    # Initialize an empty history object
    chat_history = []

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
                
            if 'messages' in trace and ('output' in trace or 'actions' in trace):
                agent_based_chat = trace['messages'][0].content
                chat_history.append(agent_based_chat)
                # print("chat_history length:", len(chat_history))
                # print("chat_history:", chat_history)
                # print("####################################")
            
        else:
            print(f"Unexpected trace format: {trace}")
            continue
        


    # Step 3: Generate the final bug report
    try:
        # Manually trigger the final bug report generation
        final_bug_report = generate_final_bug_report(agent_based_source_code_analysis, bug_report)
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
        "chat_history": chat_history,
        "bug_report": bug_report
    })


# Write output JSON file
with open(output_file, "w") as outfile:
    json.dump(output_data, outfile, indent=4)


print(f"Bug reports have been generated and saved to '{output_file}'")
