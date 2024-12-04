# prompt templating and chaining
from langchain import PromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
import json



# template
template = '''
Generate an improved or enhanced bug report.

# Guidelines
- Analyze the provided bug report, focusing on the stack traces and corresponding source code.
- Use the provided source code, specifically the methods from the call graph (starting from the stack trace), to enhance or refine the bug report.
- Improve the report by:
  - Refining the title for clarity and precision.
  - Adding any missing or incomplete sections such as steps to reproduce, expected behavior, or observed behavior.
  - Ensuring that the stack trace is accurate and complete.
  - Clarifying any ambiguous descriptions or impacts of the bug.
  - Highlighting connections between stack trace details and the corresponding source code for deeper insights.
- Do not fabricate information; use placeholders (e.g., `[Provide additional details]`) for any unknown or unavailable data.

# Steps
1. Review the provided bug report to identify areas for improvement or enhancement.
2. Cross-reference the stack trace with the provided source code to identify relevant methods and clarify the root cause.
3. Refine the title to accurately summarize the bug.
4. Check and enhance each section:
   - Ensure steps to reproduce are clear and sequential, based on insights from the stack trace and code.
   - Clearly distinguish and articulate the expected versus observed behavior.
   - Present the stack trace in a complete and clean format.
5. If any information is missing or unclear, add placeholders indicating what needs to be provided.
6. Format the final enhanced bug report in JSON format.

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



# You are given the bug report below:

{bug_report}



# You are given the source code below:

{source_code}
'''




prompt = PromptTemplate.from_template(template)
llm = ChatOpenAI(model='gpt-4o-mini', temperature = 0)

chain = LLMChain(llm=llm, prompt=prompt)



# Read developer written bug reports and source code data from JSON file
with open("source_code_data/ActiveMQ.json", "r") as file:
    source_code_data = json.load(file)

# Prepare the output format
output_data = []

for entry in source_code_data:
    filename = entry['filename']
    creation_time = entry['creation_time']
    dev_written_bug_report = entry['bug_report']
    source_code = entry['source_code']
    
    # Generate improved bug report
    bug_report_str = chain.run({'bug_report': dev_written_bug_report, 'source_code': source_code})
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
output_file = 'bug_report_from_bugReport_sourceCode/ActiveMQ.json'
with open(f"{output_file}", "w") as outfile:
    json.dump(output_data, outfile, indent=4)

print(f"Bug reports have been generated and saved to '{output_file}'")