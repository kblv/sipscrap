from debug import debug as d
from filehandler import makefilehandler 


method="^[\w,-,\.,!,%,\*,_,\+,\',~]+ (\S*) SIP/\d+\.\d+"
responsecode="SIP/\d+\.\d+ (\d{3}) .*"

templatenames=dict({"epilog":"epilog.xml","preamble":"preamble.xml","receive":"recv.xml","send":"send.xml"})

#Returns a list of uniq connections, but direction inpependent -> connection A to B is same as B to A
#The return value is a set containing tuples with the both addresses of a connection
def getlistofuniqconnection(data):
	connections=set()
	for entry in data:
		if not (entry.src,entry.dst) in connections and not (entry.dst,entry.src) in connections:
			connections.add((entry.scr,entry.dst))
	d.debug("got list of uniq connections" + str(connections))
	return connections

#Takes a list of tuples with IPs and returns a list or set of IP addresses - it could be defined whether the entries need to be uniqu
def getlistofipsfromconnections(connlist,uniq=False):
	if uniq:
		iplist=set()
		for conn in connlist:
			iplist.update(conn)
		d.debug("Got set of unique IP addresses" + str(iplist))
	else:
		iplist=list()
		for conn in connlist:
			iplist.extend(conn)	
		d.debug("Got list of IP addresses" + str(iplist))
	return iplist

#Returns from a list of connections the peer for a certain IP
def getlistofpeers(ip,connections):
	peerlist=list()
	for connection in connections:
		if ip in connection:
			if ip == connection[0]:
				peerlist.append(connection[1])
			else:
				peerlist.append(connection[0])
	d.debug("Got list of peers for "+ ip + ": " + str(peerlist))
	return peerlist
				
		
#Returns a dict mapping the connection tuple + the single IP within the connection  and the filename (key)
def getlistofoutfiles(outbasename,listofconnections):
	fileconnections=dict()
	
	uniqconn=getlistofuniqconnection(listofconnections)
	for ipnum, ip in getlistofipsfromconnections(uniqconn,True):
		fileconnections[ip]=dict()
		for peernum, peer in enumerate(getlistofpeers(ip,uniqconn)):
			fileconnections[ip].update({peer:dict()})
			fileconnection[sip][peer].update({"filename":outbasename+"_ip"+ipnum+"_"+"peer"+peernum})
			d.debug("Added file "+ fileconnections[ip][peer]["filename"] + " for " + ip + " and its peer " + peer)
	return fileconnections 

#returns either the status code or the method of the message
def getMethodorStatus(data):
	#There could be empty lines in the beginning, so we are looping
	for line in data:
		result=re.match(method + "|" + responsecode,data)
		if result:
			if result.group(1):
				return result.group(1) 
				d.debug("Found Method:" + result.group(1))
			else:
				return result.group(2)
				d.debug("Found Responsecode:" + result.group(2))

#Returns a dict, containing the name (functional name)  and the content	of the template
def gettemplates(path,filelist):
	templates=dict()
	for name,filename in filelist:
		with makefilehandler(path+"/"+filename,"r") as fhandler:
			templates.update({name:fhandler.read()})		
		d.debug("Read template file " + filename + " as " + name)
	return templates
		
	
#This is atcually a waste, but as outfileconnections is no class which could store the outfileconnection-list, as well of a list of just the filehandlers nobody could guarantee that 
#when using 2 lists to construct the same functionality both will get updated all the time
def getlistofoutfilehandlers(outfileconnections):
	outfilhandlerlist=list()
	for ipentry in outfileconnections:
		for peerentry in ipentry:
			outfilhandlerlist.append(outfileconnections[ipentry][peerentry]["filehandler"])
	return outfilhandlerlist 
	d.debug("Returned filehandler list for outfileconnectionlist")

#Replaces marker in templates with the value and returns a list of finished processed strings
#templates is a list (needs to be) of templates (basically strings)
#replace is a dictionary containing the marker names as key and the values by which to replace as value
#markerprefix and markersuffix is what comes in the template before the marker-name to define it as marker
def replacemarker(templates,replace,markerprefix="<!scrap-",markersuffix="!>"):
	outlist=list()
	for template in templates:
		for marker, value in replace.items():
			compiledmarker=markerprefix+marker+markersuffix
			template=template.replace(compiledmarker,value)
			d.debug("Replacing in template " + template + " " + compiledmarker + "by" + value)
		outlist.append(template)
	return outlist
			
			
		
#Funktion which writes template to a file + replacing marker strings in the template with a defined value
#outfiles could be one or a list of filehandles (files need to be opened before)
#templates could be one or multiple templates to write (they will be written in the order as they appear)
#replace is a optional dictionary containing the strings to be replaced as key and the values they should be replaced by as value
def writetemplatetooutfile(outfiles,templates,replace=None):
	outfilelist=list()
	templatelist=list()
	#Sanitize stuff
	if type(outfiles)==str:
		outfilelist.append(outfiles) 
	if type(templates)==str:
		templatelist.append(templates)
	 
	if replace:
		templatelist=replacemarker(templatelist,replace)	

	for outfile in outfilelist:
		for template in templatelist:
			outfile.write(template)
	


def sippxml_out(data,outbasename=None,seperateby="ip",templatepath="templates/"):

	#Add at this point add other seperateby ways
	if seperateby=="ip":
		outfileconnections=getlistofoutfiles(outbasename, getlistofuniqconnection(data))

	#This should probably go to a own function	
	#Open the outfiles	
	d.debug("Opening the output files")
	for ipentry in outfileconnections:
		for peerentry in ipentry:
			outfileconnections[ipentry][peerentry].update({"filehandler":makefilehandler(peerentry["filename"],mode="w")})
	
	#Get the content of the templates		
	d.debug("Loading the templates")
	templates=gettemplates(templatepath,templatenames)

	#Write the preamble to all file 
	d.debug("Writing the preamble to all output files")
	writetemplatetooutfile(getlistofoutfilehandlers(outfileconnections),templates["preamble"])

	#Write the responses and requests to the files	
	d.debug("Writing the actual data to the output files") 
	for dataset in data:
		methodresponse=getMethodorStatus(dataset["message"])	 
		replacedict=dict({"methodresponse":methodresponse,"message":data})
		writetemplatetooutfile(outfileconnections[dataset["src"]],templates["send"],replacedict)	
		writetemplatetooutfile(outfileconnections[dataset["dst"]],templates["receive"],replacedict)	

	#Write the epilog to all files
	d.debug("Writing the epilog to all files")
	writetemplatetooutfile(getlistofoutfilehandlers(outfileconnections),templates["epilog"])

	d.debug("Closing all output file")
	for filehandler in getlistofoutfilehandlers(outfileconnections):
		filehandler.close()
