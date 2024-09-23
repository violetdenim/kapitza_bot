import argparse, dotenv
from queue import Queue

from connection.threads import *
from connection.host import Host


if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog='Kapitza.Reciever', \
	description='Process, accepting and processing wav files to recipient through Internet',
	epilog='Adress your questions to K.Zipa via k.zipa@skoltech.ru')
	# parsing ip and port
	parser.add_argument("--ip", help='Specify ip address. If no address is specified, it will be dynamically calculated.', default=None)
	parser.add_argument("--port", help='Specify connection port. If not specified 9611 will be used.', default=9611)
	args = parser.parse_args()

	# receive, process and play
	dotenv.load_dotenv()
	host = Host(ip=args.ip, port=args.port)

	q1, q2 = Queue(), Queue()
	pipeline = PipelineThread(q1, q2, timeout=30.0) # DummyPipeline(q1, q2) #
	receiver = ReceiverThread(q1, host, saving_period=1.0, restarting_period=30.0)
	streaming = StreamingThread(q2, timeout=30.0)
	
	receiver.start()
	pipeline.start()
	streaming.start()

	q1.join()
	q2.join()
