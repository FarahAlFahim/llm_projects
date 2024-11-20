import json
import re

# Define a regex pattern to capture stack traces (adjust the pattern if needed)
# stack_trace_pattern = r'(?:\tat\s+[\w\.]+\(.*?\))+'
stack_trace_pattern = r'at\s+\S+\.\S+\s*\(.*\.java:\d*\)'

# Load the bug reports JSON file
input_file = "bug_reports_with_stack_traces.json"
output_file = "output_stack_traces.json"

# Read the input file
with open(input_file, 'r') as f:
    bug_reports = json.load(f)

# Process the bug reports and extract stack traces
output_data = []
for report in bug_reports:
    description = report.get("description", "")
    stack_traces = re.findall(stack_trace_pattern, description, re.DOTALL)
    stack_trace = "\n".join(stack_traces) if stack_traces else None
    
    output_data.append({
        "filename": report["filename"],
        "creation_time": report["creation_time"],
        "stack_trace": stack_trace,
        "description": report['description']
    })

# Save the extracted stack traces to the output file
with open(output_file, 'w') as f:
    json.dump(output_data, f, indent=4)

print(f"Stack traces extracted and saved to {output_file}")