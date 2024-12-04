import os
import re
import ssl
import json
import subprocess
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import defaultdict
import networkx as nx
from nltk.tokenize import word_tokenize

# Set SSL context to fix SSL certificate issue with nltk.download()
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Download necessary resources
nltk.download("punkt")
nltk.download("stopwords")

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
            # print("################################")
            # print("File path: ", file_path)
            # print("codebase dir: ", codebase_dir)
            # print(relative_path.replace(os.sep, "."))
            # print("################################")
            return relative_path.replace(os.sep, ".")
    return None  # Handle files that don't match any directory

# Preprocess text: tokenization, stopword removal, stemming
def preprocess_text(text):
    from nltk.corpus import stopwords
    from nltk.stem import PorterStemmer

    stop_words = set(stopwords.words("english"))
    stemmer = PorterStemmer()
    tokens = word_tokenize(text)
    tokens = [stemmer.stem(word) for word in tokens if word.isalnum() and word not in stop_words]
    return " ".join(tokens)

# Compute VSM scores
def compute_vsm_scores(bug_report, source_files):
    vectorizer = TfidfVectorizer()
    documents = [preprocess_text(source) for source in source_files]
    bug_report_processed = preprocess_text(bug_report)
    # print("=========================================================")
    # print("TF-IDF Vectors Calculation:")
    # print(f"Bug Report Processed: {bug_report_processed}")
    # print(f"Documents Processed: {[doc[:50] for doc in documents]}")  # First 50 chars of each document
    tfidf_matrix = vectorizer.fit_transform([bug_report_processed] + documents)
    cosine_similarities = (tfidf_matrix[0] * tfidf_matrix[1:].T).toarray()
    # print("Cosine Similarities:")
    # print(cosine_similarities)
    # print("=========================================================")
    return cosine_similarities.flatten()

# Analyze logs for suspicious files
def analyze_logs(bug_report):
    log_scores = defaultdict(float)
    pattern = r"at (.+?)\((.+?):(\d+)\)"
    stack_trace = re.findall(pattern, bug_report)
    # print('-'*40)
    # print('stack trace: ', stack_trace)
    for i, (_, file_name, _) in enumerate(stack_trace):
        log_scores[file_name] += 1 / (i + 1)  # Higher weight for higher stack trace rank
    # print('log scores: ', log_scores)
    # print('-'*40)
    return log_scores


