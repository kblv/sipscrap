from filehandler import makefilehandler

#Handles the debug messages
class debug(object):
	enabled=False
	outfile=None

	def setup(enabled,outfile):
		debug.enabled=enabled
		debug.outfile=outfile 
	def debug(message):
		if debug.enabled:
			fhandler=makefilehandler(debug.outfile)
			print(message,file=fhandler)
			#This is surely not the most elegant way to close that after every single write, but everything else would need more effort
			#Prevent closing stderr -> seems you can't open it again
			if type(debug.outfile)==str:
				fhandler.close()
