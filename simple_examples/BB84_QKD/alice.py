import sys
import time
from numpy.random import binomial
from cqc.pythonLib import CQCConnection, CQCNoQubitError, qubit

##########################################################################
def main(n_qubits_to_send):
    """
    Alice chooses n random pairs of bits (x, a), using the first to 
    determine a measurement basis (computational or Hadamard) and the 
    second to determine the corresponding qubit orientation (|+> or |0>, 
    |-> or |1> respectively). She sends these qubits to Bob via Eve 
    through an untrusted quantum channel, and directly communicates her 
    determined bases to Bob via a trusted classical channel.
    """

    # Connect to network
    with CQCConnection("Alice") as Alice:

        n_qubits_sent = 0
        while n_qubits_sent < n_qubits_to_send:
            # random bits
            x = binomial(1, 0.5)  # 0 -> computational, 1 -> Hadamard
            a = binomial(1, 0.5)  # 0 -> |0> or |+>   , 1 -> |1> or |->

            # try to make a qubit
            try:
                q = qubit(Alice)  # |0>
            except CQCNoQubitError:
                continue
            # if successful, encode accordingly
            if a:
                q.X()         # |1>
            if x:
                q.H()         # |+> or |->

            # send qubit
            Alice.sendQubit(q, "Eve")
            n_qubits_sent += 1

            # communicate basis classically
            Alice.sendClassical("Bob", x)

            # debug
            states = [["|0>", "|1>"], ["|+>", "|->"]]
            print('\n')
            print("*QID{}* Alice sends to Bob: {}".format(n_qubits_sent, x))
            print("*QID{}* Alice's state is:   {}".format(n_qubits_sent, states[x][a]))

##########################################################################

# run
if __name__ == "__main__":
    n_qubits_to_send = int(sys.argv[1])
    main(n_qubits_to_send)