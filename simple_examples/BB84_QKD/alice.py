from numpy.random import binomial
from cqc.pythonLib import CQCConnection, qubit

##########################################################################
def main():
    """
    Alice chooses a random pair of bits (x, a), using the first to 
    determine a measurement basis (computational or Hadamard) and the 
    second to determine the corresponding qubit orientation (|+> or |0>, 
    |-> or |1> respectively). She sends these qubits to Bob via Eve 
    through an untrusted quantum channel, and directly communicates her 
    determined bases to Bob via a trusted classical channel.
    """

    # Connect to network
    with CQCConnection("Alice") as Alice:

        # random bits
        x = binomial(1, 0.5)  # 0 -> computational, 1 -> Hadamard
        a = binomial(1, 0.5)  # 0 -> |0> or |+>   , 1 -> |1> or |->

        # encode qubit accordingly
        q = qubit(Alice)  # |0>
        if x:
            q.H()         # |+>
        if a:
            q.X()         # |1> or |->

        # send qubit
        Alice.sendQubit(q, "Eve")

        # communicate basis classically
        Alice.sendClassical("Bob", a)

        # debug
        states = [["|0>", "|1>"], ["|+>", "|->"]]
        print("Alice sends to Bob: {}".format(x))
        print("Alice's state is:   {}".format(states[x][a]))
##########################################################################

# run
main()