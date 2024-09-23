import os, time, random
from queue import Queue

from connection.threads import SenderThread
from connection.host import Host

import dotenv

def audio_server(files, timeout=10.0, random_delay=False):
    queue = Queue()
    host = Host()
    server = SenderThread(queue, host, timeout=timeout)
    server.start()
    for f in files:
        # push with delay
        queue.put(os.path.abspath(f))
        time.sleep((random.random() if random_delay else 1 ) * timeout)

    queue.join()

if __name__ == "__main__":
    dotenv.load_dotenv()
    audio_server(["voice/1.wav", "voice/2.wav", "voice/3.wav"])
    # audio_server(["voice/short.wav"])


