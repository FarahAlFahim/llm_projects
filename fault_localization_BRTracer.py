import os
import re
import ssl
import json
import subprocess
import nltk
from collections import defaultdict
from nltk.tokenize import word_tokenize

# Set SSL context to fix SSL certificate issue with nltk.download()
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Download the punkt tokenizer for word_tokenize
nltk.download("punkt")

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
    # Ensure working directory is clean (optional)
    subprocess.run('git stash --include-untracked', shell=True, cwd=repo_path)
    # reset_command = 'git reset --hard'
    reset_command = f'git checkout {git_branch}'
    # if git_branch == "master":
    #     reset_command = 'git reset --hard'
    # else:
    #     reset_command = f'git checkout {git_branch}'
    subprocess.run(reset_command, shell=True, cwd=repo_path)
    checkout_command = f'git checkout {commit_version}'
    subprocess.run(checkout_command, shell=True, cwd=repo_path)
    
    

# Convert file path to ground truth format
def convert_to_ground_truth_format(file_path, codebase_dirs):
    for codebase_dir in codebase_dirs:
        if file_path.startswith(codebase_dir):
            relative_path = file_path.replace(codebase_dir + os.sep, "").replace(".java", "")
            return relative_path.replace(os.sep, ".")
    return None  # Handle files that don't match any directory

# Extract Stack Trace and Keywords
def extract_stack_trace(bug_report):
    pattern = r"at (.+?)\((.+?):(\d+)\)"
    stack_trace = re.findall(pattern, bug_report)
    return stack_trace

def extract_keywords(bug_report):
    words = word_tokenize(bug_report)
    keywords = [word.lower() for word in words if word.isalpha() and len(word) > 3]
    return keywords

# Search Codebase for Possible Matches with Keywords
def search_codebase(codebase_dirs, keywords):
    if isinstance(codebase_dirs, str):  # Allow single directory for backward compatibility
        codebase_dirs = [codebase_dirs]

    matches = defaultdict(list)
    for codebase_dir in codebase_dirs:
        for root, _, files in os.walk(codebase_dir):
            for file in files:
                if file.endswith(".java"):
                    file_path = os.path.join(root, file)
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        for keyword in keywords:
                            if keyword in content:
                                matches[file_path].append(keyword)
    return matches

# Rank Matches
def rank_matches(matched_files, stack_trace, codebase_dirs):
    file_scores = defaultdict(int)
    for file, keywords in matched_files.items():
        file_scores[file] += len(keywords)
    for class_name, file_name, line_number in stack_trace:
        package_path = os.sep.join(class_name.split('.')[:-1]) + ".java"
        for codebase_dir in codebase_dirs:
            full_path = os.path.join(codebase_dir, package_path)
            if full_path in file_scores:
                file_scores[full_path] += 5
    ranked_files = sorted(file_scores.items(), key=lambda x: x[1], reverse=True)
    return ranked_files

# Transform ranked files to match ground truth format
def transform_ranked_files(ranked_files, codebase_dirs):
    # print('-'*40)
    # print('Ranked files: ', ranked_files)
    # print('-'*40)
    return [convert_to_ground_truth_format(file, codebase_dirs) for file, _ in ranked_files]

# Perform fault localization for a single repository
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

            # Extract stack trace and keywords
            stack_trace = extract_stack_trace(bug_report)
            keywords = extract_keywords(bug_report)
            
            # Search and rank files
            matched_files = search_codebase(codebase_dirs, keywords)
            ranked_files = rank_matches(matched_files, stack_trace, codebase_dirs)
            
            # Transform ranked files to ground truth format for comparison
            transformed_ranked_files = transform_ranked_files(ranked_files, codebase_dirs)
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

        # Debugging: Print the ground truth and transformed ranked files
        print("---------------------------- START ------------------------------")
        print(f"\nFilename: {filename}")
        print("Ground Truth Files:", ground_truth_files)
        print("Transformed Ranked Files:", ranked_files)
        print("---------------------------- END ------------------------------")
        
        if not ground_truth_files:
            continue
        
        total_reports += 1
        relevant_found = 0
        precision_sum = 0
        relevant_within_top_n = {n: False for n in top_n_values}

        for rank, file in enumerate(ranked_files, start=1):
            # if file in ground_truth_files:
            # # Check if any ranked file ends with ground truth file (using endswith)
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
    # Print Top@N for each repo
    print(f"Final Top@N totals: {metrics['Top@N']}")
    return metrics

