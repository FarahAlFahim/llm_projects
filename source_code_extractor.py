import os
import re
import json
import subprocess
from collections import defaultdict


# Step 1: Read Stack Traces from JSON
def read_stack_traces(json_file):
    with open(json_file, "r") as file:
        return json.load(file)


# Step 2: Get the commit version before a specific timestamp
def get_commit_version(creation_time, repo_path, git_branch):
    command = f'git rev-list -n 1 --before="{creation_time}" {git_branch}'
    result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=repo_path)
    commit_version = result.stdout.strip()
    return commit_version


# Step 3: Checkout to the specific commit version
def checkout_to_commit(commit_version, repo_path, git_branch):
    # Ensure working directory is clean (optional)
    subprocess.run('git stash --include-untracked', shell=True, cwd=repo_path)
    reset_command = f'git checkout {git_branch}'
    subprocess.run(reset_command, shell=True, cwd=repo_path)
    checkout_command = f'git checkout {commit_version}'
    subprocess.run(checkout_command, shell=True, cwd=repo_path)
    


# Step 4: Extract methods from Java source code 
def extract_methods_from_file(file_path):
    methods = {}
    try:
        with open(file_path, 'r') as file:
            content = file.read()

        # Regex to extract the method signature
        method_pattern = re.compile(
            # r'(public|private|protected)?\s+\w+\s+(\w+)\(([^)]*)\)\s*(throws\s+\w+(\s*,\s*\w+)*)?\s*\{'
            # r'(public|private|protected)?\s+(static|final|synchronized|abstract)?\s*\w+(\s*<[\w\s,?]+>)?\s+([a-zA-Z_]\w*)\s*\((.*?)\)\s*(throws\s+\w+(\s*,\s*\w+)*)?\s*\{'
            r'(public|private|protected)?\s+(static|final|synchronized|abstract)?\s*\w+(\s*<[\w\s,?]+>)?\s+([a-zA-Z_]\w*)\s*\(([^)]*)\)\s*(throws\s+\w+(\s*,\s*\w+)*)?\s*\{'

        )
        matches = method_pattern.finditer(content)
        for match in matches:
            print("---------------------match------------------------")
            print(match)
            print("---------------------match------------------------")
            method_name = match.group(4)  # Extract the method name
            parameter_list = match.group(5)  # Extract the parameter list

            java_keywords = {"if", "else", "for", "while", "switch", "case", "try", "catch", "finally", "return", "break", "continue", "throw", "throws", "assert", "default", "synchronized"}
            if method_name in java_keywords:
                continue  # Skip if it's a keyword

            method_key = f"{method_name}({parameter_list})"  # Combine name and parameters
            method_start = match.start()
            brace_count = 0
            method_body = []
            for i, line in enumerate(content[method_start:].splitlines()):
                brace_count += line.count("{") - line.count("}")
                method_body.append(line)
                if brace_count == 0:
                    break
            methods[method_key] = "\n".join(method_body)  # Use method signature as key
        # print("######################################################")
        # print(f"Methods extracted from {file_path}: {methods}") 
        # print("######################################################")
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    return methods





# Step 5: Parse stack trace to locate methods
def parse_stack_trace(stack_trace, codebase_dirs):
    """
    Parses the stack trace to extract methods and resolve file paths.
    """
    method_files = {}
    for line in stack_trace.split("\n"):
        # Match stack trace lines
        match = re.match(r'at (\S+)\.(\w+)\((\w+\.java):(\d+)\)', line.strip())
        if match:
            class_path, method_name, file_name, line_number = match.groups()
            print(f"Parsing stack trace line: {line.strip()}")
            print(f"Extracted: class_path={class_path}, method_name={method_name}, file_name={file_name}, line_number={line_number}")

            # Handle inner classes by removing the `$` for file paths
            outer_class_path = class_path.split('$')[0]  # Get outer class
            inner_class_name = class_path.split('$')[-1] if '$' in class_path else None
            package_path = os.sep.join(outer_class_path.split('.')) + '.java'

            file_found = False
            for codebase_dir in codebase_dirs:
                full_path = os.path.join(codebase_dir, package_path)
                if os.path.exists(full_path):
                    print("Full path:", full_path)
                    method_files[(method_name, inner_class_name)] = full_path
                    file_found = True
                    # break

            if not file_found:
                print(f"File for method {method_name} not found in any codebase directory.")

    print("================================================================")
    print("Parsed method files:", method_files)  # Debug line
    print("================================================================")
    return method_files




# Step 6: Build call graph from methods
def build_call_graph(methods):
    call_graph = defaultdict(list)
    call_pattern = re.compile(r'\w+\s*\(')
    for method, body in methods.items():
        called_methods = call_pattern.findall(body)
        call_graph[method] = [cm.split('(')[0] for cm in called_methods]
    # print("************************************************************************")
    # print('call graph:', call_graph)
    # print("************************************************************************")
    return call_graph


# Step 7: Navigate code
# def navigate_code(stack_trace, codebase_dirs):
#     """
#     Navigates code based on stack trace and extracts methods using a call graph.
#     """
#     method_files = parse_stack_trace(stack_trace, codebase_dirs)
#     visited_methods = set()  # Keep track of visited methods to avoid duplicates
#     extracted_methods = {}

#     for method_name, file_path in method_files.items():
#         if os.path.exists(file_path) and method_name not in visited_methods:
#             print(f"Processing method: {method_name} in {file_path}")  # Debugging

