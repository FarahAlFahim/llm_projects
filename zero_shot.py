# prompt templating and chaining
from langchain import PromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain



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
    "expectedBehavior": "<What should happen>",
    "actualBehavior": "<What happens instead>",
    "possibleCause": "<Insights or hypotheses about the issue>"
  }},
  "stackTrace": "<stack trace>"
}}
'''




prompt = PromptTemplate.from_template(template)
llm = ChatOpenAI(model='gpt-4o-mini', temperature = 0)

chain = LLMChain(llm=llm, prompt=prompt)



# stack trace
stack_trace = '''
java.lang.NullPointerException
    at org.aspectj.weaver.bcel.BcelWeaver.validateOrBranch(BcelWeaver.java:584)
    at org.aspectj.weaver.bcel.BcelWeaver.validateBindings(BcelWeaver.java:552)
    at org.aspectj.weaver.bcel.BcelWeaver.rewritePointcuts(BcelWeaver.java:490)
    at org.aspectj.weaver.bcel.BcelWeaver.prepareForWeave(BcelWeaver.java:426)
    at org.aspectj.ajdt.internal.compiler.AjCompilerAdapter.weave(AjCompilerAdapter.java:248)
    at org.aspectj.ajdt.internal.compiler.AjCompilerAdapter.afterCompiling(AjCompilerAdapter.java:129)
    at org.aspectj.org.eclipse.jdt.internal.compiler.Compiler.compile(Compiler.java:385)
    at org.aspectj.ajdt.internal.core.builder.AjBuildManager.performCompilation(AjBuildManager.java:727)
    at org.aspectj.ajdt.internal.core.builder.AjBuildManager.doBuild(AjBuildManager.java:206)
    at org.aspectj.ajdt.internal.core.builder.AjBuildManager.batchBuild(AjBuildManager.java:140)
    at org.aspectj.ajde.internal.CompilerAdapter.compile(CompilerAdapter.java:121)
    at org.aspectj.ajde.internal.AspectJBuildManager$CompilerThread.run(AspectJBuildManager.java:191)
'''

print('--------------- BUG REPORT ---------------')
print(chain.run(stack_trace))
print('--------------- END ---------------')


# Check the model is being used
print(f"Model being used: {llm.model_name}")

# Check prompt template
# print(prompt.format(stack_trace={stack_trace}))