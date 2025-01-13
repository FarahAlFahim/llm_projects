import os
import json
import subprocess
import nltk
import re
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from collections import defaultdict

# # Load LLM (e.g., OpenAI GPT model)
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


# Summarize code by extracting classes, methods, and comments
def summarize_code(content):
    classes = re.findall(r"\b(class|interface)\s+\w+", content)
    methods = re.findall(r"(public|protected|private|static|\s)+[\w<>\[\]]+\s+\w+\s*\([^)]*\)\s*\{?", content)
    comments = re.findall(r"(//.*?$|/\*.*?\*/)", content, re.DOTALL | re.MULTILINE)
    
    summarized_content = "Classes:\n" + "\n".join(classes) + "\n\n"
    summarized_content += "Methods:\n" + "\n".join(methods) + "\n\n"
    summarized_content += "Comments:\n" + "\n".join(comments)
    
    return summarized_content.strip()


# Prepare the corpus text for the LLM with method and line context
def prepare_corpus_for_llm(relevant_files):
    corpus = []
    for file in relevant_files:
        try:
            with open(file["file_path"], "r", encoding="utf-8") as f:
                content = f.read()
                summary = summarize_code(content)
                
                # Include method and line details
                file_context = f"File: {file['file_path']}\n" \
                               f"Methods Referenced: {', '.join(file['methods'])}\n" \
                               f"Lines Referenced: {', '.join(file['lines'])}\n" \
                               f"Summary:\n{summary}"
                corpus.append(file_context)
        except Exception as e:
            print(f"Error reading file {file['file_path']}: {e}")
    
    return corpus


# Chunk corpus into smaller pieces for LLM processing
def chunk_corpus(corpus, chunk_size=5):
    return [corpus[i:i + chunk_size] for i in range(0, len(corpus), chunk_size)]


# Perform semantic search using LLM
def perform_semantic_search(query, corpus):
    corpus_chunks = chunk_corpus(corpus, chunk_size=5)
    file_scores = defaultdict(list)  # To store scores for each file

    for chunk in corpus_chunks:
        # Prepare corpus text for the LLM
        # corpus_text = "\n".join(chunk)
        corpus_text = chunk
        # print("-------------------- chunk (start) --------------------------")
        # print("chunk:", chunk)
        # print("corpus_text:", corpus_text)
        # print("-------------------- chunk (end) --------------------------")


        # LLM prompt
        template = """
        You are a debugging assistant. Given the following bug report or stack trace:
        {query}

        Analyze the relevant files below and assign a relevance score (0-10) to each file based on how likely it is to contain the bug.
        
        {corpus}

        # Output Format
        ```json
        [
            {{"file": "<file_path_1>", "score": <integer>}},
            {{"file": "<file_path_2>", "score": <integer>}}
        ]
        ```
        """
        prompt = PromptTemplate.from_template(template)
        llm = ChatOpenAI(model='gpt-4o-mini', temperature = 0)

        # LLM Chain
        chain = LLMChain(llm=llm, prompt=prompt)
        response = chain.run({"query": query, "corpus": corpus_text})
        # print("-------------------- response (start) --------------------------")
        # print("response:", response)
        # # print("ranked_files_response:", ranked_files_response)
        # print("-------------------- response (end) --------------------------")

        # Parse LLM response
        try:
            ranked_files_chunk = json.loads(response.replace("```json\n", "").replace("\n```", ""))
            for entry in ranked_files_chunk:
                file_scores[entry["file"]].append(entry["score"])  # Collect scores for each file
        except json.JSONDecodeError as e:
            print(f"Error parsing response: {e}")
            print("Raw response:", response)

    # Aggregate scores (e.g., take max score per file)
    aggregated_scores = {
        file: max(scores) for file, scores in file_scores.items()
    }

    # Sort files by aggregated score in descending order
    ranked_files = sorted(aggregated_scores.items(), key=lambda x: x[1], reverse=True)
    return ranked_files




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


# Perform file-level fault localization using LLM
def perform_fault_localization_single_repo(bug_reports_file, ground_truth_file, repo_path, codebase_dirs, git_branch, top_n_values):
    bug_reports = load_bug_reports(bug_reports_file)
    ground_truth = load_ground_truth(ground_truth_file)
    results = []

    for report in bug_reports:
        filename = report["filename"]
        creation_time = report["creation_time"]
        bug_report_json = report["stack_trace"]
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

            # Step 2: Prepare the corpus for LLM
            corpus = prepare_corpus_for_llm(relevant_files)
            # print("-------------------- Corpus (start) --------------------------")
            # print(corpus)
            # print("-------------------- Corpus (end) --------------------------")

            # Step 3: Perform semantic search and ranking with LLM
            ranked_files = perform_semantic_search(bug_report, corpus)
            # print("-------------------- ranked_files (start) --------------------------")
            # print(ranked_files)
            # print("-------------------- ranked_files (end) --------------------------")

            # Transform ranked files to ground truth format for comparison
            transformed_ranked_files = transform_ranked_files(ranked_files, codebase_dirs)
            # print("-------------------- transformed_ranked_files (start) --------------------------")
            # print(transformed_ranked_files)
            # print("-------------------- transformed_ranked_files (end) --------------------------")
            results.append((filename, transformed_ranked_files))

    return evaluate_metrics(results, ground_truth, top_n_values)


# Function to compare if a ranked file ends with any ground truth file
def match_ranked_to_ground_truth(ranked_file, ground_truth_files):
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

# Aggregate results across multiple repositories
# def aggregate_results(results_list, top_n_values):
#     total_reports = sum(result["total_reports"] for result in results_list)
#     overall_metrics = {"MAP": 0, "MRR": 0, "Top@N": {n: 0 for n in top_n_values}}

