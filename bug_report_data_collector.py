import os
import re
import json
from datetime import datetime

# Regex pattern to identify stack traces
# STACK_TRACE_PATTERN = r'(\bat\b|\bException\b|\bError\b|Caused by:).+' # 10640
# STACK_TRACE_PATTERN = r'(\bException\b|\bError\b|Caused by:|\bat\b)\s.*(\n\s+at\s.*)+' # No stack Trace
# STACK_TRACE_PATTERN = r'(?i)(\b(?:Exception|Error)\b.*|Caused by:.*|at\s+\S+\.\S+\(.*?\))' # 12644
# STACK_TRACE_PATTERN = r'(?i)(?:(?:\b(?:Exception|Error)\b.*|\bCaused by\b.*|\bat\s+\S+\.\S+\s*\(.*?\))(\n\s+at\s+\S+\.\S+\(.*?\))*' # Cannot read
# STACK_TRACE_PATTERN = r'(?i)(\b(?:Exception|Error|Caused by):?.*|\bat\s+\S+\.\S+\s*\(.*?\))' # 12667
# STACK_TRACE_PATTERN = r'(?i)(\b(?:Exception|Error|Caused by):?.*|\bat\s+\S+\.\S+\s*\(.*?\))|(\bat\s+\S+\.\S+\s*\(.*?\))' # 12667
STACK_TRACE_PATTERN = r'at\s+\S+\.\S+\s*\(.*\.java:\d*\)'




# Path to the main bug reports folder of Pathidea_Data
REPO_PATH = '/Users/fahim/Desktop/PhD/Projects/Pathidea_Data/bug_reports/Zookeeper'


# Function to check if bug report meets criteria
from datetime import datetime

def meets_criteria(data):
    # Check if 'fields' is present and valid
    fields = data.get("fields")
    if not fields:
        return False

    # Safely access 'resolution' field and check its 'name'
    resolution = fields.get("resolution")
    if not resolution or resolution.get("name") not in ["Resolved", "Fixed"]:
        return False

    # Safely access 'priority' field and check its 'name'
    priority = fields.get("priority")
    if not priority or priority.get("name") not in ["Major", "Critical", "Blocker"]:
        return False

    # Check the 'created' field and ensure it is 2010 or later
    created_date_str = fields.get("created")
    if created_date_str:
        try:
            created_date = datetime.fromisoformat(created_date_str.replace("Z", "+00:00"))
            if created_date.year < 2010:
                return False
        except ValueError:
            print(f"Warning: Invalid date format in 'created' field: {created_date_str}")
            return False
    else:
        return False

    return True





# Function to recursively scan JSON files for stack traces
def get_bug_reports_with_stack_traces(path, excluded_folders):
    bug_reports = []

    for root, dirs, files in os.walk(path):
        # Exclude specified folders from the traversal
        dirs[:] = [d for d in dirs if d not in excluded_folders]

        for filename in files:
            file_path = os.path.join(root, filename)

            # Check if the file is a JSON file
            if file_path.endswith('.json'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                        content = json.dumps(data)
                        # content = file.read()  # Read the raw content as text
                        if re.search(STACK_TRACE_PATTERN, content) and meets_criteria(data):
                            bug_reports.append({
                                'filename': filename,
                                # 'path': file_path,
                                'content': data 
                            })

                # except Exception as e:
                #     print(f"Warning: Could not read file {file_path}. Error: {e}")
                except json.JSONDecodeError as e:
                    print(f"Warning: Could not decode JSON in file {file_path}. Error: {e}")

    return bug_reports

# Main function
def main():
    excluded_folders = ['comments', 'details']  # Replace with actual folder names to exclude
    # Get bug reports with stack traces
    bug_reports = get_bug_reports_with_stack_traces(REPO_PATH, excluded_folders)

    if bug_reports:
        print(f"Found {len(bug_reports)} JSON files with stack traces meeting criteria.")

        # Save the results to a text file
        with open("bug_reports_with_stack_traces.json", "w", encoding='utf-8') as f:
            json.dump(bug_reports, f, indent=4)
            # for report in bug_reports:
            #     f.write(f"{report['filename']} - {report['path']}\n")
        
        print("Bug reports with stack traces saved to 'bug_reports_with_stack_traces.json'.")
    else:
        print('No JSON files with stack traces found.')

if __name__ == '__main__':
    main()