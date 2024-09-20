# Welcome to PyShine
# This is client code to receive video and audio frames over TCP

import os, sys
import socket, threading
from queue import Queue

import tempfile, struct
import pyaudio, wave

sys.path.append('../')
from pipeline import Pipeline

import dotenv
dotenv.load_dotenv()

os.chdir('../')

# host_ip = os.environ.get("HOST_IP")
host_name = socket.gethostname()
host_ip = socket.gethostbyname(host_name) # os.environ.get("HOST_IP")
port = int(os.environ.get("HOST_PORT"))

class PipelineThread(threading.Thread):
	""" Thread takes file_names from input_queue, processes them and puts answers to output_queue"""
	def __init__(self, input_queue: Queue, output_queue: Queue, timeout=None):
		threading.Thread.__init__(self)
		self.input_queue = input_queue
		self.output_queue = output_queue
		self.timeout = timeout
		self.processor = Pipeline()
	
	def run(self):
		while True:
			try:
				input_user_name, input_file_name = self.input_queue.get(timeout=self.timeout)
			except Exception as e:
				return 0
			output_file_name = self.processor.process(user_name=input_user_name, file_to_process=input_file_name)
			self.output_queue.put(output_file_name)
			self.input_queue.task_done()

class PipelineDummy(threading.Thread):
	""" Imitates Pipeline Interface, but does nothing"""
	def __init__(self, input_queue: Queue, output_queue: Queue, timeout=None):
		threading.Thread.__init__(self)
		self.input_queue = input_queue
		self.output_queue = output_queue
		self.timeout = timeout
	
	def run(self):
		while True:
			try:
				input_user_name, input_file_name = self.input_queue.get(timeout=self.timeout)
			except Exception as e:
				return 0
			self.output_queue.put(input_file_name)
			self.input_queue.task_done()

class StreamingThread(threading.Thread):
	""" Thread uses output device to play audios from queue """
	def __init__(self, input_queue: Queue, timeout=None):
		threading.Thread.__init__(self)
		self.input_queue = input_queue
		self.timeout = timeout

		self.p = pyaudio.PyAudio()
		os.environ['SDL_AUDIODRIVER'] = 'dsp'
	
	def run(self):
		while True:
			try:
				wav_name = self.input_queue.get(timeout=self.timeout)
				with wave.open(wav_name, 'rb') as wf:
					stream = self.p.open(format=self.p.get_format_from_width(wf.getsampwidth()),
									channels=wf.getnchannels(),
									rate=wf.getframerate(),
									output=True)
					while len(data := wf.readframes(1024)):
						stream.write(data)
					stream.close()
				self.input_queue.task_done()
			except Exception as e:
				return 0

	def __exit__(self):
		if self.p:
			self.p.terminate()

class SenderThread(threading.Thread):
	""" Thread sends resulting audio files using socket"""
	def __init__(self, input_queue: Queue, timeout=None):
		threading.Thread.__init__(self)
		self.input_queue = input_queue
		self.timeout = timeout
		
		self.server_socket = socket.socket()
		self.server_socket.bind((host_ip, (port-1)))
		self.server_socket.listen(5)
		self.chunk = 1024
		self.timeout = 10.0

	def run(self):
		client_socket, addr = self.server_socket.accept()
		while True:
			try:
				wav_name = self.input_queue.get(timeout=self.timeout)
				# pack file and send through TCP/IP
				with open(wav_name, 'rb') as f:
					while len(data := f.read(self.chunk)):
						try:
							message = struct.pack("Q", len(data))+data
							client_socket.sendall(message)        
						except Exception as e:
							print(f"Transmission interrupted by client for file {wav_name}. Exception: {e}")
							self.server_socket.close()
							self.queue.task_done()
							return -1
				print(f"Finished transmission for file {wav_name}")
				self.input_queue.task_done()
			except Exception as e:
				print(f"Empty queue")
				self.server_socket.close()
				return 0

class ReceiverThread(threading.Thread):
	""" Thread accepts audio files using socket and puts their names into queue"""
	def __init__(self, output_queue: Queue, cleanup=True, saving_period=3.0, restarting_period=30.0):
		threading.Thread.__init__(self)
		self.output_queue = output_queue
		self.cleanup = cleanup

		self.saving_period = saving_period
		self.restarting_period = restarting_period

		self.folder = '.received'
		if os.path.exists(self.folder):
			for f in os.listdir(self.folder):
				os.remove(os.path.join(self.folder, f))
			os.removedirs(self.folder)
		os.makedirs(self.folder, 0o777, True)

	def run(self, CHUNK=1024):
		# create socket
		client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		socket_address = (host_ip, port-1)
		client_socket.connect(socket_address)
		
		file_name = next(tempfile._get_candidate_names()) + ".wav"
		# disable class streaming, use queue for playing files
		stream = SavingBufferWithStreaming(do_streaming=False) 
		
		waiting_interval = self.saving_period
		while True:
			try:
				client_socket.settimeout(waiting_interval)
				packet = client_socket.recv(CHUNK) # 4K
				if len(packet) == 0:
					raise Exception("End of transmission")
				waiting_interval = self.saving_period
				leftover = stream.push(packet)
				if leftover:
					raise Exception("End of melody")
				# wait for the next data
			except Exception as e:
				print(f"{e}. No transmission for {waiting_interval} seconds!")
				# we will not wait anymore
				if waiting_interval > self.saving_period:
					print(f"Tired of waiting. I'm closing the connection.")
					client_socket.close()
					return 0 
				else: # end of melody
					output_name = os.path.abspath(os.path.join(self.folder, file_name) )
					stream.close(output_name)
					# put file_name to processing queue
					self.output_queue.put(("Mr.X", output_name))
					file_name = next(tempfile._get_candidate_names()) + ".wav"
					
					# wait for new melody 
					if self.restarting_period:
						waiting_interval = self.restarting_period - self.saving_period
					else:
						waiting_interval = None
					if leftover:
						# push new chunk to the next stream
						stream.push(leftover)

