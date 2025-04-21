import os
import json
import subprocess
from datetime import datetime
from pathlib import Path
import javalang
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain import PromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain



def get_commit_version(creation_time, repo_path, git_branch):
    command = f'git rev-list -n 1 --before="{creation_time}" {git_branch}'
    result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=repo_path)
    commit_version = result.stdout.strip()
    return commit_version

def checkout_to_commit(commit_version, repo_path, git_branch):
    subprocess.run('git reset --hard', shell=True, cwd=repo_path)
    subprocess.run('git stash push --include-untracked', shell=True, cwd=repo_path)
    subprocess.run(f'git checkout {git_branch}', shell=True, cwd=repo_path)
    subprocess.run('git pull', shell=True, cwd=repo_path)
    subprocess.run(f'git checkout {commit_version}', shell=True, cwd=repo_path)
    subprocess.run('git stash drop', shell=True, cwd=repo_path)


def get_method_dict(methods_list, commit_version, repo_path, git_branch):
    checkout_to_commit(commit_version, repo_path, git_branch)
    method_dict = {}
    # print("------------------ get_method_dict (start) ------------ ")
    for full_method in methods_list:
        parts = full_method.split('.')
        method_name = parts[-1]
        path = '/'.join(parts[:-1]) + '.java'
        found = False

        
        full_path = os.path.join(repo_path, path)
        # print("full_path before:", full_path)
        if os.path.exists(full_path):
            # print("full_path if exist:", full_path)
            # print("------------------ get_method_dict (end) ------------ ")
            with open(full_path, 'r') as f:
                file_content = f.read()
            try:
                tree = javalang.parse.parse(file_content)
                for _, node in tree.filter(javalang.tree.MethodDeclaration):
                    if node.name == method_name and node.position:
                        extracted_code = extract_method_code(file_content, node.position)
                        method_dict[full_method] = extracted_code
                        found = True
                        break
            except Exception as e:
                print(f"⚠️ Failed to parse {full_path}: {e}")

        if not found:
            method_dict[full_method] = []

    return method_dict

def extract_method_code(file_content, position):
    lines = file_content.splitlines()
    start_line = position.line - 1
    method_lines = []
    open_braces = 0
    found_method_start = False

    for i in range(start_line, len(lines)):
        line = lines[i]
        method_lines.append(line)
        open_braces += line.count('{')
        open_braces -= line.count('}')
        if '{' in line and not found_method_start:
            found_method_start = True
        if found_method_start and open_braces == 0:
            break

    return "\n".join(method_lines)


# Source Code Methods [from call graph of Stack Trace]
def get_source_code_dict(filename, source_code_file_path):
    with open(source_code_file_path, 'r') as f:
        data = json.load(f)
    
    for entry in data:
        if entry['filename'] == filename:
            return entry.get('source_code', {})
    
    return {}




