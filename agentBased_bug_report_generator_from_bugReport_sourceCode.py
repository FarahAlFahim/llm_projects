from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, Tool
from langchain.tools import tool
import json
from langchain_core.runnables.utils import AddableDict
from langchain import PromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain



# Define tools (as before)
@tool
def parse_stack_trace(stack_trace):
    """Parse stack traces directly provided in the input JSON."""
    print("------- Parse Stack Trace (start) ----------")
    print("input stack trace:", stack_trace)
    print(json.dumps(stack_trace))
    print("------- Parse Stack Trace (end) ----------")
    return json.dumps(stack_trace)

@tool
def provide_method(method_name_data):
    """Provide the source code for a specific method if it exists."""
    method_name = method_name_data.split(".")[-1].strip()
    if len(method_name) > 0 and method_name[-1] == "'":
        method_name = method_name[:-1]
    method_source = {}
    for key, value in source_code_dict.items():
        if key.startswith(method_name):
            method_source[key] = value
    print("------- Provide Method(start) ----------")
    print("input data:", method_name_data)
    print("method name:", method_name)
    print("method source:", method_source)
    print("source code dict:", source_code_dict)
    
    if method_source == {}:
        method_body = "[Method not found in source code]"
    else:
        method_body = method_source
    current_source_code_dict[method_name_data] = method_body
    print("current_source_code_dict:", current_source_code_dict)
    print("------- Provide Method(end) ----------")
    return json.dumps(current_source_code_dict)

@tool
def analyze_method_and_request_next(input_data):
    """
    Analyze the provided method and determine if further methods are required.
    Returns the next method to request or observation so far if no further methods are needed.
    """
    print("------- analyze_method_and_request_next(start) ----------")
    print("input data:", input_data)
    print("input data type:", type(input_data))
    
    
    method_name = input_data.split(".")[-1].strip()
    if len(method_name) > 0 and method_name[-1] == "'":
        method_name = method_name[:-1]
    method_source = {}
    for key, value in source_code_dict.items():
        if key.startswith(method_name):
            method_source[key] = value
    if method_source == {}:
        method_body = "[Method not found in source code]"
    else:
        method_body = method_source
    current_source_code_dict[input_data] = method_body
    print("source code (method body):", method_body)
    print("method name:", method_name)
    print("method source:", method_source)
    print("current_source_code_dict:", current_source_code_dict)

    template = """
    You are analyzing a call graph for a bug report. The current method is:

    Method: {input_data}
    Source Code:
    {method_body}

    If this method calls any other methods not in the stack trace, identify one such method and return its name.
    If no further methods are needed, respond observation so far based on analyzed methods.
    """
    # llm = ChatOpenAI(model='gpt-4o-mini', temperature=0)
    # response = llm(prompt)  # This returns an AIMessage object

    prompt = PromptTemplate.from_template(template)
    llm = ChatOpenAI(model='gpt-4o-mini', temperature = 0)

    chain = LLMChain(llm=llm, prompt=prompt)
    response = chain.run({'input_data': input_data, 'method_body': method_body})
    print("response from llm:", response)
    print("------- analyze_method_and_request_next(end) ----------")
    return response 



def generate_final_bug_report(agent_based_source_code_analysis, dev_written_bug_report):
    """Generate the final bug report based on analyzed methods."""
    print("------------------- generate final bug report (start) --------------")
    # print("input data:", input_data)
    print("bug report:", dev_written_bug_report)
    print("analyzed method:", agent_based_source_code_analysis)
    print("------------------- generate final bug report (end) --------------")
    # bug_report = input_data['bug_report']
    # analyzed_methods = input_data['analyzed_methods']
    template = """
    Generate an enhanced or improved bug report by analyzing the provided bug report and incorporating insights derived from agent-based analysis of source code methods.

    # Guidelines
    - Use the provided bug report as the starting point and enrich it with additional details based on the agent-based analysis of source code methods.
    - Ensure all aspects of the bug report are clear, actionable, and detailed, improving upon the original content where possible.
    - Structure the final bug report to include all relevant fields, such as method-level insights, root cause analysis, and suggested resolutions.

    # Steps
    1. **Analyze the Provided Bug Report**:
    - Review the given bug report for existing information such as the title, description, and stack trace.
    - Identify any gaps or areas that require further details or clarification.
    2. **Incorporate Agent-Based Analysis**:
    - Use insights from the agent-based analysis of source code methods to add context to the bug report.
    - Highlight any key methods or lines of code contributing to the issue.
    - Summarize relevant inner method calls or dependencies that were analyzed.
    3. **Enhance Bug Report**:
    - Refine the title, description, and any technical details for clarity and precision.
    - Provide actionable insights, root cause analysis, and suggestions for resolution.
    - Include a detailed account of all analyzed methods, with references to their source files and line numbers where applicable.
    4. **Generate JSON Output**:
    - Compile the enhanced bug report into a structured JSON format for consistency and ease of use.

    # Output Format
    Output the enhanced bug report in the following JSON structure:
    ```json
    {{
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



    # You are given the insights derived from agent-based analysis of source code methods below:
    {agent_based_source_code_analysis}
    """
    prompt = PromptTemplate.from_template(template)
    llm = ChatOpenAI(model='gpt-4o-mini', temperature = 0)

    chain = LLMChain(llm=llm, prompt=prompt)
    return chain.run({'bug_report': dev_written_bug_report, 'agent_based_source_code_analysis': agent_based_source_code_analysis})

