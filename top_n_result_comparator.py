import json

def match_ranked_to_ground_truth(ranked_file, ground_truth_files):
    """
    Function to check if the ranked file is in the ground truth.
    """
    for ground_truth_file in ground_truth_files:
        if ground_truth_file.endswith(ranked_file):
            return True
    return False

def process_file(file_path):
    """
    Process a JSON file and return a dictionary with filename and Top@1 match status.
    """
    results = {}
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Ignore the last item
    data = data[:-1] if data else []
    
    for item in data:
        filename = item.get("filename")
        ranked_files = item.get("transformed_ranked_methods", [])
        ground_truth = item.get("ground_truth", [])
        
        top_1 = ranked_files[0] if ranked_files else ""
        # print('top_1:', top_1)
        match_result = match_ranked_to_ground_truth(top_1, ground_truth) if top_1 else False
        
        if filename:
            results[filename] = match_result
    
    return results

def generate_summary(agent_file, dev_file, output_file):
    """
    Generate the result summary file.
    """
    agent_results = process_file(agent_file)
    dev_results = process_file(dev_file)
    # print("agent_results:", agent_results)
    # print("dev_results:", dev_results)
    
    summary = []
    filenames = set(agent_results.keys()).union(set(dev_results.keys()))
    # print('filenames:', filenames)
    
    for filename in filenames:
        agent_match = agent_results.get(filename, False)
        dev_match = dev_results.get(filename, False)
        summary.append({
            "filename": filename,
            "agentBased_bug_report_from_bugReport_sourceCode": agent_match,
            "developer_written_bug_reports": dev_match,
            "both": agent_match and dev_match
        })
    
    with open(output_file, 'w') as f:
        json.dump(summary, f, indent=4)

# File paths
agent_file = "results/method_level/BM25/agentBased_bug_report_from_bugReport_sourceCode.json"
dev_file = "results/method_level/BM25/developer_written_bug_reports.json"
output_file = "results/method_level/BM25/result_summary_dev_vs_agent.json"

# agent_file = "test.json"
# dev_file = "test_output.json"

generate_summary(agent_file, dev_file, output_file)
