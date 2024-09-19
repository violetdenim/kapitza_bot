# Welcome to PyShine
# This is client code to receive video and audio frames over TCP

import os
import socket, time
import threading, pyaudio, pickle, struct

import dotenv
dotenv.load_dotenv()

# host_ip = os.environ.get("HOST_IP")
host_name = socket.gethostname()
host_ip = socket.gethostbyname(host_name)#os.environ.get("HOST_IP")
port = int(os.environ.get("HOST_PORT"))

class Reciever(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		# os.environ['SDL_AUDIODRIVER'] = 'dsp'
		self.p = pyaudio.PyAudio()
		self.CHUNK = 1024
		self.waiting_period = 3.0

	def run(self):
		stream = self.p.open(format=self.p.get_format_from_width(2),
						channels=2, rate=44100, output=True, frames_per_buffer=self.CHUNK)
		block_size = 4 * self.CHUNK
		# create socket
		client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		socket_address = (host_ip, port-1)
		client_socket.connect(socket_address)
		data = b""
		payload_size = struct.calcsize("Q")
		while True:
			try:
				while len(data) < payload_size:
					client_socket.settimeout(self.waiting_period)
					packet = client_socket.recv(block_size) # 4K
					data += packet
				packed_msg_size = data[:payload_size]
				data = data[payload_size:]
				msg_size = struct.unpack("Q",packed_msg_size)[0]
				while len(data) < msg_size:
					client_socket.settimeout(self.waiting_period)
					data += client_socket.recv(block_size)
				frame_data, data = data[:msg_size], data[msg_size:] # pass left-over to the next message
				frame = pickle.loads(frame_data)
				stream.write(frame)
				# data = b""
				# wait for the next data
			except Exception as e:
				print(f"No transmission for {self.waiting_period} seconds! Closing stream. {e}")
				stream.close()
				print("Exiting!")
				self.p.terminate()
				client_socket.close()
				os._exit(0)

if __name__ == "__main__":
	Reciever().start()

 