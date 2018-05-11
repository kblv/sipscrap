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


