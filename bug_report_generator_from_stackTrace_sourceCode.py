# prompt templating and chaining
from langchain import PromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
import json



# template
template = '''
Generate a bug report based on stack traces and source code.

# Guidelines
- Utilize the provided stack traces and source code to create a detailed and structured bug report.
- Analyze the stack trace to identify the root cause and trace relevant methods from the call graph in the source code.
- Structure the bug report with clear sections including:
  - A concise and descriptive title.
  - A detailed description of the bug.
  - A cleanly formatted and complete stack trace.
  - Clear steps to reproduce the issue (if deducible from the stack trace and code).
  - Expected behavior versus observed behavior.
  - Any additional relevant details derived from the source code.
- Use placeholders (e.g., `[Provide additional details]`) for unknown or unavailable information to maintain clarity.

# Steps
1. Analyze the stack trace to determine the root cause and context of the bug.
2. Explore the source code methods involved in the stack trace, noting their role in the issue.
3. Create a concise title summarizing the bug.
4. Develop a structured bug report, ensuring:
   - Key details are included and properly organized.
   - All sections are completed or contain placeholders for missing information.
5. Format the final bug report in JSON.

# Output Format
The output should be structured in JSON format with the following fields:

```json
{{
    "Title": "string",
    "Description": "string",
    "StackTrace": "string or array of stack trace lines",
    "StepsToReproduce": ["string", "..."] or null,
    "ExpectedBehavior": "string",
    "ObservedBehavior": "string",
    "AdditionalDetails": "string or null"
}}




# You are given the stack traces below:

{stack_trace}



# You are given the source code below:

{source_code}
'''




prompt = PromptTemplate.from_template(template)
llm = ChatOpenAI(model='gpt-4o-mini', temperature = 0)

chain = LLMChain(llm=llm, prompt=prompt)



# Read developer written bug reports and source code data from JSON file
with open("source_code_data/Storm.json", "r") as file:
    source_code_data = json.load(file)

# Prepare the output format
output_data = []

for entry in source_code_data:
    filename = entry['filename']
    creation_time = entry['creation_time']
    stack_trace = entry['stack_trace']
    source_code = entry['source_code']
    
    # Generate improved bug report
    bug_report_str = chain.run({'stack_trace': stack_trace, 'source_code': source_code})
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
output_file = 'bug_report_from_stackTrace_sourceCode/Storm.json'
with open(f"{output_file}", "w") as outfile:
    json.dump(output_data, outfile, indent=4)

print(f"Bug reports have been generated and saved to '{output_file}'")