# prompt templating and chaining
from langchain import PromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain



# template
template = '''You are a fault localization assistant. 
Your task is to analyze the provided bug report and identify the most likely locations in the source code where the bug may reside. 
Use the stack trace, description, and any possible causes to guide your localization.

Bug Report:
{bug_report}


Using the information above, generate a list of files, classes, or methods where the issue is most likely located. 
Provide your response in JSON format.
'''




prompt = PromptTemplate.from_template(template)
llm = ChatOpenAI(model='gpt-4o-mini', temperature = 0)

chain = LLMChain(llm=llm, prompt=prompt)



# bug report
bug_report = '''
{
  "title": "NullPointerException in BcelWeaver during Pointcut Validation",
  "description": {
    "stepsToReproduce": [
      "1. Compile an AspectJ project with complex pointcuts.",
      "2. Ensure that the pointcuts involve multiple branches and bindings.",
      "3. Trigger the weaving process."
    ],
    "actualBehavior": "The compilation fails with a NullPointerException in the BcelWeaver.validateOrBranch method.",
    "possibleCause": "The issue may arise from uninitialized or null bindings in the leftBindings or rightBindings arrays when validating pointcuts."
  },
  "stackTrace": "java.lang.NullPointerException\n    at org.aspectj.weaver.bcel.BcelWeaver.validateOrBranch(BcelWeaver.java:584)\n    at org.aspectj.weaver.bcel.BcelWeaver.validateBindings(BcelWeaver.java:552)\n    at org.aspectj.weaver.bcel.BcelWeaver.rewritePointcuts(BcelWeaver.java:490)\n    at org.aspectj.weaver.bcel.BcelWeaver.prepareForWeave(BcelWeaver.java:426)\n    at org.aspectj.ajdt.internal.compiler.AjCompilerAdapter.weave(AjCompilerAdapter.java:248)\n    at org.aspectj.ajdt.internal.compiler.AjCompilerAdapter.afterCompiling(AjCompilerAdapter.java:129)\n    at org.aspectj.org.eclipse.jdt.internal.compiler.Compiler.compile(Compiler.java:385)\n    at org.aspectj.ajdt.internal.core.builder.AjBuildManager.performCompilation(AjBuildManager.java:727)\n    at org.aspectj.ajdt.internal.core.builder.AjBuildManager.doBuild(AjBuildManager.java:206)\n    at org.aspectj.ajdt.internal.core.builder.AjBuildManager.batchBuild(AjBuildManager.java:140)\n    at org.aspectj.ajde.internal.CompilerAdapter.compile(CompilerAdapter.java:121)\n    at org.aspectj.ajde.internal.AspectJBuildManager$CompilerThread.run(AspectJBuildManager.java:191)"
}
'''

print('--------------- FAULT LOCALIZATION ---------------')
print(chain.run(bug_report))
print('--------------- END ---------------')


# Check the model is being used
# print(f"Model being used: {llm.model_name}")

# Check prompt template
# print(prompt.format(stack_trace={stack_trace}))