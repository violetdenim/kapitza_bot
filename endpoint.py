import os
import time
import argparse
import dotenv
from queue import Queue

from connection.sender import SenderThread
from connection.threads import ReceiverThread
from connection.host import Host


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='Kapitza.Endpoint',
                                     description='Process, sending wav files to recipient through Internet',
                                     epilog='Adress your questions to K.Zipa via k.zipa@skoltech.ru')
    # parsing ip and port
    parser.add_argument(
        "--ip", help='Specify ip address. If no address is specified, it will be dynamically calculated.', default=None)
    parser.add_argument(
        "--port", help='Specify connection port. If not specified 9611 will be used.', default=9611)
    args = parser.parse_args()
    args.port = int(args.port)

    dotenv.load_dotenv()
    # dynamically evaluate current IP
    # int(os.environ.get("HOST_PORT"))
    input_queue = Queue()
    result_queue = Queue()
    SenderThread(input_queue, Host(ip=args.ip, port=args.port),
                 timeout=10.0, finalize=False).start()
    ReceiverThread(result_queue, Host(ip=args.ip, port=args.port+1),
                   do_streaming=True, folder='.received_feedback').start()

    files = ["voice/1.wav", "voice/2.wav", "voice/3.wav"]
    for f in files:
        input_queue.put(os.path.abspath(f))
        time.sleep(5.0)
    input_queue.join()

    while True:
        result = result_queue.get(block=True, timeout=30)
        if len(result) > 0:
            print(f"Got feedback: {result}")
        else:
            print("End of queue")
            break
        result_queue.task_done()

    result_queue.join()
