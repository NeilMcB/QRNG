from numpy.random import binomial
from cqc.pythonLib import CQCConnection

##########################################################################
def main():
    """
    Bob chooses a random bit y to determine a measurement basis 
    (computational or Hadamard) and uses this to measure the Qubit sent by
    Alice. If his bit matches the bit classically send by Alice, in the
    absence of any eveasdropping (which is the current scenario), he and
    Alice will share the same secret(ish) bit.
    """

    # Connect to network
    with CQCConnection("Bob") as Bob:

        # random bit
        y = binomial(1, 0.5)  # 0 -> computational, 1 -> Hadamard

        # recieve qubit from Alice (via Eve)
        q = Bob.recvQubit()
        
        # obtain result
        if y:
            q.H() 
        b = q.measure()

        # obtain classical message from Alice
        enc = Bob.recvClassical()[0]

        # debug
        states = [["|0>", "|1>"], ["|+>", "|->"]]
        print("Bob's random bit is: {}".format(y))
        print("Bob measures: {}".format(states[y][b]))
        
##########################################################################

# run
main()