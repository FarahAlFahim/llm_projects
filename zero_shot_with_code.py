# prompt templating and chaining
from langchain import PromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain



# template
template = '''You are a bug report generator. You are given a stack trace and its corresponding source code below:

Stack Trace:
{stack_trace}

Source Code:
{source_code}


Based on the given stack trace and the related source code, generate a bug report in JSON format containing the title, description, steps to reproduce, actual behavior, possible cause (if applicable), and the stack trace. 

Generate the complete bug report in the following JSON structure:

{{
  "title": "<title>",
  "description": {{
    "stepsToReproduce": [
      "<Step 1>",
      "<Step 2>",
      "<Step 3>"
    ],
    "actualBehavior": "<What happens instead>",
    "possibleCause": "<Insights or hypotheses about the issue (optional)>"
  }},
  "stackTrace": "<stack_trace>"
}}
'''





prompt = PromptTemplate.from_template(template)
llm = ChatOpenAI(model='gpt-4o-mini', temperature = 0)

chain = LLMChain(llm=llm, prompt=prompt)



# stack trace
stack_trace = '''
java.lang.NullPointerException
    at org.aspectj.weaver.bcel.BcelWeaver.weave(BcelWeaver.java:1015)
    at org.aspectj.ajdt.internal.compiler.AjCompilerAdapter.weave
    (AjCompilerAdapter.java:300)
    at org.aspectj.ajdt.internal.compiler.AjCompilerAdapter.afterCompiling
    (AjCompilerAdapter.java:178)
    at 
    org.aspectj.ajdt.internal.compiler.CompilerAdapter.ajc$afterReturning$org_aspec
    tj_ajdt_internal_compiler_CompilerAdapter$2$f9cc9ca0(CompilerAdapter.aj:70)
    at org.aspectj.org.eclipse.jdt.internal.compiler.Compiler.compile
    (Compiler.java:367)
    at org.aspectj.ajdt.internal.core.builder.AjBuildManager.performCompilation
    (AjBuildManager.java:759)
    at org.aspectj.ajdt.internal.core.builder.AjBuildManager.doBuild
    (AjBuildManager.java:249)
    at org.aspectj.ajdt.internal.core.builder.AjBuildManager.incrementalBuild
    (AjBuildManager.java:158)
    at org.aspectj.ajde.internal.CompilerAdapter.compile(CompilerAdapter.java:117)
    at org.aspectj.ajde.internal.AspectJBuildManager$CompilerThread.run
    (AspectJBuildManager.java:191)
'''


