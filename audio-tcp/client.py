# Welcome to PyShine
# This is client code to receive video and audio frames over TCP

import os
import socket, time
import threading, pyaudio, pickle, struct, wave
import numpy as np
import tempfile

import dotenv
dotenv.load_dotenv()

# host_ip = os.environ.get("HOST_IP")
host_name = socket.gethostname()
host_ip = socket.gethostbyname(host_name)#os.environ.get("HOST_IP")
port = int(os.environ.get("HOST_PORT"))

class StreamingBuffer:
	def __init__(self, stream=True, CHUNK=1024):
		os.environ['SDL_AUDIODRIVER'] = 'dsp'
		self.p = pyaudio.PyAudio()
		self.CHUNK = CHUNK
		self.stream = self.p.open(format=self.p.get_format_from_width(2),
						channels=2, rate=44100, output=True, frames_per_buffer=self.CHUNK)

	def push(self, frame):
		if self.stream.is_active():
			self.stream.write(frame)
	
	def close(self):
		if self.stream.is_active():
			self.stream.close()
		self.p.terminate()

class SavingBuffer:
	def __init__(self):
		self.data = b""

	def push(self, frame):
		self.data += frame
	
	def is_closed(self):
		return len(self.data) == 0
	
	def close(self, out_file="received.wav"):
		with wave.open(out_file, "wb") as wf:
			wf.setnchannels(2)
			wf.setsampwidth(2)
			wf.setframerate(44_100)
			wf.writeframesraw(self.data)
			wf.close()
		self.data = b""

class Receiver(threading.Thread):
	def __init__(self, cleanup=True):
		threading.Thread.__init__(self)
		self.saving_period = 3.0
		self.restarting_period = 30.0
		
		self.cleanup = cleanup
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

		stream = SavingBuffer() 
		block_size = 4 * CHUNK
		
		waiting_interval = self.saving_period
		data = b""
		payload_size = struct.calcsize("Q")
		while True:
			try:
				while len(data) < payload_size:
					client_socket.settimeout(waiting_interval)
					packet = client_socket.recv(block_size) # 4K
					if len(packet) == 0:
						raise Exception("Empty packet during payload")
					waiting_interval = self.saving_period
					data += packet
				packed_msg_size, data = data[:payload_size], data[payload_size:]
				msg_size = struct.unpack("Q",packed_msg_size)[0]
				while len(data) < msg_size:
					client_socket.settimeout(waiting_interval)
					if len(packet) == 0:
						raise Exception("Empty packet during message receive")
					data += client_socket.recv(block_size)
					waiting_interval = self.saving_period
				frame_data, data = data[:msg_size], data[msg_size:] # pass left-over to the next message
				frame = pickle.loads(frame_data)
				stream.push(frame)
				# data = b""
				# wait for the next data
			except Exception as e:
				print(f"{e}. No transmission for {waiting_interval} seconds!")
				if stream.is_closed():
					print(f"Closing connection.")
					client_socket.close()
					os._exit(0)
				else:
					print(f"Closing stream.")
					stream.close(os.path.join(self.folder, file_name))
					assert(stream.is_closed())
					file_name = next(tempfile._get_candidate_names()) + ".wav"
					# wait for more 
					waiting_interval = self.restarting_period - self.saving_period

				

if __name__ == "__main__":
	Receiver().start()

 