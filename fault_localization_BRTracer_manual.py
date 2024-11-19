import os
import re
import ssl
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
nltk.download("punkt_tab")

# Example bug report with a stack trace and keywords
bug_report = '''{
    "title": "NullPointerException in QuorumPeer.setQuorumVerifier",
    "description": {
        "stepsToReproduce": [
            "1. Start the ZooKeeper server with a quorum configuration.",
            "2. Attempt to set a quorum verifier using the QuorumPeer instance.",
            "3. Observe the server logs for any exceptions."
        ],
        "actualBehavior": "The server throws a NullPointerException when trying to set the quorum verifier.",
        "possibleCause": "It is possible that the quorum verifier being passed to the setQuorumVerifier method is null, leading to the NullPointerException."
    },
    "stackTrace": "java.lang.NullPointerException\n\tat org.apache.zookeeper.server.quorum.QuorumPeer.setQuorumVerifier(QuorumPeer.java:1320)\n\tat org.apache.zookeeper.server.quorum.QuorumPeerMain.runFromConfig(QuorumPeerMain.java:156)\n\tat org.apache.curator.test.TestingZooKeeperServer$1.run(TestingZooKeeperServer.java:134)\n\tat java.lang.Thread.run(Thread.java:722)"
}'''

# Step 1: Extract Stack Trace and Keywords
def extract_stack_trace(bug_report):
    pattern = r"at (.+?)\((.+?):(\d+)\)"
    stack_trace = re.findall(pattern, bug_report)
    return stack_trace  # Returns list of tuples (class, file, line number)

def extract_keywords(bug_report):
    words = word_tokenize(bug_report)
    keywords = [word.lower() for word in words if word.isalpha() and len(word) > 3]
    return keywords

stack_trace = extract_stack_trace(bug_report)
keywords = extract_keywords(bug_report)

print("##################################################################################")
print("Stack Trace:", stack_trace)
print("##################################################################################")
print("Keywords:", keywords)

# Step 2: Search Codebase for Possible Matches with Keywords
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

# Example codebase directory (replace with your actual codebase directory path)
codebase_dir = "/Users/fahim/Desktop/PhD/Projects/zookeeper/src/java/main"

# Find files in codebase that match keywords
matched_files = search_codebase(codebase_dir, keywords)

print("##################################################################################")
print("\nMatched Files and Keywords:")
for file, keywords in matched_files.items():
    print(f"{file}: {keywords}")

# Step 3: Rank Matches (Simple Scoring based on keyword frequency and stack trace relevance)
def rank_matches(matched_files, stack_trace, codebase_dir):
    file_scores = defaultdict(int)
    
    # Increase score based on keyword matches in matched files
    for file, keywords in matched_files.items():
        file_scores[file] += len(keywords)
    
    # Increase score based on stack trace line matches
    for class_name, file_name, line_number in stack_trace:
        # Construct the full path using the package path method
        package_path = os.sep.join(class_name.split('.')[:-1]) + ".java"
        full_path = os.path.join(codebase_dir, package_path)
        
        # Add a score for matching the stack trace line in the codebase
        if full_path in file_scores:
            file_scores[full_path] += 5  # Higher weight for stack trace matches

    # Sort files by score
    ranked_files = sorted(file_scores.items(), key=lambda x: x[1], reverse=True)
    return ranked_files


ranked_files = rank_matches(matched_files, stack_trace, codebase_dir)

print("##################################################################################")
print("\nRanked Matches with Fault Localization:")
for file, score in ranked_files:
    print(f"{file} - Score: {score}")

# Step 4: Trace Stack Trace Line Numbers
def trace_stack_trace(stack_trace, codebase_dir):
    line_matches = []
    for class_name, file_name, line_number in stack_trace:
        # Remove the method name and construct the package path
        package_path = os.sep.join(class_name.split('.')[:-1]) + ".java"
        
        # Construct the full path based on codebase_dir and package_path
        full_path = os.path.join(codebase_dir, package_path)
        
        # Debug output to check if paths are being formed correctly
        print("##################################################################################")
        print(f"Checking path: {full_path}")
        
        if os.path.exists(full_path):
            line_matches.append((full_path, int(line_number)))
        else:
            print("##################################################################################")
            print(f"File {full_path} not found.")
    return line_matches



line_matches = trace_stack_trace(stack_trace, codebase_dir)
print("##################################################################################")
print("\nLine Matches from Stack Trace:")
for file, line in line_matches:
    print(f"{file} - Line {line}")


print("----- END -----")
