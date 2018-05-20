import re
import regex
from collections import OrderedDict
import copy
from debug import debug as d 

#Hack - striping the "[" and "]" from character classes when they need to be integrated into other character classes
#If you would not do that (and having instead something like [[old-class]some new stuff] it would not work as one character class
def rg(expression):
	d.debug("Removing [ from regular expression for: "+expression)
	stripped, count=re.subn("^\[","",expression)
	if count:
		stripped=re.subn("\]$","",stripped)[0]
	d.debug("Removed [ from regular expression from "+expression+" it is now: "+stripped)
	return stripped

#Class does not support header folding (headers going over multiple lines
class sipmessage(object):
	_alpha="[a-zA-Z]"
	_num="[0-9]"
	_alphanum="["+rg(_alpha)+rg(_num)+"]"
	_UTF8_NONASCII="[\xC0-\xDF\xE0-\xEF\xF0-\xF7\xF8-\xFb\xFC-\xFD]"
	_TEXT_UTF8char="[\x21-\x7E"+rg(_UTF8_NONASCII)+"]"
	_UTF8_CONT="[\x80-\xBF]"
	_CR="\r"
	_LF="\n"
	_CRLF=_CR+_LF
	_HTAB="\x09"
	_SP="\x20"
	_WSP="["+_SP+"|"+_HTAB+"]"
	_LWS="(?:"+_WSP+"*"+_CRLF+")?"+_WSP+"+"
	_SWS=_LWS
	_COMMA=_SWS+","+_SWS
	_HCOLON="["+_SP+"|"+_HTAB+"]*:"+_SWS
	_token="["+rg(_alphanum)+"|\-|\.|\!|%|\*|_|\+|`|'|~]+"
	_header_name="(?P<header_name>"+_token+")"
	_header_value="(?P<header_value>"+_TEXT_UTF8char+"|"+_UTF8_CONT+"|"+_LWS+")*"
	#This actually does not exist in the BNF, problem however is that in section 7.3 header is defined and it could contain multiple values - in the BNF extension-header
	#which is here called _header is defined to containing just value (so just one of them)
	_header_values="(?P<header_values>"+_header_value+"(?:"+_COMMA+_header_value+")*)"
	#_header=_header_name+_HCOLON+_header_value
	#This is extension-header in the BNF - used here as generic for all headers -> there is a difference, as I use header_values (multiple) instead of header_value (one as by the BNF)
	#This is due to there are headers containing multiple values (as Contact for exapmle)
	_header=_header_name+"(?P<headervalue_seperator>"+_HCOLON+")"+_header_values
	_requestline="^[\w,-,\.,!,%,\*,_,\+,\',~]+ \S* SIP/\d+\.\d+"
	_statusline="SIP/\d+\.\d+ \d{3} .*"
	_lineseperator="\r\n"

	def __init__(self,message):
		self.message=message
		self.messagestruct=None
	
	#Actual a short cut - we are not parsing line by line, but just seperating the lines
	def get_lines(self,message=None,lineseperator=None):
		if not message:
			message=self.message
		if not lineseperator:
			lineseperator=self._lineseperator
		d.debug("Splitted messag into lines")
		return(message.split(lineseperator))
	
	##This should maybe get to a own class at some point -> makes it possible to implement multiple methods -> such as getheader or getvalue
	#Returning a list containing the headers and there values in the order as they appear
	#In the list one header is represented by one field
	#Every field contains a dict
	#Every dict contains 2 fields (it is preferred to use the field names to get the data, so that it could be extended later without breaking the code)
	#name -> headername, it could be statusline if it is the statusline or requestline if it is the requestline, it could be None if the stuff in there could not be parsed, in this case value contains the complete line
	#values -> the values as one string, the value might be None if there was no value
	#headervalue-seperator -> everything in between headername and values -> needed for re-assembling the header - will be "" in case of header could not be parsed
	#it won't be None, as that would require extra steps in every routine to check that - while if "" it will add simply nothing
	def get_headers(self,message=None,lineseperator=None):
		#Regular expressions to be checked as "headers" - this could not be easily extended, as further down you would need to adjust what to write to single fields of the result
		tocheck=dict({"header":self._header,"statusline":self._statusline,"requestline":self._requestline})
		if not message:
			message=self.message
		if not lineseperator:
			lineseperator=self._lineseperator
		result=list()
		d.debug("Getting headers")
		for line in self.get_lines(message,lineseperator):
			d.debug("Processing line of message (line-by-line): " + line)
			#Check if it is a header, statusline or requestline
			run=1
			for rexname,regularex in tocheck.items():
				try:
					d.debug("Checking line against "+rexname+" defined as: "+regularex)
					rmatch=regex.match(regularex,line)
					#headerandvaluematch=rmatch.capturesdict()
					headerandvaluematch=dict()
					#Within the capturedict every match-group is represended by a list of matches for that group - even if there is just one 
					#removing the list - add one result per capture group
					for key, value in rmatch.capturesdict().items():
						headerandvaluematch.update({key:value[0]})
						
					#This will just run if there was no exception -> meaning that the result was not None and therefore something matched
					#If the regular-expression to check was not a header, set headername to the name of the regular expression and header-value to its value
					if rexname== "statusline" or rexname=="requestline":
						headerandvalue=dict({"header-name":rexname,"header-values":rmatch[0],"headervalue-seperator":None})
					if rexname== "header":
						headerandvalue=dict({"header-name":headerandvaluematch["header_name"],"header-values":headerandvaluematch["header_values"],"headervalue-seperator":headerandvaluematch["headervalue_seperator"]})
					d.debug("Check sucessfull, type is: " + rexname)
					break
				except AttributeError:
					#If not alle regularexpressions have been checked continue 
					#In case everything has been checked there is no result -> set the header to None and values to the complete string -> we could reassemble the message doing this, even if it is inavalid
					if run == len(tocheck):
						headerandvalue=dict({"header-name":None,"header-values":line,"headervalue-seperator":None})
						d.debug("Check failed, no more regular expressions to check. Save it as unknown header (None)")
					else:
						d.debug("Check failed, checking next regular expression")
				run+=1

			#Actually no idea why this is here - actually headerandvalue would contain already the the single dictionaries -> why to create one more?
			result.append(dict({"name":headerandvalue["header-name"],"values":headerandvalue["header-values"],"headervalue-seperator":headerandvalue["headervalue-seperator"]}))
		return result	
	
	#Returning a structure representing the structure of the message as far as it could de-assembled
	#Structure of the returned structure
	#list containing dicts
	#dicts containing fields
	#tpye -> type of the part - could be None if the type could not be determined
	#value -> value of the part 
	#seperator -> the seperator which seperates this part from the next lower one - could be "" if there was none (don't set it to none, as that will require checks all the time) 
	#follower -> the next deeper level - could be None if there is none
	#starts all over in the next deeper level
	def getpartstructure(self,message=None):
		if not message:
			message=self.message

		structure=list()

		#The first part is a total chaos
		#This is done as we need first of all the complete header -> for the first element we will write
		#The get_headers function will later on do the same again, but its not avoidable
		for headernumber,header in enumerate(self.get_lines(message)):
