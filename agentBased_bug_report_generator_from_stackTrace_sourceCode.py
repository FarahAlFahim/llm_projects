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
import tiktoken


# Get the commit version before a specific timestamp
def get_commit_version(creation_time, repo_path, git_branch):
    command = f'git rev-list -n 1 --before="{creation_time}" {git_branch}'
    result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=repo_path)
    commit_version = result.stdout.strip()
    return commit_version

# Checkout to the specific commit version
def checkout_to_commit(commit_version, repo_path, git_branch):
    # Reset any local changes
    subprocess.run('git reset --hard', shell=True, cwd=repo_path)
    # Ensure a clean stash
    subprocess.run('git stash push --include-untracked', shell=True, cwd=repo_path)
    # Switch back to the main branch before checking out the commit
    subprocess.run(f'git checkout {git_branch}', shell=True, cwd=repo_path)
    # Ensure branch is up-to-date
    subprocess.run('git pull', shell=True, cwd=repo_path)
    # Checkout to the required commit
    subprocess.run(f'git checkout {commit_version}', shell=True, cwd=repo_path)
    # Drop the stash if it's no longer needed
    subprocess.run('git stash drop', shell=True, cwd=repo_path)


# Find method in codebase and return its source code along with class skeleton
def find_method_with_javalang(method_name, codebase_dirs, repo_path):
    global last_accessed_path
    global method_extracted_successfully
    # if method_name in method_cache:
    #     return method_cache[method_name]

    if method_name and method_name[-1] == ".":
        method_name = method_name[:-1]

    if " " in method_name:
        method_name_list = method_name.split(" ")
        found_name = False
        for method in method_name_list:
            if method.count('.') >= 1: # at least 1 dot [might change to at least 2 dots]
                if method.count('.') == 1 and (method[0] == "." or method[-1] == "."):
                    continue
                else:
                    method_name = method.strip()
                    if "(" in method_name:
                        method_name = method_name.split("(")[0].strip()
                    found_name = True
                    break
        if not found_name:
            return "Invalid format. Please request a method using the fully qualified format: {package}.{class}.{method}"
        
    if method_name.endswith("()"):
        method_name = method_name.replace("()", "")

    if method_name.endswith(")"):
        st_index = method_name.find("(")
        method_name = method_name[:st_index]

    if '.' in method_name:
        method_name_only = method_name.split(".")[-1].strip()
        class_method_name = ".".join(method_name.split(".")[-2:])
        class_method_name_only = ".".join(method_name.split(".")[-2:])
        if '$' in class_method_name:
            inner_start_index = class_method_name.find('$')
            dot_index = class_method_name.find('.')
            inner_class_name = class_method_name[inner_start_index:dot_index]
            class_method_name = class_method_name.replace(inner_class_name, "")
            class_method_name_only = class_method_name
    else:
        method_name_only = method_name
        class_method_name = method_name
        class_method_name_only = None
    
    # Check method_cache first
    for method_key, method_body in method_cache.items():
        if method_key.endswith(f".{class_method_name}"):
            class_path = "/".join(method_key.split(".")[:-1]) 
            last_accessed_path = f"{repo_path}/{class_path}.java"
            method_body = f"# You have already accessed this. Please avoid requesting it again. \n\n{method_body}"
            return method_body
        
        
    # Check class_skeleton_cache if it is asking for a class
    for class_key, class_body in class_skeleton_cache.items():
        if class_key.endswith(f".{method_name_only}"):
            class_path = "/".join(class_key.split(".")) 
            last_accessed_path = f"{repo_path}/{class_path}.java"
            # Access full content
            if os.path.exists(last_accessed_path):
                try:
                    with open(last_accessed_path, 'r') as f:
                        content = f.read()
                        method_cache[class_key] = [content]
                        method_extracted_successfully = True
                        return content
                except Exception as e:
                        print(f"Error extracting class content from {last_accessed_path}: {e}")
            
        
    # If not in method_cache, search in source_code_dict
    for method_key, method_body in source_code_dict.items():
        if method_key.lower().endswith(f".{class_method_name}".lower()):
            # Handle if class name is lower case
            parts = method_key.split(".")
            if parts[-2][0].islower():
                parts[-2] = parts[-2][0].upper() + parts[-2][1:]
                method_key = ".".join(parts)

            class_path = "/".join(method_key.split(".")[:-1]) 
            last_accessed_path = repo_path + '/' + class_path + '.java'
            class_full_name = ".".join(method_key.split(".")[:-1])

            class_skeleton = None
            if class_full_name not in class_skeleton_cache:
                if os.path.exists(last_accessed_path):
                    try:
                        with open(last_accessed_path, 'r') as f:
                            content = f.read()
                            tree = javalang.parse.parse(content)
                            class_skeleton = extract_class_skeleton(tree)
                            class_skeleton_cache[class_full_name] = class_skeleton
                    except Exception as e:
                        print(f"Error extracting class skeleton from {last_accessed_path}: {e}")

            if class_skeleton:
                method_cache[method_key] = method_body
                method_body = f"# Class Skeleton: {class_skeleton}\n\n# Requested Method: {method_body}"
            else:
                method_cache[method_key] = method_body
            method_extracted_successfully = True
            return method_body
        
    # If not in method_cache, search in source_code_dict [if {class}.{method} not found, then method_name only]
    for method_key, method_body in source_code_dict.items():
        if method_key.lower().endswith(f".{method_name_only}".lower()):
            # Handle if class name is lower case
            parts = method_key.split(".")
            if parts[-2][0].islower():
                parts[-2] = parts[-2][0].upper() + parts[-2][1:]
                method_key = ".".join(parts)

            class_path = "/".join(method_key.split(".")[:-1]) 
            last_accessed_path = repo_path + '/' + class_path + '.java'
            class_full_name = ".".join(method_key.split(".")[:-1])

            class_skeleton = None
            if class_full_name not in class_skeleton_cache:
                if os.path.exists(last_accessed_path):
                    try:
                        with open(last_accessed_path, 'r') as f:
                            content = f.read()
                            tree = javalang.parse.parse(content)
                            class_skeleton = extract_class_skeleton(tree)
                            class_skeleton_cache[class_full_name] = class_skeleton
                    except Exception as e:
                        print(f"Error extracting class skeleton from {last_accessed_path}: {e}")

            if class_skeleton:
                method_cache[method_key] = method_body
                method_body = f"# Class Skeleton: {class_skeleton}\n\n# Requested Method: {method_body}"
            else:
                method_cache[method_key] = method_body
            method_extracted_successfully = True
            return method_body
        
    
    # If not in source_code_dict, search method in the last_accessed_path
    if method_name_only[0].islower() and last_accessed_path:
        found_method = search_method_in_file(last_accessed_path, method_name_only, repo_path)
        if found_method:
            return found_method
        else:
            # The file path might be wrong, search the correct file path
            if class_method_name_only:
                class_name_only = class_method_name_only.split(".")[0]
                correct_file_path = find_class_file(class_name_only, codebase_dirs)
                if correct_file_path:
                    found_method = search_method_in_file(correct_file_path, method_name_only, repo_path)
                    if found_method:
                        last_accessed_path = correct_file_path
                        return found_method

    
    # If still not found, attempt caller method resolution
    calling_method = resolve_caller_method(method_name_only, last_accessed_path)
    if calling_method and last_accessed_path:
        new_class_name = calling_method.split(".")[0]
        # Replace the old class name in the path with the new one
        dir_path, old_file_name = os.path.split(last_accessed_path)
        new_file_path = os.path.join(dir_path, f"{new_class_name}.java")
        # Search method in the new path
        found_method = search_method_in_file(new_file_path, method_name_only, repo_path)
        if found_method:
            last_accessed_path = new_file_path
            return found_method
        
    # If the requested method name starts with upper case, it requested full class
    if method_name_only[0].isupper():
        if last_accessed_path:
            # Replace the old class name in the path with the new one
            dir_path, old_file_name = os.path.split(last_accessed_path)
            new_file_path = os.path.join(dir_path, f"{method_name_only}.java")
            # Access full content
            if os.path.exists(new_file_path):
                try:
                    with open(new_file_path, 'r') as f:
                        content = f.read()
                        new_class_key = new_file_path.replace(repo_path + '/', '').replace('/', '.')
                        new_class_key = new_class_key[:-5]
                        method_cache[new_class_key] = [content]
                        method_extracted_successfully = True
                        last_accessed_path = new_file_path
                        return content
                except Exception as e:
                        print(f"Error extracting class content from {new_file_path}: {e}")
            else:
                # If the file path is wrong, search for the correct file
                correct_file_path = find_class_file(method_name_only, codebase_dirs)
                if correct_file_path:
                    try:
                        with open(correct_file_path, 'r') as f:
                            content = f.read()
                            correct_class_key = correct_file_path.replace(repo_path + '/', '').replace('/', '.')
                            correct_class_key = correct_class_key[:-5]
                            method_cache[correct_class_key] = [content]
                            method_extracted_successfully = True
                            last_accessed_path = correct_file_path
                            return content
                    except Exception as e:
                        print(f"Error extracting class content from {correct_file_path}: {e}")
                else:
                    print(f"Class file {method_name_only}.java not found in the codebase.")


    method_cache[method_name] = "[Method not found in codebase]"
    return "[Method not found in codebase]"


