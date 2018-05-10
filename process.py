from scapy.all import *
import re
from argparse import ArgumentParser

#Actually they are not quite accurate - in request line the url schemes are represented by any non-whitespace-character -> too lazy to implement all the schemes
#statusline -> the Reason-Phrase is represented by .*, as it could be nearly everything (but by BPF just >nearl< everything)
requestline="^[\w,-,\.,!,%,\*,_,\+,\',~]+ \S* SIP/\d+\.\d+"
statusline="SIP/\d+\.\d+ \d{3} .*"
debug=True

gargs=None
collectedmessages=list()

def processargs():
	argparser=ArgumentParser(description="Processes PCAP files and returns the raw SIP (+everything in the Body/Content)")
	argparser.add_argument("-d","--debug",type=bool,default=0,dest="debug",help="1 -> enable debug messages, 0 (default) -> disable debug messages")
	argparser.add_argument("-e","--debugfile",type=str,default=sys.stderr,dest="debugfile",help="Write debug messages to file -> default is stderr (print it on termial)")
	argparser.add_argument("-f","--file",type=str,required=True,dest="infile",help="File to parse (must be pcap or pcapng)")
	argparser.add_argument("-o","--out","--outputfile",type=str,default=sys.stdout,dest="outfile",help="Write SIP messages to file - default is print to stdout")

	return(vars(argparser.parse_args()))

#Opens a file (based on the path) and returns the handle, if not a string has been passed return what was passed (it could be already a file handler)
def makefilehandler(filepath,mode="a",dieonerror=True):
	#Check whether it is a string -> if not return what you have got -> it could be that it already a file handler or similar (stdout, stderr)
	if type(filepath)==str:
		try:
			fhandler=open(filepath,mode)
		except Exception as ex:
			print("File", filepath, "could not be opened in mode", mode)
			print (ex)
			if dieonerror:
				print("Program terminated")
				exit(1)
			else: fhandler=None
	else:
		fhandler=filepath
	return fhandler

def debug(message):
	if gargs["debug"]:
		fhandler=makefilehandler(gargs["debugfile"])
		print(message,file=fhandler)
		#This is surely not the most elegant way to close that after every single write, but everything else would need more effort
		#Prevent closing stderr -> seems you can't open it again
		if type(gargs["debug"])==str:
			fhandler.close()

def result(sipmessage):
	fhandler=makefilehandler(gargs["outfile"])
	for message in sipmessage:
		print (message,file=fhandler)
	fhandler.close()

gargs=processargs()

try:
	fhandler = rdpcap(gargs["infile"])
except Exception as ex:
	print("Problem opening capture file",gargs["infile"])
	print (ex)
	exit()
for pcount,packet in enumerate(fhandler):
	debug("\nProcessing packet:"+ str(pcount+1))
	counter=0
	#Running through layers
	while True:
		debug("Processing layer"+str(counter))
		try:
			debug("Checking for SIP, result:" + str(re.match("^"+requestline+"|"+statusline,str(bytes(packet[counter]),"UTF-8"))))
			if re.match("^"+requestline+"|"+statusline,str(bytes(packet[counter]),"UTF-8")):
				debug ("Found SIP, stop processing of packet")
				collectedmessages.append(str(bytes(packet[counter]),"UTF-8"))
				break
		#It is possible that in the Layer are data which are resulting in invalid unicode -> in this case it is not SIP -> continue searching
		except UnicodeDecodeError:
			debug("Checking layer gave unicodeError -> expected if not SIP")
			continue

		#Have not found a way to know how many layers there are (len is returning length of the layer, not how many there are) and iteration just returns the current layer
		#So just try and react to IndexError -> if that occurs we know there are no more layers in this packet to check
		except IndexError:
			debug("Found no SIP in packet - next packet")
			break
		#Increasing counter needs to be run even if UnicodeDecodeError happens and loop will run the next loop -> else endless loop by not increasing counter
		finally:
			counter+=1
result(collectedmessages)

#	packet.show()
#	print(dir(type(packet)))
#	print ("Packet:", type(packet))
#	payload=packet.payload
#	#print (payload)
#	ip=packet.getlayer(UDP)
#	print (type(ip))
#	print ("Ausgabe:",str(bytes(ip.payload),"UTF-8"))
#	print ("Last Layer:",str(bytes(ip.lastlayer()),"UTF-8"))
#
#	fhandle=open("hallo.txt","w")
#	fhandle.write(str(ip.payload))
#	fhandle.close()
