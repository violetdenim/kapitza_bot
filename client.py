from queue import Queue
from connection.threads import *
from connection.host import Host

import dotenv

if __name__ == "__main__":
	dotenv.load_dotenv()
	# DummyReceiver(host=Host(), waiting_period=10.0).start()
	
	# receive, process and play
	dotenv.load_dotenv()
	host = Host()

	q1, q2 = Queue(), Queue()
	pipeline = PipelineThread(q1, q2, timeout=30.0) # DummyPipeline(q1, q2) #
	receiver = ReceiverThread(q1, host, saving_period=1.0, restarting_period=30.0)
	streaming = StreamingThread(q2, timeout=30.0)
	
	receiver.start()
	pipeline.start()
	streaming.start()

	q1.join()
	q2.join()
