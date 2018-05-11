#Returns a list of uniq connections, but direction inpependent -> connection A to B is same as B to A
#The return value is a set containing tuples with the both addresses of a connection
def getlistofuniqconnection(data):
	connections=set()
	for entry in data:
		if not (entry.src,entry.dst) in connections and not (entry.dst,entry.src) in connections:
			connections.add((entry.scr,entry.dst))
	return connections

#Returns a dict mapping the connection tuple + the single IP within the connection  and the filename (key)
def getlistofoutfiles(outbasename,listofconnections):
	fileconnections=dict()
	for connumber,connection in enumerate(listofconnections):
		for ipnum, ip in enumerate(connection):
		#fileconnections[outbasename+"_c"+connumber+"_"+ipnum]=dict({"ForIP":ip,"Connection"	
		fileconnections[ip]=dict()
		fileconnections[ip].update({connection:outbasename+"_c"+connumber+"_"+ipnum})
		
def sippxml_out(data,outbasename=None,seperateby="ip",templatepath="templates/"):

	if seperateby=="ip":
		getlistofoutfiles(outbasename, getlistofuniqconnection(data))
		
