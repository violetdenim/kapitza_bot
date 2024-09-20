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
host_ip = socket.gethostbyname(host_name) # os.environ.get("HOST_IP")
port = int(os.environ.get("HOST_PORT"))

class SavingBuffer:
	def __init__(self):
		self.data = b""

	def push(self, frame):
		self.data += frame
	
	def is_closed(self):
		return len(self.data) == 0
	
	def close(self, out_file="received.wav"):
		with open(out_file, "wb") as f:
			f.write(self.data)
		self.data = b""

class WavInfo:
    """Class for storing wav parameters to pass to pyaudio"""
    frame_rate: int
    num_channels: int
    sample_width: int

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
        # num_samples = data_size // (num_channels * sample_width)

class SavingBufferWithStreaming:
	def __init__(self, do_streaming=True):
		self.data = b""
		if do_streaming:
			self.p = pyaudio.PyAudio()
			os.environ['SDL_AUDIODRIVER'] = 'dsp'
			self.stream = None
		else:
			self.p = None

	def push(self, frame):
		if self.p:
			if self.stream is None:
				WAV_HEADER_SIZE = 44
				header = WavInfo(frame[:WAV_HEADER_SIZE])
				self.stream = self.p.open(format=self.p.get_format_from_width(header.sample_width),
						channels=header.num_channels,
						rate=header.frame_rate,
						output=True)
				if self.stream.is_active():
					self.stream.write(frame[WAV_HEADER_SIZE:])
			else:
				if self.stream.is_active():
					self.stream.write(frame)
		self.data += frame
		
	def is_closed(self):
		return len(self.data) == 0
	
	def close(self, out_file="received.wav"):
		if self.p:
			if self.stream.is_active():
				self.stream.close()
			self.stream = None # prepare for the next transmission

		with open(out_file, "wb") as f:
			f.write(self.data)
		self.data = b""
	
	def __exit__(self):
		if self.p:
			self.p.terminate()

class Receiver(threading.Thread):
	def __init__(self, cleanup=True, stream_to_output=True):
		threading.Thread.__init__(self)
		self.stream_to_output = True
		self.cleanup = cleanup

		self.saving_period = 3.0
		self.restarting_period = 30.0
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

		stream = SavingBufferWithStreaming(do_streaming=self.stream_to_output) 
		
		waiting_interval = self.saving_period
		data = b""
		payload_size = struct.calcsize("Q")
		while True:
			try:
				while len(data) < payload_size:
					client_socket.settimeout(waiting_interval)
					packet = client_socket.recv(CHUNK) # 4K
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
					data += client_socket.recv(CHUNK)
					waiting_interval = self.saving_period
				frame_data, data = data[:msg_size], data[msg_size:] # pass left-over to the next message
				# frame = pickle.loads(frame_data)
				frame = frame_data
				stream.push(frame)
				# wait for the next data
			except Exception as e:
				print(f"{e}. No transmission for {waiting_interval} seconds!")
				if stream.is_closed():
					print(f"Client is closing connection.")
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
	Receiver(stream_to_output=True).start()

 