# Tools for the agent
tools = [
    Tool(name="Parse Stack Trace", func=parse_stack_trace, description="Extract stack traces from the input JSON."),
    Tool(name="Provide Method", func=provide_method, description="Provide the source code for a specific method."),
    Tool(name="Analyze and Request Next", func=analyze_method_and_request_next, description="Analyze the method and request the next one if needed.")
    # Tool(name="Generate Final Bug Report", func=generate_final_bug_report, description="Generate the final bug report using analyzed methods.")
]

# Initialize LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Initialize the agent
agent_executor = initialize_agent(
    tools=tools,
    llm=llm,
    agent="zero-shot-react-description",  
    verbose=True,
)


# Read input and prepare output data
# input_file = "test.json"
# output_file = "test_output.json"
input_file = "source_code_data/Hadoop.json"
output_file = "agentBased_bug_report_from_bugReport_sourceCode/Hadoop.json"

with open(input_file, "r") as file:
    source_code_data = json.load(file)

# Prepare output data
output_data = []

for entry in source_code_data:
    filename = entry['filename']
    creation_time = entry['creation_time']
    bug_report = entry['bug_report']
    stack_trace = entry['stack_trace']
    source_code_dict = entry['source_code']

    # Step 1: Parse the stack trace
    current_source_code_dict = {}
    parsed_stack_traces = agent_executor.stream({"input": stack_trace})
    print("================ parsed_stack_traces (start) ====================")
    print(f"parsed_stack_traces: {parsed_stack_traces} (type: {type(parsed_stack_traces)})")

    # Ensure parsed_stack_traces is iterable and extract traces
    if isinstance(parsed_stack_traces, dict) or hasattr(parsed_stack_traces, "items"):
        parsed_stack_traces = list(parsed_stack_traces.values())
        print("parsed stack traces list:", parsed_stack_traces)
    # parsed_stack_traces = list(parsed_stack_traces)  # Fully consume the generator
    print("================ parsed_stack_traces (end) ====================")


    # Step 2: Sequentially request and analyze methods
    analyzed_methods = {}
    for trace in parsed_stack_traces:
        print("================ trace in parsed_stack_traces (start) ====================")
        print(f"Trace: {trace}, Type: {type(trace)}, length: {len(trace)}")
        print(isinstance(trace, AddableDict))
        print("================ trace in parsed_stack_traces (end) ====================")
        if isinstance(trace, dict) or isinstance(trace, AddableDict):
            if 'output' in trace:
                agent_based_source_code_analysis = trace['output']
                print("####################################")
                print("agent_based_source_code_analysis:", agent_based_source_code_analysis)
                print("####################################")

            
        else:
            print(f"Unexpected trace format: {trace}")
            continue
        


    # Step 3: Generate the final bug report
    try:
        # Manually trigger the final bug report generation
        final_bug_report = generate_final_bug_report(agent_based_source_code_analysis, bug_report)
        print("####################################")
        print("Final bug report called manually:", final_bug_report)
        print("####################################")

        # Parse and include the generated bug report
        bug_report = json.loads(final_bug_report.replace("```json\n", "").replace("\n```", ""))

    except Exception as e:
        print(f"Error generating final bug report: {e}")



    # # Parse the bug report JSON from the generated string
    # try:
    #     # Remove any markdown-style code block indicators (` ```json `) if present
    #     bug_report = json.loads(final_bug_report.replace("```json\n", "").replace("\n```", ""))
    # except json.JSONDecodeError:
    #     print(f"Failed to parse JSON for filename: {filename}")
    #     continue  # Skip this entry if JSON parsing fails



    # Add to output data
    output_data.append({
        "filename": filename,
        "creation_time": creation_time,
        "bug_report": bug_report
    })


# Write output JSON file
with open(output_file, "w") as outfile:
    json.dump(output_data, outfile, indent=4)


print(f"Bug reports have been generated and saved to '{output_file}'")
