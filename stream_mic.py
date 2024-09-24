"""PyAudio example: Record a few seconds of audio and save to a WAVE file."""
import os
import threading
from queue import Queue
from connection.host import Host, InputMedium, OutputMedium
from connection.threads import DummyPipeline
import pyaudio
import argparse
# from connection.sender import SenderThread
# from connection.threads import ReceiverThread
import io, wave
from dataclasses import dataclass
from enum import Enum

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
    def __init__(self, input_medium: InputMedium, data_settings: DataSettings, serialization_settings: SerializationSettings):
        threading.Thread.__init__(self)
        self.p = pyaudio.PyAudio()
        self.medium = input_medium
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
                # data = self.queue.get(block=True, timeout=None if is_first else self.serialization_settings.timeout)
                data = self.medium.get(timeout=None if is_first else self.serialization_settings.timeout)
                if len(data) == 0:
                    raise Exception("No Data!")
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
                self.medium.task_done()
            except Exception as e:
                print(f"Streaming: exception {e}")
                return -1
            
    def __exit__(self):
        self.stream.close()
        self.p.terminate()


class RecordingWavsThread(threading.Thread):
    """ Thread uses input device to record audio blocks, pack it to wav-files and put them to queue """
    def __init__(self, output_medium: OutputMedium, record_seconds, data_settings: DataSettings, serialization_settings: SerializationSettings):
        threading.Thread.__init__(self)
        self.p = pyaudio.PyAudio()
        self.medium = output_medium
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
                # self.queue.put(data)
                self.medium.send(data)
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
    StreamingWavsThread(InputMedium(connector=q), data_settings=data_settings, serialization_settings=serialization_settings).start()
    RecordingWavsThread(OutputMedium(connector=q), record_seconds=3, data_settings=data_settings, serialization_settings=serialization_settings).start()
    q.join()

    

def stream_between_nodes(serialize_to_wav):
    os.environ['SDL_AUDIODRIVER'] = 'dsp'
    
    data_settings = DataSettings()
    serialization_settings = SerializationSettings()
    # overrde defaults
    serialization_settings.serialize_to_wav = serialize_to_wav
    ip = None
    port1 = 6911
    # sender should be run before acceptor
    
    node1_proc1 = RecordingWavsThread(OutputMedium(ip=ip, port=port1), record_seconds=3, data_settings=data_settings, serialization_settings=serialization_settings)
    node2_proc1 = StreamingWavsThread(InputMedium(ip=ip, port=port1), data_settings=data_settings, serialization_settings=serialization_settings)

    node1_proc1.start()
    node2_proc1.start()


def stream_between_nodes2(serialize_to_wav):
    os.environ['SDL_AUDIODRIVER'] = 'dsp'
    
    data_settings = DataSettings()
    serialization_settings = SerializationSettings()
    # overrde defaults
    serialization_settings.serialize_to_wav = serialize_to_wav
    ip = None
    port1 = 6902
    port2 = port1 + 1
    # sender should be run before acceptor
    node1_proc1 = RecordingWavsThread(OutputMedium(ip=ip, port=port1), record_seconds=3, data_settings=data_settings, serialization_settings=serialization_settings)
    node1_proc2 = StreamingWavsThread(InputMedium(ip=ip, port=port2), data_settings=data_settings, serialization_settings=serialization_settings)

    q = Queue() # use intermediate queue as an example
    DummyPipeline(InputMedium(ip=ip, port=port1), OutputMedium(connector=q)).start()
    DummyPipeline(InputMedium(connector=q), OutputMedium(ip=ip, port=port2)).start()
    q.join()
    
    node1_proc1.start()
    node1_proc2.start()

    

if __name__ == "__main__":
    # stream_default()
    # stream_between_threads(serialize_to_wav=True)

    stream_between_nodes2(serialize_to_wav=True)


