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
    # subprocess.run('git stash --include-untracked', shell=True, cwd=repo_path)
    checkout_command = f'git checkout {commit_version}'
    subprocess.run(checkout_command, shell=True, cwd=repo_path)
    if git_branch == "master":
        reset_command = 'git reset --hard'
    else:
        reset_command = f'git checkout {git_branch}'
    subprocess.run(reset_command, shell=True, cwd=repo_path)
    

# Convert file path to ground truth format
def convert_to_ground_truth_format(file_path, codebase_dir):
    relative_path = file_path.replace(codebase_dir + os.sep, "").replace(".java", "")
    return relative_path.replace(os.sep, ".")

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
def search_codebase(codebase_dir, keywords):
    matches = defaultdict(list)
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
def rank_matches(matched_files, stack_trace, codebase_dir):
    file_scores = defaultdict(int)
    for file, keywords in matched_files.items():
        file_scores[file] += len(keywords)
    for class_name, file_name, line_number in stack_trace:
        package_path = os.sep.join(class_name.split('.')[:-1]) + ".java"
        full_path = os.path.join(codebase_dir, package_path)
        if full_path in file_scores:
            file_scores[full_path] += 5
    ranked_files = sorted(file_scores.items(), key=lambda x: x[1], reverse=True)
    return ranked_files

# Transform ranked files to match ground truth format
def transform_ranked_files(ranked_files, codebase_dir):
    return [convert_to_ground_truth_format(file, codebase_dir) for file, _ in ranked_files]

# Perform fault localization for a single repository
def perform_fault_localization_single_repo(bug_reports_file, ground_truth_file, repo_path, codebase_dir, git_branch, top_n_values):
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
            matched_files = search_codebase(codebase_dir, keywords)
            ranked_files = rank_matches(matched_files, stack_trace, codebase_dir)
            
            # Transform ranked files to ground truth format for comparison
            transformed_ranked_files = transform_ranked_files(ranked_files, codebase_dir)
            results.append((filename, transformed_ranked_files))
    
    return evaluate_metrics(results, ground_truth, top_n_values)

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
            if file in ground_truth_files:
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
bug_report_folder = 'developer_written_bug_reports'
repositories = [
    {"bug_reports": f"{bug_report_folder}/Zookeeper.json", "ground_truth": "ground_truth/Zookeeper.json", "repo_path": "/Users/fahim/Desktop/PhD/Projects/zookeeper", "codebase_dir": "/Users/fahim/Desktop/PhD/Projects/zookeeper/src/java/main", "git_branch": 'master'},
    {"bug_reports": f"{bug_report_folder}/ActiveMQ.json", "ground_truth": "ground_truth/ActiveMQ.json", "repo_path": "/Users/fahim/Desktop/PhD/Projects/activemq", "codebase_dir": "/Users/fahim/Desktop/PhD/Projects/activemq/activemq-client/src/main/java", "git_branch": 'main'},
    # Add all 8 repositories
]

top_n_values = [1, 3, 5, 10]
process_repositories(repositories, top_n_values)