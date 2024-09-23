import os, time, argparse, dotenv
from queue import Queue

from connection.sender import SenderThread
from connection.host import Host


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='Kapitza.Sender', \
    description='Process, sending wav files to recipient through Internet',
    epilog='Adress your questions to K.Zipa via k.zipa@skoltech.ru')
    # parsing ip and port
    parser.add_argument("--ip", help='Specify ip address. If no address is specified, it will be dynamically calculated.', default=None)
    parser.add_argument("--port", help='Specify connection port. If not specified 9611 will be used.', default=9611)
    args = parser.parse_args()

    dotenv.load_dotenv()
    # dynamically evaluate current IP
    # int(os.environ.get("HOST_PORT"))
    host = Host(ip=args.ip, port=args.port)
    queue = Queue()
    SenderThread(queue, host, timeout=10.0).start()

    files = ["voice/1.wav", "voice/2.wav", "voice/3.wav"]
    for f in files:
        queue.put(os.path.abspath(f))
        time.sleep(5.0)
    queue.join()


