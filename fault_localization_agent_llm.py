import os
import json
import subprocess
import re
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from collections import defaultdict
import tiktoken

# # Load LLM 
# llm = OpenAI(model="gpt-4o-mini", temperature=0)

# Load bug reports from JSON file
def load_bug_reports(file_path):
    with open(file_path, "r") as f:
        bug_reports = json.load(f)
    return bug_reports

# Load ground truth data
def load_ground_truth(file_path):
    with open(file_path, "r") as f:
        ground_truth = json.load(f)
    return ground_truth

# Convert JSON bug report to a string
def convert_bug_report_to_string(bug_report):
    return json.dumps(bug_report, indent=4)

# Get the commit version before a specific timestamp
def get_commit_version(creation_time, repo_path, git_branch):
    command = f'git rev-list -n 1 --before="{creation_time}" {git_branch}'
    result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=repo_path)
    commit_version = result.stdout.strip()
    return commit_version

# Checkout to the specific commit version
def checkout_to_commit(commit_version, repo_path, git_branch):
    subprocess.run('git stash --include-untracked', shell=True, cwd=repo_path)
    reset_command = f'git checkout {git_branch}'
    subprocess.run(reset_command, shell=True, cwd=repo_path)
    checkout_command = f'git checkout {commit_version}'
    subprocess.run(checkout_command, shell=True, cwd=repo_path)


# Extract stack trace from bug reports
def extract_stack_trace(bug_report):
    pattern = r"at (.+?)\((.+?):(\d+)\)"
    stack_trace = re.findall(pattern, bug_report)
    return stack_trace

# Process stack trace: Group by file, aggregate methods and lines
def process_stack_trace(stack_trace):
    file_to_methods = defaultdict(lambda: {"methods": set(), "lines": set()})
    
    for class_name, file_name, line_number in stack_trace:
        package_path = os.sep.join(class_name.split('.')[:-1]) + ".java"
        file_key = package_path  # Use package_path as the key
        method_name = class_name.split('.')[-1]  # Extract method name (last part after the dot)
        
        file_to_methods[file_key]["methods"].add(method_name)
        file_to_methods[file_key]["lines"].add(line_number)
    
    # Convert sets to lists for JSON serialization or further processing
    return {
        file_name: {"methods": list(data["methods"]), "lines": list(data["lines"])}
        for file_name, data in file_to_methods.items()
    }


# Retrieve unique files referenced in the stack trace
def get_relevant_files(stack_trace, codebase_dirs):
    processed_trace = process_stack_trace(stack_trace)
    # print("-------------------- processed_trace (start) --------------------------")
    # print(processed_trace)
    # print("-------------------- processed_trace (end) --------------------------")
    relevant_files = []

    for file_name, details in processed_trace.items():
        for codebase_dir in codebase_dirs:
            full_path = os.path.join(codebase_dir, file_name)
            if os.path.exists(full_path):
                relevant_files.append({
                    "file_path": full_path,
                    "methods": details["methods"],
                    "lines": details["lines"]
                })
    
    return relevant_files




# Prepare the corpus text for the LLM with method and line context
def prepare_corpus_for_llm(relevant_files):
    # print("------------- prepare_corpus_for_llm (start) ---------------")
    # print(relevant_files)
    # print("------------- prepare_corpus_for_llm (end) ---------------")
    corpus = []
    for file in relevant_files:
        try:
            with open(file["file_path"], "r", encoding="utf-8") as f:
                content = f.read()
                
                # Include method and line details
                file_context = f"File: {file['file_path']}\n" \
                               f"Methods Referenced: {', '.join(file['methods'])}\n" \
                               f"Lines Referenced: {', '.join(file['lines'])}\n" \
                               f"Content:\n{content}"
                corpus.append(file_context)
        except Exception as e:
            # file_context = f"File: '{file['file_path']}' not found in the codebase."
            # corpus.append(file_context)
            print(f"Error reading file {file['file_path']}: {e}")
    
    return corpus