# source code
source_code = '''
// class: BcelWeaver.java, method: weave()
public Collection weave(File file) throws IOException {
    OutputStream os = FileUtil.makeOutputStream(file);
    this.zipOutputStream = new ZipOutputStream(os);
    prepareForWeave();
    Collection c = weave( new IClassFileProvider() {
        
        public Iterator getClassFileIterator() {
            return addedClasses.iterator();
        }
        
        public IWeaveRequestor getRequestor() {
            return new IWeaveRequestor() {
                public void acceptResult(UnwovenClassFile result) {
                    try {
                        writeZipEntry(result.filename, result.bytes);
                    } catch(IOException ex) {}
                }
                public void processingReweavableState() {}
                public void addingTypeMungers() {}
                public void weavingAspects() {}
                public void weavingClasses() {}
                public void weaveCompleted() {}
            };
        }
    });
//     /* BUG 40943*/
//     dumpResourcesToOutJar();
    zipOutputStream.close();  //this flushes and closes the acutal file
    return c;
}


// class: AjCompilerAdapter.java, method: weave()
private void weave() throws IOException {
    // ensure weaver state is set up correctly
    for (Iterator iter = resultsPendingWeave.iterator(); iter.hasNext();) {
        InterimCompilationResult iresult = (InterimCompilationResult) iter.next();
        for (int i = 0; i < iresult.unwovenClassFiles().length; i++) {
            weaver.addClassFile(iresult.unwovenClassFiles()[i]);
        }   
    }
    
    weaver.prepareForWeave();
    if (weaver.needToReweaveWorld()) {
        if (!isBatchCompile) addAllKnownClassesToWeaveList(); // if it's batch, they're already on the list...
        resultsPendingWeave.addAll(getBinarySourcesFrom(binarySourceSetForFullWeave));
    } else {
        Map binarySourcesToAdd = binarySourceProvider.getBinarySourcesForThisWeave();
        resultsPendingWeave.addAll(getBinarySourcesFrom(binarySourcesToAdd));
    }
    
//  if (isBatchCompile) {
//   resultsPendingWeave.addAll(getBinarySourcesFrom(binarySourceSetForFullWeave));  
//   // passed into the compiler, the set of classes in injars and inpath...
//  } else if (weaver.needToReweaveWorld()) {
//   addAllKnownClassesToWeaveList();
//   resultsPendingWeave.addAll(getBinarySourcesFrom(binarySourceSetForFullWeave));
//  }
    try {
        weaver.weave(new WeaverAdapter(this,weaverMessageHandler,progressListener));
    } finally {
        // ???: is this the right point for this? After weaving has finished clear the caches.
        CflowPointcut.clearCaches();
    }
}


// class: AjCompilerAdapter.java, method: afterCompiling()
public void afterCompiling(CompilationUnitDeclaration[] units) {
    try {
        if (isXNoWeave || (reportedErrors && !proceedOnError)) {
            // no point weaving... just tell the requestor we're done
            notifyRequestor();
        } else {
            weave();  // notification happens as weave progresses...
        }
    } catch (IOException ex) {
        AbortCompilation ac = new AbortCompilation(null,ex);
        throw ac;
    } catch (RuntimeException rEx) {
        if (rEx instanceof AbortCompilation) throw rEx; // Don't wrap AbortCompilation exceptions!
        
        // This will be unwrapped in Compiler.handleInternalException() and the nested
        // RuntimeException thrown back to the original caller - which is AspectJ
        // which will then then log it as a compiler problem.
        throw new AbortCompilation(true,rEx);
    }
}


// class: AjBuildManager.java, method: performCompilation()
public void performCompilation(List files) {
    if (progressListener != null) {
        compiledCount=0;
        sourceFileCount = files.size();
        progressListener.setText("compiling source files");
    }
    //System.err.println("got files: " + files);
    String[] filenames = new String[files.size()];
    String[] encodings = new String[files.size()];
    //System.err.println("filename: " + this.filenames);
    for (int i=0; i < files.size(); i++) {
        filenames[i] = ((File)files.get(i)).getPath();
    }
    
    List cps = buildConfig.getFullClasspath();
    Dump.saveFullClasspath(cps);
    String[] classpaths = new String[cps.size()];
    for (int i=0; i < cps.size(); i++) {
        classpaths[i] = (String)cps.get(i);
    }
    
    //System.out.println("compiling");
    environment = getLibraryAccess(classpaths, filenames);
    
    if (!state.classesFromName.isEmpty()) {
        environment = new StatefulNameEnvironment(environment, state.classesFromName);
    }
    
    org.aspectj.ajdt.internal.compiler.CompilerAdapter.setCompilerAdapterFactory(this);
    org.aspectj.org.eclipse.jdt.internal.compiler.Compiler compiler = 
        new org.aspectj.org.eclipse.jdt.internal.compiler.Compiler(environment,
                                                                   DefaultErrorHandlingPolicies.proceedWithAllProblems(),
                                                                   buildConfig.getOptions().getMap(),
                                                                   getBatchRequestor(),
                                                                   getProblemFactory());
    
    CompilerOptions options = compiler.options;
    
    options.produceReferenceInfo = true; //TODO turn off when not needed
    
    try {
        compiler.compile(getCompilationUnits(filenames, encodings));
    } catch (OperationCanceledException oce) {
        handler.handleMessage(new Message("build cancelled:"+oce.getMessage(),IMessage.WARNING,null,null));
    }
    // cleanup
    environment.cleanup();
    environment = null;
}


// class: AjBuildManager.java, method: doBuild()
protected boolean doBuild(
                          AjBuildConfig buildConfig, 
                          IMessageHandler baseHandler, 
                          boolean batch) throws IOException, AbortException {
    boolean ret = true;
    batchCompile = batch;
    
    try {
        if (batch) {
            this.state = new AjState(this);
        }
        
        boolean canIncremental = state.prepareForNextBuild(buildConfig);
        if (!canIncremental && !batch) { // retry as batch?
            return doBuild(buildConfig, baseHandler, true);
        }
        this.handler = 
            CountingMessageHandler.makeCountingMessageHandler(baseHandler);
        // XXX duplicate, no? remove?
        String check = checkRtJar(buildConfig);
        if (check != null) {
            if (FAIL_IF_RUNTIME_NOT_FOUND) {
                MessageUtil.error(handler, check);
                return false;
            } else {
                MessageUtil.warn(handler, check);
            }
        }
        // if (batch) {
        setBuildConfig(buildConfig);
        //}
        if (batch || !AsmManager.attemptIncrementalModelRepairs) {
//                if (buildConfig.isEmacsSymMode() || buildConfig.isGenerateModelMode()) { 
            setupModel(buildConfig);
//                }
        }
        if (batch) {
            initBcelWorld(handler);
        }
        if (handler.hasErrors()) {
            return false;
        }
        
        if (buildConfig.getOutputJar() != null) {
            if (!openOutputStream(buildConfig.getOutputJar())) return false;
        }
        
        if (batch) {
            // System.err.println("XXXX batch: " + buildConfig.getFiles());
            if (buildConfig.isEmacsSymMode() || buildConfig.isGenerateModelMode()) {  
                getWorld().setModel(AsmManager.getDefault().getHierarchy());
                // in incremental build, only get updated model?
            }
            binarySourcesForTheNextCompile = state.getBinaryFilesToCompile(true);
            performCompilation(buildConfig.getFiles());
            if (handler.hasErrors()) {
                return false;
            }
            
            if (AsmManager.isReporting())
                AsmManager.getDefault().reportModelInfo("After a batch build");
            
        } else {
// done already?
//                if (buildConfig.isEmacsSymMode() || buildConfig.isGenerateModelMode()) {  
//                    bcelWorld.setModel(StructureModelManager.INSTANCE.getStructureModel());
//                }
            // System.err.println("XXXX start inc ");
            binarySourcesForTheNextCompile = state.getBinaryFilesToCompile(true);
            List files = state.getFilesToCompile(true);
            if (buildConfig.isEmacsSymMode() || buildConfig.isGenerateModelMode())
                if (AsmManager.attemptIncrementalModelRepairs)
                AsmManager.getDefault().processDelta(files,state.addedFiles,state.deletedFiles);
            boolean hereWeGoAgain = !(files.isEmpty() && binarySourcesForTheNextCompile.isEmpty());
            for (int i = 0; (i < 5) && hereWeGoAgain; i++) {
                // System.err.println("XXXX inc: " + files);
                
                performCompilation(files);
                if (handler.hasErrors() || (progressListener!=null && progressListener.isCancelledRequested())) {
                    return false;
                } 
                binarySourcesForTheNextCompile = state.getBinaryFilesToCompile(false);
                files = state.getFilesToCompile(false);
                hereWeGoAgain = !(files.isEmpty() && binarySourcesForTheNextCompile.isEmpty());
                // TODO Andy - Needs some thought here...
                // I think here we might want to pass empty addedFiles/deletedFiles as they were
                // dealt with on the first call to processDelta - we are going through this loop
                // again because in compiling something we found something else we needed to
                // rebuild.  But what case causes this?
                if (hereWeGoAgain) 
                    if (buildConfig.isEmacsSymMode() || buildConfig.isGenerateModelMode())
                    if (AsmManager.attemptIncrementalModelRepairs)
                    AsmManager.getDefault().processDelta(files,state.addedFiles,state.deletedFiles);
            }
            if (!files.isEmpty()) {
                return batchBuild(buildConfig, baseHandler);
            } else {                
                if (AsmManager.isReporting()) 
                    AsmManager.getDefault().reportModelInfo("After an incremental build");
            }
        }
        
        // XXX not in Mik's incremental
        if (buildConfig.isEmacsSymMode()) {
            new org.aspectj.ajdt.internal.core.builder.EmacsStructureModelManager().externalizeModel();
        }
        // have to tell state we succeeded or next is not incremental
        state.successfulCompile(buildConfig,batch);
        
        copyResourcesToDestination();
        /*boolean weaved = *///weaveAndGenerateClassFiles();
        // if not weaved, then no-op build, no model changes
        // but always returns true
        // XXX weaved not in Mik's incremental
        if (buildConfig.isGenerateModelMode()) {
            AsmManager.getDefault().fireModelUpdated();  
        }
    } finally {
        if (zos != null) {
            closeOutputStream(buildConfig.getOutputJar());
        }
        ret = !handler.hasErrors();
        getBcelWorld().tidyUp();
        // bug 59895, don't release reference to handler as may be needed by a nested call
        //handler = null;
    }
    return ret;
}


// class: AjBuildManager.java, method: incrementalBuild()
public boolean incrementalBuild(
                                AjBuildConfig buildConfig, 
                                IMessageHandler baseHandler) 
    throws IOException, AbortException {
    return doBuild(buildConfig, baseHandler, false);
}


// class: CompilerAdapter.java, method: compile()
public boolean compile(String configFile, BuildProgressMonitor progressMonitor, boolean buildModel) {
    if (configFile == null) {
        Ajde.getDefault().getErrorHandler().handleError("Tried to build null config file.");
    }
    init();
    try { 
        AjBuildConfig buildConfig = genBuildConfig(configFile);
        if (buildConfig == null) {
            return false;
        }
        buildConfig.setGenerateModelMode(buildModel);
        currNotifier = new BuildNotifierAdapter(progressMonitor, buildManager);  
        buildManager.setProgressListener(currNotifier);
        messageHandler.setBuildNotifierAdapter(currNotifier);
        
        String rtInfo = buildManager.checkRtJar(buildConfig); // !!! will get called twice
        if (rtInfo != null) {
            Ajde.getDefault().getErrorHandler().handleWarning(
                                                              "AspectJ Runtime error: " + rtInfo
                                                                  + "  Please place a valid aspectjrt.jar on the classpath.");
            return false;
        }
        boolean incrementalEnabled = 
            buildConfig.isIncrementalMode()
            || buildConfig.isIncrementalFileMode();
        boolean successfulBuild;
        if (incrementalEnabled && nextBuild) {
            successfulBuild = buildManager.incrementalBuild(buildConfig, messageHandler);
        } else {
            if (incrementalEnabled) {
                nextBuild = incrementalEnabled;
            } 
            successfulBuild = buildManager.batchBuild(buildConfig, messageHandler); 
        }
        IncrementalStateManager.recordSuccessfulBuild(configFile,buildManager.getState());
        return successfulBuild;
//        } catch (OperationCanceledException ce) {
//   Ajde.getDefault().getErrorHandler().handleWarning(
//    "build cancelled by user");
//            return false;
    } catch (AbortException e) {
        final IMessage message = e.getIMessage();
        if (null == message) {
            signalThrown(e);
        } else if (null != message.getMessage()) {
            Ajde.getDefault().getErrorHandler().handleWarning(message.getMessage());
        } else if (null != message.getThrown()) {
            signalThrown(message.getThrown());
        } else {
            signalThrown(e);
        }
        return false;
    } catch (Throwable t) {
        signalThrown(t);
        return false; 
    } 
}


// class: AspectJBuildManager.java, method: CompilerThread.run()
public void run() {
    boolean succeeded = true;
    boolean warnings = false;
    try {
        long timeStart = System.currentTimeMillis();
        notifyCompileStarted(configFile);
        progressMonitor.start(configFile);
        compilerMessages.clearTasks();
        
        if (Ajde.getDefault().isLogging())
            Ajde.getDefault().logEvent("building with options: " 
                                           + getFormattedOptionsString(buildOptions, Ajde.getDefault().getProjectProperties()));
        
        succeeded = compilerAdapter.compile(configFile, progressMonitor, buildModelMode);
        
        long timeEnd = System.currentTimeMillis();
        lastCompileTime = (int)(timeEnd - timeStart);
    } catch (ConfigParser.ParseException pe) {
        Ajde.getDefault().getErrorHandler().handleWarning(
                                                          "Config file entry invalid, file: " 
                                                              + pe.getFile().getPath() 
                                                              + ", line number: " 
                                                              + pe.getLine());
    } catch (Throwable e) {
        Ajde.getDefault().getErrorHandler().handleError("Compile error, caught Throwable: " + e.toString(), e);
    } finally {
        warnings = compilerMessages.hasWarning();
        progressMonitor.finish();
    }
    notifyCompileFinished(configFile, lastCompileTime, succeeded, warnings);
}
'''




print('--------------- BUG REPORT ---------------')
print(chain.run({'stack_trace': stack_trace, 'source_code': source_code}))
print('--------------- END ---------------')


# Check the model is being used
# print(f"Model being used: {llm.model_name}")

# Check prompt template
# print(prompt.format(stack_trace={stack_trace}))