def find_class_file(class_name, codebase_dirs):
    """
    Searches for a Java file with the given class name inside the provided codebase directories.
    
    :param class_name: The class name to search for (e.g., "QuorumVerifier").
    :param codebase_dirs: List of directories to search in.
    :return: Full path of the file if found, else None.
    """
    for base_dir in codebase_dirs:
        for root, _, files in os.walk(base_dir):
            for file in files:
                if file == f"{class_name}.java":
                    return os.path.join(root, file)
    return None  # File not found


# Search for a method inside a Java file
def search_method_in_file(file_path, method_name, repo_path):
    global method_extracted_successfully
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            tree = javalang.parse.parse(content)
            class_name = file_path.replace(repo_path + '/', '').replace('/', '.')
            class_name = class_name[:-5]
            
            class_skeleton = None
            # Store class skeleton if not cached
            if class_name not in class_skeleton_cache:
                class_skeleton = extract_class_skeleton(tree)
                class_skeleton_cache[class_name] = class_skeleton
            
            for _, method in tree.filter(javalang.tree.MethodDeclaration):
                if method.name == method_name:
                    found_method = extract_method_code(content, method.position)
                    
                    # Cache the method
                    method_key = f"{class_name}.{method_name}"
                    if class_skeleton:
                        method_cache[method_key] = found_method
                        found_method = f"# Class Skeleton: {class_skeleton}\n\n# Requested Method: {found_method}"
                    else:
                        method_cache[method_key] = found_method
                    method_extracted_successfully = True
                    return found_method
    except Exception as e:
        print(f"Error parsing file {file_path}: {e}")
    return None