def find_correct_codebase_path(requested_file, codebase_dirs):
    """
    Removes incorrect codebase_dir prefix from the requested file 
    and checks which codebase_dir contains the actual file.
    """
    for codebase_dir in codebase_dirs:
        if requested_file.startswith(codebase_dir):
            relative_path = requested_file[len(codebase_dir):].lstrip("/")
            break
    else:
        relative_path = requested_file  # If no prefix matches, use the original file name

    # Check in all codebase_dirs to find where the file actually exists
    for codebase_dir in codebase_dirs:
        corrected_path = os.path.join(codebase_dir, relative_path)
        if os.path.exists(corrected_path):
            return corrected_path  # Return the correct path if found

    return None  # File not found in any codebase_dir



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



def perform_agent_analysis(query, initial_files, codebase_dirs):
    analyzed_files = set()
    file_scores = {}

    # Track file paths already in initial_files to prevent duplicates
    initial_files_set = set(file["file_path"] for file in initial_files)

    while initial_files:
        file_to_analyze = initial_files.pop(0)
        analyzed_files.add(file_to_analyze["file_path"])
        initial_files_set.discard(file_to_analyze["file_path"])  # Remove from tracking set
        
        # Prepare corpus
        corpus = prepare_corpus_for_llm([file_to_analyze])
        print("-------------------- Corpus (start) --------------------------")
        # print(corpus)
        if corpus == []:
            print("Continue to the next iteration")
            continue
        print("-------------------- Corpus (end) --------------------------")

        # LLM prompt
        template = """
        You are an AI debugging assistant analyzing a bug report:
        {query}

        Review the file below:
        {corpus}

        If the issue is found, provide a fault likelihood score (0-10). 
        If the issue is not conclusive, list additional files that may be needed for analysis.

        # Important Instructions:
        - Always provide additional files using their full file path as seen in the corpus.
        - Do NOT return just filenames; return full paths.

        # Output Format
        ```json
        {{
            "file": "<full_file_path>", 
            "score": <integer>,
            "additional_files": ["<full_file_path_1>", "<full_file_path_2>"]
        }}
        ```
        """
        # Handle Max Token limit exceed cases
        # Format the full prompt
        full_prompt = template.format(
            query=query, 
            corpus=corpus
        )

        # Check token count
        token_count = count_tokens(full_prompt)
        if token_count > 100000:
            print(f"Token count ({token_count}) exceeds limit! Splitting into chunks...")
            prompt_chunks = split_into_chunks(full_prompt, max_tokens=100000)
            responses = []
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
            count = 0
            for chunk in prompt_chunks:
                count += 1
                if count == len(prompt_chunks):
                    text = f"You analyzed File: '{file_to_analyze["file_path"]}' in chunks. Now generate the final output in JSON structure according to the output format."
                    chunk = chunk + text

                llm_response = llm.invoke(chunk)
                responses.append(llm_response)
            # parse response to get the json output
            response = ""
            for message in responses:
                if "json" in message.content and "file" in message.content and "score" in message.content and "additional_files" in message.content:
                    response = message.content
                    break
        else:
            # Normal LLM call
            prompt = PromptTemplate.from_template(template)
            llm = ChatOpenAI(model='gpt-4o-mini', temperature=0)
            chain = LLMChain(llm=llm, prompt=prompt)
            response = chain.run({"query": query, "corpus": corpus})
            
        
        # Parse LLM response
        try:
            # print("-------------------- response (start) --------------------------")
            # print("response:", response)
            # print("-------------------- response (end) --------------------------")
            parsed_response = json.loads(response.replace("```json\n", "").replace("\n```", ""))
            file_scores[parsed_response["file"]] = parsed_response["score"]

            # Add new files to be analyzed (Avoid duplicates)
            for new_file in parsed_response.get("additional_files", []):
                if new_file not in analyzed_files and new_file not in initial_files_set:
                    if os.path.exists(new_file):
                        initial_files.append({"file_path": new_file, "methods": [], "lines": []})
                        initial_files_set.add(new_file)  # Track it to prevent duplicates
                    else:
                        correct_path = find_correct_codebase_path(new_file, codebase_dirs)
                        if correct_path:
                            if correct_path not in analyzed_files and correct_path not in initial_files_set:
                                initial_files.append({"file_path": correct_path, "methods": [], "lines": []})
                                initial_files_set.add(correct_path)  # Track it to prevent duplicates
                    # print("-------------------- initial_files (start) --------------------------")
                    # print("analyzed_files:", analyzed_files)
                    # print("initial_files_set:", initial_files_set)
                    # print("initial_files:", initial_files)
                    # print("-------------------- initial_files (end) --------------------------")

        except json.JSONDecodeError as e:
            print(f"Error parsing response: {e}")

    return sorted(file_scores.items(), key=lambda x: x[1], reverse=True)




