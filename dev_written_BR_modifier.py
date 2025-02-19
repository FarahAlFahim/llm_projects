import json
import os

def modify_bug_reports(input_file, output_file):
    # Ensure the output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Read the input JSON file
    with open(input_file, 'r', encoding='utf-8') as f:
        bug_reports = json.load(f)
    
    modified_reports = []
    
    for report in bug_reports:
        bug_report = report.get("bug_report")
        modified_report = {
            "filename": report.get("filename"),
            "creation_time": report.get("creation_time"),
            "bug_report": {
                "Title": bug_report["fields"].get("summary"),
                "Description": bug_report["fields"].get("description")
            }
        }
        modified_reports.append(modified_report)
    
    # Write the modified bug reports to the output file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(modified_reports, f, indent=4)

# File paths
input_file = "developer_written_bug_reports/Zookeeper.json"
output_file = "modified_dev_written_bug_reports/Zookeeper.json"

# Process the bug reports
modify_bug_reports(input_file, output_file)
print(f"Results saved to {output_file}")