def build_dynamic_call_graph(codebase_dirs):
    if isinstance(codebase_dirs, str):  # Allow single directory for backward compatibility
        codebase_dirs = [codebase_dirs]

    call_graph = nx.DiGraph()  # Create directed graph

    for codebase_dir in codebase_dirs:
        # Traverse the codebase to read all Java files
        for root, _, files in os.walk(codebase_dir):
            for file in files:
                if file.endswith(".java"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()

                            # Use regex to find method calls, e.g., "ClassName.methodName("
                            # method_calls = re.findall(r"(\w+)\.\w+\(", content)
                            # method_calls = re.findall(r"(\w+)\.(\w+)\(", content)
                            # method_calls = re.findall(r"(\w+)\.(\w+)\([^\)]*\)", content)
                            method_calls = re.findall(r"(\w+)\.(\w+)\([^\)]*\);", content)
                            # print(f"Method Calls in {file}: {method_calls}")
                            # print(f"File content of {file}: {content}")

                            # Check how the edges are being added to the call graph
                            # print("Adding edges to the call graph:")
                            for called_class in method_calls:
                                called_file = os.path.join(root, f"{called_class}.java")

                                # If the called class exists as a file, add an edge to the call graph
                                if os.path.exists(called_file):
                                    call_graph.add_edge(file_path, called_file)
                                    # print(f"Added edge from {file_path} to {called_file}")

                    except Exception as e:
                        print(f"Error reading file {file_path}: {e}")
                    
    return call_graph



# Reconstruct execution paths using a call graph
def reconstruct_execution_paths(logs, source_files, codebase_dirs):
    # Build the call graph dynamically
    call_graph = build_dynamic_call_graph(codebase_dirs)
    # print("//////////////////////////////")
    # print("Call Graph:")
    # print(call_graph.edges())
    path_scores = defaultdict(float)
    for log in logs:
        match = re.search(r"(\w+)\.java", log)
        if match:
            file_name = match.group(1)
            for codebase_dir in codebase_dirs:
                file_path = os.path.join(codebase_dir, f"{file_name}.java")
                # file_path = os.path.abspath(file_path)  # Ensure absolute path

                # Debugging: Print the file path and call graph nodes
                # print(f"Checking if {file_path} exists in the graph...")
                # print("Call Graph Nodes:", list(call_graph.nodes()))

                # Initialize paths in case file is not found in the graph
                paths = {}

                if call_graph.has_node(file_path):
                    # Find all reachable nodes (shortest paths) from this file
                    # print(f"Node {file_path} found in the graph.")
                    paths = nx.single_source_shortest_path_length(call_graph, file_path)
                    print(f"Paths for {file_name}: {paths}")
                # else:
                #     print(f"Node {file_path} not found in the call graph.")

                # If paths exist, assign scores based on proximity
                if paths:
                    for node, length in paths.items():
                        path_scores[node] += 1 / (length + 1)
    # print("Path Scores:")
    # print(path_scores)
    # print("//////////////////////////////")
    return path_scores



def calculate_suspiciousness(vsm_scores, log_scores, path_scores, source_files):
    suspiciousness = {}
    file_list = [os.path.abspath(file) for file in source_files]  # Use full paths

    for i, file_path in enumerate(file_list):
        vsm_score = vsm_scores[i]
        log_score = log_scores.get(os.path.basename(file_path).replace(".java", ""), 0)
        path_score = path_scores.get(os.path.basename(file_path).replace(".java", ""), 0)

        suspiciousness[file_path] = (
            vsm_score * 0.5 +
            log_score * 0.3 +
            path_score * 0.2
        )
    return suspiciousness





# Rank suspicious files
def rank_suspicious_files(suspiciousness, source_files):
    file_list = [os.path.abspath(file) for file in source_files]  # Ensure full paths
    ranked = [(file_list[i], score) for i, score in enumerate(suspiciousness.values())]
    ranked_files = sorted(ranked, key=lambda x: x[1], reverse=True)
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

            # Extract components
            log_scores = analyze_logs(bug_report)
            
            # Prepare lists for file paths and file contents
            file_paths = []
            file_contents = []
            for codebase_dir in codebase_dirs:
                for root, _, files in os.walk(codebase_dir):
                    for file in files:
                        if file.endswith(".java"):
                            file_path = os.path.join(root, file)
                            file_paths.append(file_path)  # Store the file path
                            try:
                                with open(file_path, "r", encoding="utf-8") as f:
                                    content = f.read()
                                    file_contents.append(content)  # Store the file content
                            except Exception as e:
                                print(f"Error reading file {file_path}: {e}")
                                file_contents.append("")  # Add empty content if reading fails

            # Compute scores
            vsm_scores = compute_vsm_scores(bug_report, file_contents)
            path_scores = reconstruct_execution_paths(log_scores.keys(), file_paths, codebase_dirs)
            suspiciousness = calculate_suspiciousness(vsm_scores, log_scores, path_scores, file_paths)

            # Rank files and transform
            ranked_files = rank_suspicious_files(suspiciousness, file_paths)
            # print("--------------------- Ranked Files (with full paths): ------------------------")
            # for file, score in ranked_files:
            #     print(f"{file}: {score}")
            # print("--------------------- END Ranking ------------------------")
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
        # print("---------------------------- START ------------------------------")
        # print(f"\nFilename: {filename}")
        # print("Ground Truth Files:", ground_truth_files)
        # print("Transformed Ranked Files:", ranked_files)
        # print("---------------------------- END ------------------------------")

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

# Aggregate results across repositories
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
    

# Main function to process repositories
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

# Example repository configuration
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
    # Add all 8 repositories (hdfs, mapreduce - change dir | hive - find dir | Storm - add dir)
]

top_n_values = [1, 3, 5, 10]
process_repositories(repositories, top_n_values)
