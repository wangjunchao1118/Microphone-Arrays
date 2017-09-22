#Socket client example in python
 
import socket   #for sockets
import sys  #for exit
 
#create an INET, STREAMing socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
except socket.error:
    print 'Failed to create socket'
    sys.exit()
     
print 'Socket Created'
 
host = '155.69.146.210';
port = 8000;
  
#Connect to remote server
s.connect((host , port))
 
#print 'Socket Connected to ' + host + ' on ip ' + remote_ip
f = open('test.wav','rb')

print 'sending...'

wav = f.read(1024)
  
while (wav):
	print 'Sending...'
	s.send(wav)
	wav = f.read(1024)

f.close()
print "done sending" 
 
s.close()
