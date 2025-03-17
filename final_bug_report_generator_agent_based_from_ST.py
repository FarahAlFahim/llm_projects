# prompt templating and chaining
from langchain import PromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
import json




# template
template = '''
Generate a bug report with the goal of diagnosing the root cause.

You are a professional assistant analyzing stack traces. You will be provided with three key input data sources:
1. **Raw Stack Traces**: These contain error messages and exceptions.
2. **Agent-Based Chat History**: Logs of source code method analysis, showing methods requested by the agent and its reasoning.
3. **Source Code Methods Analyzed by the Agent**: Methods referenced in the stack traces or their dependent methods.

## Steps

1. **Analyze the Stack Trace**:  
   - Identify key error messages and exceptions.  
   - Determine which methods or classes are involved.  

2. **Correlate with Agent-Based Chat History**:  
   - Extract the agent’s reasoning behind method requests.  
   - Identify patterns in how the agent analyzed methods.  

3. **Examine the Source Code Methods**:  
   - Review the actual implementations of the methods mentioned in the stack trace and chat history.  
   - Look for logical errors, incorrect dependencies, or improper exception handling.  
   - Trace the flow of execution using method dependencies.  

4. **Determine the Root Cause**:  
   - Identify the primary source of the bug based on stack trace information and source code examination.  
   - Avoid assumptions—base your findings solely on provided data.  

5. **Generate a Bug Report**:  
   - Populate each field in the bug report using your analysis:  
     - **Title**: Concise description of the bug.  
     - **Description**: Summary of findings.  
     - **Root Cause**: Clear explanation of what is causing the issue.  
     - **Steps to Reproduce**: How the issue can be replicated.  
     - **Expected Behavior**: What should happen instead.  
     - **Observed Behavior**: The actual incorrect behavior.  
     - **Suggestions**: Possible directions for fixing the issue.  
     - **Problem Location**: Specific file/class/method responsible for the issue.  
     - **Possible Fix**: If a solution is evident, provide a suggestion.  

## Output Format

Provide the bug report in **JSON format** with the following structure:

```json
{{
    "Title": "<Bug Title>",
    "Description": "<Detailed Description based on analysis>",
    "StackTrace": "string or array of stack trace lines",
    "RootCause": "<Explanation of the root cause>",
    "StepsToReproduce": ["<Step-by-step reproduction guide>"] or null,
    "ExpectedBehavior": "<Correct system behavior>",
    "ObservedBehavior": "<Actual faulty behavior>",
    "Suggestions": "<Possible fixes or mitigation steps>",
    "problem_location": {{
        "files": ["file1.java", "file2.java"],
        "classes": ["com.example.ClassA", "com.example.ClassB"],
        "methods": ["ClassA.methodX", "ClassB.methodY"]
    }},
    "possible_fix": "[Proposed code fix or strategy]"
}}


### **Notes**  
- Do **not** hallucinate information—only use provided data.
- Follow a **structured reasoning approach** before reaching conclusions.
- Ensure all fields are **accurate and complete** based on available inputs.
- Maintain **clarity and conciseness** in all explanations.




# You are given the **Raw Stack Traces** below:

{stack_trace}



# You are given the **Agent-Based Chat History** below:

{chat_history}



# You are given the **Source Code Methods Analyzed by the Agent** below:

{analyzed_methods}
'''




prompt = PromptTemplate.from_template(template)
llm = ChatOpenAI(model='gpt-4o-mini', temperature = 0)

chain = LLMChain(llm=llm, prompt=prompt)



# File paths
agent_based_file = "agentBased_bug_report_from_stackTrace_sourceCode/without_analyzed_methods/YARN.json"
stack_trace_file = "stack_traces/YARN.json"
output_file = "agentBased_bug_report_from_stackTrace_sourceCode/YARN.json"

# agent_based_file = "test.json"
# stack_trace_file = "test1.json"
# output_file = "test_output.json"


# Load JSON data from a file
def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
    

# Load the JSON files
agent_based_data = load_json(agent_based_file)
stack_trace_data = load_json(stack_trace_file)

# Create a mapping from filename to stack_trace for stack_trace_data
stack_trace_info = {item["filename"]: item["stack_trace"] for item in stack_trace_data}

# Prepare the output format
output_data = []

for entry in agent_based_data:
    filename = entry['filename']
    creation_time = entry['creation_time']
    analyzed_methods = entry['analyzed_methods']
    class_skeleton_cache = entry['class_skeleton_cache']
    chat_history = entry['chat_history']
    stack_trace = stack_trace_info.get(filename, {})  # Get stack_trace if available
    
    # Generate improved bug report
    bug_report_str = chain.run({'stack_trace': stack_trace, 'chat_history': chat_history, 'analyzed_methods': analyzed_methods})
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
        "analyzed_methods": analyzed_methods,
        "class_skeleton_cache": class_skeleton_cache,
        "chat_history": chat_history,
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