# Convert file path to ground truth format
def convert_to_ground_truth_format(file_path, codebase_dirs):
    for codebase_dir in codebase_dirs:
        if file_path.startswith(codebase_dir):
            relative_path = file_path.replace(codebase_dir + os.sep, "").replace(".java", "")
            return relative_path.replace(os.sep, ".")
    return None  # Handle files that don't match any directory

# Transform ranked files to ground truth format
def transform_ranked_files(ranked_files, codebase_dirs):
    return [convert_to_ground_truth_format(file, codebase_dirs) for file, _ in ranked_files]


def save_ranked_files(filename, ranked_files, transformed_ranked_files, ground_truth):
    results_file = f"results/LLM/{bug_report_folder}.json"
    # Load existing results if the file exists
    if os.path.exists(results_file):
        with open(results_file, "r") as f:
            try:
                results = json.load(f)
            except json.JSONDecodeError:
                results = []
    else:
        results = []

    # Append new data
    results.append({
        "filename": filename,
        "ranked_files": ranked_files,
        "transformed_ranked_files": transformed_ranked_files,
        "ground_truth": ground_truth.get(filename, [])
    })

    # Save the updated results back to the file
    with open(results_file, "w") as f:
        json.dump(results, f, indent=4)


# Perform file-level fault localization using LLM
def perform_fault_localization_single_repo(bug_reports_file, ground_truth_file, repo_path, codebase_dirs, git_branch, top_n_values):
    bug_reports = load_bug_reports(bug_reports_file)
    ground_truth = load_ground_truth(ground_truth_file)
    results = []

    for report in bug_reports:
        filename = report["filename"]
        creation_time = report["creation_time"]
        bug_report_json = report["bug_report"]
        bug_report = convert_bug_report_to_string(bug_report_json)

        # Get commit version and checkout
        commit_version = get_commit_version(creation_time, repo_path, git_branch)
        if commit_version:
            checkout_to_commit(commit_version, repo_path, git_branch)

            # Extract stack trace
            stack_trace = extract_stack_trace(bug_report)
            # print("-------------------- stack trace (start) --------------------------")
            # print(stack_trace)
            # print("-------------------- stack trace (end) --------------------------")
            
            # Step 1: Filter files based on the stack trace
            relevant_files = get_relevant_files(stack_trace, codebase_dirs)
            # print("-------------------- relevant_files (start) --------------------------")
            # print(relevant_files)
            # print("-------------------- relevant_files (end) --------------------------")


            # Step 2: Perform agent-based analysis iteratively
            ranked_files = perform_agent_analysis(bug_report, relevant_files, codebase_dirs)
            # print("-------------------- ranked_files (start) --------------------------")
            # print(ranked_files)
            # print("-------------------- ranked_files (end) --------------------------")

            # Transform ranked files to ground truth format for comparison
            transformed_ranked_files = transform_ranked_files(ranked_files, codebase_dirs)
            # print("-------------------- transformed_ranked_files (start) --------------------------")
            # print(transformed_ranked_files)
            # print("-------------------- transformed_ranked_files (end) --------------------------")
            results.append((filename, transformed_ranked_files))

            # Save to results file
            save_ranked_files(filename, ranked_files, transformed_ranked_files, ground_truth)

    return evaluate_metrics(results, ground_truth, top_n_values)