#			structure.append({"type":"header","value":header,"follower":None,"seperator":"\r\n"}	
#			headersplitresult=get_headers(line)[0]	
#			headervalues=list([dict({"type":"header-values","value":headersplitresult["values"],"follower":None,"seperator":None}
#			headername=list([dict({"type":"header-name","value":headersplitresult[headervalue-seperator]+headersplitresult[values],"follower":None,"seperator":headersplitresult["headervalue-seperator"]})])
#			structure[headernumber].update({"follower":headername})
			headerparts=list()
			headersplitresult=self.get_headers(header)[0]	
			headerparts.append(dict({"type":"header-name","value":headersplitresult["name"],"follower":None,"seperator":headersplitresult["headervalue-seperator"]}))
			headerparts.append(dict({"type":"header-values","value":headersplitresult["values"],"follower":None,"seperator":""}))
			#seperator=\r\n is a hack -> actually the BNF needs to be changed
			#This needs to be done manually, also in the future - it is a exception, as the type is named by part of the element value -> header by the headername, instead of
			#by its BNF element name - needed for headers as else we could not address the concrete header 
			structure.append(dict({"type":headersplitresult["name"],"value":header,"follower":headerparts,"seperator":"\r\n"}))	
			d.debug("Created structure from " + str(message) + " looks like this: " + str(structure))
		return structure

	#Builds the message from the struct of the message - using the top level values + there seperators
	def _buildmessage(self,struckt):
		message=str()
		for header in struckt:	
			d.debug("Building message, adding header: " + str(header["value"]))
			message+=header["value"]
			if header["seperator"]:
				d.debug("Building message, adding seperator : " + str(header["value"]))
				message+=header["seperator"]
		return (message)
			
	#Replace something or delete it
	#returns the message where the part has been replaced
	#message -> the sip message itself
	#part -> part to replace (it needs to be in the list partlist (above) or a header name
	#replacement -> by what it should be replaced, put None if it should be deleted
	#xte -> means if there are possible multiple occurences of "part" the how manity of them should be replaced - optional it could be 0 -> meaning all of them
	#justvalue -> makes mostly just sense with headers, it will not replace the "part" defined, but just its value
	def replace(self,part,replacement,xte=1,justvalue=False,message=None):
		if not message:
			message=self.message
		
		partlist=part.split(".")	
		if not self.messagestruct:
			self.messagestruct=self.getpartstructure(message)
		messagestruct=copy.deepcopy(self.messagestruct)
		#Not used, since not applicable - working with the real struct (real in the sense of real for the function - it is a copy of the one used in the class)
		workingmstruct=copy.deepcopy(messagestruct)
		selector=list(["typ","seperator","value"])
		counterxte=0
		changecounter=0
		partlistindex=0
		#visitedlevel=messagestruct[0]
		visitedlevel=list([messagestruct])
		###
		lastvisitedlevel=list([visitedlevel[len(visitedlevel)-1]])
		print ("messagestruct:",messagestruct)
		print ("lastvisitedlevel:",lastvisitedlevel)
		visitedelement=list()

		#### Code handling xte=0 needs to be removed -> the functionality needs to be build outside this block-this block allows just one element at a time to be modified
		#After this block message needs to be rebuild and structure (both became invalid after this block)
		while True:
			#The following is the case if the xte element should be found and has been found -> in this case leave the loop
			if counterxte==xte:
				break
			#Looking for element which has not cheched as state in the last level
			###for element in visitedlevel[len(visitedlevel)-1]:
			###Replaced for loop
			elementsonlevel=len(visitedlevel[len(visitedlevel)-1])
			elementcounter=0
			godeeper=False
			#Added instead of for 
			#while elementcounter < elementsonlevel-1:
			while elementcounter < elementsonlevel:
				elementcounter+=1
				print ("elementcounter", elementcounter)
				print ("elementsonlevel", elementsonlevel)
				print("Länge von visitedelement", len(visitedlevel[len(visitedlevel)-1]))
				element=visitedlevel[len(visitedlevel)-1][elementcounter-1]
			#for element in lastvisitedlevel:
				d.debug("Using element : " + str(element) + " on level number " + str(len(visitedlevel)-1) + " which looks like this: " + str(lastvisitedlevel[len(lastvisitedlevel)-1])) 
				d.debug("Comparing1 "+str(element["type"])+" to "+str(partlist[partlistindex]))
				try:
					elementchecked=element["checked"]
				except KeyError:
					elementchecked=0
					d.debug("No elementchecked attribute - set it to 0")
				if not elementchecked:
					d.debug("Element has not been checked yet… checking")
					#Check whether the element is of type we are looking for on this level
					print (element["type"])
					print (partlist[partlistindex])
					d.debug("Comparing "+str(element["type"])+" to "+str(partlist[partlistindex]))
					if element["type"]==partlist[partlistindex]:
						d.debug("Found matching subelement, " + str(element["type"]) + " matches " + str(partlist[partlistindex]) + " of partlist " + str(partlist))
						#Check if next part would be just the selector -> in this case we have found a element -> no need to go deeper 
						if partlist[partlistindex+1] in selector:
							counterxte+=1
							element["checked"]=1
							#d.debug("Found matching subelement, " + str(element["type"]) + " matches " + str(partlist["partlistindex"]) + " of partlist " + str(partlist))
							#Check whether it is the xte element we where searching for or whether we need to find all element of the type
							if counterxte==xte or xte==0:
								#Update the element and within it the field indicated by selector (which is at the end of the partlist) 
								selector=partlist[partlistindex+1]
								#If replacement is None
								if not replacement:
									replacement=""
									d.debug("Replacement is None, setting replacement string to empty string")
								element[partlist[partlistindex+1]]=replacement
								#remove all levels which came after the current one -> they have become invalid, as something has been updated for 
								#the current one and they do not reflect this change -> but are the building-blocks from which the current one would 
								#be created (in the view of the BNF)
								element["follower"]=None
								changecounter+=1 
								#Go through the whole thing end rebuild all values
								while True:
									#There is no way to go higher -> so leave
									if len(visitedlevel) == 1:
										break
									#Blanking the value of the element whichs value will be rebuild
									visitedelement[len(visitedelement)-1]["value"]=""
									#Running through all the elements of the current level and add there values+seperator to the next higher element
									#(the last one in visitedelement) - rebuilding its value
									ielementsonlevel=len(visitedlevel[len(visitedlevel)-1])
									ielementcounter=0
									while ielementcounter < ielementsonlevel:
										ielementcounter+=1
										print ("ielementcounter", ielementcounter)
										print ("elementsonlevel", ielementsonlevel)
										element=visitedlevel[len(visitedlevel)-1][ielementcounter-1]
									###for element in visitedlevel[len(visitedlevel)-1]:
										try:
											elementchanged=element["changed"]	
										except KeyError:
											elementchanged=0
										if not elementchanged:
											print ("Assembling: ",str(visitedelement[len(visitedelement)-1]["value"]),str(element["value"]),str(element["seperator"]))
											visitedelement[len(visitedelement)-1]["value"]+=element["value"]+element["seperator"]
											element["changed"]=1
											continue
										else:
											continue
									visitedlevel.pop()
									visitedelement.pop()
									#Extra step, we need to add the highest level (entry) in visitedlevel to lastvisitedlevel 
									lastvisitedlevel.append([len(visitedlevel)-1])
								#If we are looking just for the xte element we have found everything to be fonud -> leave the loop
								if counterxte==xte:
									break
								#If we are not just looking for the xte-element we need to search everything -> so continue
								else:
									continue
							#If current element is not the xte element we are looking for and we are not looking for all occurences of that element
							#We have found a element matching the criteria, but unfortunatel it is not the xte which is being looked for
							#therefore continue search
							else:
								continue
						#If next part would be not the selector, we need to travel further down the structure
						else:
							#Does the current element has a next level?
							#If yes -> go in partlistindex, level into the next level, add the element to the list of visited elements
							#repeat the loop -> running throug the level (as visitedlevel is on another now it will check the next level)
							if element["follower"]:
								d.debug("Element has a additional level - going deeper")
								partlistindex+=1
								visitedelement.append(element)
								visitedlevel.append(element["follower"])	
								d.debug("Follower is:" + str(element["follower"]))
								#Extra step, we need to add the highest level (entry) in visitedlevel to lastvisitedlevel 
								lastvisitedlevel.append([len(visitedlevel)-1])
								#I think that was a bug
								#continue
								godeeper=True
								break
							#Element has no next level 
							else:
								d.debug("Element has no level - check next element on same level")
								element["checked"]=1				
								continue
					#If element does not mach			
					else:
						element["checked"]=1				
						continue

			#Outside of the inner loop
			#Check if loop was left because we need to go to a deeper level - if not we need to go up (all elements of level have been checked)
			if godeeper:
				godeeper=False
			else:
				#This coud be  the case if all elements have been checked/there is no element whose checked-indicator is 0 
				#We need to shift one level up if possible
				#If we are currently already on the highest level -> we have done everything, there is nothing left to check
				if len(visitedlevel) == 1:
					break
				#If not on the highest level, go one level higher
				else:
					#Remove last level from levellist
					visitedlevel.pop()
					#Extra step, we need to add the highest level (entry) in visitedlevel to lastvisitedlevel 
					lastvisitedlevel.append([len(visitedlevel)-1])
					#Set element over which we entered the level to checked and remove it from the list
					visitedelement[len(visitedelement)-1]["checked"]=1
					visitedelement.pop()
					#Reduce partlistindex (index telling what element we are looking for on this level) by 1 -> as we also reduce the level by 1
					partlistindex-=1
					continue
					
		#Rebuilding the message using the struct
		message=self._buildmessage(messagestruct)
		self.message=message
		#Update the objects message structure
		messagestruct=self.getpartstructure(message)
		self.messagestruct=messagestruct	

		return message

	#Wraper around replace, making it possible to replace more than one field 
	#It expects a list with dictionary in it -  which has at least element, replacement and otpional attributnumber in it 
	#Optional a message to parse could be hand over -> but note, that the message of the object will become the message provided here - if no message, it is the message given
	#to the object at initalization time
	def replace_multiple(self,replacementlist,message=None):
		if not message:
			message=self.message	
		
		for replacementdict in replacementlist:
			if replacementdict["attributnumber"]:
				newmessage=self.replace(replacementdict["element"],replacementdict["replacement"],replacementdict["attributnumber"])
			else:
				newmessage=self.replace(replacementdict["element"],replacementdict["replacement"])

		return newmessage


