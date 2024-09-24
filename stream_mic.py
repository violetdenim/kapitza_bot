"""PyAudio example: Record a few seconds of audio and save to a WAVE file."""
import os
import threading
from queue import Queue
from connection.host import Host
import pyaudio
import argparse
# from connection.sender import SenderThread
# from connection.threads import ReceiverThread
import io, wave
from dataclasses import dataclass

@dataclass
class DataSettings:
    channels = 2
    chunk = 1024
    rate = 44_100

@dataclass
class SerializationSettings:
    timeout = 1.0 # in seconds
    serialize_wav = True

class StreamingWavsThread(threading.Thread):
    """ Thread uses output device to play audios from queue """
    def __init__(self, input_queue: Queue, data_settings: DataSettings, serialization_settings: SerializationSettings):
        threading.Thread.__init__(self)
        self.p = pyaudio.PyAudio()
        self.queue = input_queue
        self.data_settings = data_settings
        self.serialization_settings = serialization_settings

        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=self.data_settings.channels,
            rate=self.data_settings.rate,
            output=True,
            frames_per_buffer=self.data_settings.chunk)
	
    def run(self):
        is_first = True
        while True:
            try:
                # first time wait indefinitelly, and after that wait for self.timeout seconds
                data = self.queue.get(block=True, timeout=None if is_first else self.serialization_settings.timeout)
                print(f"Got {len(data)} bytes")
                if self.serialization_settings.serialize_wav:
                    bytes_obj = io.BytesIO(data)
                    with wave.open(bytes_obj, 'rb') as wf:
                        data = wf.readframes(self.data_settings.chunk)
                is_first = False
            except Exception as e:
                print(f"Streaming: empty queue {e}")
                return 0
            try:
                print(f"Writing {len(data)} bytes to stream")
                self.stream.write(data)
                self.queue.task_done()
            except Exception as e:
                print(f"Streaming: exception {e}")
                return -1
            
    def __exit__(self):
        self.stream.close()
        self.p.terminate()


class RecordingWavsThread(threading.Thread):
    """ Thread uses input device to record audio blocks, pack it to wav-files and put them to queue """
    def __init__(self, output_queue: Queue, record_seconds, data_settings: DataSettings, serialization_settings: SerializationSettings):
        threading.Thread.__init__(self)
        self.p = pyaudio.PyAudio()
        self.queue = output_queue
        self.data_settings = data_settings
        self.serialization_settings = serialization_settings

        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=self.data_settings.channels,
            rate=self.data_settings.rate,
            input=True,
            frames_per_buffer=self.data_settings.chunk)
        self.buffer_count = int(self.data_settings.rate * record_seconds / self.data_settings.chunk)
	
    def run(self):
        try:
            for _ in range(self.buffer_count):
                # pack data to wav file
                data = self.stream.read(self.data_settings.chunk)
                if self.serialization_settings.serialize_wav:
                    bytes_obj = io.BytesIO()
                    with wave.open(bytes_obj, 'wb') as wf:
                        wf.setnchannels(2)
                        wf.setsampwidth(2)
                        wf.setframerate(self.data_settings.rate)
                        wf.writeframes(data)
                    bytes_obj.seek(0)
                    data = bytes_obj.read()
                self.queue.put(data)
                print(f"RecordingWavsThread sent {len(data)} bytes")
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

def stream_between_threads(serialize_to_wav):
    os.environ['SDL_AUDIODRIVER'] = 'dsp'
    
    data_settings = DataSettings()
    serialization_settings = SerializationSettings()
    # overrde defaults
    serialization_settings.serialize_to_wav = serialize_to_wav

    q = Queue()
    StreamingWavsThread(q, data_settings=data_settings, serialization_settings=serialization_settings).start()
    RecordingWavsThread(q, record_seconds=3, data_settings=data_settings, serialization_settings=serialization_settings).start()
    q.join()

def stream_between_nodes():
    # TBD:
    parser = argparse.ArgumentParser(prog='Program to stream mic to audio using ports', \
    description='First node sends data to the second node. \
        Second node does something with that data and sends packets back. \
        First node plays back response. \
        Run this script twice as first and second node.',
    epilog='Adress your questions to K.Zipa via k.zipa@skoltech.ru')
    # parsing ip and port
    parser.add_argument("--node", help='Specify node index - 0 or 1.', required=True)
    parser.add_argument("--ip", help='Specify ip address. If no address is specified, it will be dynamically calculated.', default=None)
    parser.add_argument("--port1", help='Specify connection port1 (from node0 to node1). If not specified 9611 will be used.', default=9611)
    parser.add_argument("--port2", help='Specify connection port2 (from node1 to node0). If not specified 9612 will be used.', default=9612)
    args = parser.parse_args()

    if args.node == 0:
        sending_host = Host(ip=args.ip)

if __name__ == "__main__":
    # stream_default()
    stream_between_threads(serialize_to_wav=False)
    # stream_between_nodes()