# Function to compare if a ranked file ends with any ground truth file
def match_ranked_to_ground_truth(ranked_file, ground_truth_files):
    if ranked_file is None:  # Avoid AttributeError
        return False
    # Loop over each ground truth file
    for ground_truth_file in ground_truth_files:
        # Check if the ranked file ends with the ground truth file (i.e., matches the last part)
        if ranked_file.endswith(ground_truth_file):
            return True
    return False

# Evaluation function for MAP, MRR, and Top N scores
def evaluate_metrics(results, ground_truth, top_n_values):
    metrics = {"MAP": [], "MRR": [], "Top@N": {n: 0 for n in top_n_values}, "total_reports": 0}
    total_reports = 0

    for filename, ranked_files in results:
        ground_truth_files = ground_truth.get(filename, [])
        if not ground_truth_files:
            continue

        total_reports += 1
        relevant_found = 0
        precision_sum = 0
        relevant_within_top_n = {n: False for n in top_n_values}

        for rank, file in enumerate(ranked_files, start=1):
            if match_ranked_to_ground_truth(file, ground_truth_files):
                relevant_found += 1
                precision_sum += relevant_found / rank
                if relevant_found == 1:
                    metrics["MRR"].append(1 / rank)
                for n in top_n_values:
                    if rank <= n and not relevant_within_top_n[n]:
                        metrics["Top@N"][n] += 1
                        relevant_within_top_n[n] = True

        avg_precision = precision_sum / relevant_found if relevant_found > 0 else 0
        metrics["MAP"].append(avg_precision)

    metrics["total_reports"] = total_reports
    return metrics

def aggregate_results(results_list, top_n_values):
    total_reports = sum(result["total_reports"] for result in results_list)
    overall_metrics = {"MAP": 0, "MRR": 0, "Top@N": {n: 0 for n in top_n_values}}

    for result in results_list:
        if len(result["MAP"]) > 0:  # Check to avoid division by zero
            overall_metrics["MAP"] += sum(result["MAP"]) / len(result["MAP"]) * result["total_reports"]
        overall_metrics["MRR"] += (sum(result["MRR"]) / len(result["MRR"]) * result["total_reports"]) if len(result["MRR"]) > 0 else 0
        for n in top_n_values:
            overall_metrics["Top@N"][n] += result["Top@N"][n]

    # Print Top@N accross all repositories
    print("\nTotal Top@N counts across all repositories (raw counts):")
    top_n_counts = {}
    for n in top_n_values:
        print(f"Top-{n}: {overall_metrics['Top@N'][n]}")
        top_n_counts[f"Top-{n}"] = overall_metrics['Top@N'][n]

    if total_reports > 0:
        overall_metrics["MAP"] /= total_reports
        overall_metrics["MRR"] /= total_reports
        for n in top_n_values:
            overall_metrics["Top@N"][n] /= total_reports

    return overall_metrics, top_n_counts


