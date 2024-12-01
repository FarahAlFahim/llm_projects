# prompt templating and chaining
from langchain import PromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
import json



# template
template = '''
Enhance or improve a bug report containing stack traces.

# Guidelines
- Analyze the provided bug report to identify incomplete, unclear, or missing details.
- Improve the bug report by:
  - Refining the title for clarity and conciseness.
  - Adding any missing sections such as steps to reproduce, expected behavior, or observed behavior if not included.
  - Ensuring the stack trace is complete and formatted properly.
  - Clarifying ambiguous descriptions or impacts of the bug.
- Do not fabricate information; use placeholders (e.g., `[Provide additional details]`) for unknown or unavailable data.

# Steps
1. Review the provided bug report to identify areas for improvement.
2. Refine the title to succinctly summarize the issue.
3. Check and enhance each section:
   - Ensure steps to reproduce are clear and sequential.
   - Verify expected behavior and observed behavior fields are filled and clearly distinguished.
   - Format and present the stack trace cleanly.
4. If the original bug report lacks certain details, add placeholders indicating what information is needed.
5. Format the enhanced bug report in JSON.

# Output Format
The output should be structured in JSON format with the following fields:
```json
{{
    "BugID": "string or null",
    "Title": "string",
    "Description": "string",
    "StackTrace": "string or array of stack trace lines",
    "StepsToReproduce": ["string", "..."] or null,
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
with open("developer_written_bug_reports/ActiveMQ.json", "r") as file:
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
output_file = 'llm_enhanced_bug_reports/ActiveMQ.json'
with open(f"{output_file}", "w") as outfile:
    json.dump(output_data, outfile, indent=4)

print(f"Bug reports have been generated and saved to '{output_file}'")