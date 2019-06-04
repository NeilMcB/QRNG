import sys
from cqc.pythonLib import CQCConnection

##########################################################################
def main(n_qubits_to_recieve):
	"""
	Eve receives a qubit from Alice and passes it on to Bob without 
	peeking (thanks, Eve).
	"""

	# connect to network
	with CQCConnection("Eve") as Eve:

		for _ in range(n_qubits_to_recieve):
			# recieve qubit from Alice
			q = Eve.recvQubit()

			# send qubit to Bob
			Eve.sendQubit(q, "Bob")

##########################################################################

# run
if __name__ == "__main__":
	n_qubits_to_recieve = int(sys.argv[1])
	main(n_qubits_to_recieve)