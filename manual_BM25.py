import os
import re
import ssl
import json
import subprocess
import nltk
from collections import defaultdict
from nltk.tokenize import word_tokenize
from rank_bm25 import BM25Okapi

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

# Set the repository path
# repo_path = '/Users/fahim/Desktop/PhD/Projects/zookeeper'
repo_path = '/Users/fahim/Desktop/PhD/Projects/activemq'

# Get the commit version before a specific timestamp
def get_commit_version(creation_time):
    command = f'git rev-list -n 1 --before="{creation_time}" main'
    result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=repo_path)
    commit_version = result.stdout.strip()
    return commit_version

# Checkout to the specific commit version
def checkout_to_commit(commit_version):
    checkout_command = f'git checkout {commit_version}'
    subprocess.run(checkout_command, shell=True, cwd=repo_path)
    # reset_command = 'git reset --hard'
    reset_command = 'git checkout main'
    subprocess.run(reset_command, shell=True, cwd=repo_path)
    

# Add this function to tokenize and preprocess file content
def preprocess_text(text):
    tokens = word_tokenize(text.lower())
    return [token for token in tokens if token.isalnum()]

# Step 2: Index the codebase files using BM25
def index_codebase_with_bm25(codebase_dir):
    corpus = []
    file_list = []

    for root, _, files in os.walk(codebase_dir):
        for file in files:
            if file.endswith(".java"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        tokens = preprocess_text(content)
                        if tokens:  # Ensure tokens list is not empty
                            corpus.append(tokens)
                            file_list.append(file_path)
                except Exception as e:
                    print(f"Error reading file {file_path}: {e}")

    if not corpus:
        raise ValueError(f"No valid .java files found in {codebase_dir}. Ensure the directory contains non-empty .java files.")

    bm25 = BM25Okapi(corpus)
    return bm25, file_list


# Extract stack trace from the bug report
def extract_stack_trace(bug_report):
    pattern = r"at (.+?)\((.+?):(\d+)\)"
    stack_trace = re.findall(pattern, bug_report)
    print('stack trace:', stack_trace)
    return stack_trace

# Extract keywords from the bug report
def extract_keywords(bug_report):
    words = word_tokenize(bug_report)
    keywords = [word.lower() for word in words if word.isalpha() and len(word) > 3]
    print('keywords:', keywords)
    return keywords

# Rank files using BM25 and stack trace bonus
def rank_files_with_bm25(bm25, file_list, keywords, stack_trace, codebase_dir):
    query = preprocess_text(" ".join(keywords))
    scores = bm25.get_scores(query)
    
    # Combine BM25 scores with stack trace heuristic
    file_scores = {file: score for file, score in zip(file_list, scores)}
    
    for class_name, file_name, line_number in stack_trace:
        package_path = os.sep.join(class_name.split('.')[:-1]) + ".java"
        full_path = os.path.join(codebase_dir, package_path)
        if full_path in file_scores:
            file_scores[full_path] += 5  # Stack trace heuristic bonus

    # Rank files by combined scores
    ranked_files = sorted(file_scores.items(), key=lambda x: x[1], reverse=True)
    return ranked_files

# Convert file path to ground truth format
def convert_to_ground_truth_format(file_path, codebase_dir):
    relative_path = file_path.replace(codebase_dir + os.sep, "").replace(".java", "")
    return relative_path.replace(os.sep, ".")

# Transform ranked files to ground truth format
def transform_ranked_files(ranked_files, codebase_dir):
    return [convert_to_ground_truth_format(file, codebase_dir) for file, _ in ranked_files]

# Main function to perform fault localization
def perform_fault_localization_with_bm25(bug_reports_file, ground_truth_file):
    bug_reports = load_bug_reports(bug_reports_file)
    ground_truth = load_ground_truth(ground_truth_file)
    results = []

    for report in bug_reports:
        filename = report["filename"]
        creation_time = report["creation_time"]
        bug_report_json = report["bug_report"]
        bug_report = convert_bug_report_to_string(bug_report_json)

        # Get commit version and checkout
        commit_version = get_commit_version(creation_time)
        if commit_version:
            checkout_to_commit(commit_version)
            # codebase_dir = "/Users/fahim/Desktop/PhD/Projects/zookeeper/src/java/main"
            codebase_dir = "/Users/fahim/Desktop/PhD/Projects/activemq/activemq-client/src/main/java"

            # Index the repository files with BM25
            bm25, file_list = index_codebase_with_bm25(codebase_dir)

            # Extract stack trace and keywords
            stack_trace = extract_stack_trace(bug_report)
            keywords = extract_keywords(bug_report)

            # Rank files using BM25
            ranked_files = rank_files_with_bm25(bm25, file_list, keywords, stack_trace, codebase_dir)

            # Transform ranked files to ground truth format for comparison
            transformed_ranked_files = transform_ranked_files(ranked_files, codebase_dir)
            results.append((filename, transformed_ranked_files))
    
    evaluate_metrics(results, ground_truth)

# Evaluation function for MAP, MRR, and Top N scores
def evaluate_metrics(results, ground_truth, top_n=10):
    avg_precision_scores = []
    reciprocal_ranks = []
    top_n_hits = 0
    total_reports = 0

    for filename, ranked_files in results:
        ground_truth_files = ground_truth.get(filename, [])

        # Debugging: Print the ground truth and transformed ranked files
        print("---------------------------- START ------------------------------")
        print(f"\nFilename: {filename}")
        print("Ground Truth Files:", ground_truth_files)
        print("Transformed Ranked Files:", ranked_files)
        print("---------------------------- END ------------------------------")

        # Skip if there is no ground truth for this report
        if not ground_truth_files:
            continue
        
        total_reports += 1

        # Calculate precision for each relevant file
        relevant_found = 0
        precision_sum = 0
        relevant_within_top_n = False

        for rank, file in enumerate(ranked_files, start=1):
            if file in ground_truth_files:
                relevant_found += 1
                precision_sum += relevant_found / rank
                if relevant_found == 1:
                    reciprocal_ranks.append(1 / rank)
                # Check for Top-N hits, only count once per report
                if rank <= top_n and not relevant_within_top_n:
                    top_n_hits += 1
                    relevant_within_top_n = True

        avg_precision = precision_sum / relevant_found if relevant_found > 0 else 0
        avg_precision_scores.append(avg_precision)

    # Calculate MAP and MRR
    map_score = sum(avg_precision_scores) / len(avg_precision_scores) if avg_precision_scores else 0
    mrr_score = sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0

    # Calculate Top-N accuracy
    top_n_accuracy = top_n_hits / total_reports if total_reports else 0

    # Print the evaluation metrics
    print("\nEvaluation Metrics:")
    print("Mean Average Precision (MAP):", map_score)
    print("Mean Reciprocal Rank (MRR):", mrr_score)
    print(f"Top-{top_n} Accuracy:", top_n_accuracy)

# Example usage
perform_fault_localization_with_bm25("llm_generated_bug_reports/ActiveMQ.json", "ground_truth/ActiveMQ.json")