import re
import regex
from collections import OrderedDict
import copy

#Hack - striping the "[" and "]" from character classes when they need to be integrated into other character classes
#If you would not do that (and having instead something like [[old-class]some new stuff] it would not work as one character class
def rg(expression):
	stripped, count=re.subn("^[","",expression)
	if count:
		stripped=re.subn("]$","",stripped)
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
	_HCOLON="["+_SP+"|"+_HTAB+"]*:"+_SWS
	_token="["+rg(_alphanum)+"|\!|%|\*|_|\+|`|'|~]+"
	_header_name=("?P<header-name>"+_token+")"
	_header_value="(?P<header-value>"+_TEXT_UTF8char+"|"+_UTF8-CONT+"|"+_LWS+")*"
	#This actually does not exist in the BNF, problem however is that in section 7.3 header is defined and it could contain multiple values - in the BNF extension-header
	#which is here called _header is defined to containing just value (so just one of them)
	_header_values="(?P<header-values>"+_header_value+"(?:"+_COMMA+_header_value+")*)"
	#_header=_header_name+_HCOLON+_header_value
	#This is extension-header in the BNF - used here as generic for all headers -> there is a difference, as I use header_values (multiple) instead of header_value (one as by the BNF)
	#This is due to there are headers containing multiple values (as Contact for exapmle)
	_header=_header_name+"(?P<headervalue-seperator>"_HCOLON+")"+_header_values
	_requestline="^[\w,-,\.,!,%,\*,_,\+,\',~]+ \S* SIP/\d+\.\d+"
	_statusline="SIP/\d+\.\d+ \d{3} .*"
	_lineseperator="\r\n"

	def __init__(self,message):
		self.message=message
		self.structure=None
	
	#Actual a short cut - we are not parsing line by line, but just seperating the lines
	get_lines(self,message=None,lineseperator=None):
		if not message:
			message=self.message
		if not lineseperator:
			lineseperator=_lineseperator
		return(message.split(lineseperator))
	
	##This should maybe get to a own class at some point -> makes it possible to implement multiple methods -> such as getheader or getvalue
	#Returning a list containing the headers and there values in the order as they appear
	#In the list one header is represented by one field
	#Every field contains a dict
	#Every dict contains 2 fields (it is preferred to use the field names to get the data, so that it could be extended later without breaking the code)
	#name -> headername, it could be statusline if it is the statusline or requestline if it is the requestline, it could be None if the stuff in there could not be parsed, in this case value contains the complete line
	#values -> the values as one string, the value might be None if there was no value
	#headervalue-seperator -> everything in between headername and values -> needed for re-assembling the header - will be None in case of header could not be parsed
	get_headers(self,message=None,lineseperator=None):
		#Regular expressions to be checked as "headers" - this could not be easily extended, as further down you would need to adjust what to write to single fields of the result
		tocheck=dict({"header":_header,"statusline":_statusline,"requestline":_requestline})
		if message=None:
			message=self.message
		if lineseperator=self.lineseperator:
			lineseperator=_lineseperator
		result=list()
		for line in get_lines(message,lineseperator):
			#Check if it is a header, statusline or requestline
			for rexname,regularex in tocheck
				try:
					rmatch=regex.match(regularex,line)
					headerandvaluematch=rmatch.capturesdict()
					#This will just run if there was no exception -> meaning that the result was not None and therefore something matched
					#If the regular-expression to check was not a header, set headername to the name of the regular expression and header-value to its value
					if rexname== "statusline":
						headerandvalue=dict({"header-name":rexname,"header-values":rmatch[0],"headervalue-seperator":None})
					break
				except AttributeError:
					#If not alle regularexpressions have been checked continue 
					#In case everything has been checked there is no result -> set the header to None and values to the complete string -> we could reassemble the message doing this, even if it is inavalid
					if run == len(tocheck):
						headerandvalue=dict({"header-name":None,"header-values":line,"headervalue-seperator":None})
					else:
						continue
					
		result.append(dict({"name":headerandvalue["header-name"],"values":headerandvalue["header-values"],"headervalue-seperator":headerandvalue["headerandvalue-seperator"]})
		return result	
	
	#Returning a structure representing the structure of the message as far as it could de-assembled
	#Structure of the returned structure
	#list containing dicts
	#dicts containing fields
	#tpye -> type of the part - could be None if the type could not be determined
	#value -> value of the part 
	#seperator -> the seperator which seperates this part from the next lower one - could be None if there is no such thing or if there is no next lower part
	#follower -> the next deeper level - could be None if there is none
	#starts all over in the next deeper level
	def getpartstructure(self,message=None):
		if not message:
			message=self.message

		structure=list()

		#The first part is a total chaos
		for headernumber,header in enumerate(get_lines(message)):
			structure.append({"type":"header","value":header,"follower":None,"seperator":"\r\n"}	
			headersplitresult=get_headers(line)[0]	
			headervalues=list([dict({"type":"header-values","value":headersplitresult["values"],"follower":None,"seperator":None}
			headername=list([dict({"type":"header-name","value":headersplitresult[headervalue-seperator]+headersplitresult[values],"follower":None,"seperator":headersplitresult["headervalue-seperator"]})])
			structure[headernumber].update({"follower":headername})
		return structure

	#Builds the message from the struct of the message - using the top level values + there seperators
	def _buildmessage(self,struckt):
		message=str
		for header in struckt:	
			message+=header["value"]
			if header["seperator"]:
				message+=header["seperator"]
		return (message)
			
	
	#Replace something or delete it
	#returns the message where the part has been replaced
	#message -> the sip message itself
	#part -> part to replace (it needs to be in the list partlist (above) or a header name
	#replacement -> by what it should be replaced, put None if it should be deleted
	#xte -> means if there are possible multiple occurences of "part" the how manity of them should be replaced - optional it could be 0 -> meaning all of them
	#justvalue -> makes mostly just sense with headers, it will not replace the "part" defined, but just its value
	replace(part,replacement,xte=1,justvalue=False,message=None):
		if not message:
			message=self.message()
		
		partlist=part.split(".")	
		if not self.messagestruct:
			self.messagestruct=getpartstructure(message)
		messagestruct=copy.deepcopy(self.messagestruct)
		#Not used, since not applicable - working with the real struct (real in the sense of real for the function - it is a copy of the one used in the class)
		workingmstruct=copy.deepcopy(messagestruct)
		selector=list([typ,seperator,value])
		counterxte=0
		changecounter=0
		partlistindex=0
		visitedlevel=structure[0]
		visitedelement=list()

		#### Code handling xte=0 needs to be removed -> the functionality needs to be build outside this block-this block allows just one element at a time to be modified
		#After this block message needs to be rebuild and structure (both became invalid after this block)
		while True:
			#The following is the case if the xte element should be found and has been found -> in this case leave the loop
			if counterxte==xte:
				break
			#Looking for element which has not cheched as state in the last level
			for element in visitedlevel[len(visitedlevel-1]:
				try:
					elementchecked=element["checked"]
				except KeyError:
					elementchecked=0
				if not elementchecked:
					#Check whether the element is of type we are looking for on this level
					if element["type"]==partlist[partlistindex]:
						#Check if next part would be just the selector -> in this case we have found a element -> no need to go deeper 
						if partlist[partlistindex+1] in selector:
							counterxte+=1
							element["checked"]=1
							#Check whether it is the xte element we where searching for or whether we need to find all element of the type
							if counterxte==xte or xte==0:
								#Update the element and within it the field indicated by selector (which is at the end of the partlist) 
								selector=partlist[partlistindex+1]
								#If replacement is None
								if not replacement:
									replacement=""
								element[partlist[partlistindex+1]=replacement
								#remove all levels which came after the current one -> they have become invalid, as something has been updated for 
								#the current one and they do not reflect this change -> but are the building-blocks from which the current one would 
								#be created (in the view of the BNF)
								element["follower"]=None
								changecounter+=1 
								#Go through the whole thing end rebuild all values
								while true:
									#There is no way to go higher -> so leave
									if len(visitedlevel) == 1:
										break
									#Running through all the elements of the current level and add there values+seperator to the next higher element
									#(the last one in visitedelement) - rebuilding its value
									for element in visitedlevel[len(visitedlevel)-1]:
										try:
											elementchanged=element["changed"]	
										except KeyError:
											elementchanged=0
										if not elementchanged:
											visitedelement[len(visitedelement)-1]["value"]+=element["value"]+element["separator"]
											element["changed"]=1
											continue
										else:
											continue
									visitedlevel.pop()
									visitedelement.pop()

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
								partlistindex+=1
								visitedelement.append(element)
								visitedlevel.append(element["follower"])	
								continue
							#Element has no next level 
							else:
								element["checked"]=1				
								continue
					#If element does not mach			
					else:
						element["checked"]=1				
						continue

			#Outside of the inner loop
			#This is the case if all elements have been checked/there is no element whose checked-indicator is 0 
			#We need to shift one level up if possible
			#If we are currently already on the highest level -> we have done everything, there is nothing left to check
			if len(visitedlevel) == 1:
				break
			#If not on the highest level, go one level higher
			else:
				#Remove last level from levellist
				visitedlevel.pop()
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
