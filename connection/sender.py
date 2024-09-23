import os, threading

from .host import Host
from queue import Queue

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