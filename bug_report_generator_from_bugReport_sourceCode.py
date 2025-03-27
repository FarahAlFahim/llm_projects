# prompt templating and chaining
from langchain import PromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
import json



# # template for three fields
# template = '''
# Generate an enhanced bug report by analyzing stack traces and source code to diagnose the root cause and suggest possible fixes.

# # Guidelines
# - Act as an intelligent assistant specialized in bug report analysis.
# - Given an initial bug report containing stack traces and source code methods:
#   - Extract stack traces from the `Description` field and place them in the `StackTrace` field.
#   - Enhance the `Title` and `Description` using insights from the provided source code.
#   - The `Description` should:
#     - Clearly explain the root cause of the bug.
#     - Optionally suggest potential fixes if applicable.
# - The source code consists of methods related to call dependencies within the stack traces.

# # Steps
# 1. **Extract Stack Traces**:
#    - Identify and remove stack traces from the `Description` field.
#    - Store the extracted stack traces in the `StackTrace` field.

# 2. **Analyze Source Code**:
#    - Examine the provided source code methods.
#    - Determine their relevance to the stack traces and how they contribute to the bug.
#    - Use this analysis to enhance the `Description` with details about the root cause and potential fixes.

# 3. **Refine the Title and Description**:
#    - The `Title` should succinctly capture the bug's main issue.
#    - The `Description` should provide a concise yet detailed explanation of the bug, its root cause, and possible fixes.

# 4. **Output the Enhanced Bug Report**:
#    - Format the output as JSON.

# # Output Format
# Output a structured JSON with the following fields:
# ```json
# {{
#     "Title": "string",
#     "Description": "string",
#     "StackTrace": ["string", "..."]
# }}



# # You are given the bug report below:

# {bug_report}



# # You are given the source code methods below:

# {source_code}
# '''



# # template for four fields
# template = """
# Generate an enhanced bug report by analyzing stack traces and source code to diagnose the root cause and suggest possible fixes.

# # Guidelines
# - Act as an intelligent assistant specializing in bug report analysis.
# - Given an initial bug report containing stack traces and source code methods:
#   - Extract stack traces from the `Description` field and place them in the `StackTrace` field.
#   - Enhance the `Title`, `Description`, and `Resolution` using insights from the provided source code.
#   - The `Description` should:
#     - Clearly explain the root cause of the bug.
#   - The `Resolution` should:
#     - Provide possible fixes or mitigation strategies.
# - The source code consists of methods related to call dependencies within the stack traces.

# # Steps
# 1. **Extract Stack Traces**:
#    - Identify and remove stack traces from the `Description` field.
#    - Store the extracted stack traces in the `StackTrace` field.

# 2. **Analyze Source Code**:
#    - Examine the provided source code methods.
#    - Determine their relevance to the stack traces and how they contribute to the bug.
#    - Use this analysis to enhance the `Description` with details about the root cause.

# 3. **Enhance the Title, Description, and Resolution**:
#    - The `Title` should succinctly describe the bug's main issue.
#    - The `Description` should provide a clear explanation of the bug and its root cause.
#    - The `Resolution` should offer possible fixes or mitigation strategies.

# 4. **Output the Enhanced Bug Report**:
#    - Format the output as JSON.

# # Output Format
# Output a structured JSON with the following fields:
# ```json
# {{
#     "Title": "string",
#     "Description": "string",
#     "StackTrace": ["string", "..."],
#     "Resolution": "string"
# }}



# # You are given the bug report below:

# {bug_report}



# # You are given the source code methods below:

# {source_code}
# """



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
# input_file = "source_code_data/Modified_dev_written_BR/MAPREDUCE.json"
# output_file = "bug_report_from_modified_bugReport_sourceCode/YARN.json"
# output_file = "bug_report_from_modified_bugReport_sourceCode/title_desc_stackTrace/MAPREDUCE.json"

input_file = "test.json"
output_file = "test_output.json"


with open(input_file, "r") as file:
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
    # print("--------------------------------------------------------------------")
    # print(bug_report_str)
    # print("--------------------------------------------------------------------")


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

    # Write to output file after each bug report
    with open(output_file, "w") as outfile:
        json.dump(output_data, outfile, indent=4)
    print(f"Progress saved to {output_file}")


# # Write the summarized bug reports to a new JSON file
# with open(f"{output_file}", "w") as outfile:
#     json.dump(output_data, outfile, indent=4)

print(f"Bug reports have been generated and saved to '{output_file}'")