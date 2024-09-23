import tempfile, os
import pyaudio, wave

from .buffer import SavingBufferWithStreaming
from .host import Host
import threading
from queue import Queue
from pipeline import Pipeline

class DummyReceiver(threading.Thread):
	def __init__(self, host: Host, waiting_period = 30.0):
		threading.Thread.__init__(self)
		self.waiting_period = waiting_period
		self.host = host

	def run(self):
		# create socket
		client_socket = self.host.connected_client_socket()
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

class DummyPipeline(threading.Thread):
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
	def __init__(self, input_queue: Queue, host: Host, timeout=None, finalize=True):
		threading.Thread.__init__(self)
		self.queue = input_queue
		self.timeout = timeout
		self.finalize = finalize
		self.chunk = 1024

		self.server_socket = host.server_socket()

	def run(self):
		client_socket, addr = self.server_socket.accept()
		# connected to a client, pass files from queue to a client
		while True:
			# close connection after delay
			try:
				file_name = self.queue.get(block=True, timeout=self.timeout) 
			except Exception as e:
				print(f"Empty queue for {self.timeout} seconds! Server is closing connection.")
				self.server_socket.close()
				if self.finalize:
					os._exit(0)
				else:
					return 0
			data_len = 0
			with open(file_name, 'rb') as f:
				while len(data := f.read(self.chunk)):
					try:
						client_socket.sendall(data)        
						data_len += len(data)
					except Exception as e:
						print(f"Transmission interrupted by client for file {file_name}. Exception: {e}")
						self.server_socket.close()
						self.queue.task_done()
						os._exit(-1)
			print(f"Finished transmission for file {file_name}. Sent {data_len} bytes")
			self.queue.task_done()

class ReceiverThread(threading.Thread):
	""" Thread accepts audio files using socket and puts their names into queue"""
	def __init__(self, output_queue: Queue, host: Host, cleanup=True, saving_period=3.0, restarting_period=30.0):
		threading.Thread.__init__(self)
		self.output_queue = output_queue
		self.host = host
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
		client_socket = self.host.connected_client_socket()
		
		file_name = next(tempfile._get_candidate_names()) + ".wav"
		# disable class streaming, use queue for playing files
		stream = SavingBufferWithStreaming(do_streaming=False) 
		
		waiting_interval = self.saving_period
		leftover = None
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

		from pipeline import Pipeline

class PipelineThread(threading.Thread):
	""" Thread takes file_names from input_queue, processes them and puts answers to output_queue"""
	def __init__(self, input_queue: Queue, output_queue: Queue, timeout=None):
		# prevent heavy import if parent module doesn't need this thread
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
			print("Got from queue:", input_user_name, input_file_name)
			output_file_name = self.processor.process(user_name=input_user_name, file_to_process=input_file_name)
			self.output_queue.put(output_file_name)
			self.input_queue.task_done()
