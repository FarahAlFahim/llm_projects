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
{'attachment_id': None, 'bug_id': 117622, 'count': 11, 'creation_time': '2005-11-23T16:55:35Z', 'creator': 'rbodkin+LISTS@gmail.com', 'id': 570508, 'is_private': False, 'raw_text': "Ok I see the first two bugs are fixed (thanks!). Now I'm seeing another old friend when I run my tests (this may be the same one that you noted you can recreate and are trying to fix, Andy). See stack trace below. I will work on recreating the infinite recursion bug and submit in a separate bug report (for sanity's sake).\n\njava.lang.IllegalStateException: Can't ask to parameterize a member of a non-generic type\n\tat org.aspectj.weaver.ResolvedMemberImpl.parameterizedWith(ResolvedMemberImpl.java:605)\n\tat org.aspectj.weaver.ResolvedMemberImpl.parameterizedWith(ResolvedMemberImpl.java:590)\n\tat org.aspectj.weaver.ReferenceType.getDeclaredMethods(ReferenceType.java:402)\n\tat org.aspectj.weaver.reflect.ReflectionBasedReferenceTypeDelegateTest.testGetDeclaredMethods(ReflectionBasedReferenceTypeDelegateTest.java:134)\n\tat sun.reflect.NativeMethodAccessorImpl.invoke0(Native Method)\n\tat sun.reflect.NativeMethodAccessorImpl.invoke(NativeMethodAccessorImpl.java:39)\n\tat sun.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:25)\n\tat java.lang.reflect.Method.invoke(Method.java:585)\n\tat junit.framework.TestCase.runTest(TestCase.java:154)\n\tat junit.framework.TestCase.runBare(TestCase.java:127)\n\tat junit.framework.TestResult$1.protect(TestResult.java:106)\n\tat junit.framework.TestResult.runProtected(TestResult.java:124)\n\tat junit.framework.TestResult.run(TestResult.java:109)\n\tat junit.framework.TestCase.run(TestCase.java:118)\n\tat junit.framework.TestSuite.runTest(TestSuite.java:208)\n\tat junit.framework.TestSuite.run(TestSuite.java:203)\n\tat org.eclipse.jdt.internal.junit.runner.RemoteTestRunner.runTests(RemoteTestRunner.java:478)\n\tat org.eclipse.jdt.internal.junit.runner.RemoteTestRunner.run(RemoteTestRunner.java:344)\n\tat org.eclipse.jdt.internal.junit.runner.RemoteTestRunner.main(RemoteTestRunner.java:196)\n\n", 'tags': [], 'text': "Ok I see the first two bugs are fixed (thanks!). Now I'm seeing another old friend when I run my tests (this may be the same one that you noted you can recreate and are trying to fix, Andy). See stack trace below. I will work on recreating the infinite recursion bug and submit in a separate bug report (for sanity's sake).\n\njava.lang.IllegalStateException: Can't ask to parameterize a member of a non-generic type\n\tat org.aspectj.weaver.ResolvedMemberImpl.parameterizedWith(ResolvedMemberImpl.java:605)\n\tat org.aspectj.weaver.ResolvedMemberImpl.parameterizedWith(ResolvedMemberImpl.java:590)\n\tat org.aspectj.weaver.ReferenceType.getDeclaredMethods(ReferenceType.java:402)\n\tat org.aspectj.weaver.reflect.ReflectionBasedReferenceTypeDelegateTest.testGetDeclaredMethods(ReflectionBasedReferenceTypeDelegateTest.java:134)\n\tat sun.reflect.NativeMethodAccessorImpl.invoke0(Native Method)\n\tat sun.reflect.NativeMethodAccessorImpl.invoke(NativeMethodAccessorImpl.java:39)\n\tat sun.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:25)\n\tat java.lang.reflect.Method.invoke(Method.java:585)\n\tat junit.framework.TestCase.runTest(TestCase.java:154)\n\tat junit.framework.TestCase.runBare(TestCase.java:127)\n\tat junit.framework.TestResult$1.protect(TestResult.java:106)\n\tat junit.framework.TestResult.runProtected(TestResult.java:124)\n\tat junit.framework.TestResult.run(TestResult.java:109)\n\tat junit.framework.TestCase.run(TestCase.java:118)\n\tat junit.framework.TestSuite.runTest(TestSuite.java:208)\n\tat junit.framework.TestSuite.run(TestSuite.java:203)\n\tat org.eclipse.jdt.internal.junit.runner.RemoteTestRunner.runTests(RemoteTestRunner.java:478)\n\tat org.eclipse.jdt.internal.junit.runner.RemoteTestRunner.run(RemoteTestRunner.java:344)\n\tat org.eclipse.jdt.internal.junit.runner.RemoteTestRunner.main(RemoteTestRunner.java:196)\n\n", 'time': '2005-11-23T16:55:35Z'}

'''

print('--------------- BUG REPORT ---------------')
print(chain.run(bug_report))
print('--------------- END ---------------')


# Check the model is being used
# print(f"Model being used: {llm.model_name}")

# Check prompt template
# print(prompt.format(stack_trace={stack_trace}))