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
    # template = """
    # Generate an enhanced or improved bug report by analyzing the provided bug report and incorporating insights derived from agent-based analysis of source code methods.

    # # Guidelines
    # - Use the provided bug report as the starting point and enrich it with additional details based on the agent-based analysis of source code methods.
    # - Ensure all aspects of the bug report are clear, actionable, and detailed, improving upon the original content where possible.
    # - Structure the final bug report to include all relevant fields, such as method-level insights, root cause analysis, and suggested resolutions.

    # # Steps
    # 1. **Analyze the Provided Bug Report**:
    # - Review the given bug report for existing information such as the title, description, and stack trace.
    # - Identify any gaps or areas that require further details or clarification.
    # 2. **Incorporate Agent-Based Analysis**:
    # - Use insights from the agent-based analysis of source code methods to add context to the bug report.
    # - Highlight any key methods or lines of code contributing to the issue.
    # - Summarize relevant inner method calls or dependencies that were analyzed.
    # 3. **Enhance Bug Report**:
    # - Refine the title, description, and any technical details for clarity and precision.
    # - Provide actionable insights, root cause analysis, and suggestions for resolution.
    # - Include a detailed account of all analyzed methods, with references to their source files and line numbers where applicable.
    # 4. **Generate JSON Output**:
    # - Compile the enhanced bug report into a structured JSON format for consistency and ease of use.

    # # Output Format
    # Output the enhanced bug report in the following JSON structure:
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


    # # You are given the bug report below:
    # {bug_report}



    # # You are given the insights derived from agent-based analysis of source code methods below:
    # {agent_based_source_code_analysis}


    
    # # You are given the source code methods analyzed by agent-based approach below:
    # {method_cache}
    # """

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

    # template = """
    # Generate or enhance a bug report with the goal of diagnosing the root cause, using the provided bug report, agent-based analysis of source code methods, and the analyzed source code methods themselves.

    # # Guidelines
    # - **Understand the Inputs**:
    # - Analyze the existing bug report for key details such as error descriptions, stack traces, and other relevant information.
    # - Utilize insights from the agent-based system analysis, including identified methods, lines of code, and any highlighted issues.
    # - Cross-reference the analyzed source code methods to provide context and validate findings.
    # - **Focus on the Root Cause**:
    # - Identify and describe the root cause based on the combined analysis of the bug report, agent insights, and source code methods.
    # - Ensure the root cause is clearly explained and linked to the identified methods or lines of code.
    # - **Enhance the Bug Report**:
    # - Update the bug report with missing details, actionable insights, and resolution steps.
    # - Maintain a clear, logical structure for better readability and utility.
    # - **Ensure JSON Output**:
    # - Structure the output as a JSON object for clarity and consistency.

    # # Steps
    # 1. **Analyze the Bug Report**:
    # - Extract key components, including the error type, message, stack trace, and any provided details on affected components.
    # - Identify any gaps or ambiguities in the report.
    # 2. **Incorporate Agent-Based Analysis**:
    # - Use the agent's findings to pinpoint specific methods or code sections related to the bug.
    # - Highlight dependencies, relationships, or contextual insights that support root cause identification.
    # 3. **Diagnose the Root Cause**:
    # - Synthesize the extracted information to determine the root cause of the bug.
    # - Clearly articulate how the identified methods or code areas contribute to the issue.
    # 4. **Enhance the Bug Report**:
    # - Add actionable details, such as steps to reproduce, expected vs. observed behavior, and suggestions for resolution.
    # - Include relevant insights from the agent-based analysis.
    # 5. **Format as JSON**:
    # - Ensure the output is a well-structured JSON object, adhering to the specified format.

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


    # # You are given the bug report below:
    # {bug_report}



    # # You are given the insights derived from agent-based analysis of source code methods below:
    # {agent_based_source_code_analysis}

    

    # # You are given the analyzed source code methods below:
    # {method_cache}

    # """

    prompt = PromptTemplate.from_template(template)
    llm = ChatOpenAI(model='gpt-4o-mini', temperature = 0)

    chain = LLMChain(llm=llm, prompt=prompt)
    return chain.run({'bug_report': dev_written_bug_report, 'agent_based_source_code_analysis': agent_based_source_code_analysis})

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
output_file = "agentBased_bug_report_from_bugReport_sourceCode/Hadoop.json"

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
        "bug_report": bug_report
    })


# Write output JSON file
with open(output_file, "w") as outfile:
    json.dump(output_data, outfile, indent=4)


print(f"Bug reports have been generated and saved to '{output_file}'")
