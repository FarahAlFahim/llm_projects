# prompt templating and chaining
from langchain import PromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
import json



# template
template = '''
Summarize a bug report containing stack traces.

# Guidelines
- Extract key details from the bug report, including:
  - "BugID": The unique identifier for the bug (if available).
  - "Title": A brief and descriptive title of the issue.
  - "Description": A concise summary of the problem.
  - "StackTrace": Key stack trace information relevant to the bug.
  - "StepsToReproduce": A list of steps (if available) to replicate the issue.
  - "ExpectedBehavior": The intended or correct behavior of the system.
  - "ObservedBehavior": What actually happens when the bug occurs.
  - "Resolution": The resolution status or fix applied (if available).
- Emphasize details related to stack traces that can help in debugging or understanding the issue.
- Keep the summary concise but informative, focusing on relevant and actionable details.
- Omit redundant or irrelevant information.

# Steps
1. Identify and extract key sections of the bug report.
2. Parse and include stack trace details explicitly in the summary.
3. Format the output in JSON as per the specified structure.

# Output Format
The output should be structured in JSON format with the following fields:
```json
{{
    "BugID": "string or null",
    "Title": "string",
    "Description": "string",
    "StackTrace": "string or array of stack trace lines",
    "StepsToReproduce": ["step1", "step2", "..."] or null,
    "ExpectedBehavior": "string",
    "ObservedBehavior": "string",
    "Resolution": "string or null"
}}

You are given the bug report below:

{bug_report}
'''




prompt = PromptTemplate.from_template(template)
llm = ChatOpenAI(model='gpt-4o-mini', temperature = 0)

chain = LLMChain(llm=llm, prompt=prompt)



# Read developer written bug reports from JSON file
with open("developer_written_bug_reports/Zookeeper.json", "r") as file:
    dev_written_bug_report_data = json.load(file)

# Prepare the output format
output_data = []

for entry in dev_written_bug_report_data:
    filename = entry['filename']
    creation_time = entry['creation_time']
    dev_written_bug_report = entry['bug_report']
    
    # Generate summary of bug report
    bug_report_str = chain.run({'bug_report': dev_written_bug_report})
    print("--------------------------------------------------------------------")
    print(bug_report_str)
    print("--------------------------------------------------------------------")


    # Parse the bug report JSON from the generated string
    try:
        # Remove any markdown-style code block indicators (` ```json `) if present
        bug_report = json.loads(bug_report_str.replace("```json\n", "").replace("\n```", ""))
    except json.JSONDecodeError:
        print(f"Failed to parse JSON for filename: {filename}")
        continue  # Skip this entry if JSON parsing fails

    
    # Add to output data
    output_data.append({
        'filename': filename,
        'creation_time': creation_time,
        'bug_report': bug_report
    })

# Write the summarized bug reports to a new JSON file
output_file = 'summary_of_dev_written_bug_reports/Zookeeper.json'
with open(f"{output_file}", "w") as outfile:
    json.dump(output_data, outfile, indent=4)

print(f"Bug reports have been generated and saved to '{output_file}'")