# Resolve the caller method for a given method
def resolve_caller_method(method_name, file_path):
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            tree = javalang.parse.parse(content)

            for _, call in tree.filter(javalang.tree.MethodInvocation):
                if call.member == method_name:
                    if call.qualifier:
                        if call.qualifier[0].isupper():  # Ensure it's a class name
                            return f"{call.qualifier}.{method_name}"
                        elif call.qualifier[0].islower():  # It's likely an object, resolve its class type
                            class_type = resolve_variable_type_with_javalang(call.qualifier, tree)
                            if class_type:
                                return f"{class_type}.{method_name}"

    except Exception as e:
        print(f"Error resolving caller method in {file_path}: {e}")
    return None


def resolve_variable_type_with_javalang(variable_name, tree):
    """
    Resolves the class type of a given variable by analyzing the AST with javalang.
    """
    for path, local_var in tree.filter(javalang.tree.LocalVariableDeclaration):
        for declarator in local_var.declarators:
            if declarator.name == variable_name:
                if hasattr(local_var.type, 'name'):
                    return local_var.type.name
    return None



# Extract class skeleton
def extract_class_skeleton(tree):
    skeleton = []
    for _, node in tree.filter(javalang.tree.ClassDeclaration):
        skeleton.append(f"class {node.name} {{")
        for method in node.methods:
            params = ', '.join([p.type.name + ' ' + p.name for p in method.parameters])
            skeleton.append(f"    {method.return_type.name if method.return_type else 'void'} {method.name}({params});")
        skeleton.append("}")
    return '\n'.join(skeleton)

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
    method_code = find_method_with_javalang(full_identifier, codebase_dirs, repo_path)
    print("------- provide_method (start) ----------")
    print(f"Method '{full_identifier}' provided.")
    # print(method_code)
    print("------- provide_method (end) ----------")
    return method_code




