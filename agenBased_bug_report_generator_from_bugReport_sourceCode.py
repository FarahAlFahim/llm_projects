from langchain.agents import initialize_agent, Tool
from langchain.chat_models import ChatOpenAI
from langchain.tools import tool
import json



@tool
def parse_stack_trace(stack_trace):
    """Parse stack traces directly provided in the input JSON."""
    print("------- Parse Stack Trace (start) ----------")
    print(json.dumps(stack_trace))
    print("------- Parse Stack Trace (end) ----------")
    return json.dumps(stack_trace)

@tool
def provide_method(method_name_data):
    """Provide the source code for a specific method if it exists."""
    # method_body = source_code_dict.get(method_name, "[Method not found in source code]")
    method_name = method_name_data.split(".")[-1]
    if method_name[-1] == "'":
        method_name = method_name[:-1]
    method_source = {}
    for key, value in source_code_dict.items():
        if key.startswith(method_name):
            method_source[key] = value
    print("------- Provide Method(start) ----------")
    # print("input data:", method_name_data)
    print("Method name:", method_name)
    # print("Source methods:", method_source)
    # print("source code dict:", source_code_dict.items())
    print("returned value:", json.dumps({method_name_data: method_source}))
    print("------- Provide Method (end) ----------")
    if method_source == {}:
        return json.dumps({method_name_data: "[Method not found in source code]"})
    return json.dumps({method_name_data: method_source})

@tool
def analyze_method_and_request_next(input_data):
    """
    Analyze the provided method and determine if further methods are required.
    Returns the next method to request or 'END' if no further methods are needed.
    """
    print("------------------- analyze method and request next (start) --------------")
    print("input data:", input_data)
    print("------------------- analyze method and request next (end) --------------")
    method_name = input_data['method_name']
    method_body = input_data['method_body']

    prompt = f"""
    You are analyzing a call graph for a bug report. The current method is:

    Method: {method_name}
    Source Code:
    {method_body}

    If this method calls any other methods not in the stack trace, identify one such method and return its name.
    If no further methods are needed, respond with 'END'.
    """
    llm = ChatOpenAI(model='gpt-4o-mini', temperature=0)
    response = llm.run(prompt)
    return response.strip()

@tool
def generate_final_bug_report(input_data):
    """Generate the final bug report based on analyzed methods."""
    bug_report = input_data['bug_report']
    analyzed_methods = input_data['analyzed_methods']

    prompt = f"""
    Generate an improved bug report based on the following inputs:

    # Bug Report
    {bug_report}

    # Analyzed Methods and Call Graph
    {json.dumps(analyzed_methods, indent=4)}
    """
    llm = ChatOpenAI(model='gpt-4o-mini', temperature=0)
    return llm.run(prompt)

# Tools for the agent
tools = [
    Tool(name="Parse Stack Trace", func=parse_stack_trace, description="Extract stack traces from the input JSON."),
    Tool(name="Provide Method", func=provide_method, description="Provide the source code for a specific method."),
    Tool(name="Analyze and Request Next", func=analyze_method_and_request_next, description="Analyze the method and request the next one if needed."),
    Tool(name="Generate Final Bug Report", func=generate_final_bug_report, description="Generate the final bug report using analyzed methods.")
]

# Initialize agent
llm = ChatOpenAI(model='gpt-4o-mini', temperature=0)
agent = initialize_agent(tools, llm, agent_type="zero-shot-react-description", verbose=True)



# Read JSON file containing bug reports
# input_file = "source_code_data/ActiveMQ.json"
# output_file = "bug_report_from_bugReport_sourceCode/ActiveMQ.json"
# Test input output
input_file = "test.json"
output_file = "test_output.json"

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
    parsed_stack_traces = json.loads(agent.run({"input": stack_trace, "tool": "Parse Stack Trace"}))
    # parsed_stack_traces = json.loads(agent.run(stack_trace))
    # parsed_stack_traces = agent.run(stack_trace)
    print("================ parsed_stack_traces (start) ====================")
    print(parsed_stack_traces)
    print("================ parsed_stack_traces (end) ====================")

    # Step 2: Sequentially request and analyze methods
    analyzed_methods = {}
    for trace in parsed_stack_traces:
        method_name = trace.split("at ")[1].split("(")[0].strip()

        while method_name != "END":
            # Request the source code for the current method
            method_response = json.loads(agent.run({"input": method_name, "tool": "Provide Method"}))
            # method_response = json.loads(agent.run({
            #     "input": {"method_name": method_name, "source_code_dict": source_code_dict},
            #     "tool": "Provide Method"
            # }))
            print("####################################")
            print("method resonse:", method_response)
            print("####################################")

            method_body = method_response.get(method_name, "[Method not found]")

            # Analyze the method and request the next one if needed
            next_method_name = agent.run({
                "input": {"method_name": method_name, "method_body": method_body},
                "tool": "Analyze and Request Next"
            })
            # next_method_name = agent.run({
            #     "method_name": method_name,
            #     "method_body": method_body
            # })


            # Store the analyzed method
            analyzed_methods[method_name] = method_body

            # Update the method name for the next iteration
            method_name = next_method_name.strip()

    # Step 3: Generate the final bug report
    final_bug_report_input = {
        "bug_report": bug_report,
        "analyzed_methods": analyzed_methods
    }
    final_bug_report = agent.run({"input": final_bug_report_input, "tool": "Generate Final Bug Report"})
    # final_bug_report = agent.run({
    #     "bug_report": bug_report,
    #     "analyzed_methods": analyzed_methods,
    #     "tool": "Generate Final Bug Report"
    # })


    # Add to output data
    output_data.append({
        "filename": filename,
        "creation_time": creation_time,
        "bug_report": final_bug_report
    })

# Write output JSON file
with open(output_file, "w") as outfile:
    json.dump(output_data, outfile, indent=4)

print(f"Bug reports have been generated and saved to '{output_file}'")
