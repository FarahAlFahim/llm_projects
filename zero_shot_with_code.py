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


# source code
source_code = '''
// class: BcelWeaver.java, method: validateOrBranch()
private void validateOrBranch(OrPointcut pc, Pointcut userPointcut, int numFormals, 
    		String[] names, Pointcut[] leftBindings, Pointcut[] rightBindings) {
    	Pointcut left = pc.getLeft();
    	Pointcut right = pc.getRight();
    	if (left instanceof OrPointcut) {
    		Pointcut[] newRightBindings = new Pointcut[numFormals];
    		validateOrBranch((OrPointcut)left,userPointcut,numFormals,names,leftBindings,newRightBindings);    		
    	} else {
    		if (left.couldMatchKinds().size() > 0)
    			validateSingleBranch(left, userPointcut, numFormals, names, leftBindings);
    	}
    	if (right instanceof OrPointcut) {
    		Pointcut[] newLeftBindings = new Pointcut[numFormals];
    		validateOrBranch((OrPointcut)right,userPointcut,numFormals,names,newLeftBindings,rightBindings);
    	} else {
    		if (right.couldMatchKinds().size() > 0)
    			validateSingleBranch(right, userPointcut, numFormals, names, rightBindings);    		
    	}
		Set kindsInCommon = left.couldMatchKinds();
		kindsInCommon.retainAll(right.couldMatchKinds());
		if (!kindsInCommon.isEmpty() && couldEverMatchSameJoinPoints(left,right)) {
			// we know that every branch binds every formal, so there is no ambiguity
			// if each branch binds it in exactly the same way...
			List ambiguousNames = new ArrayList();
			for (int i = 0; i < numFormals; i++) {
				if (!leftBindings[i].equals(rightBindings[i])) {
					ambiguousNames.add(names[i]);
				}
			}
			if (!ambiguousNames.isEmpty())
				raiseAmbiguityInDisjunctionError(userPointcut,ambiguousNames);
		}    	
    }


// class: BcelWeaver.java, method: validateBindings()
private void validateBindings(Pointcut dnfPointcut, Pointcut userPointcut, int numFormals, String[] names) {
    	if (numFormals == 0) return; // nothing to check
    	if (dnfPointcut.couldMatchKinds().isEmpty()) return; // cant have problems if you dont match!
    	if (dnfPointcut instanceof OrPointcut) {
    		OrPointcut orBasedDNFPointcut = (OrPointcut) dnfPointcut;
    		Pointcut[] leftBindings = new Pointcut[numFormals];
    		Pointcut[] rightBindings = new Pointcut[numFormals];
    		validateOrBranch(orBasedDNFPointcut,userPointcut,numFormals,names,leftBindings,rightBindings);
    	} else {
    		Pointcut[] bindings = new Pointcut[numFormals];
    		validateSingleBranch(dnfPointcut, userPointcut, numFormals, names,bindings);
    	}
    }


// class: BcelWeaver.java, method: rewritePointcuts()
private void rewritePointcuts(List/*ShadowMunger*/ shadowMungers) {
    	PointcutRewriter rewriter = new PointcutRewriter();
    	for (Iterator iter = shadowMungers.iterator(); iter.hasNext();) {
			ShadowMunger munger = (ShadowMunger) iter.next();
			Pointcut p = munger.getPointcut();
			Pointcut newP = rewriter.rewrite(p);
			// validateBindings now whilst we still have around the pointcut
			// that resembles what the user actually wrote in their program
		    // text.
			if (munger instanceof Advice) {
				Advice advice = (Advice) munger;
				if (advice.getSignature() != null) {
					final int numFormals;
                    final String names[];
                    //ATAJ for @AJ aspect, the formal have to be checked according to the argument number
                    // since xxxJoinPoint presence or not have side effects
                    if (advice.getConcreteAspect().isAnnotationStyleAspect()) {
                        numFormals = advice.getBaseParameterCount();
                        int numArgs = advice.getSignature().getParameterTypes().length;
                        if (numFormals > 0) {
                            names = advice.getSignature().getParameterNames(world);
                            validateBindings(newP,p,numArgs,names);
                        }
                    } else {
                        numFormals = advice.getBaseParameterCount();
                        if (numFormals > 0) {
                            names = advice.getBaseParameterNames(world);
                            validateBindings(newP,p,numFormals,names);
                        }
                    }
				}
			}
			munger.setPointcut(newP);
		}
    	// now that we have optimized individual pointcuts, optimize
    	// across the set of pointcuts....
    	// Use a map from key based on pc equality, to value based on
    	// pc identity.
    	Map/*<Pointcut,Pointcut>*/ pcMap = new HashMap();
    	for (Iterator iter = shadowMungers.iterator(); iter.hasNext();) {
			ShadowMunger munger = (ShadowMunger) iter.next();
			Pointcut p = munger.getPointcut();
			munger.setPointcut(shareEntriesFromMap(p,pcMap));
		}    	
    }


// class: BcelWeaver.java, method: prepareForWeave()
public void prepareForWeave() {
    	needToReweaveWorld = false;

    	CflowPointcut.clearCaches();
    	
    	// update mungers
    	for (Iterator i = addedClasses.iterator(); i.hasNext(); ) { 
    		UnwovenClassFile jc = (UnwovenClassFile)i.next();
    		String name = jc.getClassName();
    		ResolvedTypeX type = world.resolve(name);
    		//System.err.println("added: " + type + " aspect? " + type.isAspect());
    		if (type.isAspect()) {
    			needToReweaveWorld |= xcutSet.addOrReplaceAspect(type);
    		}
    	}

    	for (Iterator i = deletedTypenames.iterator(); i.hasNext(); ) { 
    		String name = (String)i.next();
    		if (xcutSet.deleteAspect(TypeX.forName(name))) needToReweaveWorld = true;
    	}

		shadowMungerList = xcutSet.getShadowMungers();
		rewritePointcuts(shadowMungerList);
		typeMungerList = xcutSet.getTypeMungers();
        lateTypeMungerList = xcutSet.getLateTypeMungers();
		declareParentsList = xcutSet.getDeclareParents();
    	
		// The ordering here used to be based on a string compare on toString() for the two mungers - 
		// that breaks for the @AJ style where advice names aren't programmatically generated.  So we
		// have changed the sorting to be based on source location in the file - this is reliable, in
		// the case of source locations missing, we assume they are 'sorted' - i.e. the order in
		// which they were added to the collection is correct, this enables the @AJ stuff to work properly.
		
		// When @AJ processing starts filling in source locations for mungers, this code may need
		// a bit of alteration...
				
		Collections.sort(
			shadowMungerList,
			new Comparator() {
				public int compare(Object o1, Object o2) {
					ShadowMunger sm1 = (ShadowMunger)o1;
					ShadowMunger sm2 = (ShadowMunger)o2;
					if (sm1.getSourceLocation()==null) return (sm2.getSourceLocation()==null?0:1);
					if (sm2.getSourceLocation()==null) return -1;
					
					return (sm2.getSourceLocation().getOffset()-sm1.getSourceLocation().getOffset());
				}
			});
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

//		if (isBatchCompile) {
//			resultsPendingWeave.addAll(getBinarySourcesFrom(binarySourceSetForFullWeave));  
//			// passed into the compiler, the set of classes in injars and inpath...
//		} else if (weaver.needToReweaveWorld()) {
//			addAllKnownClassesToWeaveList();
//			resultsPendingWeave.addAll(getBinarySourcesFrom(binarySourceSetForFullWeave));
//		}
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