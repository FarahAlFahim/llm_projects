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



def generate_final_bug_report(agent_based_source_code_analysis, stack_trace):
    """Generate the final bug report based on analyzed methods."""
    print("------------------- generate final bug report (start) --------------")
    # print("input data:", input_data)
    print("stack trace:", stack_trace)
    print("analyzed method:", agent_based_source_code_analysis)
    print("current_source_code_dict:", current_source_code_dict)
    print("------------------- generate final bug report (end) --------------")
    # bug_report = input_data['bug_report']
    # analyzed_methods = input_data['analyzed_methods']
    template = """
    Generate a detailed bug report based on the given stack traces and insights from agent-based analysis of source code methods.

    # Guidelines
    - Analyze the stack traces to identify the error, root cause, and relevant source code context.
    - Leverage agent-based insights to enrich the report with detailed information on affected methods, associated files, and potential causes.
    - Ensure the report includes actionable steps for debugging and resolving the issue.
    - Structure the output in a clear and concise JSON format.

    # Steps
    1. **Analyze Stack Traces**:
    - Parse the stack traces to extract key details, such as error types, method calls, and file locations.
    - Identify the error's originating method and relevant line numbers.
    2. **Incorporate Agent-Based Insights**:
    - Use the analysis of source code methods to provide deeper context on the issue.
    - Highlight any inner method calls, dependencies, or code paths contributing to the problem.
    3. **Construct the Bug Report**:
    - Summarize the issue, including a clear title, description, and affected components.
    - Include steps to reproduce, expected behavior, and observed behavior.
    - Provide actionable suggestions for resolving the issue.
    4. **Format the Output**:
    - Compile the bug report in JSON format, ensuring all fields are completed accurately.

    # Output Format
    Output the bug report in the following JSON structure:
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



    # You are given the stack traces below:
    {stack_trace}



    # You are given the insights derived from agent-based analysis of source code methods below:
    {agent_based_source_code_analysis}


    
    # You are given the source code methods analyzed by agent-based approach below:
    {current_source_code_dict}
    """
    prompt = PromptTemplate.from_template(template)
    llm = ChatOpenAI(model='gpt-4o-mini', temperature = 0)

    chain = LLMChain(llm=llm, prompt=prompt)
    return chain.run({'stack_trace': stack_trace, 'agent_based_source_code_analysis': agent_based_source_code_analysis, 'current_source_code_dict': current_source_code_dict})

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
input_file = "test.json"
output_file = "test_output.json"
# input_file = "source_code_data/Hadoop.json"
# output_file = "agentBased_bug_report_from_stackTrace_sourceCode/Hadoop.json"

with open(input_file, "r") as file:
    source_code_data = json.load(file)

# Prepare output data
output_data = []

for entry in source_code_data:
    filename = entry['filename']
    creation_time = entry['creation_time']
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
        final_bug_report = generate_final_bug_report(agent_based_source_code_analysis, stack_trace)
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
