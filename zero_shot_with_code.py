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
java.util.zip.ZipException: error in opening zip file
Can't open archive: struts.jar: java.util.zip.ZipException: error in opening 
zip file
org.aspectj.weaver.BCException: Can't open archive: struts.jar: 
java.util.zip.ZipException: error in opening zip file
	at org.aspectj.weaver.bcel.ClassPathManager$ZipFileEntry.ensureOpen
(ClassPathManager.java:253)
	at org.aspectj.weaver.bcel.ClassPathManager$ZipFileEntry.find
(ClassPathManager.java:225)
	at org.aspectj.weaver.bcel.ClassPathManager.find
(ClassPathManager.java:92)
	at org.aspectj.weaver.bcel.BcelWorld.lookupJavaClass
(BcelWorld.java:259)
	at org.aspectj.weaver.bcel.BcelWorld.resolveDelegate
(BcelWorld.java:234)
	at org.aspectj.weaver.World.resolveToReferenceType(World.java:282)
	at org.aspectj.weaver.World.resolve(World.java:205)
	at org.aspectj.weaver.World.resolve(World.java:127)
	at org.aspectj.weaver.World.resolve(World.java:250)
	at org.aspectj.ajdt.internal.core.builder.AjBuildManager.initBcelWorld
(AjBuildManager.java:594)
	at org.aspectj.ajdt.internal.core.builder.AjBuildManager.doBuild
(AjBuildManager.java:189)
	at org.aspectj.ajdt.internal.core.builder.AjBuildManager.batchBuild
(AjBuildManager.java:140)
	at org.aspectj.ajdt.ajc.AjdtCommand.doCommand(AjdtCommand.java:112)
	at org.aspectj.ajdt.ajc.AjdtCommand.runCommand(AjdtCommand.java:60)
	at org.aspectj.tools.ajc.Main.run(Main.java:324)
	at org.aspectj.tools.ajc.Main.runMain(Main.java:238)
	at org.aspectj.tools.ajc.Main.main(Main.java:82)
'''


# source code
source_code = '''
// class: ClassPathManager.java, method: ZipFileEntry.ensureOpen()
private void ensureOpen() {
    if (zipFile != null) return; // If its not null, the zip is already open
    try {
        if (openArchives.size()>=maxOpenArchives) {
            closeSomeArchives(openArchives.size()/10); // Close 10% of those open
        }
        zipFile = new ZipFile(file);
        openArchives.add(zipFile);
    } catch (IOException ioe) {
        throw new BCException("Can't open archive: "+file.getName()+": "+ioe.toString());
    }
}


// class: ClassPathManager.java, method: ZipFileEntry.find()
public ClassFile find(String name) {
    ensureOpen();
    String key = name.replace('.', '/') + ".class";
    ZipEntry entry = zipFile.getEntry(key);
    if (entry != null) return new ZipEntryClassFile(this, entry);
    else               return null; // This zip will be closed when necessary...
}


// class: ClassPathManager.java, method: find()
public ClassFile find(TypeX type) {
    String name = type.getName();
    for (Iterator i = entries.iterator(); i.hasNext(); ) {
        Entry entry = (Entry)i.next();
        ClassFile ret = entry.find(name);
        if (ret != null) return ret;
    }
    return null;
}


// class: BcelWorld.java, method: lookupJavaClass()
private JavaClass lookupJavaClass(ClassPathManager classPath, String name) {
    if (classPath == null) {
        try {
            return delegate.loadClass(name);
        } catch (ClassNotFoundException e) {
            return null;
        }
    }
}


