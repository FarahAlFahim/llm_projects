import json

# Load JSON files
with open("bug_report_from_bugReport_sourceCode/Hadoop.json", "r") as f1, open("source_code_data/Hadoop.json", "r") as f2:
    data1 = json.load(f1)  # 124 items
    data2 = json.load(f2)  # 126 items

# Extract filenames
filenames1 = {d["filename"] for d in data1}
filenames2 = {d["filename"] for d in data2}

# Find missing filenames
missing_in_data1 = filenames2 - filenames1  # Files present in data2 but missing in data1
missing_in_data2 = filenames1 - filenames2  # Files present in data1 but missing in data2

print("Missing in bug_report_from_stackTrace_sourceCode/Hive.json:", missing_in_data1)
print("Missing in source_code_data/Hive.json:", missing_in_data2)
