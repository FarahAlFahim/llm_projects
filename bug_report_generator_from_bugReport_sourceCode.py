# prompt templating and chaining
from langchain import PromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
import json



# template
template = '''
Generate an improved bug report by diagnosing the root cause based on a developer-written bug report and source code methods extracted from a call graph.

You are a professional bug report assistant. Your task is to enhance a given bug report by analyzing both the original report and the relevant source code to identify the root cause of the issue.

## Input Data
You will be given:
1. **Developer-Written Bug Report**: Includes a description of the issue and stack traces.
2. **Source Code Methods**: These methods are extracted from the call graph of the methods referenced in the stack trace.

## Task Details
- Analyze the bug report and stack trace to determine the methods that may be responsible for the issue.
- Examine the provided source code methods, going through each line to find the root cause and problem location.
- Do **not** hallucinate or make assumptions beyond the given data.
- Enhance the bug report by clearly articulating the root cause and problem location based on your analysis.
- Maintain factual accuracy and only use information found in the provided inputs.

## Output Format
Return the enhanced bug report in **JSON format**:

```json
{{
    "Title": "<Bug title>",
    "Description": "<Improved description based on analysis>",
    "StackTrace": "string or array of stack trace lines",
    "RootCause": "<Identified root cause>",
    "StepsToReproduce": ["<Step-by-step reproduction guide>"] or null,
    "ExpectedBehavior": "<Correct system behavior>",
    "ObservedBehavior": "<Actual faulty behavior>",
    "Suggestions": "<Possible fixes or mitigation steps>",
    "problem_location": {{
        "files": ["file1.java", "file2.java"],
        "classes": ["com.example.ClassA", "com.example.ClassB"],
        "methods": ["ClassA.methodX", "ClassB.methodY"]
    }},
    "possible_fix": "[Suggested resolution, including code changes if necessary.]"
}}



## You are given the **Developer-Written Bug Report** below:

{bug_report}



## You are given the **Source Code Methods** below:

{source_code}
'''



prompt = PromptTemplate.from_template(template)
llm = ChatOpenAI(model='gpt-4o-mini', temperature = 0)

chain = LLMChain(llm=llm, prompt=prompt)



# Read developer written bug reports and source code data from JSON file
input_file = "source_code_data/method_list/YARN.json"
output_file = "bug_report_from_modified_bugReport_sourceCode/YARN.json"

# input_file = "test.json"
# output_file = "test_output.json"


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