# Aggregate results across multiple repositories
def aggregate_results(results_list, top_n_values):
    total_reports = sum(result["total_reports"] for result in results_list)
    overall_metrics = {"MAP": 0, "MRR": 0, "Top@N": {n: 0 for n in top_n_values}}

    for result in results_list:
        overall_metrics["MAP"] += sum(result["MAP"]) / len(result["MAP"]) * result["total_reports"]
        overall_metrics["MRR"] += sum(result["MRR"]) / len(result["MRR"]) * result["total_reports"]
        for n in top_n_values:
            overall_metrics["Top@N"][n] += result["Top@N"][n]

    # Print Top@N accross all repositories
    print("\nTotal Top@N counts across all repositories (raw counts):")
    for n in top_n_values:
        print(f"Top-{n}: {overall_metrics['Top@N'][n]}")

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
bug_report_folder = 'bug_report_from_stackTrace_sourceCode'
repositories = [
    {"bug_reports": f"{bug_report_folder}/Zookeeper.json", "ground_truth": "ground_truth/Zookeeper.json", "repo_path": "/Users/fahim/Desktop/PhD/Projects/zookeeper", "codebase_dir": ["/Users/fahim/Desktop/PhD/Projects/zookeeper/src/java/main", "/Users/fahim/Desktop/PhD/Projects/zookeeper/src/java/test"], "git_branch": 'master'},
    {"bug_reports": f"{bug_report_folder}/ActiveMQ.json", "ground_truth": "ground_truth/ActiveMQ.json", "repo_path": "/Users/fahim/Desktop/PhD/Projects/activemq", "codebase_dir": ["/Users/fahim/Desktop/PhD/Projects/activemq/activemq-client/src/main/java", "/Users/fahim/Desktop/PhD/Projects/activemq/activemq-core/src/main/java", "/Users/fahim/Desktop/PhD/Projects/activemq/activemq-broker/src/main/java", "/Users/fahim/Desktop/PhD/Projects/activemq/activemq-karaf/src/main/java", "/Users/fahim/Desktop/PhD/Projects/activemq/activemq-kahadb-store/src/main/java", "/Users/fahim/Desktop/PhD/Projects/activemq/activemq-optional/src/main/java"], "git_branch": 'main'},
    {"bug_reports": f"{bug_report_folder}/Hadoop.json", "ground_truth": "ground_truth/Hadoop.json", "repo_path": "/Users/fahim/Desktop/PhD/Projects/hadoop", "codebase_dir": ["/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-common/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-common/src/test/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/src/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/src/test/core", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-common/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-hdfs-project/hadoop-hdfs/src/main/java","/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-tools/hadoop-distcp/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-tools/hadoop-azure/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-nfs/src/main/java", "/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-common-project/hadoop-auth/src/main/java"], "git_branch": 'trunk'},
    # {"bug_reports": f"{bug_report_folder}/HDFS.json", "ground_truth": "ground_truth/HDFS.json", "repo_path": "/Users/fahim/Desktop/PhD/Projects/hadoop-hdfs", "codebase_dir": ["/Users/fahim/Desktop/PhD/Projects/hadoop-hdfs/src/java"], "git_branch": 'trunk'},
    # {"bug_reports": f"{bug_report_folder}/Hive.json", "ground_truth": "ground_truth/Hive.json", "repo_path": "/Users/fahim/Desktop/PhD/Projects/hive", "codebase_dir": ["/Users/fahim/Desktop/PhD/Projects/hive"], "git_branch": 'master'},
    # {"bug_reports": f"{bug_report_folder}/MAPREDUCE.json", "ground_truth": "ground_truth/MAPREDUCE.json", "repo_path": "/Users/fahim/Desktop/PhD/Projects/hadoop-mapreduce", "codebase_dir": ["/Users/fahim/Desktop/PhD/Projects/hadoop-mapreduce/src/java"], "git_branch": 'trunk'},
    # {"bug_reports": f"{bug_report_folder}/Storm.json", "ground_truth": "ground_truth/Storm.json", "repo_path": "/Users/fahim/Desktop/PhD/Projects/storm", "codebase_dir": ["/Users/fahim/Desktop/PhD/Projects/storm/storm-client/src/jvm", "/Users/fahim/Desktop/PhD/Projects/storm/storm-server/src/main/java"], "git_branch": 'master'},
    # {"bug_reports": f"{bug_report_folder}/YARN.json", "ground_truth": "ground_truth/YARN.json", "repo_path": "/Users/fahim/Desktop/PhD/Projects/hadoop", "codebase_dir": ["/Users/fahim/Desktop/PhD/Projects/hadoop/hadoop-yarn-project/hadoop-yarn/hadoop-yarn-server/hadoop-yarn-server-resourcemanager/src/main/java"], "git_branch": 'trunk'},
    # Add all 8 repositories
]

top_n_values = [1, 3, 5, 10]
process_repositories(repositories, top_n_values)
