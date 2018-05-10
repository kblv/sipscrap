#What it is

Sipscrap is thought as a tool to extract raw SIP messages (as used for voice over IP) out of a pcap file.

Raw SIP messages in this context means just the SIP message + its body (for example SDP), nothing else.
You will get a text representation (as file or to stdout) of the message, as SIP is just text.

This is useful for example if you want to use the SIP messages in a sipp tester scenario - for this case you could simply copy the message and copy-paste it to the scenario (make sure you copy the blank lines at the end) or if you need to validate some stuff using text processing tools.


#Limitations

Currently there are the following limitations:

* The Request-Line (in SIP Requests) or the Status-Line (in Responses) must be valid as by the BNF in RFC 3261
** you don't need to worry about that if you are sure it is valid SIP which is in the PCAP
* No seperation of call flows
** sipscrap will not care about which messages belong to which call, but just find all messages and print them
** if you need them to be separated it is advised to filter the PCAP (for example in Wireshark) and just save the messages you want as new PCAP
* No taking into account of Content-Length
** The Content-Length header is not being checked, instead everything from the start of the message, till the end of the packet is being taken as being part of the SIP message/its body
* Multiple SIP messages per Layer-4 packet are not supported
** If a UPD, TCP, SCTP packet contains multiple SIP messages it will detect the first one and everything after it as being part of the same SIP message (so you will have a SIP message with SIP messages in it in this case)
* SIP messages across multiple layer 4 messages are not supported
** If the SIP message is longer than one layer 4 packet (UPD, SIP, SCTP) it will not be fetched completely, but just the part which starts in one packet


#What it could handle

* Non-SIP messages are no problem - they will be simply skipped
* It should support most of the common transport protocols (everything up to layer 4)
** this should include things like VAN-tunnels (Ethernet-in-Ethernet header encapsulation)
** it uses the python library scapy for that and basically does not care about the layers, but just for that they are seperated, so it could take the Unknown one and checks wheter it is SIP 


#What is needed to use it

In the following pip (Python package installer) is being used, please note that in Linux you usually need to be root to use it


* Python 3
* pip3 (Used to install additional python packages)
* The scapy python library
** pip install scapy
** it might require some additional tools and libraries (please see here: [Instruction] (http://scapy.readthedocs.io/en/latest/installation.html#platform-specific-instructions)
* re (Regular-Expression Parser) - that should be usually be part of the Python installation
* argparse (Command line argument parser)
** pip install argparse



#Usage

* process.py -f \<File to Parse\>
** This will process the given file and print the output on the command line
* -o \<File\> will write the output to a file
