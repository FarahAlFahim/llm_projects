# prompt templating and chaining
from langchain import PromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
import json



def agent_interaction(bug_report, source_code_dict, chain):
    # Initial prompt with only the bug report
    response = chain.run({'bug_report': bug_report, 'source_code': '[No methods provided yet]'})
    print("###################################### Initial Prompt only with bug report ########################")
    print(response)
    print("###################################### Initial Prompt only with bug report ########################")

    context = bug_report
    processed_methods = set()

    response = json.loads(response.replace("```json\n", "").replace("\n```", ""))

    while "requested_method" in response:
        if "stack_trace_line_processed" in response:
            # convert context into string
            context = json.dumps(context, indent=4)
            context = context.replace(response['stack_trace_line_processed'], "")

            # convert context back to json
            context = json.loads(context)

        # Parse the requested method
        if '.' in response['requested_method']:
            requested_method = response['requested_method'].split(".")[-1]
        elif "(" in response['requested_method']:
            requested_method = response['requested_method'].split('(')[0]
        else:
            requested_method = response['requested_method']
        print("************* Requested Method **************")
        print(requested_method)
        print("************* Requested Method **************")

        if requested_method in processed_methods:
            response = chain.run({'bug_report': context, 'source_code': 'This method is already Processed. Go to the next line of the Stack Trace and Extract and request the associated method using `requested_method`. If already analyzed the whole stack trace, generate the final bug report'})
            try:
                response = json.loads(response.replace("```json\n", "").replace("\n```", ""))
            except json.JSONDecodeError:
                print("Failed to parse the response as JSON after providing method.")
            print("###################################### Response in Processed Method ########################")
            print(response)
            print("###################################### Response in Processed Method ########################")

        # Fetch the method from the source_code_dict
        method_source = {}
        for key, value in source_code_dict.items():
            if requested_method in key:
                method_source[key] = value
        if method_source == {}:
            response = chain.run({'bug_report': context, 'source_code': 'Method not found. Go to the next line of the Stack Trace and Extract and request the associated method using `requested_method`. If already analyzed the whole stack trace, generate the final bug report'})
            try:
                response = json.loads(response.replace("```json\n", "").replace("\n```", ""))
            except json.JSONDecodeError:
                print("Failed to parse the response as JSON after providing method.")
            print("###################################### Response in Processed Method ########################")
            print(response)
            print("###################################### Response in Processed Method ########################")
            continue

        print("************* Method from source code **************")
        print(method_source)
        print("************* Method from source code **************")
        # Update context with the method source code
        # context += f"\n\n--- Source code for {requested_method} ---\n{method_source}\n"
        response = chain.run({'bug_report': context, 'source_code': method_source})
        try:
            response = json.loads(response.replace("```json\n", "").replace("\n```", ""))
        except json.JSONDecodeError:
            print("Failed to parse the response as JSON after providing method.")
        print("###################################### Response in Found Method ########################")
        print(response)
        print("###################################### Response in Found Method ########################")

        processed_methods.add(requested_method)

    # Final enhanced bug report
    # try:
    #     return json.loads(response.replace("```json\n", "").replace("\n```", ""))
    # except json.JSONDecodeError:
    #     return {"error": "Failed to parse the final bug report."}
    return response


# Define the prompt template
template = '''
Generate an enhanced bug report by analyzing stack traces and iteratively requesting methods based on their relevance, ensuring no method or stack trace line is processed multiple times.

# Guidelines
- Analyze each line of the provided stack trace sequentially.
- For each line, output a `requested_method` corresponding to the method in the stack trace, ensuring:
  - You do not re-analyze methods or stack trace lines that have already been processed.
  - Requests for methods are unique and do not repeat.
- Analyze the content of each `requested_method` provided by the system and determine:
  - Whether further methods are needed based on inner method calls or dependencies within the `requested_method`.
  - When all necessary methods have been processed or no further analysis is required.
- Conclude the task by generating an enhanced bug report once all relevant data has been gathered.

# Steps
1. **Initialize Analysis**:
   - Start with the first line of the stack trace and extract the method to request.
   - Ensure no stack trace line is processed multiple times.
2. **Request Method Details**:
   - Output a `requested_method` for each relevant method until all lines in the stack trace and their inner dependencies have been addressed.
   - Avoid duplicating requests for methods already analyzed.
3. **Analyze Method Content**:
   - Examine each `requested_method` for its logic, dependencies, and inner calls.
   - Use insights to determine if further methods need to be requested.
4. **Iterate**:
   - Repeat the process for inner calls and dependencies until all necessary data has been collected.
5. **Generate Enhanced Bug Report**:
   - Use the insights gathered to create a comprehensive bug report, including actionable recommendations.

# Output Format
- **For Method Requests**: Output only two fields "requested_method" and "stack_trace_line_processed" and nothing else. The format should be:
  ```json
    {{
        "requested_method": "string",
        "stack_trace_line_processed": "string of the stack trace line"
    }}

- **Final Bug Report**: When no further methods are required, output the enhanced bug report in the following JSON format:
  ```json
    {{
        "BugID": "string or null",
        "Title": "string",
        "Description": "string",
        "StackTrace": "string or array of stack trace lines",
        "RootCause": "string or null",
        "StepsToReproduce": ["string", "..."] or null,
        "ExpectedBehavior": "string",
        "ObservedBehavior": "string",
        "Suggestions": "string or null"
    }}





# You are given the bug report below:

{bug_report}



# You are given the source code below:

{source_code}
'''

# Initialize LangChain
prompt = PromptTemplate.from_template(template)
llm = ChatOpenAI(model='gpt-4o-mini', temperature = 0)

chain = LLMChain(llm=llm, prompt=prompt)




# Read developer written bug reports and source code data from JSON file
with open("test.json", "r") as file:
    source_code_data = json.load(file)

# Prepare the output format
output_data = []

for entry in source_code_data:
    filename = entry['filename']
    creation_time = entry['creation_time']
    dev_written_bug_report = entry['bug_report']
    source_code = entry['source_code']
    
    # Generate improved bug report
    # improved_bug_report = chain.run({'bug_report': dev_written_bug_report, 'source_code': source_code})
    # Run agent interaction
    improved_bug_report = agent_interaction(dev_written_bug_report, source_code, chain)
    print("--------------------------------------------------------------------")
    print(improved_bug_report)
    print("--------------------------------------------------------------------")


    
    # Add to output data
    output_data.append({
        'filename': filename,
        'creation_time': creation_time,
        'bug_report': improved_bug_report
    })

# Write the summarized bug reports to a new JSON file
output_file = 'test_output.json'
with open(f"{output_file}", "w") as outfile:
    json.dump(output_data, outfile, indent=4)

print(f"Bug reports have been generated and saved to '{output_file}'")
