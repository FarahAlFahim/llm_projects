# prompt templating and chaining
from langchain import PromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain



# template
template = '''You are a bug report generator. Below are examples of stack traces and their corresponding bug reports.

### Example 1:
#### Stack Trace (Stack Trace - 1):
java.lang.NullPointerException\n\tat org.aspectj.weaver.ResolvedType.collectInterTypeMungers(ResolvedType.java:1158)\n\tat org.aspectj.weaver.ResolvedType.collectInterTypeMungers(ResolvedType.java:1158)\n\tat org.aspectj.weaver.ResolvedType.getInterTypeMungersIncludingSupers(ResolvedType.java:1135)\n\tat org.aspectj.weaver.ResolvedType.checkInterTypeMungers(ResolvedType.java:1202)\n\tat org.aspectj.ajdt.internal.compiler.lookup.AjLookupEnvironment.weaveInterTypeDeclarations(AjLookupEnvironment.java:643)\n\tat org.aspectj.ajdt.internal.compiler.lookup.AjLookupEnvironment.weaveInterTypeDeclarations(AjLookupEnvironment.java:519)\n\tat org.aspectj.ajdt.internal.compiler.lookup.AjLookupEnvironment.createBinaryTypeFrom(AjLookupEnvironment.java:1060)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.lookup.LookupEnvironment.createBinaryTypeFrom(LookupEnvironment.java:480)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.Compiler.accept(Compiler.java:190)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.lookup.LookupEnvironment.askForType(LookupEnvironment.java:111)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.lookup.UnresolvedReferenceBinding.resolve(UnresolvedReferenceBinding.java:43)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.lookup.BinaryTypeBinding.resolveType(BinaryTypeBinding.java:53)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.lookup.BinaryTypeBinding.getMemberType(BinaryTypeBinding.java:618)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.lookup.Scope.findMemberType(Scope.java:928)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.lookup.BlockScope.getBinding(BlockScope.java:449)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.ast.QualifiedNameReference.resolveType(QualifiedNameReference.java:903)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.ast.MessageSend.resolveType(MessageSend.java:326)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.ast.MessageSend.resolveType(MessageSend.java:326)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.ast.Expression.resolve(Expression.java:829)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.ast.AbstractMethodDeclaration.resolveStatements(AbstractMethodDeclaration.java:422)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.ast.MethodDeclaration.resolveStatements(MethodDeclaration.java:178)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.ast.AbstractMethodDeclaration.resolve(AbstractMethodDeclaration.java:400)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.ast.TypeDeclaration.resolve(TypeDeclaration.java:1088)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.ast.TypeDeclaration.resolve(TypeDeclaration.java:1137)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.ast.CompilationUnitDeclaration.resolve(CompilationUnitDeclaration.java:305)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.Compiler.process(Compiler.java:519)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.Compiler.compile(Compiler.java:329)\n\tat org.aspectj.ajdt.internal.core.builder.AjBuildManager.performCompilation(AjBuildManager.java:906)\n\tat org.aspectj.ajdt.internal.core.builder.AjBuildManager.doBuild(AjBuildManager.java:289)\n\tat org.aspectj.ajdt.internal.core.builder.AjBuildManager.incrementalBuild(AjBuildManager.java:183)\n\tat org.aspectj.ajde.internal.CompilerAdapter.compile(CompilerAdapter.java:102)\n\tat org.aspectj.ajde.internal.AspectJBuildManager$CompilerThread.run(AspectJBuildManager.java:191)\n\tteneros-noc-ui/src/test/com/teneros/noc/ui/server\tConvertersTestCase.java\tUnknown\t1167948750140\t112503\n\n[from the bug popup window]\n\njava.lang.NullPointerException\nat org.aspectj.weaver.ResolvedType.collectInterTypeMungers(ResolvedType.java:1158)\nat org.aspectj.weaver.ResolvedType.collectInterTypeMungers(ResolvedType.java:1158)\nat org.aspectj.weaver.ResolvedType.getInterTypeMungersIncludingSupers(ResolvedType.java:1135)\nat org.aspectj.weaver.ResolvedType.checkInterTypeMungers(ResolvedType.java:1202)\nat org.aspectj.ajdt.internal.compiler.lookup.AjLookupEnvironment.weaveInt ... Adapter.java:102)\nat org.aspectj.ajde.internal.AspectJBuildManager$CompilerThread.run(AspectJBuildManager.java:191)

#### Bug Report:
{{
  "raw_text": "Sorry, no test code.  This occurs whenever I save any file in this project after it gets into a broken state.\n\nSeems to center around a test case that, as far as I can tell does not have any aspects applied.  If I do not change this test class things go well.\n\n[from the Problems tab]\n\nSeverity and Description\tPath\tResource\tLocation\tCreation Time\tId\nInternal compiler error",
  "stackTrace": <Refer to Stack Trace - 1>
}}

### Example 2:
#### Stack Trace (Stack Trace - 2):
java.lang.StackOverflowError\n\tat java.lang.ref.ReferenceQueue.poll(ReferenceQueue.java:82)\n\tat java.util.WeakHashMap.expungeStaleEntries(WeakHashMap.java:274)\n\tat java.util.WeakHashMap.getTable(WeakHashMap.java:302)\n\tat java.util.WeakHashMap.get(WeakHashMap.java:349)\n\tat java.util.Collections$SynchronizedMap.get(Collections.java:1975)\n\tat org.aspectj.weaver.World$TypeMap.get(World.java:1036)\n\tat org.aspectj.weaver.World.resolve(World.java:255)\n\tat org.aspectj.weaver.World.resolve(World.java:192)\n\tat org.aspectj.weaver.UnresolvedType.resolve(UnresolvedType.java:625)\n\tat org.aspectj.weaver.ReferenceType.getRawType(ReferenceType.java:733)\n\tat org.aspectj.weaver.ReferenceType.isAssignableFrom(ReferenceType.java:389)\n\tat org.aspectj.weaver.ReferenceType.isAssignableFrom(ReferenceType.java:363)\n\tat org.aspectj.weaver.ReferenceType.isAssignableFrom(ReferenceType.java:389)\n\tat org.aspectj.weaver.ReferenceType.isAssignableFrom(ReferenceType.java:363)\n\tat org.aspectj.weaver.ReferenceType.isAssignableFrom(ReferenceType.java:389)\n\tat org.aspectj.weaver.ReferenceType.isAssignableFrom(ReferenceType.java:363)\n\tat org.aspectj.weaver.ReferenceType.isAssignableFrom(ReferenceType.java:389)\n\tat org.aspectj.weaver.ReferenceType.isAssignableFrom(ReferenceType.java:363)\n\tat org.aspectj.weaver.ReferenceType.isAssignableFrom(ReferenceType.java:389)\n\tat org.aspectj.weaver.ReferenceType.isAssignableFrom(ReferenceType.java:363)

#### Bug Report:
{{
  "raw_text": 'User-Agent:       Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.0; Trident/4.0; SLCC1; .NET CLR 2.0.50727; Media Center PC 5.0; InfoPath.2; .NET CLR 3.5.30729; .NET CLR 3.0.30618; OfficeLivePatch.1.3; OfficeLiveConnector.1.4)\nBuild Identifier: AspectJ 1.6.5\n\nWhen compiling one of my classes with iacj, I get the following output:\n\n\t\nException thrown from AspectJ 1.6.5\n\nThis might be logged as a bug already -- find current bugs at\n  http://bugs.eclipse.org/bugs/buglist.cgi?product=AspectJ&component=Compiler\n\nBugs for exceptions thrown have titles File:line from the top stack, \ne.g., "SomeFile.java:243"\n\nIf you don\'t find the exception below in a bug, please add a new bug\nat http://bugs.eclipse.org/bugs/enter_bug.cgi?product=AspectJ\nTo make the bug a priority, please include a test program\nthat can reproduce this exception.\n\nwhen weaving type com.webroot.models.account.OneToMany\nwhen weaving classes \nwhen weaving \nwhen batch building BuildConfig[null] #Files=198 AopXmls=#0\nnull',
  "stackTrace": <Refer to Stack Trace - 2>
}}

### Example 3:
#### Stack Trace (Stack Trace - 3):
java.lang.NullPointerException\n\tat org.aspectj.weaver.ReferenceType.isAssignableFrom(ReferenceType.java:281)\n\tat org.aspectj.weaver.ReferenceType.isAssignableFrom(ReferenceType.java:353)\n\tat org.aspectj.weaver.ReferenceType.isAssignableFrom(ReferenceType.java:353)\n\tat org.aspectj.weaver.ResolvedType.isTopmostImplementor(ResolvedType.java:1729)\n\tat org.aspectj.weaver.ResolvedTypeMunger.matches(ResolvedTypeMunger.java:113)\n\tat org.aspectj.weaver.ConcreteTypeMunger.matches(ConcreteTypeMunger.java:65)\n\tat org.aspectj.ajdt.internal.compiler.lookup.AjLookupEnvironment.weaveInterTypeDeclarations(AjLookupEnvironment.java:630)\n\tat org.aspectj.ajdt.internal.compiler.lookup.AjLookupEnvironment.weaveInterTypeDeclarations(AjLookupEnvironment.java:519)\n\tat org.aspectj.ajdt.internal.compiler.lookup.AjLookupEnvironment.createBinaryTypeFrom(AjLookupEnvironment.java:1060)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.lookup.LookupEnvironment.createBinaryTypeFrom(LookupEnvironment.java:480)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.Compiler.accept(Compiler.java:190)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.lookup.LookupEnvironment.askForType(LookupEnvironment.java:111)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.lookup.UnresolvedReferenceBinding.resolve(UnresolvedReferenceBinding.java:43)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.lookup.BinaryTypeBinding.resolveType(BinaryTypeBinding.java:53)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.lookup.BinaryTypeBinding.getMemberType(BinaryTypeBinding.java:618)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.lookup.CompilationUnitScope.findImport(CompilationUnitScope.java:444)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.lookup.CompilationUnitScope.findSingleImport(CompilationUnitScope.java:466)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.lookup.CompilationUnitScope.faultInImports(CompilationUnitScope.java:331)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.lookup.CompilationUnitScope.faultInTypes(CompilationUnitScope.java:400)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.Compiler.process(Compiler.java:512)\n\tat org.aspectj.org.eclipse.jdt.internal.compiler.Compiler.compile(Compiler.java:329)\n\tat org.aspectj.ajdt.internal.core.builder.AjBuildManager.performCompilation(AjBuildManager.java:906)\n\tat org.aspectj.ajdt.internal.core.builder.AjBuildManager.doBuild(AjBuildManager.java:289)\n\tat org.aspectj.ajdt.internal.core.builder.AjBuildManager.incrementalBuild(AjBuildManager.java:183)\n\tat org.aspectj.ajde.internal.CompilerAdapter.compile(CompilerAdapter.java:102)\n\tat org.aspectj.ajde.internal.AspectJBuildManager$CompilerThread.run(AspectJBuildManager.java:191)

#### Bug Report:
{{
  "raw_text": 'I think I have a similar bug: \nSystem: eclipse 3.2.1\nADJT: 1.4.1\n\nOnce in a while, if I edit a java file (from eclipse) that "use an Aspect modified object", I get the error below. It used to work with AJDT 1.4.0. If I clean the project and rebuild all, and then I am fine.  \n\n--- error display in the "error alert dialog box" ',
  "stackTrace": <Refer to Stack Trace - 3>
}}

### Example 4:
#### Stack Trace (Stack Trace - 4):
java.lang.ClassCastException:\norg.aspectj.org.eclipse.jdt.core.dom.DefaultCommentMapper$CommentMapperVisitor\n\tat\norg.aspectj.org.eclipse.jdt.core.dom.PointcutDeclaration.accept0(PointcutDeclaration.java:291)\n\tat org.aspectj.org.eclipse.jdt.core.dom.ASTNode.accept(ASTNode.java:2450)\n\tat org.aspectj.org.eclipse.jdt.core.dom.ASTNode.acceptChildren(ASTNode.java:2520)\n\tat\norg.aspectj.org.eclipse.jdt.core.dom.AspectDeclaration.accept0(AspectDeclaration.java:94)\n\tat org.aspectj.org.eclipse.jdt.core.dom.ASTNode.accept(ASTNode.java:2450)\n\tat org.aspectj.org.eclipse.jdt.core.dom.ASTNode.acceptChildren(ASTNode.java:2520)\n\tat\norg.aspectj.org.eclipse.jdt.core.dom.CompilationUnit.accept0(CompilationUnit.java:299)\n\tat org.aspectj.org.eclipse.jdt.core.dom.ASTNode.accept(ASTNode.java:2450)\n\tat\norg.aspectj.org.eclipse.jdt.core.dom.DefaultCommentMapper.initialize(DefaultCommentMapper.java:242)\n\tat\norg.aspectj.org.eclipse.jdt.core.dom.CompilationUnit.initCommentMapper(CompilationUnit.java:483)\n\tat\norg.aspectj.org.eclipse.jdt.core.dom.AjASTConverter.convert(AjASTConverter.java:1025)\n\tat\norg.aspectj.org.eclipse.jdt.core.dom.CompilationUnitResolver.convert(CompilationUnitResolver.java:252)\n\tat\norg.aspectj.org.eclipse.jdt.core.dom.ASTParser.internalCreateAST(ASTParser.java:803)\n\tat org.aspectj.org.eclipse.jdt.core.dom.ASTParser.createAST(ASTParser.java:591)\n\tat br.ufrgs.inf.badSmells.BBB.check(BBB.java:15)\n\tat br.ufrgs.inf.badSmells.BBB.main(BBB.java:23)

#### Bug Report:
{{
  "raw_text": 'Hi,\n\nCould you please add the following test method to the ASTVisitorTest? (It also\nraises a ClassCastException).\n\nbtw: This bug was initially an enhancement about the work in the AST features.\nDon\'t you think that it\'s better to split this bug (one for the\nClassCastException and another to the enhancements of AST) and give them\ndifferent priority and severity?\n\nBest Regards,\nEduardo Piveta\n----------------------------------------------------------------\npublic class ASTVisitorTest extends TestCase {{\n\t\n// from bug 110465 - will currently break because of casts\n...\npublic void testAspectWithCommentThenPointcut() {{\n   a.check("aspect A{{ /** */ pointcut x(); }}");\n}}\n}}\n\nException in thread "main"',
  "stackTrace": <Refer to Stack Trace - 4>
}}

### Example 5:
#### Stack Trace (Stack Trace - 5):
java.lang.NullPointerException\n\tat org.aspectj.weaver.reflect.ShadowMatchImpl$RuntimeTestEvaluator.visit(ShadowMatchImpl.java:140)\n\tat org.aspectj.weaver.ast.Instanceof.accept(Instanceof.java:29)\n\tat org.aspectj.weaver.reflect.ShadowMatchImpl$RuntimeTestEvaluator.matches(ShadowMatchImpl.java:121)\n\tat org.aspectj.weaver.reflect.ShadowMatchImpl.matchesJoinPoint(ShadowMatchImpl.java:78)\n\nThis bug occurs in aspectJ 1.6.1 and 1.6.8 so i think all versions in between are affected as well. I\'m using aspectJ together with Spring 2.5.6 but i think that does not matter.\n\nExpected behavior:\nWhen using @Before("args(myId,..)") to match all methods that have an argument of type MyInterface as first argument (see steps to reproduce), the methods declared argument types should be used to determine if the method matches when null is passed as first argument.\n\nActual Behavior:\nNullPointerException is thrown from org.aspectj.weaver.reflect.ShadowMatchImpl$RuntimeTestEvaluator.visit(ShadowMatchImpl.java:140)

#### Bug Report:
{{
  "raw_text": "Build Identifier: \n\nThis bug is related to Bug 257833. I\'m wondering why nobody has faced and reported that bug before?!?!",
  "stackTrace": <Refer to Stack Trace - 5>
}}

### Example 6:
#### Stack Trace (Stack Trace - 6):
java.lang.NullPointerException\nat org.aspectj.ajdt.internal.compiler.ast.InterTypeMethodDeclaration.resolve(InterTypeMethodDeclaration.java:90)\nat org.aspectj.org.eclipse.jdt.internal.compiler.ast.TypeDeclaration.resolve(TypeDeclaration.java:1088)\nat org.aspectj.ajdt.internal.compiler.ast.AspectDeclaration.resolve(AspectDeclaration.java:116)\nat org.aspectj.org.eclipse.jdt.internal.compiler.ast.TypeDeclaration.resolve(TypeDeclaration.java:1137)\nat org.aspectj.org.eclipse.jdt.internal.compiler.ast.CompilationUnitDeclaration.resolve(CompilationUnitDeclaration.java:305)\nat org.aspectj.org.eclipse.jdt.internal.compiler.Compiler.process(Compiler.java:519)\nat org.aspectj.org.eclipse.jdt.internal.compiler.Compiler.compile(Compiler.java:329)\nat org.aspectj.ajdt.internal.core.builder.AjBuildManager.performCompilation(AjBuildManager.java:887)\nat org.aspectj.ajdt.internal.core.builder.AjBuildManager.doBuild(AjBuildManager.java:244)\nat org.aspectj.ajdt.internal.core.builder.AjBuildManager.doBuild(AjBuildManager.java:199)\nat org.aspectj.ajdt.internal.core.builder.AjBuildManager.incrementalBuild(AjBuildManager.java:170)\nat org.aspectj.ajde.internal.CompilerAdapter.compile(CompilerAdapter.java:117)\nat org.aspectj.ajde.internal.AspectJBuildManager$CompilerThread.run(AspectJBuildManager.java:191)

#### Bug Report:
{{
  "raw_text": "The following exception is caused by a duplicate inter-type introduction method declaration in an aspect. Removing the duplicate method solves the problem.",
  "stackTrace": <Refer to Stack Trace - 6>
}}

### Now, based on the following stack trace, generate a bug report in JSON format:

#### Stack Trace:
{stack_trace}

Please generate the full bug report using the following format:

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
stack_trace_list = ['''java.util.zip.ZipException: error in opening zip file\nCan't open archive: struts.jar: java.util.zip.ZipException: error in opening \nzip file\norg.aspectj.weaver.BCException: Can't open archive: struts.jar: \njava.util.zip.ZipException: error in opening zip file\n\tat org.aspectj.weaver.bcel.ClassPathManager$ZipFileEntry.ensureOpen\n(ClassPathManager.java:253)\n\tat org.aspectj.weaver.bcel.ClassPathManager$ZipFileEntry.find\n(ClassPathManager.java:225)\n\tat org.aspectj.weaver.bcel.ClassPathManager.find\n(ClassPathManager.java:92)\n\tat org.aspectj.weaver.bcel.BcelWorld.lookupJavaClass\n(BcelWorld.java:259)\n\tat org.aspectj.weaver.bcel.BcelWorld.resolveDelegate\n(BcelWorld.java:234)\n\tat org.aspectj.weaver.World.resolveToReferenceType(World.java:282)\n\tat org.aspectj.weaver.World.resolve(World.java:205)\n\tat org.aspectj.weaver.World.resolve(World.java:127)\n\tat org.aspectj.weaver.World.resolve(World.java:250)\n\tat org.aspectj.ajdt.internal.core.builder.AjBuildManager.initBcelWorld\n(AjBuildManager.java:594)\n\tat org.aspectj.ajdt.internal.core.builder.AjBuildManager.doBuild\n(AjBuildManager.java:189)\n\tat org.aspectj.ajdt.internal.core.builder.AjBuildManager.batchBuild\n(AjBuildManager.java:140)\n\tat org.aspectj.ajdt.ajc.AjdtCommand.doCommand(AjdtCommand.java:112)\n\tat org.aspectj.ajdt.ajc.AjdtCommand.runCommand(AjdtCommand.java:60)\n\tat org.aspectj.tools.ajc.Main.run(Main.java:324)\n\tat org.aspectj.tools.ajc.Main.runMain(Main.java:238)\n\tat org.aspectj.tools.ajc.Main.main(Main.java:82)''',
                    '''java.lang.NullPointerException\nat org.aspectj.weaver.bcel.BcelWeaver.weave(BcelWeaver.java:1015)\nat org.aspectj.ajdt.internal.compiler.AjCompilerAdapter.weave\n(AjCompilerAdapter.java:300)\nat org.aspectj.ajdt.internal.compiler.AjCompilerAdapter.afterCompiling\n(AjCompilerAdapter.java:178)\nat \norg.aspectj.ajdt.internal.compiler.CompilerAdapter.ajc$afterReturning$org_aspec\ntj_ajdt_internal_compiler_CompilerAdapter$2$f9cc9ca0(CompilerAdapter.aj:70)\nat org.aspectj.org.eclipse.jdt.internal.compiler.Compiler.compile\n(Compiler.java:367)\nat org.aspectj.ajdt.internal.core.builder.AjBuildManager.performCompilation\n(AjBuildManager.java:759)\nat org.aspectj.ajdt.internal.core.builder.AjBuildManager.doBuild\n(AjBuildManager.java:249)\nat org.aspectj.ajdt.internal.core.builder.AjBuildManager.incrementalBuild\n(AjBuildManager.java:158)\nat org.aspectj.ajde.internal.CompilerAdapter.compile(CompilerAdapter.java:117)\nat org.aspectj.ajde.internal.AspectJBuildManager$CompilerThread.run\n(AspectJBuildManager.java:191)''',
                    '''java.lang.IllegalStateException: Can't ask to parameterize a member of a non-generic type\n\tat org.aspectj.weaver.ResolvedMemberImpl.parameterizedWith(ResolvedMemberImpl.java:605)\n\tat org.aspectj.weaver.ResolvedMemberImpl.parameterizedWith(ResolvedMemberImpl.java:590)\n\tat org.aspectj.weaver.ReferenceType.getDeclaredMethods(ReferenceType.java:402)\n\tat org.aspectj.weaver.reflect.ReflectionBasedReferenceTypeDelegateTest.testGetDeclaredMethods(ReflectionBasedReferenceTypeDelegateTest.java:134)\n\tat sun.reflect.NativeMethodAccessorImpl.invoke0(Native Method)\n\tat sun.reflect.NativeMethodAccessorImpl.invoke(NativeMethodAccessorImpl.java:39)\n\tat sun.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:25)\n\tat java.lang.reflect.Method.invoke(Method.java:585)\n\tat junit.framework.TestCase.runTest(TestCase.java:154)\n\tat junit.framework.TestCase.runBare(TestCase.java:127)\n\tat junit.framework.TestResult$1.protect(TestResult.java:106)\n\tat junit.framework.TestResult.runProtected(TestResult.java:124)\n\tat junit.framework.TestResult.run(TestResult.java:109)\n\tat junit.framework.TestCase.run(TestCase.java:118)\n\tat junit.framework.TestSuite.runTest(TestSuite.java:208)\n\tat junit.framework.TestSuite.run(TestSuite.java:203)\n\tat org.eclipse.jdt.internal.junit.runner.RemoteTestRunner.runTests(RemoteTestRunner.java:478)\n\tat org.eclipse.jdt.internal.junit.runner.RemoteTestRunner.run(RemoteTestRunner.java:344)\n\tat org.eclipse.jdt.internal.junit.runner.RemoteTestRunner.main(RemoteTestRunner.java:196)''']




for stack_trace in stack_trace_list:
    print('--------------- BUG REPORT ---------------')
    print(chain.run(stack_trace))
    print('--------------- END ---------------')
    print()
    print()


# Check the model is being used
# print(f"Model being used: {llm.model_name}")

# Check prompt template
# print(prompt.format(stack_trace={stack_trace}))