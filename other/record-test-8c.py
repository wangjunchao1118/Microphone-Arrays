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
		#self.running = False
		self.tgtdir="/home/pi/wjc/recorddata/{0}_{1}_{2}_{3}_{4}_{5}".format(self.now.year, self.now.month, self.now.day, self.now.hour, self.now.minute, self.now.second)
		try:
                        if not os.path.exists(self.tgtdir):
                                os.makedirs(self.tgtdir)
		except:
                        raise Exception("failed to make folder '{0}'".format(self.tgtdir))
		
		# try:
		#	self.f0 = open("{0}/c0.wav".format(tgtdir), 'wb')
		#	self.f1 = open("{0}/c1.wav".format(tgtdir), 'wb')
		#	self.f2 = open("{0}/c2.wav".format(tgtdir), 'wb')
		#	self.f3 = open("{0}/c3.wav".format(tgtdir), 'wb')
		#	self.f4 = open("{0}/c4.wav".format(tgtdir), 'wb')
		#	self.f5 = open("{0}/c5.wav".format(tgtdir), 'wb')
		#	self.f6 = open("{0}/c6.wav".format(tgtdir), 'wb')
		#	self.f7 = open("{0}/c7.wav".format(tgtdir), 'wb')
		#	self.f8 = open("{0}/c8.wav".format(tgtdir), 'wb')
		# except IOError:
		#	print "Error to open file"
		
	def run(self):
		
		#self.running = True					
		a0 = "arecord --device=mic_channel0 -r 16000 -c 1 -f S16_LE {0}/c0.wav".format(self.tgtdir)
		a1 = "arecord --device=mic_channel1 -r 16000 -c 1 -f S16_LE {0}/c1.wav".format(self.tgtdir)
		a2 = "arecord --device=mic_channel2 -r 16000 -c 1 -f S16_LE {0}/c2.wav".format(self.tgtdir)
		a3 = "arecord --device=mic_channel3 -r 16000 -c 1 -f S16_LE {0}/c3.wav".format(self.tgtdir)
		a4 = "arecord --device=mic_channel4 -r 16000 -c 1 -f S16_LE {0}/c4.wav".format(self.tgtdir)
		a5 = "arecord --device=mic_channel5 -r 16000 -c 1 -f S16_LE {0}/c5.wav".format(self.tgtdir)
		a6 = "arecord --device=mic_channel6 -r 16000 -c 1 -f S16_LE {0}/c6.wav".format(self.tgtdir)
		a7 = "arecord --device=mic_channel7 -r 16000 -c 1 -f S16_LE {0}/c7.wav".format(self.tgtdir)
		#a8 = "arecord --device=mic_channel8 -r 16000 -c 1 -f S16_LE {0}/c8.wav".format(self.tgtdir)
		
		# self.result0 = subprocess.Popen(a0.split(), stdout=self.f0, preexec_fn=os.setsid)
		self.result0 = subprocess.Popen(a0.split(), stdout=subprocess.PIPE, preexec_fn=os.setsid)
		self.result1 = subprocess.Popen(a1.split(), stdout=subprocess.PIPE, preexec_fn=os.setsid)
		self.result2 = subprocess.Popen(a2.split(), stdout=subprocess.PIPE, preexec_fn=os.setsid)
		self.result3 = subprocess.Popen(a3.split(), stdout=subprocess.PIPE, preexec_fn=os.setsid)
		self.result4 = subprocess.Popen(a4.split(), stdout=subprocess.PIPE, preexec_fn=os.setsid)
		self.result5 = subprocess.Popen(a5.split(), stdout=subprocess.PIPE, preexec_fn=os.setsid)
		self.result6 = subprocess.Popen(a6.split(), stdout=subprocess.PIPE, preexec_fn=os.setsid)
		self.result7 = subprocess.Popen(a7.split(), stdout=subprocess.PIPE, preexec_fn=os.setsid)
		#self.result8 = subprocess.Popen(a8.split(), stdout=subprocess.PIPE, preexec_fn=os.setsid)
	
		
		# while self.running:
			
		#	wav0 = self.result0.stdout.read(1024)
		#	wav1 = self.result1.stdout.read(1024)
		#	wav2 = self.result2.stdout.read(1024)
		#	wav3 = self.result3.stdout.read(1024)
		#	wav4 = self.result4.stdout.read(1024)
		#	wav5 = self.result5.stdout.read(1024)
		#	wav6 = self.result6.stdout.read(1024)
		#	wav7 = self.result7.stdout.read(1024)
		#	wav8 = self.result8.stdout.read(1024)
			
		#	self.f0.write(wav0)
		#	self.f1.write(wav1)
		#	self.f2.write(wav2)
		#	self.f3.write(wav3)
		#	self.f4.write(wav4)
		#	self.f5.write(wav5)
		#	self.f6.write(wav6)
		#	self.f7.write(wav7)
		#	self.f8.write(wav8)
			
			
			
			#nIndex = 0
			#while nIndex < 9:
				
				#wavBuffer = "wav{0}".format(nIndex)
				#ostream = "f{0}".format(nIndex)
				#ostream.write(wavBuffer)
				#wavBuffer = self.result.stdout.read(1024)
	# def close(self):	
	#	self.f0.close()
	#	self.f1.close()
	#	self.f2.close()
	#	self.f3.close()
	#	self.f4.close()
	#	self.f5.close()
	#	self.f6.close()
	#	self.f7.close()
	#	self.f8.close()
	
	def stop(self):
		#self.running = False
		#self.close()
		os.killpg(os.getpgid(self.result0.pid), signal.SIGTERM)
		os.killpg(os.getpgid(self.result1.pid), signal.SIGTERM)
		os.killpg(os.getpgid(self.result2.pid), signal.SIGTERM)
		os.killpg(os.getpgid(self.result3.pid), signal.SIGTERM)
		os.killpg(os.getpgid(self.result4.pid), signal.SIGTERM)
		os.killpg(os.getpgid(self.result5.pid), signal.SIGTERM)
		os.killpg(os.getpgid(self.result6.pid), signal.SIGTERM)
		os.killpg(os.getpgid(self.result7.pid), signal.SIGTERM)
		#os.killpg(os.getpgid(self.result8.pid), signal.SIGTERM)
		

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
	
	
	
