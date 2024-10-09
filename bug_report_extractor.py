# prompt templating and chaining
from langchain import PromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain



# template
template = '''You are an expert at extracting structured information from bug reports. You are given a bug report, and your task is to extract the following information in JSON format:

Here is the format to follow:

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

If any field cannot be extracted, leave it blank. Perform the extraction from the following bug report:

{bug_report}
'''



prompt = PromptTemplate.from_template(template)
llm = ChatOpenAI(model='gpt-4o-mini', temperature = 0)

chain = LLMChain(llm=llm, prompt=prompt)



# bug report
bug_report = '''
attachment_id: None
bug_id: 102210
count: 0
creation_time: 2005-06-29T21:06:18Z
creator: mark.strecker@ugs.com
id: 493535
is_private: False
raw_text: Hello,

  I am getting a NullPointerException when trying to compile my project. I am 
just using pointcuts with before and after advice. I have a pointcut which 
matches 6 methods in a class and when it's included in the aspect, I get this 
error ... and when I comment it out, everything compiles. It was working fine 
and then I restarted Eclipse and now I see this error.

Thanks,
Mark


!ENTRY org.eclipse.ajdt.ui 4 0 Jun 29, 2005 16:42:43.516

!MESSAGE NullPointerException thrown: null

!STACK 0

java.lang.NullPointerException

	at org.aspectj.weaver.bcel.BcelWeaver.validateOrBranch
(BcelWeaver.java:584)

	at org.aspectj.weaver.bcel.BcelWeaver.validateBindings
(BcelWeaver.java:552)

	at org.aspectj.weaver.bcel.BcelWeaver.rewritePointcuts
(BcelWeaver.java:490)

	at org.aspectj.weaver.bcel.BcelWeaver.prepareForWeave
(BcelWeaver.java:426)

	at org.aspectj.ajdt.internal.compiler.AjCompilerAdapter.weave
(AjCompilerAdapter.java:248)

	at org.aspectj.ajdt.internal.compiler.AjCompilerAdapter.afterCompiling
(AjCompilerAdapter.java:129)

	at org.aspectj.org.eclipse.jdt.internal.compiler.Compiler.compile
(Compiler.java:385)

	at 
org.aspectj.ajdt.internal.core.builder.AjBuildManager.performCompilation
(AjBuildManager.java:727)

	at org.aspectj.ajdt.internal.core.builder.AjBuildManager.doBuild
(AjBuildManager.java:206)

	at org.aspectj.ajdt.internal.core.builder.AjBuildManager.batchBuild
(AjBuildManager.java:140)

	at org.aspectj.ajde.internal.CompilerAdapter.compile
(CompilerAdapter.java:121)

	at org.aspectj.ajde.internal.AspectJBuildManager$CompilerThread.run
(AspectJBuildManager.java:191)
tags: []
text: Hello,

  I am getting a NullPointerException when trying to compile my project. I am 
just using pointcuts with before and after advice. I have a pointcut which 
matches 6 methods in a class and when it's included in the aspect, I get this 
error ... and when I comment it out, everything compiles. It was working fine 
and then I restarted Eclipse and now I see this error.

Thanks,
Mark


!ENTRY org.eclipse.ajdt.ui 4 0 Jun 29, 2005 16:42:43.516

!MESSAGE NullPointerException thrown: null

!STACK 0

java.lang.NullPointerException

	at org.aspectj.weaver.bcel.BcelWeaver.validateOrBranch
(BcelWeaver.java:584)

	at org.aspectj.weaver.bcel.BcelWeaver.validateBindings
(BcelWeaver.java:552)

	at org.aspectj.weaver.bcel.BcelWeaver.rewritePointcuts
(BcelWeaver.java:490)

	at org.aspectj.weaver.bcel.BcelWeaver.prepareForWeave
(BcelWeaver.java:426)

	at org.aspectj.ajdt.internal.compiler.AjCompilerAdapter.weave
(AjCompilerAdapter.java:248)

	at org.aspectj.ajdt.internal.compiler.AjCompilerAdapter.afterCompiling
(AjCompilerAdapter.java:129)

	at org.aspectj.org.eclipse.jdt.internal.compiler.Compiler.compile
(Compiler.java:385)

	at 
org.aspectj.ajdt.internal.core.builder.AjBuildManager.performCompilation
(AjBuildManager.java:727)

	at org.aspectj.ajdt.internal.core.builder.AjBuildManager.doBuild
(AjBuildManager.java:206)

	at org.aspectj.ajdt.internal.core.builder.AjBuildManager.batchBuild
(AjBuildManager.java:140)

	at org.aspectj.ajde.internal.CompilerAdapter.compile
(CompilerAdapter.java:121)

	at org.aspectj.ajde.internal.AspectJBuildManager$CompilerThread.run
(AspectJBuildManager.java:191)
time: 2005-06-29T21:06:18Z

'''

print('--------------- BUG REPORT ---------------')
print(chain.run(bug_report))
print('--------------- END ---------------')


# Check the model is being used
# print(f"Model being used: {llm.model_name}")

# Check prompt template
# print(prompt.format(stack_trace={stack_trace}))