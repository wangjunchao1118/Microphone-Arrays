import subprocess, os, sys
import threading
import time
import signal
import zmq
import datetime
import socket

from matrix_io.proto.malos.v1 import driver_pb2
from matrix_io.proto.malos.v1 import io_pb2

from multiprocessing import Process
from zmq.eventloop import ioloop

inputflag = 'flag'
startflag = False

creator_ip = os.environ.get('CREATOR_IP', '127.0.0.1')
creator_everloop_base_port = 20013 + 8
now = datetime.datetime.now()
host = '155.69.146.210';
port = 8000;
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((host, port))
	
class recordThread (threading.Thread):
	
	def __init__(self):
		threading.Thread.__init__(self)
		self.result = None
		 
		
	def run(self):
				
		a1 = "arecord --device=mic_channel8 -r 16000 -c 1 -f S16_LE"
		self.result = subprocess.Popen(a1.split(), stdout=subprocess.PIPE, preexec_fn=os.setsid)
	
		wav = self.result.stdout.read(1024)
		while(wav):
			s.send(wav)
			wav = self.result.stdout.read(1024)
	
	def stop(self):
		os.killpg(os.getpgid(self.result.pid), signal.SIGTERM)


def ledall(light):
	"""Sets all of the LEDS to a given rgbw value"""

	context = zmq.Context()

	config_socket = context.socket(zmq.PUSH)
	config_socket.connect('tcp://{0}:{1}'.format(creator_ip, creator_everloop_base_port))

	config = driver_pb2.DriverConfig()

	image = []

	for led in range(35):
		ledValue = io_pb2.LedValue()
		ledValue.blue = 0
		ledValue.red = 0
		ledValue.green = light
		ledValue.white = 0
		image.append(ledValue)

	config.image.led.extend(image)

	config_socket.send(config.SerializeToString())

	
def ledloop(flag):
	"""Sets all of the LEDS to a given rgbw value"""
	context = zmq.Context()

	config_socket = context.socket(zmq.PUSH)
	config_socket.connect('tcp://{0}:{1}'.format(creator_ip, creator_everloop_base_port))

	config = driver_pb2.DriverConfig()

	image = []

	for led in range(35):
		if led == flag :
			ledValue = io_pb2.LedValue()
			ledValue.blue = 0
			ledValue.red = 0
			ledValue.green = 20
			ledValue.white = 0
			image.append(ledValue)
		else :
			ledValue = io_pb2.LedValue()
			ledValue.blue = 0
			ledValue.red = 0
			ledValue.green = 0
			ledValue.white = 0
			image.append(ledValue)
			
	config.image.led.extend(image)
	config_socket.send(config.SerializeToString())
		
class everloopThread (threading.Thread):
	
	def __init__(self):
		self.running = False
		threading.Thread.__init__(self)
	
	def start(self):
		self.running = True
		threading.Thread.start(self)
	
	def run(self):
		ledall(20)
		time.sleep(0.5)
		ledall(0)
		while self.running:
			for i in range(35):
				ledloop(i)
				time.sleep(0.5)
				if self.running == False :
					break;
				
	def stop(self):
		self.running = False
		ledall(20)
		time.sleep(0.5)
		ledall(0)
		
		
def inputcommand():
	str = raw_input("Please input start or stop or exit:")
	return str
		

if __name__ == "__main__":
	
	# Instantiate ioloop
	ioloop.install()
	
	while True:
		inputflag = inputcommand()
		if inputflag == 'start' and startflag == False:
				
				threadrecord = recordThread()
				threadeverloop = everloopThread()
				threadrecord.start()
				threadeverloop.start()
				
				print "start recording"
				time.sleep(0.5)
				startflag = True		
				
		elif inputflag == 'start' and startflag == True:
				print "record is running "
			
		elif inputflag == 'stop' and startflag == True:
				startflag = False
				threadrecord.stop()
				threadeverloop.stop()
				time.sleep(0.5)	
				print "recording done"
				
		elif inputflag == 'stop' and startflag == False:
				print "there is no record"
				
		elif inputflag == 'exit' and startflag == True:
				print "Please input stop first"

		elif inputflag == 'exit' and startflag == False:
				print "record work is over"
				exit()
		else:
				print "input wrong"
			
			
