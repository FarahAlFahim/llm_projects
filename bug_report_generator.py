# prompt templating and chaining
from langchain import PromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
import json



# template
template = '''You are a bug report generator. You are given a stack trace below:

{stack_trace}

Based on the given stack trace info, generate a bug report in json format having title, description, steps to reproduce, expected behaviour, actual behaviour, possible cause and the stack trace. 
Generate the full bug report in json format using the following template:

{{
  "title": "<title>",
  "description": {{
    "stepsToReproduce": [
      "<Step 1>",
      "<Step 2>",
      "<Step 3>"
    ],
    "actualBehavior": "<What happens instead>",
    "possibleCause": "<Insights or hypotheses about the issue (optional)>"
  }},
  "stackTrace": "<stack_trace>"
}}
'''




prompt = PromptTemplate.from_template(template)
llm = ChatOpenAI(model='gpt-4o-mini', temperature = 0)

chain = LLMChain(llm=llm, prompt=prompt)



# Read stack traces from JSON file
with open("stack_traces/YARN.json", "r") as file:
    stack_trace_data = json.load(file)

# Prepare the output format
output_data = []

for entry in stack_trace_data:
    filename = entry['filename']
    creation_time = entry['creation_time']
    stack_trace = entry['stack_trace']
    
    # Generate bug report
    bug_report_str = chain.run(stack_trace)
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

# Write the generated bug reports to a new JSON file
with open("llm_generated_bug_reports/YARN.json", "w") as outfile:
    json.dump(output_data, outfile, indent=4)

print("Bug reports have been generated and saved to 'generated_bug_reports.json'")