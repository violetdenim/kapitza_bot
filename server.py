import argparse
import dotenv
from queue import Queue

from connection.sender import SenderThread
from connection.threads import ReceiverThread
from connection.pipethread import PipelineThread
from connection.host import Host


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='Kapitza.Sender',
                                     description='Process, accepting and processing wav files to recipient through Internet',
                                     epilog='Adress your questions to K.Zipa via k.zipa@skoltech.ru')
    # parsing ip and port
    parser.add_argument(
        "--ip", help='Specify ip address. If no address is specified, it will be dynamically calculated.', default=None)
    parser.add_argument(
        "--port", help='Specify connection port. If not specified 9611 will be used.', default=9611)
    parser.add_argument(
        "--timeout", help='Specify waiting period in seconds. Default is None - infinite wait.', default=None)
    args = parser.parse_args()
    args.port = int(args.port)
    args.timeout = int(args.timeout) if args.timeout else None # 30.0

    # receive, process and play
    dotenv.load_dotenv()

    q1, q2 = Queue(), Queue()
    receiver = ReceiverThread(q1, Host(
        ip=args.ip, port=args.port), saving_period=1.0, restarting_period=args.timeout)
    pipeline = PipelineThread(q1, q2, timeout=args.timeout)  # DummyPipeline(q1, q2) #
    # streaming = StreamingThread(q2, timeout=30.0)
    sender = SenderThread(
        q2, Host(ip=args.ip, port=args.port + 1), timeout=args.timeout)

    receiver.start()
    pipeline.start()
    # streaming.start()
    sender.start()

    q1.join()
    q2.join()
