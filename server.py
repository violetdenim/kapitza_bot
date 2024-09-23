import os, time
from queue import Queue

from connection.sender import SenderThread
from connection.host import Host

import dotenv


if __name__ == "__main__":
    dotenv.load_dotenv()
    # dynamically evaluate current IP
    host = Host(evaluate=True)
    queue = Queue()
    SenderThread(queue, host, timeout=10.0).start()

    files = ["voice/1.wav", "voice/2.wav", "voice/3.wav"]
    for f in files:
        queue.put(os.path.abspath(f))
        time.sleep(5.0)
    queue.join()