// class: AjBuildManager.java, method: initBcelWorld()
private void initBcelWorld(IMessageHandler handler) throws IOException {
  List cp = buildConfig.getBootclasspath();
  cp.addAll(buildConfig.getClasspath());
  BcelWorld bcelWorld = new BcelWorld(cp, handler, null);
  bcelWorld.setBehaveInJava5Way(buildConfig.getBehaveInJava5Way());
  bcelWorld.setXnoInline(buildConfig.isXnoInline());
  bcelWorld.setXlazyTjp(buildConfig.isXlazyTjp());
  BcelWeaver bcelWeaver = new BcelWeaver(bcelWorld);
  state.setWorld(bcelWorld);
  state.setWeaver(bcelWeaver);
  state.binarySourceFiles = new HashMap();
  
  for (Iterator i = buildConfig.getAspectpath().iterator(); i.hasNext();) {
   File f = (File) i.next();
   bcelWeaver.addLibraryJarFile(f);
  }
  
//  String lintMode = buildConfig.getLintMode();
  
  if (buildConfig.getLintMode().equals(AjBuildConfig.AJLINT_DEFAULT)) {
   bcelWorld.getLint().loadDefaultProperties();
  } else {
   bcelWorld.getLint().setAll(buildConfig.getLintMode());
  }
  
  if (buildConfig.getLintSpecFile() != null) {
   bcelWorld.getLint().setFromProperties(buildConfig.getLintSpecFile());
  }
  
  //??? incremental issues
  for (Iterator i = buildConfig.getInJars().iterator(); i.hasNext(); ) {
   File inJar = (File)i.next();
   List unwovenClasses = bcelWeaver.addJarFile(inJar, buildConfig.getOutputDir(),false);
   state.binarySourceFiles.put(inJar.getPath(), unwovenClasses);
  }
  
  for (Iterator i = buildConfig.getInpath().iterator(); i.hasNext(); ) {
   File inPathElement = (File)i.next();
   if (!inPathElement.isDirectory()) {
    // its a jar file on the inpath
    // the weaver method can actually handle dirs, but we don't call it, see next block
    List unwovenClasses = bcelWeaver.addJarFile(inPathElement,buildConfig.getOutputDir(),true);
    state.binarySourceFiles.put(inPathElement.getPath(),unwovenClasses);
   } else {
    // add each class file in an in-dir individually, this gives us the best error reporting
    // (they are like 'source' files then), and enables a cleaner incremental treatment of
    // class file changes in indirs.
    File[] binSrcs = FileUtil.listFiles(inPathElement, binarySourceFilter);
    for (int j = 0; j < binSrcs.length; j++) {
     UnwovenClassFile ucf = 
      bcelWeaver.addClassFile(binSrcs[j], inPathElement, buildConfig.getOutputDir());
     List ucfl = new ArrayList();
     ucfl.add(ucf);
     state.binarySourceFiles.put(binSrcs[j].getPath(),ucfl);
    }
   }
  }
  bcelWeaver.setReweavableMode(buildConfig.isXreweavable(),buildConfig.getXreweavableCompressClasses());

  //check for org.aspectj.runtime.JoinPoint
  bcelWorld.resolve("org.aspectj.lang.JoinPoint");
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


// class: AjBuildManager.java, method: batchBuild()
public boolean batchBuild(
                          AjBuildConfig buildConfig, 
                          IMessageHandler baseHandler) 
    throws IOException, AbortException {
    return doBuild(buildConfig, baseHandler, true);
}


// class: AjdtCommand.java, method: doCommand()
protected boolean doCommand(IMessageHandler handler, boolean repeat) {
    try {
        if (handler instanceof IMessageHolder) {
            Dump.saveMessageHolder((IMessageHolder) handler);
        }
        // buildManager.setMessageHandler(handler);
        CountingMessageHandler counter = new CountingMessageHandler(handler);
        if (counter.hasErrors()) {
            return false;
        }
        // regenerate configuration b/c world might have changed (?)
        AjBuildConfig config = genBuildConfig(savedArgs, counter);
        if (!config.shouldProceed()) {
            return true;
        }
        if (!config.hasSources()) {
            MessageUtil.error(counter, "no sources specified");
        }
        if (counter.hasErrors())  { // print usage for config errors
            String usage = BuildArgParser.getUsage();
            MessageUtil.abort(handler, usage);
            return false;
        }
        //System.err.println("errs: " + counter.hasErrors());          
        boolean result = ((repeat 
                               ? buildManager.incrementalBuild(config, handler)
                               : buildManager.batchBuild(config, handler))
                              && !counter.hasErrors());
        Dump.dumpOnExit();
        return result;
    } catch (AbortException ae) {
        if (ae.isSilent()) {
            throw ae;
        } else {
            MessageUtil.abort(handler, ABORT_MESSAGE, ae);
        }
    } catch (MissingSourceFileException t) { 
        MessageUtil.error(handler, t.getMessage());
    } catch (Throwable t) {
        MessageUtil.abort(handler, ABORT_MESSAGE, t);
        Dump.dumpWithException(t);
    } 
    return false;
}


// class: AjdtCommand.java, method: runCommand()
public boolean runCommand(String[] args, IMessageHandler handler) {
    buildManager = new AjBuildManager(handler); 
    savedArgs = new String[args.length];
    System.arraycopy(args, 0, savedArgs, 0, savedArgs.length);
    for (int i = 0; i < args.length; i++) {
// AMC - PR58681. No need to abort on -help as the Eclipse compiler does the right thing.
//            if ("-help".equals(args[i])) {
//                // should be info, but handler usually suppresses
//                MessageUtil.abort(handler, BuildArgParser.getUsage());
//                return true;
//            } else 
        if ("-X".equals(args[i])) {
            // should be info, but handler usually suppresses
            MessageUtil.abort(handler, BuildArgParser.getXOptionUsage());
            return true;
        }
    }
    return doCommand(handler, false);
}


// class: Main.java, method: run()
public void run(String[] args, IMessageHolder holder) {
    
    boolean logMode = (-1 != ("" + LangUtil.arrayAsList(args)).indexOf("-log"));
    PrintStream logStream = null;
    FileOutputStream fos = null;
    if (logMode){
        int logIndex = LangUtil.arrayAsList(args).indexOf("-log");
        String logFileName = args[logIndex + 1];
        File logFile = new File(logFileName);
        try{
            logFile.createNewFile();
            fos = new FileOutputStream(logFileName, true);
            logStream = new PrintStream(fos,true);
        } catch(Exception e){   
            fail(holder, "Couldn't open log file: ", e);    
        }
        Date now = new Date();
        logStream.println(now.toString());
        boolean verbose = (-1 != ("" + LangUtil.arrayAsList(args)).indexOf("-verbose"));
        if (verbose) {
            ourHandler.setInterceptor(new LogModeMessagePrinter(true,logStream));
        } else {
            ourHandler.ignore(IMessage.INFO);
            ourHandler.setInterceptor(new LogModeMessagePrinter(false,logStream));
        }
        holder = ourHandler;
    }
    
    if (LangUtil.isEmpty(args)) {
        args = new String[] { "-?" };
    }  else if (controller.running()) {
        fail(holder, "already running with controller: " + controller, null);
        return;
    } 
    args = controller.init(args, holder);
    if (0 < holder.numMessages(IMessage.ERROR, true)) {
        return;
    }      
    ICommand command = ReflectionFactory.makeCommand(commandName, holder);
    if (0 < holder.numMessages(IMessage.ERROR, true)) {
        return;
    }      
    try {
//            boolean verbose = (-1 != ("" + Arrays.asList(args)).indexOf("-verbose"));
        outer:
            while (true) {
            boolean passed = command.runCommand(args, holder);
            if (report(passed, holder) && controller.incremental()) {
//                    final boolean onCommandLine = controller.commandLineIncremental();
                while (controller.doRepeatCommand(command)) {
                    holder.clearMessages();
                    if (controller.buildFresh()) {
                        continue outer;
                    } else {
                        passed = command.repeatCommand(holder);
                    }
                    if (!report(passed, holder)) {
                        break;
                    }
                }
            }
            break;
        }
    } catch (AbortException ae) {
        if (ae.isSilent()) { 
            quit();
        } else {
            IMessage message = ae.getIMessage();
            Throwable thrown = ae.getThrown();
            if (null == thrown) { // toss AbortException wrapper
                if (null != message) {
                    holder.handleMessage(message);
                } else {
                    fail(holder, "abort without message", ae);
                }
            } else if (null == message) {
                fail(holder, "aborted", thrown);
            } else {
                String mssg = MessageUtil.MESSAGE_MOST.renderToString(message);
                fail(holder, mssg, thrown);
            }
        }
    } catch (Throwable t) {
        fail(holder, "unexpected exception", t);
    } finally{
        if (logStream != null){
            logStream.close();
            logStream = null;
        }
        if (fos != null){
            try {
                fos.close();
            } catch (IOException e){
                fail(holder, "unexpected exception", e);
            }
            fos = null;
        }
    }
}


// class: Main.java, method: runMain()
public void runMain(String[] args, boolean useSystemExit) {
        boolean verbose = (-1 != ("" + LangUtil.arrayAsList(args)).indexOf("-verbose"));
        IMessageHolder holder = clientHolder;
        if (null == holder) {
            holder = ourHandler;
            if (verbose) {
                ourHandler.setInterceptor(MessagePrinter.VERBOSE);
            } else {
                ourHandler.ignore(IMessage.INFO);
                ourHandler.setInterceptor(MessagePrinter.TERSE);
            }
        }
        
        // make sure we handle out of memory gracefully...
        try {
        	// byte[] b = new byte[100000000]; for testing OoME only!
        	run(args, holder);
        } catch (OutOfMemoryError outOfMemory) {
        	IMessage outOfMemoryMessage = new Message(OUT_OF_MEMORY_MSG,null,true);
        	holder.handleMessage(outOfMemoryMessage);
        	systemExit(holder);  // we can't reasonably continue from this point.
        }

        boolean skipExit = false;
        if (useSystemExit && !LangUtil.isEmpty(args)) {  // sigh - pluck -noExit
            for (int i = 0; i < args.length; i++) {
				if ("-noExit".equals(args[i])) {
                    skipExit = true;
                    break;
                }
			}
        }
        if (useSystemExit && !skipExit) {
            systemExit(holder);
        }
    }


// class: Main.java, method: main()
public static void main(String[] args) throws IOException {
    new Main().runMain(args, true);
}
public Main() {
    controller = new CommandController();
    commandName = ReflectionFactory.ECLIPSE;
    ourHandler = new MessageHandler(true);
} 
'''




print('--------------- BUG REPORT ---------------')
print(chain.run({'stack_trace': stack_trace, 'source_code': source_code}))
print('--------------- END ---------------')


# Check the model is being used
# print(f"Model being used: {llm.model_name}")

# Check prompt template
# print(prompt.format(stack_trace={stack_trace}))