class WavInfo:
    """Class for storing wav parameters to pass to pyaudio"""
    frame_rate: int
    num_channels: int
    sample_width: int
    wav_size: int

    def __init__(self, frame) -> float:
        assert(len(frame)==44)
        assert(frame[0:4]==b'RIFF')
        wav_size = struct.unpack('I', frame[4:8])[0]
        assert(frame[8:12]==b'WAVE')
        assert(frame[12:16]==b'fmt ')
        assert(struct.unpack('I', frame[16:20])[0] == 16)
        format_tag, num_channels = struct.unpack('2h', frame[20:24])
        sample_rate, byte_rate = struct.unpack('2I', frame[24:32])
        block_align, bits_per_sample = struct.unpack('2h', frame[32:36])
        assert(byte_rate == block_align * sample_rate)
        assert(frame[36:40]==b'data')
        data_size = struct.unpack('I', frame[40:44])[0]
        assert(wav_size == data_size + 36)

        self.sample_width = bits_per_sample // 8
        self.frame_rate = sample_rate
        self.num_channels = num_channels
        self.wav_size = wav_size
        # num_samples = data_size // (num_channels * sample_width)

class SavingBufferWithStreaming:
	def __init__(self, do_streaming=True):
		self.data = b""
		self.bytes_to_read = None
		if do_streaming:
			self.p = pyaudio.PyAudio()
			os.environ['SDL_AUDIODRIVER'] = 'dsp'
			self.stream = None
		else:
			self.p = None

	def push(self, frame):
		WAV_HEADER_SIZE = 44
		leftover = None

		self.data += frame
		if len(self.data) < WAV_HEADER_SIZE:
			return leftover 

		if not self.bytes_to_read: # first batch
			header = WavInfo(frame[:WAV_HEADER_SIZE])
			self.bytes_to_read = header.wav_size + 8
			if self.p:
				self.stream = self.p.open(
					format=self.p.get_format_from_width(header.sample_width),
					channels=header.num_channels,
					rate=header.frame_rate,
					output=True)
				if self.stream.is_active():
					self.stream.write(frame[WAV_HEADER_SIZE:])
		if self.p:
			if self.stream.is_active():
				self.stream.write(frame)
		if len(self.data) > self.bytes_to_read:
			self.data, leftover = self.data[:self.bytes_to_read], self.data[self.bytes_to_read:]
		return leftover

	def is_closed(self):
		return len(self.data) == 0
	
	def close(self, out_file="received.wav"):
		if self.p:
			if self.stream.is_active():
				self.stream.close()
			self.stream = None # prepare for the next transmission

		with open(out_file, "wb") as f:
			f.write(self.data)

		self.data = b"" # prepare for the next transmission
		self.bytes_to_read = None
	
	def __exit__(self):
		if self.p:
			self.p.terminate()

class DummyReceiver(threading.Thread):
	def __init__(self, waiting_period = 30.0):
		threading.Thread.__init__(self)
		self.waiting_period = waiting_period

	def run(self):
		# create socket
		client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		socket_address = (host_ip, port-1)
		client_socket.connect(socket_address)
		print(f"Established connection successfully")
		data_len = 0
		while True:
			try:
				client_socket.settimeout(self.waiting_period)
				packet = client_socket.recv(1024)
				if len(packet) == 0:
					raise Exception("End of transmission")
				data_len += len(packet)
			except Exception as e:
				print(f"{e}. No transmission for {self.waiting_period} seconds! Received {data_len} bytes")
				return 0


if __name__ == "__main__":
	# DummyReceiver(10.0).start()
	# ReceiverThread(Queue()).start()

	# receive, process and play
	q1, q2 = Queue(), Queue()
	pipeline = PipelineThread(q1, q2, timeout=30.0) # PipelineDummy(q1, q2) #
	receiver = ReceiverThread(q1, saving_period=1.0, restarting_period=30.0)
	streaming = StreamingThread(q2, timeout=30.0)
	
	receiver.start()
	pipeline.start()
	streaming.start()

	q1.join()
	q2.join()
