# prompt templating and chaining
from langchain import PromptTemplate
from langchain_community.llms import OpenAI
from langchain.chains import LLMChain


# template
template = '''You are a bug report generator. 
Based on the given {stack_trace}, generated a bug report in json format having title, description, steps to reproduce, expected behaviour, actual behaviour, possible cause. 
please generate the bug report in json format using the following template:

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
  "stackTrace": "<Stack trace>"
}}
'''




prompt = PromptTemplate.from_template(template)
llm = OpenAI(temperature = 0.9)

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

print(chain.run(stack_trace))