def count_tokens(text, model="gpt-4o-mini"):
    encoder = tiktoken.encoding_for_model(model)
    return len(encoder.encode(text))

# This model's maximum context length is 128000 tokens
def split_into_chunks(text, max_tokens=100000, model="gpt-4o-mini"):
    encoder = tiktoken.encoding_for_model(model)
    tokens = encoder.encode(text)
    
    chunks = []
    for i in range(0, len(tokens), max_tokens):
        chunk_tokens = tokens[i:i+max_tokens]
        chunk_text = encoder.decode(chunk_tokens)
        chunks.append(chunk_text)
    
    return chunks


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
    method_body = find_method_with_javalang(input_data, codebase_dirs, repo_path)
    
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

    # Handle Max Token limit exceed cases
    # Format the full prompt
    full_prompt = template.format(
        stack_trace=stack_trace, 
        chat_history=chat_history, 
        input_data=input_data, 
        method_body=method_body
    )

    # Check token count
    token_count = count_tokens(full_prompt)

    if token_count > 100000:
        print(f"Token count ({token_count}) exceeds limit! Splitting into chunks...")
        prompt_chunks = split_into_chunks(full_prompt, max_tokens=100000)

        responses = []
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

        for chunk in prompt_chunks:
            response = llm.invoke(chunk)
            responses.append(response)

        return "\n".join(responses)
    else:
        # Run normally when within token limit
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







