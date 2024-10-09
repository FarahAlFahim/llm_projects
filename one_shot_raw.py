# prompt templating and chaining
from langchain import PromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain



# template
template = '''You are a bug report generator. Below is an example of a stack trace and its corresponding bug report:

### Example Stack Trace:
"java.lang.NullPointerException\n\tat org.aspectj.weaver.bcel.BcelWeaver.validateOrBranch(BcelWeaver.java:584)\n\tat org.aspectj.weaver.bcel.BcelWeaver.validateBindings(BcelWeaver.java:552)\n\tat org.aspectj.weaver.bcel.BcelWeaver.rewritePointcuts(BcelWeaver.java:490)\n\tat org.aspectj.weaver.bcel.BcelWeaver.prepareForWeave(BcelWeaver.java:426)\n\tat org.aspectj.ajdt.internal.compiler.AjCompilerAdapter.weave(AjCompilerAdapter.java:248)\n\tat org.aspectj.ajdt.internal.compiler.AjCompilerAdapter.afterCompiling(AjCompilerAdapter.java:129)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.Compiler.compile(Compiler.java:385)\n\tat org.aspectj.ajdt.internal.core.builder.AjBuildManager.performCompilation(AjBuildManager.java:727)\n\tat org.aspectj.ajdt.internal.core.builder.AjBuildManager.doBuild(AjBuildManager.java:206)\n\tat org.aspectj.ajdt.internal.core.builder.AjBuildManager.batchBuild(AjBuildManager.java:140)\n\tat org.aspectj.ajde.internal.CompilerAdapter.compile(CompilerAdapter.java:121)\n\tat org.aspectj.ajde.internal.AspectJBuildManager$CompilerThread.run(AspectJBuildManager.java:191)"


### Example Bug Report:
{{
  'raw_text': "Hello,\n\n I am getting a NullPointerException when trying to compile my project. I am \njust using pointcuts with before and after advice. I have a pointcut which \nmatches 6 methods in a class and when it's included in the aspect, I get this \nerror ... and when I comment it out, everything compiles. It was working fine \nand then I restarted Eclipse and now I see this error.\n\nThanks,\nMark\n\n\n!ENTRY org.eclipse.ajdt.ui 4 0 Jun 29, 2005 16:42:43.516\n\n!MESSAGE NullPointerException thrown: null\n\n!STACK 0\n\njava.lang.NullPointerException\n\n\tat org.aspectj.weaver.bcel.BcelWeaver.validateOrBranch\n(BcelWeaver.java:584)\n\n\tat org.aspectj.weaver.bcel.BcelWeaver.validateBindings\n(BcelWeaver.java:552)\n\n\tat org.aspectj.weaver.bcel.BcelWeaver.rewritePointcuts\n(BcelWeaver.java:490)\n\n\tat org.aspectj.weaver.bcel.BcelWeaver.prepareForWeave\n(BcelWeaver.java:426)\n\n\tat org.aspectj.ajdt.internal.compiler.AjCompilerAdapter.weave\n(AjCompilerAdapter.java:248)\n\n\tat org.aspectj.ajdt.internal.compiler.AjCompilerAdapter.afterCompiling\n(AjCompilerAdapter.java:129)\n\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.Compiler.compile\n(Compiler.java:385)\n\n\tat \norg.aspectj.ajdt.internal.core.builder.AjBuildManager.performCompilation\n(AjBuildManager.java:727)\n\n\tat org.aspectj.ajdt.internal.core.builder.AjBuildManager.doBuild\n(AjBuildManager.java:206)\n\n\tat org.aspectj.ajdt.internal.core.builder.AjBuildManager.batchBuild\n(AjBuildManager.java:140)\n\n\tat org.aspectj.ajde.internal.CompilerAdapter.compile\n(CompilerAdapter.java:121)\n\n\tat org.aspectj.ajde.internal.AspectJBuildManager$CompilerThread.run\n(AspectJBuildManager.java:191)"
}}

Now you are going to be provided with a new stack trace and you will need to generate a bug report. Here's the stack trace:

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
    at org.aspectj.weaver.bcel.BcelWeaver.validateOrBranch(BcelWeaver.java:593)
    at org.aspectj.weaver.bcel.BcelWeaver.validateBindings(BcelWeaver.java:561)
    at org.aspectj.weaver.bcel.BcelWeaver.rewritePointcuts(BcelWeaver.java:499)
    at org.aspectj.weaver.bcel.BcelWeaver.prepareForWeave(BcelWeaver.java:434)
    at org.aspectj.ajdt.internal.compiler.AjCompilerAdapter.weave(AjCompilerAdapter.java:269)
    at org.aspectj.ajdt.internal.compiler.AjCompilerAdapter.afterCompiling(AjCompilerAdapter.java:165)
    at org.aspectj.org.eclipse.jdt.internal.compiler.Compiler.compile(Compiler.java:367)
    at org.aspectj.ajdt.internal.core.builder.AjBuildManager.performCompilation(AjBuildManager.java:728)
    at org.aspectj.ajdt.internal.core.builder.AjBuildManager.doBuild(AjBuildManager.java:206)
    at org.aspectj.ajdt.internal.core.builder.AjBuildManager.batchBuild(AjBuildManager.java:140)
    at org.aspectj.ajdt.ajc.AjdtCommand.doCommand(AjdtCommand.java:114)
    at org.aspectj.ajdt.ajc.AjdtCommand.runCommand(AjdtCommand.java:60)
    at org.aspectj.tools.ajc.Main.run(Main.java:324)
    at org.aspectj.tools.ajc.Main.runMain(Main.java:238)
    at org.aspectj.tools.ajc.Main.main(Main.java:82)
'''

print('--------------- BUG REPORT ---------------')
print(chain.run(stack_trace))
print('--------------- END ---------------')


# Check the model is being used
# print(f"Model being used: {llm.model_name}")

# Check prompt template
# print(prompt.format(stack_trace={stack_trace}))