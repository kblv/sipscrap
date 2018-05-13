from scapy.all import *
import re
from argparse import ArgumentParser
from debug import debug as d
from sippxml import sippxml_out 

#Actually they are not quite accurate - in request line the url schemes are represented by any non-whitespace-character -> too lazy to implement all the schemes
#statusline -> the Reason-Phrase is represented by .*, as it could be nearly everything (but by BPF just >nearl< everything)
requestline="^[\w,-,\.,!,%,\*,_,\+,\',~]+ \S* SIP/\d+\.\d+"
statusline="SIP/\d+\.\d+ \d{3} .*"
debug=True

gargs=None


def processargs():
	argparser=ArgumentParser(description="Processes PCAP files and returns the raw SIP (+everything in the Body/Content)")
	argparser.add_argument("-d","--debug",type=bool,default=0,dest="debug",help="1 -> enable debug messages, 0 (default) -> disable debug messages")
	argparser.add_argument("-e","--debugfile",type=str,default=sys.stderr,dest="debugfile",help="Write debug messages to file -> default is stderr (print it on termial)")
	argparser.add_argument("-f","--file",type=str,required=True,dest="infile",help="File to parse (must be pcap or pcapng)")
	argparser.add_argument("-o","--out","--outputfile",type=str,default=sys.stdout,dest="outfile",help="Write SIP messages to file - default is print to stdout")
	argparser.add_argument("-x","--xml",dest="xml",action="store_true",help="Writes sipp xml files")

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

#def d.debug(message):
#	if gargs["debug"]:
#		fhandler=makefilehandler(gargs["debugfile"])
#		print(message,file=fhandler)
#		#This is surely not the most elegant way to close that after every single write, but everything else would need more effort
#		#Prevent closing stderr -> seems you can't open it again
#		if type(gargs["debug"])==str:
#			fhandler.close()
#
def result(sipmessage):
	if gargs["xml"]:
		sippxml_out(sipmessage,"/tmp/outfile")	
	fhandler=makefilehandler(gargs["outfile"])
	for message in sipmessage:
		print (message["message"],file=fhandler)
	fhandler.close()

###Check for IPv6 required
def getips(packet):
	if packet.haslayer(scapy.layers.inet.IP):
		d.debug("Found the following src and dst IP in the packet: " + packet.getlayer(scapy.layers.inet.IP).src + " " + packet.getlayer(scapy.layers.inet.IP).dst)
		return packet.getlayer(scapy.layers.inet.IP).src, packet.getlayer(scapy.layers.inet.IP).dst
	else:
		d.debug("Didn't found any IP header in the packet - so no IPs available")
		return None, None


#collectedmessages is a list of dicts containing src-addr, dst-addr, message
def scrap():
	collectedmessages=list()
	try:
		fhandler = rdpcap(gargs["infile"])
	except Exception as ex:
		print("Problem opening capture file",gargs["infile"])
		print (ex)
		exit()
	for pcount,packet in enumerate(fhandler):
		d.debug("\nProcessing packet:"+ str(pcount+1))
		counter=0
		#Running through layers
		while True:
			d.debug("Processing layer"+str(counter))
			try:
				d.debug("Checking for SIP, result:" + str(re.match("^"+requestline+"|"+statusline,str(bytes(packet[counter]),"UTF-8"))))
				if re.match("^"+requestline+"|"+statusline,str(bytes(packet[counter]),"UTF-8")):
					d.debug ("Found SIP, stop processing of packet")
					collectedmessages.append(dict({"message":str(bytes(packet[counter]),"UTF-8")}))
					src,dst = getips(packet)	
					collectedmessages[len(collectedmessages)-1].update({"src":src,"dst":dst})
					break
			#It is possible that in the Layer are data which are resulting in invalid unicode -> in this case it is not SIP -> continue searching
			except UnicodeDecodeError:
				d.debug("Checking layer gave unicodeError -> expected if not SIP")
				continue

			#Have not found a way to know how many layers there are (len is returning length of the layer, not how many there are) and iteration just returns the current layer
			#So just try and react to IndexError -> if that occurs we know there are no more layers in this packet to check
			except IndexError:
				d.debug("Found no SIP in packet - next packet")
				break
			#Increasing counter needs to be run even if UnicodeDecodeError happens and loop will run the next loop -> else endless loop by not increasing counter
			finally:
				counter+=1
	return(collectedmessages)

gargs=processargs()
#Initalizing the debug static object
d.setup(gargs["debug"],gargs["debugfile"])
result(scrap())