# Main function to process all repositories
def process_repositories(repositories, top_n_values):
    results_list = []
    for repo_config in repositories:
        result = perform_fault_localization_single_repo(
            repo_config["bug_reports"],
            repo_config["ground_truth"],
            repo_config["repo_path"],
            repo_config["codebase_dir"],
            repo_config["git_branch"],
            top_n_values
        )
        results_list.append(result)

    overall_metrics, top_n_counts = aggregate_results(results_list, top_n_values)

    # Save overall result to the output file
    results_file = f"results/LLM/{bug_report_folder}.json"
    # Load existing results if the file exists
    if os.path.exists(results_file):
        with open(results_file, "r") as f:
            try:
                overall_results = json.load(f)
            except json.JSONDecodeError:
                overall_results = []
    else:
        overall_results = []

    overall_results.append({
        "bug_report_folder": bug_report_folder,
        "overall_metrics": overall_metrics,
        "top@N_value_counts": top_n_counts
    })
    # Save the updated results back to the file
    with open(results_file, "w") as f:
        json.dump(overall_results, f, indent=4)


    print("\nOverall Metrics:")
    print(f"Mean Average Precision (MAP): {overall_metrics['MAP']}")
    print(f"Mean Reciprocal Rank (MRR): {overall_metrics['MRR']}")
    for n in top_n_values:
        print(f"Top-{n} Accuracy: {overall_metrics['Top@N'][n]}")


