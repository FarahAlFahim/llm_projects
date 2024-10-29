# prompt templating and chaining
from langchain import PromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain



# template
template = '''
You are a fault localization expert. You are given a bug report and its corresponding source code. 

Bug Report:
{bug_report}

Source Code:
{source_code}

Based on the information provided, your task is to localize the fault by identifying the **most likely source(s) of the issue**. Analyze the stack trace, relevant methods, and the description provided to pinpoint the problematic area in the code.
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
//			Ajde.getDefault().getErrorHandler().handleWarning(
//				"build cancelled by user");
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




print('--------------- FAULT LOCALIZATION ---------------')
print(chain.run({'bug_report': bug_report, 'source_code': source_code}))
print('--------------- END ---------------')


# Check the model is being used
# print(f"Model being used: {llm.model_name}")

# Check prompt template
# print(prompt.format(stack_trace={stack_trace}))