#             # Extract methods from the file
#             methods = extract_methods_from_file(file_path)
#             # print("----------methods--------")
#             # print("Methods:", methods)
#             # print("----------methods--------")
#             # print(method_name in methods)
#             # print("Method name", method_name)
#             # print("Method keys", methods.keys())
#             if method_name in methods:
#                 # Add the method to extracted_methods
#                 extracted_methods[method_name] = methods[method_name]
#                 visited_methods.add(method_name)
#                 # print("----------extracted methods--------")
#                 # print("Extracted Methods:", extracted_methods)
#                 # print("----------extracted methods--------")

#                 # Build the call graph and explore called methods
#                 call_graph = build_call_graph(methods)
#                 for called_method in call_graph.get(method_name, []):
#                     if called_method in methods and called_method not in visited_methods:
#                         extracted_methods[called_method] = methods[called_method]
#                         visited_methods.add(called_method)

#     print("Extracted methods:", extracted_methods.keys())  # Debugging output
#     return extracted_methods

# Step 7: Navigate code
def navigate_code(stack_trace, codebase_dirs):
    """
    Navigates code based on stack trace and extracts methods using a call graph.
    """
    method_files = parse_stack_trace(stack_trace, codebase_dirs)
    visited_methods = set()  # Keep track of visited methods to avoid duplicates
    extracted_methods = {}

    for (method_name, inner_class_name), file_path in method_files.items():
        if os.path.exists(file_path):
            print(f"Processing method: {method_name} in {file_path}")  # Debugging

            # Extract all methods from the file
            methods = extract_methods_from_file(file_path)
            print("----------methods--------")
            print("Methods:", methods)
            print("----------methods--------")
            # print(method_name in methods)
            # print("Method name", method_name)
            # print("Method keys", methods.keys())

            # Locate the exact method by name
            matched_method_keys = [
                key for key in methods if key.startswith(f"{method_name}(")
            ]

            print("matched_method_keys:", matched_method_keys)

            for matched_key in matched_method_keys:
                if matched_key not in visited_methods:
                    # Add the method to extracted_methods
                    extracted_methods[matched_key] = methods[matched_key]
                    visited_methods.add(matched_key)

                    # Build the call graph and explore called methods
                    call_graph = build_call_graph(methods)
                    for called_method in call_graph.get(matched_key, []):
                        called_method_keys = [
                            key for key in methods if key.startswith(f"{called_method}(")
                        ]
                        for called_key in called_method_keys:
                            if called_key not in visited_methods:
                                extracted_methods[called_key] = methods[called_key]
                                visited_methods.add(called_key)

    print("Extracted methods:", extracted_methods.keys())  # Debugging output
    return extracted_methods





# Step 8: Merge with developer written bug reports
def merge_bug_reports(output_data, bug_reports_file):
    """
    Merge developer-written bug reports into the output data.
    Checks if 'filename' and 'creation_time' match and adds the 'bug_report' field if found.
    """
    with open(bug_reports_file, "r") as file:
        developer_bug_reports = json.load(file)

    # Create a lookup for developer bug reports based on filename and creation_time
    bug_report_lookup = {
        (entry["filename"], entry["creation_time"]): entry["bug_report"]
        for entry in developer_bug_reports
    }

    # Add 'bug_report' to the output data if there is a match
    for output_entry in output_data:
        key = (output_entry["filename"], output_entry["creation_time"])
        if key in bug_report_lookup:
            output_entry["bug_report"] = bug_report_lookup[key]

    print("Bug reports have been merged into the output data.")
    return output_data




# Step 9: Main Execution
if __name__ == "__main__":
    # Read stack trace data
    # stack_trace_file = "test.json"
    stack_trace_file = "stack_traces/Hive.json"
    stack_trace_data = read_stack_traces(stack_trace_file)

    # Path to source code and Git repository
    repo_path = "/Users/fahim/Desktop/PhD/Projects/hive"
    codebase_dirs = ["/Users/fahim/Desktop/PhD/Projects/hive/shims/0.23/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hive/hcatalog/webhcat/svr/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hive/metastore/src/java", "/Users/fahim/Desktop/PhD/Projects/hive/metastore/src/gen/thrift/gen-javabean", "/Users/fahim/Desktop/PhD/Projects/hive/ql/src/java", "/Users/fahim/Desktop/PhD/Projects/hive/serde/src/java", "/Users/fahim/Desktop/PhD/Projects/hive/spark-client/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hive/service/src/java", "/Users/fahim/Desktop/PhD/Projects/hive/shims/common/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hive/contrib/src/java", "/Users/fahim/Desktop/PhD/Projects/hive/hcatalog/core/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hive/hcatalog/hcatalog-pig-adapter/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hive/hcatalog/hcatalog-pig-adapter/src/test/java"]
    git_branch = "master"
    # Path to developer-written bug reports
    dev_written_bug_reports_file = "developer_written_bug_reports/Hive.json"

    # Prepare output
    output_data = []

    for entry in stack_trace_data:
        filename = entry['filename']
        creation_time = entry['creation_time']
        stack_trace = entry['stack_trace']

        # Switch to the appropriate commit
        commit_version = get_commit_version(creation_time, repo_path, git_branch)
        print("Commit Version:", commit_version)
        checkout_to_commit(commit_version, repo_path, git_branch)

        # Extract relevant methods using stack trace and call graph
        relevant_methods = navigate_code(stack_trace, codebase_dirs)

        # Add to output data
        output_data.append({
            'filename': filename,
            'creation_time': creation_time,
            'stack_trace': stack_trace,
            'source_code': relevant_methods
        })

    # Merge developer-written bug reports into the output data
    output_data = merge_bug_reports(output_data, dev_written_bug_reports_file)

    # Write output to JSON
    # output_file = 'test_output.json'
    output_file = 'source_code_data/Hive.json'
    with open(f"{output_file}", "w") as outfile:
        json.dump(output_data, outfile, indent=4)

    print(f"Source code have been extracted and saved to '{output_file}'")