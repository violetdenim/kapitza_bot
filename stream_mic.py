"""PyAudio example: Record a few seconds of audio and save to a WAVE file."""
import os
import threading
from queue import Queue
import pyaudio


class StreamingThread(threading.Thread):
    """ Thread uses output device to play audios from queue """
    def __init__(self, input_queue: Queue, timeout=None, chunk=1024, rate=44_100):
        threading.Thread.__init__(self)
        self.p = pyaudio.PyAudio()
        self.queue = input_queue
        self.timeout = timeout
        self.stream = self.p.open(format=pyaudio.paInt16, channels=2, rate=rate, output=True, frames_per_buffer=chunk)
	
    def run(self):
        is_first = True
        while True:
            try:
                # first time wait indefinitelly, and after that wait for self.timeout seconds
                data = self.queue.get(block=True, timeout=None if is_first else self.timeout)
                is_first = False
            except Exception as e:
                print(f"Streaming: empty queue {e}")
                return 0
            try:
                self.stream.write(data)
                self.queue.task_done()
            except Exception as e:
                print(f"Streaming: exception {e}")
                return -1
            
    def __exit__(self):
        self.stream.close()
        self.p.terminate()
        
class RecordingThread(threading.Thread):
    """ Thread uses output device to play audios from queue """
    def __init__(self, output_queue: Queue, record_seconds, chunk=1024, rate=44_100):
        threading.Thread.__init__(self)
        self.p = pyaudio.PyAudio()
        self.queue = output_queue
        self.stream = self.p.open(format=pyaudio.paInt16, channels=2, rate=rate, input=True, frames_per_buffer=chunk)
        self.chunk = chunk
        self.buffer_count = int(rate * record_seconds / chunk)
	
    def run(self):
        try:
            for _ in range(self.buffer_count):
                self.queue.put(self.stream.read(self.chunk))
            print("Finished recording!")
            return 0
        except Exception as e:
            return -1

    def __exit__(self):
        self.stream.close()
        self.p.terminate()

def stream_default():
    CHUNK = 1024
    RATE = 44_100
    RECORD_SECONDS = 5
    os.environ['SDL_AUDIODRIVER'] = 'dsp'

    p = pyaudio.PyAudio()
    input_stream = p.open(format=pyaudio.paInt16, channels=2, rate=RATE, input=True, frames_per_buffer=CHUNK)
    output_stream = p.open(format=pyaudio.paInt16, channels=2, rate=RATE, output=True, frames_per_buffer=CHUNK)
    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = input_stream.read(CHUNK)
        output_stream.write(data)
    input_stream.stop_stream()
    output_stream.stop_stream()
    input_stream.close()
    output_stream.close()
    p.terminate()

def stream_between_threads():
    CHUNK = 1024
    RATE = 44_100
    os.environ['SDL_AUDIODRIVER'] = 'dsp'

    q = Queue()
    StreamingThread(q, timeout=1, chunk=CHUNK, rate=RATE).start()
    RecordingThread(q, 3, chunk=CHUNK, rate=RATE).start()
    q.join()

if __name__ == "__main__":
    # stream_default()
    stream_between_threads()