#     for result in results_list:
#         overall_metrics["MAP"] += sum(result["MAP"]) / len(result["MAP"]) * result["total_reports"]
#         overall_metrics["MRR"] += sum(result["MRR"]) / len(result["MRR"]) * result["total_reports"]
#         for n in top_n_values:
#             overall_metrics["Top@N"][n] += result["Top@N"][n]

#     overall_metrics["MAP"] /= total_reports
#     overall_metrics["MRR"] /= total_reports
#     for n in top_n_values:
#         overall_metrics["Top@N"][n] /= total_reports

#     return overall_metrics

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
    for n in top_n_values:
        print(f"Top-{n}: {overall_metrics['Top@N'][n]}")

    if total_reports > 0:
        overall_metrics["MAP"] /= total_reports
        overall_metrics["MRR"] /= total_reports
        for n in top_n_values:
            overall_metrics["Top@N"][n] /= total_reports

    return overall_metrics


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

    overall_metrics = aggregate_results(results_list, top_n_values)
    print("\nOverall Metrics:")
    print(f"Mean Average Precision (MAP): {overall_metrics['MAP']}")
    print(f"Mean Reciprocal Rank (MRR): {overall_metrics['MRR']}")
    for n in top_n_values:
        print(f"Top-{n} Accuracy: {overall_metrics['Top@N'][n]}")


# Example repository configuration and usage
bug_report_folder = 'stack_traces'
repositories = [
    {"bug_reports": f"{bug_report_folder}/Zookeeper.json", "ground_truth": "ground_truth/Zookeeper.json", "repo_path": "/Users/fahim/Desktop/PhD/Projects/zookeeper", "codebase_dir": ["/Users/fahim/Desktop/PhD/Projects/zookeeper/src/java/main", "/Users/fahim/Desktop/PhD/Projects/zookeeper/src/java/test"], "git_branch": 'master'},
    {"bug_reports": f"{bug_report_folder}/ActiveMQ.json", "ground_truth": "ground_truth/ActiveMQ.json", "repo_path": "/Users/fahim/Desktop/PhD/Projects/activemq", "codebase_dir": ["/Users/fahim/Desktop/PhD/Projects/activemq/activemq-client/src/main/java", "/Users/fahim/Desktop/PhD/Projects/activemq/activemq-core/src/main/java", "/Users/fahim/Desktop/PhD/Projects/activemq/activemq-broker/src/main/java", "/Users/fahim/Desktop/PhD/Projects/activemq/activemq-karaf/src/main/java", "/Users/fahim/Desktop/PhD/Projects/activemq/activemq-kahadb-store/src/main/java", "/Users/fahim/Desktop/PhD/Projects/activemq/activemq-optional/src/main/java"], "git_branch": 'main'},
    {"bug_reports": f"{bug_report_folder}/Hadoop.json", "ground_truth": "ground_truth/Hadoop.json", "repo_path": "/Users/fahim/Desktop/PhD/Projects/hadoop", "codebase_dir": ["/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-common/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-common/src/test/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/src/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/src/test/core", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-common/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-hdfs-project/hadoop-hdfs/src/main/java","/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-tools/hadoop-distcp/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-tools/hadoop-azure/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-nfs/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-auth/src/main/java"], "git_branch": 'trunk'},
    # {"bug_reports": f"{bug_report_folder}/HDFS.json", "ground_truth": "ground_truth/HDFS.json", "repo_path": "/Users/fahim/Desktop/PhD/Projects/hadoop-hdfs", "codebase_dir": ["/Users/fahim/Desktop/PhD/Projects/hadoop-hdfs/src/java"], "git_branch": 'trunk'},
    # {"bug_reports": f"{bug_report_folder}/Hive.json", "ground_truth": "ground_truth/Hive.json", "repo_path": "/Users/fahim/Desktop/PhD/Projects/hive", "codebase_dir": ["/Users/fahim/Desktop/PhD/Projects/hive"], "git_branch": 'master'},
    # {"bug_reports": f"{bug_report_folder}/MAPREDUCE.json", "ground_truth": "ground_truth/MAPREDUCE.json", "repo_path": "/Users/fahim/Desktop/PhD/Projects/hadoop-mapreduce", "codebase_dir": ["/Users/fahim/Desktop/PhD/Projects/hadoop-mapreduce/src/java"], "git_branch": 'trunk'},
    # {"bug_reports": f"{bug_report_folder}/Storm.json", "ground_truth": "ground_truth/Storm.json", "repo_path": "/Users/fahim/Desktop/PhD/Projects/storm", "codebase_dir": ["/Users/fahim/Desktop/PhD/Projects/storm/storm-client/src/jvm", "/Users/fahim/Desktop/PhD/Projects/storm/storm-server/src/main/java"], "git_branch": 'master'},
    # {"bug_reports": f"{bug_report_folder}/YARN.json", "ground_truth": "ground_truth/YARN.json", "repo_path": "/Users/fahim/Desktop/PhD/Projects/hadoop", "codebase_dir": ["/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-server/hadoop-yarn-server-resourcemanager/src/main/java"], "git_branch": 'trunk'},
    # Add all 8 repositories (hdfs, mapreduce - change dir | hive - find dir | Storm - add dir)
    # /Users/fahim/Desktop/PhD/Projects/storm/storm-client/src/jvm
    # /Users/fahim/Desktop/PhD/Projects/storm/storm-server/src/main/java
]

top_n_values = [1, 3, 5, 10]
process_repositories(repositories, top_n_values)