def call_llm_judge(bug_report, ground_truth_methods, code_difference, source_code_methods):
    template = """
    You are a software engineering expert evaluating a bug report based on its ability to accurately describe and diagnose a real bug. You will be given:

    - A generated bug report
    - A list of method names where the bug actually occurred (ground truth)
    - The source code of those ground truth methods before and after the fix (representing the developer's actual fix)
    - Source code methods from the call dependency of the methods of stack traces

    Evaluate the bug report based on the following four criteria:

    1. **Root Cause Identification**  
    - **Precise**: Identifies the exact root cause related to any of the ground truth methods.
    - **Partial**: Mentions which error occurred and also mentions where the error occurred. But, it is not the actual root cause at the ground truth method(s).
    - **Missing**: No such fields or no information about the cause of the bug.

    2. **Fix Suggestion**  
    - **Correct**: Matches the developer’s fix as seen in the “after” version of the method. In case, there is no `Suggestions` or `problem_location` field in the bug report, check the `description` field carefully to find if any fixing suggestions exists.
    - **Alternative Fix**: Different than the developer’s fix, but would likely resolve the bug in the same way. In case, there is no `Suggestions` or `problem_location` field in the bug report, check the `description` field carefully to find if any fixing suggestions exists.
    - **Preventive**: Would prevent or mitigate the bug at any of the buggy locations. It can be as simple as implementing conditions to prevent the error. In case, there is no `Suggestions` or `problem_location` field in the bug report, check the `description` field carefully to find if any fixing suggestions exists.
    - **Missing**: No suggestions provided to fix the bug. 

    3. **Problem Location Identification**  
    - **Precise**: The `problem_location` field mentions at least one method from the ground truth list. If the `problem_location` field is missing, the `title` field or the `description` field might contain some information about it, but do not consider it, if it is inside stack traces of the `description` field as that is not a direct problem location suggestion.
    - **Partial**: The `problem_location` field mentions methods related to the problem or related to methods mentioned in the stack traces, but not from the ground truth list. If the `problem_location` field is missing, the `title` field or the `description` field might contain some information about it, but do not consider it, if it is inside stack traces of the `description` field as that is not a direct problem location suggestion.
    - **Missing**: No methods or locations identified even from title or description of the bug report.

    4. **Wrong Information**  
    - **Yes**: The bug report contains statements that are completely unrelated or incorrect.
    - **No**: All information appears grounded in the context of the bug.

    ---

    ### Bug Report:
    {bug_report}

    ---

    ### Ground Truth Method Names:
    {ground_truth_methods}

    ---

    ### Ground Truth Methods (Before and After Code):

    {code_difference}

    ---

    ### Source Code Methods (from the call dependency of the methods of stack traces):

    {source_code_methods}

    ---



    Provide your response in the following JSON format:
    ```json
    {{
        "root_cause_identification": "[Precise | Partial | Missing]",
        "fix_suggestion": "[Correct | Alternative Fix | Preventive | Missing]",
        "problem_location_identification": "[Precise | Partial | Missing]",
        "wrong_information": "[Yes | No]",
        "explanation_of_judgement": "<brief justification for each evaluation>"
    }}

    """

    prompt = PromptTemplate.from_template(template)
    llm = ChatOpenAI(model='gpt-4o', temperature = 0)

    chain = LLMChain(llm=llm, prompt=prompt)
    return chain.run({'bug_report': bug_report, 'ground_truth_methods': ground_truth_methods, 'code_difference': code_difference, 'source_code_methods': source_code_methods})





# Repository Information
repo_path = "/Users/fahim/Desktop/PhD/Projects/hadoop"
git_branch = "trunk"

# File Paths
bug_report_path = "test.json"
# bug_report_path = "modified_dev_written_bug_reports/YARN.json"
# bug_report_path = "agentBased_bug_report_from_modified_bugReport_sourceCode/YARN.json"
# bug_report_path = "agentBased_bug_report_from_stackTrace_sourceCode/YARN.json"
# bug_report_path = "bug_report_from_modified_bugReport_sourceCode/YARN.json"
# bug_report_path = "bug_report_from_stackTrace_sourceCode/YARN.json"

ground_truth_methods_path = "ground_truth/methods/YARN.json"
code_changes_path = "ground_truth/code_changes.json"
source_code_methods_from_call_graph = "source_code_data/method_list/YARN.json"

# Output File Paths
output_file = "test_output.json"
# output_file = "llm_judge/developer_written_BR/YARN.json"
# output_file = "llm_judge/agent_based_BR_from_BR_SC/YARN.json"
# output_file = "llm_judge/agent_based_BR_from_ST_SC/YARN.json"
# output_file = "llm_judge/bug_report_from_BR_SC/YARN.json"
# output_file = "llm_judge/bug_report_from_ST_SC/YARN.json"

with open(bug_report_path) as f:
    bug_reports = json.load(f)
with open(ground_truth_methods_path) as f:
    gt_methods = json.load(f)
with open(code_changes_path) as f:
    code_changes = json.load(f)



