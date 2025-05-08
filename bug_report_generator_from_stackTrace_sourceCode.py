# prompt templating and chaining
from langchain import PromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
import json



# template
template = '''
You are a professional bug report assistant. Your task is to analyze raw stack traces and their corresponding source code methods to generate a structured bug report that identifies the root cause of an issue.  

## **Task Overview**  
- You are provided with:  
  1. **Raw stack traces** containing error messages and method call sequences.  
  2. **Source code methods** extracted from the call graph, including all methods dependent on those in the stack trace.  

- Your goal is to **diagnose the root cause** by carefully examining both inputs.  
- **Do not hallucinate information**—base your analysis strictly on the provided data.  

---

## **# Steps**  

1. **Extract and Parse the Stack Trace**  
   - Identify the error type, message, and the sequence of method calls.  
   - Determine where the execution failure occurs.  

2. **Analyze the Source Code Methods**  
   - Inspect each method referenced in the stack trace along with its dependencies.  
   - Look for issues such as unhandled exceptions, incorrect logic, or invalid inputs.  

3. **Determine the Root Cause**  
   - Pinpoint the specific function or line of code responsible for the failure.  
   - Clearly explain how the issue propagates through the execution flow.  

4. **Generate a Structured Bug Report**  
   - Summarize the problem concisely.  
   - Provide supporting evidence from the stack trace and source code analysis.  
   - Suggest potential fixes when applicable.  

---

## **# Output Format**  

The output should be structured in JSON format with the following fields:

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




## You are given the **Raw stack traces** below:

{stack_trace}



## You are given the **Source code methods** below:

{source_code}
'''




prompt = PromptTemplate.from_template(template)
llm = ChatOpenAI(model='gpt-4o-mini', temperature = 0)

chain = LLMChain(llm=llm, prompt=prompt)


# Read developer written bug reports and source code data from JSON file
input_file = "source_code_data/method_list/YARN.json"
output_file = 'bug_report_from_stackTrace_sourceCode/YARN.json'

# input_file = "test.json"
# output_file = "test_output.json"


# Read developer written bug reports and source code data from JSON file
with open(input_file, "r") as file:
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