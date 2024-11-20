import re

def parse_stack_trace(log_string):
    """
    Parses the stack trace from a log string.

    Args:
        log_string (str): The log string containing the stack trace.

    Returns:
        dict: A dictionary with 'exception' and 'stack_trace' as keys.
    """
    # Regex for the exception message (first line)
    exception_pattern = r"^([\w.$]+): (.+)"
    # Regex for the stack trace method calls
    stack_trace_pattern = r"^\s*at ([\w.$]+)\.([\w<>]+)\(([\w.]+):(\d+)\)"
    
    lines = log_string.splitlines()
    exception = None
    stack_trace = []

    for line in lines:
        # Match the exception message
        if not exception:
            match = re.match(exception_pattern, line)
            if match:
                exception = {
                    "type": match.group(1),
                    "message": match.group(2)
                }
        # Match stack trace lines
        else:
            match = re.match(stack_trace_pattern, line)
            if match:
                stack_trace.append({
                    "class": match.group(1),
                    "method": match.group(2),
                    "file": match.group(3),
                    "line": int(match.group(4))
                })

    return {
        "exception": exception,
        "stack_trace": stack_trace
    }



log_string = "When sending a lot of Messages to Queue via Webconsole and advisdoryForFastProducers=\"true\" (so the advisory triggers)\na exception occurs:\n\njvm 1    |  WARN | Failed to fire fast producer advisory, reason: java.lang.NullPointerException\n\n2012-07-12 11:40:48,623 | DEBUG | fast producer detail | org.apache.activemq.advisory.AdvisoryBroker | VMTransport: vm://localhost#1\njava.lang.NullPointerException\n\tat org.apache.activemq.advisory.AdvisorySupport.getFastProducerAdvisoryTopic(AdvisorySupport.java:195)\n\tat org.apache.activemq.advisory.AdvisoryBroker.fastProducer(AdvisoryBroker.java:352)\n\tat org.apache.activemq.broker.BrokerFilter.fastProducer(BrokerFilter.java:275)\n\tat org.apache.activemq.broker.BrokerFilter.fastProducer(BrokerFilter.java:275)\n\tat org.apache.activemq.broker.MutableBrokerFilter.fastProducer(MutableBrokerFilter.java:286)\n\tat org.apache.activemq.broker.region.BaseDestination.fastProducer(BaseDestination.java:512)\n\tat org.apache.activemq.broker.region.Queue.send(Queue.java:605)\n\tat org.apache.activemq.broker.region.AbstractRegion.send(AbstractRegion.java:407)\n\tat org.apache.activemq.broker.region.RegionBroker.send(RegionBroker.java:503)\n\tat org.apache.activemq.broker.jmx.ManagedRegionBroker.send(ManagedRegionBroker.java:305)\n\tat org.apache.activemq.broker.BrokerFilter.send(BrokerFilter.java:129)\n\tat org.apache.activemq.broker.scheduler.SchedulerBroker.send(SchedulerBroker.java:189)\n\tat org.apache.activemq.broker.BrokerFilter.send(BrokerFilter.java:129)\n\tat org.apache.activemq.broker.CompositeDestinationBroker.send(CompositeDestinationBroker.java:96)\n\tat org.apache.activemq.broker.TransactionBroker.send(TransactionBroker.java:306)\n\tat org.apache.activemq.broker.MutableBrokerFilter.send(MutableBrokerFilter.java:135)\n\tat org.apache.activemq.broker.TransportConnection.processMessage(TransportConnection.java:453)\n\tat org.apache.activemq.command.ActiveMQMessage.visit(ActiveMQMessage.java:681)\n\tat org.apache.activemq.broker.TransportConnection.service(TransportConnection.java:292)\n\tat org.apache.activemq.broker.TransportConnection$1.onCommand(TransportConnection.java:150)\n\tat org.apache.activemq.transport.ResponseCorrelator.onCommand(ResponseCorrelator.java:116)\n\tat org.apache.activemq.transport.MutexTransport.onCommand(MutexTransport.java:50)\n\tat org.apache.activemq.transport.vm.VMTransport.iterate(VMTransport.java:231)\n\tat org.apache.activemq.thread.DedicatedTaskRunner.runTask(DedicatedTaskRunner.java:98)\n\tat org.apache.activemq.thread.DedicatedTaskRunner$1.run(DedicatedTaskRunner.java:36)"

print(parse_stack_trace(log_string))