output_data = []


processed_files = {entry['filename'] for entry in output_data}

# List of bug reports to skip for method level FL
bug_reports_to_skip_for_method_level_fl = ["HDFS-6533.json", "HADOOP-12611.json", "HADOOP-11149.json", "HDFS-6904.json", "HDFS-13635.json", "HDFS-7884.json", "HIVE-2958.json", "MAPREDUCE-3070.json", "MAPREDUCE-5451.json", "MAPREDUCE-3531.json", "MAPREDUCE-7077.json", "MAPREDUCE-6702.json", "STORM-1520.json", "STORM-2873.json", "YARN-1550.json", "YARN-2649.json", "YARN-5728.json", "YARN-7645.json", "YARN-7849.json"]


for report in bug_reports:
    filename = report['filename']

    if filename in processed_files:
        continue

    # Skip bug reports for method level FL
    if filename in bug_reports_to_skip_for_method_level_fl:
        print(f"Skipping bug report: {filename}")
        continue  # Move to the next bug report

    creation_time = report['creation_time']
    bug_report = report['bug_report']
    method_list = gt_methods.get(filename, [])
    bug_id = filename.replace('.json', '')
    commit_after = None
    for key in code_changes:
        if key.startswith(bug_id):
            commit_after = key.split('@')[1]
            break
    if not commit_after:
        continue

    commit_before = get_commit_version(creation_time, repo_path, git_branch)
    method_before = get_method_dict(method_list, commit_before, repo_path, git_branch)
    method_after = get_method_dict(method_list, commit_after, repo_path, git_branch)

    code_diff = {}
    for method in method_list:
        code_diff[method] = {
            "code_before_change": method_before.get(method, []),
            "code_after_change": method_after.get(method, [])
        }

    source_code_methods = get_source_code_dict(filename, source_code_methods_from_call_graph)

    judgement_str = call_llm_judge(bug_report, method_list, code_diff, source_code_methods)
    # Parse the judgement reponse JSON from the generated string
    try:
        # Remove any markdown-style code block indicators (` ```json `) if present
        judgement = json.loads(judgement_str.replace("```json\n", "").replace("\n```", ""))
    except json.JSONDecodeError:
        print("--------------------- LLM Judge Response [START] --------------------")
        print(judgement_str)
        print("--------------------- LLM Judge Response [END] --------------------")
        print(f"Failed to parse JSON for filename: {filename}")
        continue  # Skip this entry if JSON parsing fails


    # print("--------------- PRINT ---------------")
    # print("Filename:", filename)
    # print('commit before:', commit_before)
    # print('commit after:', commit_after)
    # print("Ground Truth Method List:", method_list)
    # print("--------------------- CODE BEFORE CHANGE [START] --------------------")
    # print(method_before)
    # print("--------------------- CODE BEFORE CHANGE [END] --------------------")
    # print("--------------------- CODE AFTER CHANGE [START] --------------------")
    # print(method_after)
    # print("--------------------- CODE AFTER CHANGE [END] --------------------")
    # print("--------------------- CODE DIFF OVERALL [START] --------------------")
    # print(code_diff)
    # print("--------------------- CODE DIFF OVERALL [END] --------------------")
    # print("--------------------- source_code_methods_from_call_graph[START] --------------------")
    # print(source_code_methods)
    # print("--------------------- source_code_methods_from_call_graph [END] --------------------")
    # print("--------------------- LLM Judge Response [START] --------------------")
    # print(judgement)
    # print("--------------------- LLM Judge Response [END] --------------------")
    # print("--------------- PRINT ---------------")



    # Add to output data
    output_data.append({
        'filename': filename,
        'code_diff': code_diff,
        'llm_judgement': judgement
    })

    # Write to output file after each bug report
    with open(output_file, "w") as outfile:
        json.dump(output_data, outfile, indent=4)
    print(f"Progress saved to {output_file}")


print(f"LLM Judgement have been generated and saved to '{output_file}'")