def generate_final_bug_report(method_cache, stack_trace):
    """Generate the final bug report based on analyzed methods."""
    # print("------------------- generate final bug report (start) --------------")
    # print("stack_trace:", stack_trace)
    # print("analyzed method:", agent_based_source_code_analysis)
    # print("current_source_code_dict:", current_source_code_dict)
    # print("------------------- generate final bug report (end) --------------")

    template = '''
    Generate a bug report with the goal of diagnosing the root cause.

    You are a professional assistant analyzing stack traces. You will be provided with three key input data sources:
    1. **Raw Stack Traces**: These contain error messages and exceptions.
    2. **Agent-Based Chat History**: Logs of source code method analysis, showing methods requested by the agent and its reasoning.
    3. **Source Code Methods Analyzed by the Agent**: Methods referenced in the stack traces or their dependent methods.

    ## Steps

    1. **Analyze the Stack Trace**:  
    - Identify key error messages and exceptions.  
    - Determine which methods or classes are involved.  

    2. **Correlate with Agent-Based Chat History**:  
    - Extract the agent’s reasoning behind method requests.  
    - Identify patterns in how the agent analyzed methods.  

    3. **Examine the Source Code Methods**:  
    - Review the actual implementations of the methods mentioned in the stack trace and chat history.  
    - Look for logical errors, incorrect dependencies, or improper exception handling.  
    - Trace the flow of execution using method dependencies.  

    4. **Determine the Root Cause**:  
    - Identify the primary source of the bug based on stack trace information and source code examination.  
    - Avoid assumptions—base your findings solely on provided data.  

    5. **Generate a Bug Report**:  
    - Populate each field in the bug report using your analysis:  
        - **Title**: Concise description of the bug.  
        - **Description**: Summary of findings.  
        - **Root Cause**: Clear explanation of what is causing the issue.  
        - **Steps to Reproduce**: How the issue can be replicated.  
        - **Expected Behavior**: What should happen instead.  
        - **Observed Behavior**: The actual incorrect behavior.  
        - **Suggestions**: Possible directions for fixing the issue.  
        - **Problem Location**: Specific file/class/method responsible for the issue.  
        - **Possible Fix**: If a solution is evident, provide a suggestion.  

    ## Output Format

    Provide the bug report in **JSON format** with the following structure:

    ```json
    {{
        "Title": "<Bug Title>",
        "Description": "<Detailed Description based on analysis>",
        "StackTrace": "string or array of stack trace lines",
        "RootCause": "<Explanation of the root cause>",
        "StepsToReproduce": ["<Step-by-step reproduction guide>"] or null,
        "ExpectedBehavior": "<Correct system behavior>",
        "ObservedBehavior": "<Actual faulty behavior>",
        "Suggestions": "<Possible fixes or mitigation steps>",
        "problem_location": {{
            "files": ["file1.java", "file2.java"],
            "classes": ["com.example.ClassA", "com.example.ClassB"],
            "methods": ["ClassA.methodX", "ClassB.methodY"]
        }},
        "possible_fix": "[Proposed code fix or strategy]"
    }}


    ### **Notes**  
    - Do **not** hallucinate information—only use provided data.
    - Follow a **structured reasoning approach** before reaching conclusions.
    - Ensure all fields are **accurate and complete** based on available inputs.
    - Maintain **clarity and conciseness** in all explanations.




    # You are given the **Raw Stack Traces** below:

    {stack_trace}



    # You are given the **Agent-Based Chat History** below:

    {chat_history}



    # You are given the **Source Code Methods Analyzed by the Agent** below:

    {analyzed_methods}
    '''


    
    prompt = PromptTemplate.from_template(template)
    llm = ChatOpenAI(model='gpt-4o-mini', temperature = 0)

    chain = LLMChain(llm=llm, prompt=prompt)
    if method_extracted_successfully:
        return chain.run({'stack_trace': stack_trace, 'chat_history': chat_history, 'analyzed_methods': method_cache})
    else:
        return chain.run({'stack_trace': stack_trace, 'chat_history': chat_history, 'analyzed_methods': source_code_dict})

# Tools for the agent
tools = [
    # Tool(name="Parse Stack Trace", func=parse_stack_trace, description="Extract stack traces from the input JSON."),
    Tool(name="Provide Method", func=provide_method, description="Use this to request specific methods from the source code."),
    Tool(name="Analyze and Request Next", func=analyze_method_and_request_next, description="Use this to analyze the provided method and determine if more methods are needed.")
    # Tool(name="Generate Final Bug Report", func=generate_final_bug_report, description="Generate the final bug report using analyzed methods.")
]

# Initialize LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


