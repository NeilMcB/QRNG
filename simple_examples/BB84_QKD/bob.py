import sys
from numpy.random import binomial
from cqc.pythonLib import CQCConnection

##########################################################################
def main(n_qubits_to_recieve):
    """
    Bob chooses a random bit y to determine a measurement basis 
    (computational or Hadamard) and uses this to measure the Qubit sent by
    Alice. If his bit matches the bit classically send by Alice, in the
    absence of any eveasdropping (which is the current scenario), he and
    Alice will share the same secret(ish) bit.
    """

    # Connect to network
    with CQCConnection("Bob") as Bob:
        for i in range(1,n_qubits_to_recieve+1):
            # random bit
            y = binomial(1, 0.5)  # 0 -> computational, 1 -> Hadamard

            # recieve qubit from Alice (via Eve)
            q = Bob.recvQubit()
        
            # obtain result
            if y:    
                q.H() 
            b = q.measure()

            # obtain classical message from Alice
            x = Bob.recvClassical()[0]

            # debug
            states = [["|0>", "|1>"], ["|+>", "|->"]]
            print("*QID{}* Bob has recieved from Alice: {}".format(i, x))
            print("*QID{}* Bob's random bit is: {}".format(i, y))
            print("*QID{}* Bob measures: {}"       .format(i, states[y][b]))
        
##########################################################################

# run
if __name__ == "__main__":
    n_qubits_to_recieve = int(sys.argv[1])
    main(n_qubits_to_recieve)