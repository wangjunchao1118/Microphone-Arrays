import os, sys
import subprocess
import zmq
import time
import datetime
import threading
import signal
from matrix_io.proto.malos.v1 import driver_pb2
from matrix_io.proto.malos.v1 import io_pb2

from multiprocessing import Process
from zmq.eventloop import ioloop, zmqstream

creator_ip = os.environ.get('CREATOR_IP', '127.0.0.1')
creator_gpio_base_port = 20013 + 36
creator_everloop_base_port = 20013 + 8
#now = datetime.datetime.now()

gpio_value = 0
#inputflag = 'flag'
recordflag = 0

def config_gpio_read(pin):
	"""This function sets up a pin for use as an input pin"""
	# Create a new driver config
	config = driver_pb2.DriverConfig()
	# Set 250 miliseconds between updates.
	config.delay_between_updates = 0.25
	# Stop sending updates 2 seconds after pings.
	config.timeout_after_last_ping = 2
	# Set the pin to the value provided by the function param
	config.gpio.pin = pin
	# Set the pin mode to input
	config.gpio.mode = io_pb2.GpioParams.INPUT
	# Send configuration to malOS using global sconfig
	sconfig.send(config.SerializeToString())

def gpio_callback(msg):
	data = io_pb2.GpioParams().FromString(msg[0])
	global gpio_value
	if format(data) == '':
		#print("0\n")
		gpio_value = 0
	else:
		#print("1\n")
		gpio_value = 1

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
		
	
class gpioThread (threading.Thread):
	
	def __init__(self, callback, creator_ip, sensor_port):
		self.running = False
		self.callback = callback
		self.creator_ip = creator_ip
		self.sensor_port = sensor_port
		threading.Thread.__init__(self)
	
	def start(self):
		self.running = True
		threading.Thread.start(self)
	
	def run(self):
		context = zmq.Context()
		socket = context.socket(zmq.SUB)
		data_port = self.sensor_port + 3
		socket.connect('tcp://{0}:{1}'.format(self.creator_ip, data_port))
		socket.setsockopt(zmq.SUBSCRIBE, b'')
		stream = zmqstream.ZMQStream(socket)
		stream.on_recv(self.callback)
		ioloop.IOLoop.instance().start()
	
	def stop(self):
		ioloop.IOLoop.instance().stop()
		self.running = False
		
class keep_aliveThread (threading.Thread):
	
	def __init__(self, creator_ip, sensor_port, ping):
		self.running = False
		self.creator_ip = creator_ip
		self.sensor_port = sensor_port
		self.ping = ping
		threading.Thread.__init__(self)
	
	def start(self):
		self.running = True
		threading.Thread.start(self)
	
	def run(self):
		context = zmq.Context()
		# Set up socket as a push
		sping = context.socket(zmq.PUSH)
		# Set the keep alive port to the sensor port from the function args + 1
		keep_alive_port = self.sensor_port + 1
		# Connect to the socket
		sping.connect('tcp://{0}:{1}'.format(self.creator_ip, keep_alive_port))
		# Start a forever loop
		while self.running:
			# Ping with empty string to let the drive know we're still listening
			sping.send_string('')
			time.sleep(self.ping)
				
	def stop(self):
		self.running = False

class recordThread (threading.Thread):
	
	def __init__(self):
		threading.Thread.__init__(self)
		self.result = None
		self.now = datetime.datetime.now() 
		
	def run(self):
		
		try:
			f = open("/home/pi/wjc/recorddata/%s_%s_%s_%s_%s_%s.wav" % (self.now.year, self.now.month, self.now.day, self.now.hour, self.now.minute, self.now.second), "w")
		except IOError:
			print "Error to open file"
			
		a1 = "arecord --device=mic_channel8 -r 16000 -c 1 -f S16_LE"
		self.result = subprocess.Popen(a1.split(), stdout=subprocess.PIPE, preexec_fn=os.setsid)
	
		wav = self.result.stdout.read(1024)
		while(wav):
			f.write(wav)
			wav = self.result.stdout.read(1024)
	
	def stop(self):
		os.killpg(os.getpgid(self.result.pid), signal.SIGTERM)
		

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
	
		
if __name__ == "__main__":
	# Instantiate an ioloop
	ioloop.install()
	#Grab zmq context
	context = zmq.Context()
	# Create sconfig object that will be used by all subsequent functions
	# Essentially a gloabl
	sconfig = context.socket(zmq.PUSH)
	sconfig.connect('tcp://{0}:{1}'.format(creator_ip, creator_gpio_base_port))
	# pin 1 in input mode
	config_gpio_read(1)
	
	keep_alivethread = keep_aliveThread(creator_ip, creator_gpio_base_port, 1)
	gpiothread = gpioThread(gpio_callback, creator_ip, creator_gpio_base_port)
	#recordthread = recordThread()
	#everloopthread = everloopThread()
	
	keep_alivethread.start()
	gpiothread.start()
	
	while True:
		if gpio_value == 0 and recordflag == 0:
			print "no record\n"

		elif gpio_value == 1 and recordflag == 0:
			print "start record\n"
			recordthread = recordThread()
			everloopthread = everloopThread()
			recordthread.start()
			everloopthread.start()
			recordflag = 1
		elif gpio_value == 0 and recordflag == 1:
			print "stop record\n"
			recordthread.stop()
			everloopthread.stop()
			recordflag = 0
		else: 
			#gpio_value == 1 and recordflag == 1:
			print "recording\n"
		#print gpio_value
		time.sleep(0.5)
		
		#	recordthread.start()
		#	everloopthread.start()
		#	if gpio_value == 0:
		#		print "0\n"
		#		recordthread.stop()
		#		everloopthread.stop()
		#		break;
		

	gpiothread.stop()
	keep_alivethread.stop()
	
	
	