# System Prompt for two tools
system_prompt = """
You are an intelligent assistant specialized in analyzing stack traces and source code to diagnose the root cause of issues. 
Your goal is to iteratively analyze methods, extract insights, and ensure efficient debugging by avoiding redundant method requests.

# Guidelines
- **Tools Available**:
  - `provide_method`: Retrieves methods from the source code based on the call dependency of stack traces.
  - `analyze_method_and_request_next`: Analyzes a method and requests additional methods from the call dependency if needed.
- **Tracking Requested Methods**:
  - Keep track of all previously requested methods.
  - **Do not request a method again if it has already been retrieved and analyzed**.
  - If additional analysis is needed, refer to previous findings instead of making redundant requests.
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
input_file = "test.json"
output_file = "test_output.json"
# input_file = "source_code_data/method_list/Hive.json"
# output_file = "agentBased_bug_report_from_stackTrace_sourceCode/Hive.json"

# Path to source code and Git repository
# For Zookeeper.json
# repo_path = "/Users/fahim/Desktop/PhD/Projects/zookeeper"
# codebase_dirs = ['/Users/fahim/Desktop/PhD/Projects/zookeeper/src/java/main']
# git_branch = "master"

# For ActiveMQ.json
# repo_path = "/Users/fahim/Desktop/PhD/Projects/activemq"
# codebase_dirs = ['/Users/fahim/Desktop/PhD/Projects/activemq/activemq-broker/src/main/java', '/Users/fahim/Desktop/PhD/Projects/activemq/activemq-client/src/main/java', '/Users/fahim/Desktop/PhD/Projects/activemq/activemq-core/src/main/java', '/Users/fahim/Desktop/PhD/Projects/activemq/activemq-jdbc-store/src/main/java', '/Users/fahim/Desktop/PhD/Projects/activemq/activemq-kahadb-store/src/main/java', '/Users/fahim/Desktop/PhD/Projects/activemq/activemq-karaf/src/main/java', '/Users/fahim/Desktop/PhD/Projects/activemq/activemq-optional/src/main/java', '/Users/fahim/Desktop/PhD/Projects/activemq/kahadb/src/main/java']
# git_branch = "main"

# For Hadoop.json
# repo_path = "/Users/fahim/Desktop/PhD/Projects/hadoop"
# codebase_dirs = ['/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-auth/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-common/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-kms/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-nfs/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-hdfs-project/hadoop-hdfs/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-mapreduce-project/hadoop-mapreduce-client/hadoop-mapreduce-client-app/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-mapreduce-project/hadoop-mapreduce-client/hadoop-mapreduce-client-core/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-tools/hadoop-aws/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-tools/hadoop-azure/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-tools/hadoop-distcp/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-server/hadoop-yarn-server-nodemanager/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/src/java']
# git_branch = "trunk"

# For HDFS.json
# repo_path = "/Users/fahim/Desktop/PhD/Projects/hadoop"
# codebase_dirs = ['/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-common/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-nfs/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-hdfs-project/hadoop-hdfs-client/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-hdfs-project/hadoop-hdfs-nfs/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-hdfs-project/hadoop-hdfs/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hdfs/src/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/src/core', '/Users/fahim/Desktop/PhD/Projects/hadoop/src/hdfs']
# git_branch = "trunk"

# For Storm.json
# repo_path = "/Users/fahim/Desktop/PhD/Projects/storm"
# codebase_dirs = ['/Users/fahim/Desktop/PhD/Projects/storm/examples/storm-loadgen/src/main/java', '/Users/fahim/Desktop/PhD/Projects/storm/external/storm-hdfs-blobstore/src/main/java', '/Users/fahim/Desktop/PhD/Projects/storm/external/storm-hdfs/src/main/java', '/Users/fahim/Desktop/PhD/Projects/storm/external/storm-kafka-client/src/main/java', '/Users/fahim/Desktop/PhD/Projects/storm/storm-client/src/jvm', '/Users/fahim/Desktop/PhD/Projects/storm/storm-core/src/jvm', '/Users/fahim/Desktop/PhD/Projects/storm/storm-server/src/main/java', '/Users/fahim/Desktop/PhD/Projects/storm/storm-webapp/src/main/java']
# git_branch = "master"

# For MAPREDUCE.json
# repo_path = "/Users/fahim/Desktop/PhD/Projects/hadoop"
# codebase_dirs = ['/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-common/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-mapreduce-project/hadoop-mapreduce-client/hadoop-mapreduce-client-app/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-mapreduce-project/hadoop-mapreduce-client/hadoop-mapreduce-client-common/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-mapreduce-project/hadoop-mapreduce-client/hadoop-mapreduce-client-core/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-mapreduce-project/hadoop-mapreduce-client/hadoop-mapreduce-client-hs/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-mapreduce-project/hadoop-mapreduce-client/hadoop-mapreduce-client-jobclient/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-mapreduce-project/hadoop-yarn/hadoop-yarn-api/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-mapreduce-project/hadoop-yarn/hadoop-yarn-common/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-mapreduce-project/hadoop-yarn/hadoop-yarn-server/hadoop-yarn-server-nodemanager/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-mapreduce-project/hadoop-yarn/hadoop-yarn-server/hadoop-yarn-server-resourcemanager/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-mapreduce-project/hadoop-yarn/hadoop-yarn-server/hadoop-yarn-server-web-proxy/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-mapreduce-project/src/contrib/gridmix/src/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-mapreduce-project/src/tools', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-tools/hadoop-streaming/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/mapreduce/src/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/src/contrib/fairscheduler/src/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/src/core', '/Users/fahim/Desktop/PhD/Projects/hadoop/src/examples', '/Users/fahim/Desktop/PhD/Projects/hadoop/src/mapred']
# git_branch = "trunk"

# For YARN.json
# repo_path = "/Users/fahim/Desktop/PhD/Projects/hadoop"
# codebase_dirs = ['/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-common/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-mapreduce-project/hadoop-mapreduce-client/hadoop-mapreduce-client-app/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-tools/hadoop-sls/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-api/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-applications/hadoop-yarn-applications-distributedshell/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-applications/hadoop-yarn-applications-unmanaged-am-launcher/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-applications/hadoop-yarn-services/hadoop-yarn-services-core/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-client/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-common/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-registry/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-server/hadoop-yarn-server-applicationhistoryservice/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-server/hadoop-yarn-server-common/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-server/hadoop-yarn-server-nodemanager/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-server/hadoop-yarn-server-resourcemanager/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-server/hadoop-yarn-server-timelineservice/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-server/hadoop-yarn-server-web-proxy/src/main/java']
# git_branch = "trunk"

# For Hive.json
repo_path = "/Users/fahim/Desktop/PhD/Projects/hive"
codebase_dirs = ['/Users/fahim/Desktop/PhD/Projects/hive/common/src/java', '/Users/fahim/Desktop/PhD/Projects/hive/hbase-handler/src/java', '/Users/fahim/Desktop/PhD/Projects/hive/hcatalog/core/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hive/hcatalog/server-extensions/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hive/hcatalog/webhcat/svr/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hive/metastore/src/java', '/Users/fahim/Desktop/PhD/Projects/hive/orc/src/java', '/Users/fahim/Desktop/PhD/Projects/hive/ql/src/java', '/Users/fahim/Desktop/PhD/Projects/hive/serde/src/java', '/Users/fahim/Desktop/PhD/Projects/hive/service/src/java', '/Users/fahim/Desktop/PhD/Projects/hive/shims/0/20S/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hive/shims/0/23/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hive/shims/common/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hive/shims/src/0/20/java', '/Users/fahim/Desktop/PhD/Projects/hive/shims/src/common-secure/java', '/Users/fahim/Desktop/PhD/Projects/hive/spark-client/src/main/java', '/Users/fahim/Desktop/PhD/Projects/hive/standalone-metastore/src/main/java']
git_branch = "master"

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
    class_skeleton_cache = {}
    last_accessed_path = None
    method_extracted_successfully = False # True if method requested by agent can be extracted


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
        final_bug_report = generate_final_bug_report(method_cache, stack_trace)
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
        "class_skeleton_cache": class_skeleton_cache,
        "chat_history": chat_history,
        "method_extracted_successfully": method_extracted_successfully,
        "bug_report": bug_report
    })

    # Write to output file after each bug report
    with open(output_file, "w") as outfile:
        json.dump(output_data, outfile, indent=4)
    print(f"Progress saved to {output_file}")


# # Write output JSON file
# with open(output_file, "w") as outfile:
#     json.dump(output_data, outfile, indent=4)


print(f"Bug reports have been generated and saved to '{output_file}'")
