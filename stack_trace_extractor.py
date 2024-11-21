# prompt templating and chaining
from langchain import PromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
import json



# template
template = '''You are a system log analyzer. Your task is to extract all stack traces from the input text provided. 

A stack trace typically starts with an exception type (e.g., `Exception`, `Error`, or `Caused by:`) followed by lines starting with `at` that represent method calls and their file/line number information.

Extract stack traces in plain text.

Input text:
{log_data}

'''




prompt = PromptTemplate.from_template(template)
llm = ChatOpenAI(model='gpt-4o-mini', temperature = 0)

chain = LLMChain(llm=llm, prompt=prompt)



# Read stack traces from JSON file
with open("bug_reports_with_stack_traces.json", "r") as file:
    stack_trace_data = json.load(file)

# Prepare the output format
output_data = []

for entry in stack_trace_data:
    filename = entry['filename']
    creation_time = entry['creation_time']
    log_data = entry['description']
    
    # Generate bug report
    stack_trace = chain.run(log_data)
    # print("--------------------------------------------------------------------")
    # print(stack_trace)
    # print("--------------------------------------------------------------------")


    
    # Add to output data
    output_data.append({
        'filename': filename,
        'creation_time': creation_time,
        'stack_trace': stack_trace
    })

# Write the generated bug reports to a new JSON file
output_file = "stack_traces/YARN.json"
with open(f"{output_file}", "w") as outfile:
    json.dump(output_data, outfile, indent=4)

print(f"Stack traces have been generated and saved to '{output_file}'")