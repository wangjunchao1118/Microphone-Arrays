import os
import sys
import zmq
import time
import datetime
import threading
import signal
from matrix_io.proto.malos.v1 import driver_pb2
from matrix_io.proto.malos.v1 import io_pb2

#from multiprocessing import Process
from zmq.eventloop import ioloop, zmqstream

creator_ip = os.environ.get('CREATOR_IP', '127.0.0.1')
creator_gpio_base_port = 20013 + 36
creator_everloop_base_port = 20013 + 8
now = datetime.datetime.now()




def driver_keep_alive():
	"""
	This doesn't take a callback function as it's purpose is very specific.
	This will ping the driver every n seconds to keep the driver alive and sending updates
	"""
	# Grab zmq context
	context = zmq.Context()
	# Set up socket as a push
	sping = context.socket(zmq.PUSH)
	# Set the keep alive port to the sensor port from the function args + 1
	keep_alive_port = creator_gpio_base_port + 1
	# Connect to the socket
	sping.connect('tcp://{0}:{1}'.format(creator_ip, keep_alive_port))
	# Start a forever loop
    	while True:
		# Ping with empty string to let the drive know we're still listening
		sping.send_string('')
		# Delay between next ping
		time.sleep(5)

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
	sconfig_gpio_setread.send(config.SerializeToString())
	print("3\n")

def gpio_callback(msg):
	"""Captures an error message and prints it to stdout"""
	#data = io_pb2.GpioParams().FromString(msg[0])
	print("2\n")
	
	#print "received gpio s" 
	#print('Received gpio register: {0}'.format(data))
	
class gpioThread (threading.Thread):
	
	def __init__(self):
		self.running = False
		threading.Thread.__init__(self)
	
	def start(self):
		self.running = True
		threading.Thread.start(self)
	
	def run(self):
		
		context_gpio_run = zmq.Context()
		socket_gpio_run = context_gpio_run.socket(zmq.SUB)
		data_port = creator_gpio_base_port + 3
		socket_gpio_run.connect('tcp://{0}:{1}'.format(creator_ip, data_port))
		# Set socket options to subscribe and send off en empty string to let it know we're ready
		socket_gpio_run.setsockopt(zmq.SUBSCRIBE, b'')
		# Create the stream to listen to
		stream = zmqstream.ZMQStream(socket_gpio_run)
		# When data comes across the stream, execute the callback with it's contents as parameters
		#print socket_gpio_run.recv_multipart()
		#stream.on_recv(gpio_callback)
		#gpio_callback()
		def echo(msg):
			print("4\n")
			stream.send_multipart(msg)
			print("2\n")
		
		stream.on_recv(echo)
		
		print("1\n")
		# Print some debug information
		#print('Connected to data publisher with port {0}'.format(data_port))
		# Start a global IO loop from tornado
		ioloop.IOLoop.instance().start()
		
		#while self.running:
			
			#if self.running == False :
			#	break;
				
	def stop(self):
		self.running = False
		

if __name__ == "__main__":

	ioloop.install()
	
	context_gpio_setread = zmq.Context()
	sconfig_gpio_setread = context_gpio_setread.socket(zmq.PUSH)
	sconfig_gpio_setread.connect('tcp://{0}:{1}'.format(creator_ip, creator_gpio_base_port))
	config_gpio_read(1)

#	driver_keep_alive()	
	threadgpio = gpioThread()
	threadgpio.start()
	#threadgpio.stop()
	
	
	# Start up a process to keep the driver alive and sending updates
	#Process(target=driver_keep_alive, args=(creator_ip, creator_gpio_base_port, 1)).start()
	# Register the callback to send data from the read pin
	#Process(target=register_data_callback, args=(gpio_callback, creator_ip, creator_gpio_base_port)).start()
