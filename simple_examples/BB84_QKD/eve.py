from cqc.pythonLib import CQCConnection

##########################################################################
def main():
	"""
	Eve receives a qubit from Alice and passes it on to Bob without 
	peeking (thanks, Eve).
	"""

	# connect to network
	with CQCConnection("Eve") as Eve:

		# recieve qubit from Alice
		q = Eve.recvQubit()

		# send qubit to Bob
		Eve.sendQubit(q, "Bob")

		# debug
		print("Hello from Eve")
##########################################################################

# run
main()