# Example repository configuration and usage
bug_report_folder = 'agentBased_bug_report_from_bugReport_sourceCode'
repositories = [
    {"bug_reports": f"{bug_report_folder}/Zookeeper.json", "ground_truth": "ground_truth/Zookeeper.json", "repo_path": "/Users/fahim/Desktop/PhD/Projects/zookeeper", "codebase_dir": ["/Users/fahim/Desktop/PhD/Projects/zookeeper/src/java/main", "/Users/fahim/Desktop/PhD/Projects/zookeeper/src/java/test"], "git_branch": 'master'},
    {"bug_reports": f"{bug_report_folder}/ActiveMQ.json", "ground_truth": "ground_truth/ActiveMQ.json", "repo_path": "/Users/fahim/Desktop/PhD/Projects/activemq", "codebase_dir": ["/Users/fahim/Desktop/PhD/Projects/activemq/activemq-client/src/main/java", "/Users/fahim/Desktop/PhD/Projects/activemq/activemq-core/src/main/java", "/Users/fahim/Desktop/PhD/Projects/activemq/activemq-broker/src/main/java", "/Users/fahim/Desktop/PhD/Projects/activemq/activemq-karaf/src/main/java", "/Users/fahim/Desktop/PhD/Projects/activemq/activemq-kahadb-store/src/main/java", "/Users/fahim/Desktop/PhD/Projects/activemq/activemq-optional/src/main/java"], "git_branch": 'main'},
    {"bug_reports": f"{bug_report_folder}/Hadoop.json", "ground_truth": "ground_truth/Hadoop.json", "repo_path": "/Users/fahim/Desktop/PhD/Projects/hadoop", "codebase_dir": ["/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-common/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-common/src/test/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/src/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/src/test/core", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-common/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-hdfs-project/hadoop-hdfs/src/main/java","/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-tools/hadoop-distcp/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-tools/hadoop-azure/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-nfs/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-auth/src/main/java"], "git_branch": 'trunk'},
    {"bug_reports": f"{bug_report_folder}/HDFS.json", "ground_truth": "ground_truth/HDFS.json", "repo_path": "/Users/fahim/Desktop/PhD/Projects/hadoop", "codebase_dir": ["/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-hdfs-project/hadoop-hdfs/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-hdfs-project/hadoop-hdfs/src/test/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-hdfs-project/hadoop-hdfs-client/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-hdfs-project/hadoop-hdfs-nfs/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hdfs/src/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-nfs/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-common/src/main/java"], "git_branch": 'trunk'},
    {"bug_reports": f"{bug_report_folder}/Hive.json", "ground_truth": "ground_truth/Hive.json", "repo_path": "/Users/fahim/Desktop/PhD/Projects/hive", "codebase_dir": ["/Users/fahim/Desktop/PhD/Projects/hive/shims/0.23/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hive/hcatalog/webhcat/svr/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hive/metastore/src/java", "/Users/fahim/Desktop/PhD/Projects/hive/metastore/src/gen/thrift/gen-javabean", "/Users/fahim/Desktop/PhD/Projects/hive/ql/src/java", "/Users/fahim/Desktop/PhD/Projects/hive/serde/src/java", "/Users/fahim/Desktop/PhD/Projects/hive/spark-client/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hive/service/src/java", "/Users/fahim/Desktop/PhD/Projects/hive/shims/common/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hive/contrib/src/java", "/Users/fahim/Desktop/PhD/Projects/hive/hcatalog/core/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hive/hcatalog/hcatalog-pig-adapter/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hive/hcatalog/hcatalog-pig-adapter/src/test/java"], "git_branch": 'master'},
    {"bug_reports": f"{bug_report_folder}/MAPREDUCE.json", "ground_truth": "ground_truth/MAPREDUCE.json", "repo_path": "/Users/fahim/Desktop/PhD/Projects/hadoop", "codebase_dir": ["/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-mapreduce-project/hadoop-mapreduce-client/hadoop-mapreduce-client-core/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-mapreduce-project/hadoop-mapreduce-client/hadoop-mapreduce-client-app/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-mapreduce-project/hadoop-mapreduce-client/hadoop-mapreduce-client-app/src/test/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-common/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-mapreduce-project/hadoop-yarn/hadoop-yarn-common/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-mapreduce-project/hadoop-yarn/hadoop-yarn-server/hadoop-yarn-server-nodemanager/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-mapreduce-project/hadoop-yarn/hadoop-yarn-server/hadoop-yarn-server-resourcemanager/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-mapreduce-project/hadoop-yarn/hadoop-yarn-server/hadoop-yarn-server-resourcemanager/src/test/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-mapreduce-project/hadoop-yarn/hadoop-yarn-server/hadoop-yarn-server-common/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-mapreduce-project/hadoop-yarn/hadoop-yarn-server/hadoop-yarn-server-web-proxy/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/src/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-common/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/common/src/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/mapreduce/src/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/mapreduce/src/test/mapred", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-mapreduce-project/hadoop-mapreduce-client/hadoop-mapreduce-client-jobclient/src/test/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-hdfs-project/hadoop-hdfs/src/main/java"], "git_branch": 'trunk'},
    {"bug_reports": f"{bug_report_folder}/Storm.json", "ground_truth": "ground_truth/Storm.json", "repo_path": "/Users/fahim/Desktop/PhD/Projects/storm", "codebase_dir": ["/Users/fahim/Desktop/PhD/Projects/storm/storm-client/src/jvm", "/Users/fahim/Desktop/PhD/Projects/storm/storm-server/src/main/java", "/Users/fahim/Desktop/PhD/Projects/storm/storm-core/src/jvm", "/Users/fahim/Desktop/PhD/Projects/storm/external/storm-kafka-client/src/main/java", "/Users/fahim/Desktop/PhD/Projects/storm/external/storm-hdfs/src/main/java"], "git_branch": 'master'},
    {"bug_reports": f"{bug_report_folder}/YARN.json", "ground_truth": "ground_truth/YARN.json", "repo_path": "/Users/fahim/Desktop/PhD/Projects/hadoop", "codebase_dir": ["/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-server/hadoop-yarn-server-resourcemanager/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-server/hadoop-yarn-server-resourcemanager/src/test/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-server/hadoop-yarn-server-nodemanager/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-common/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-server/hadoop-yarn-server-common/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-server/hadoop-yarn-server-applicationhistoryservice/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-api/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-common/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-mapreduce-project/hadoop-mapreduce-client/hadoop-mapreduce-client-jobclient/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-tools/hadoop-gridmix/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-client/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-server/hadoop-yarn-server-web-proxy/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-registry/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-server/hadoop-yarn-server-tests/src/test/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-applications/hadoop-yarn-services/hadoop-yarn-services-core/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-client/src/test/java"], "git_branch": 'trunk'}
]

top_n_values = [1, 3, 5, 10]
process_repositories(repositories, top_n_values)
