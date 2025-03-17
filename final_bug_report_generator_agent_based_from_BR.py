# prompt templating and chaining
from langchain import PromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
import json




# template
template = '''
You are a **professional bug report assistant** responsible for analyzing and improving bug reports to diagnose the root cause effectively.  

### **Task**  
Given three input sources, enhance an existing developer-written bug report by establishing connections between the provided information and improving key fields.  

### **Inputs**  
1. **Original Bug Report**: Developer-written report containing stack traces.  
2. **Agent-Based Chat History**: Conversation log where an agent analyzes source code methods related to the bug.  
3. **Source Code Methods**: Methods analyzed by the agent that appear in stack traces or are part of the call dependency graph of those methods.  

### **Guidelines for Enhancement**  
- **Analyze the Input Data**:  
  - Examine the original bug report and its stack trace.  
  - Correlate insights from the agent-based chat history.  
  - Identify key methods and dependencies from the provided source code.  
- **Determine the Root Cause**:  
  - Establish logical connections between the stack trace, analyzed methods, and chat history.  
  - Focus on the most relevant methods contributing to the issue.  
- **Enhance Each Bug Report Field**:  
  - **Description**: Provide a more detailed and structured summary.  
  - **RootCause**: Explain the exact issue identified from the analysis.  
  - **StepsToReproduce**: Refine reproduction steps for accuracy.  
  - **ExpectedBehavior**: Describe what should happen in a properly functioning system.  
  - **ObservedBehavior**: Detail the actual faulty behavior observed.  
  - **Suggestions**: Offer possible solutions or workarounds if identifiable.  
  - **problem_location**: Specify the file(s) or method(s) likely responsible.  
  - **possible_fix**: Provide any potential code fixes or modifications if evident.  
- **Do Not Hallucinate**:  
  - Only use information present in the provided inputs.  
  - Avoid speculating beyond what is supported by the evidence.  

### **Output Format**  
The enhanced bug report should be structured in **valid JSON** as follows:  

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


### **Notes**  
- If certain fields cannot be improved due to insufficient data, retain the original content.
- Keep responses **concise, structured, and fact-based**.
- The final output should **strictly** follow the JSON format above.




# You are given the **Original Bug Report** below:

{bug_report}



# You are given the **Agent-Based Chat History** below:

{chat_history}



# You are given the **Source Code Methods** below:

{analyzed_methods}
'''




prompt = PromptTemplate.from_template(template)
llm = ChatOpenAI(model='gpt-4o-mini', temperature = 0)

chain = LLMChain(llm=llm, prompt=prompt)



# File paths
# agent_based_file = "agentBased_bug_report_from_modified_bugReport_sourceCode/without_analyzed_methods/YARN.json"
# modified_dev_file = "modified_dev_written_bug_reports/YARN.json"
# output_file = "agentBased_bug_report_from_modified_bugReport_sourceCode/YARN.json"

agent_based_file = "test.json"
modified_dev_file = "test1.json"
output_file = "test_output.json"


# Load JSON data from a file
def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
    

# Load the JSON files
agent_based_data = load_json(agent_based_file)
modified_dev_data = load_json(modified_dev_file)

# Create a mapping from filename to bug_report for modified_dev_data
modified_bug_reports = {item["filename"]: item["bug_report"] for item in modified_dev_data}

# Prepare the output format
output_data = []

for entry in agent_based_data:
    filename = entry['filename']
    creation_time = entry['creation_time']
    analyzed_methods = entry['analyzed_methods']
    class_skeleton_cache = entry['class_skeleton_cache']
    chat_history = entry['chat_history']
    dev_written_bug_report = modified_bug_reports.get(filename, {})  # Get bug_report if available
    
    # Generate improved bug report
    bug_report_str = chain.run({'bug_report': dev_written_bug_report, 'chat_history': chat_history, 'analyzed_methods': analyzed_methods})
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