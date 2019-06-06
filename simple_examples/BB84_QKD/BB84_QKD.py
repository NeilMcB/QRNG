from cqc.pythonLib import CQCConnection, CQCNoQubitError, qubit
import logging
from threading import Thread
import sys
import numpy as np
from numpy.random import binomial
from simulaqron.network import Network

FORMAT = "%(levelname)s: %(message)s"
STATES = [["|0>", "|1>"], ["|+>", "|->"]]

##########################################################################
class ThreadManager:
    """
    Class to manage running of Alice, Bob and Eve's threads, and storing
    of the corresponding results.
    """

    def __init__(self, n_qubits):
        """
        Create new ThreadManager for n qubit BB84. Create empty arrays for
        storing bases and measurements, initialising to -1 as this is an
        impossible value for either to be. Initialise network for running
        the protocol on.

        Arguments:
        n_qubits -- the number of qubits to be sent from Alice to Bob
        """
        self.n_qubits = n_qubits
        
        self.alice_results = -1*np.ones((2, n_qubits))
        self.bob_results   = -1*np.ones((3, n_qubits))
        
        self.network = initNetwork()

    
    def start(self):
        """
        Start Alice, Bob and Eve's threads.
        """
        logging.info("TM     : Starting threads.")

        self.alice_thread = Thread(target=alice, 
                                   args=(self.n_qubits, 
                                         self.alice_results,))
        self.bob_thread   = Thread(target=bob  , 
                                   args=(self.n_qubits,
                                         self.bob_results,))
        self.eve_thread   = Thread(target=eve  , 
                                   args=(self.n_qubits,
                                         True,))

        self.alice_thread.start()
        self.bob_thread  .start()
        self.eve_thread  .start()

    
    def join(self):
        """
        Join (i.e. wait for) Alice, Bob and Eve's threads. Stop the 
        network as we no longer need it.

        Returns:
        results -- (np.ndarray, np.ndarray), Alice's and Bob's bases and
        qubits/measurements.
        """
        self.alice_thread.join()
        self.bob_thread  .join()
        self.eve_thread  .join()
        logging.info("TM     : Threads joined.")

        self.network.stop()

        results = (self.alice_results, self.bob_results)
        return results

##########################################################################

##########################################################################
def initNetwork(nodes=["Alice","Bob","Eve"], topology=None):
    """
    Start simulaqron network with default name.

    Arguments:
    nodes -- list of nodes, identified by a string (name)
    topology -- dict representing adjacency list of network

    Returns:
    network -- pointer to initialised network
    """
    logging.info("NETWORK: Initialising network.")
    network = Network(nodes=nodes, topology=topology)
    network.start()
    logging.info("NETWORK: Network started.")

    return network

##########################################################################

##########################################################################
def alice(n_qubits_to_send, results):
    """
    Alice chooses n random pairs of bits (x, a), using the first to 
    determine a measurement basis (computational or Hadamard) and the 
    second to determine the corresponding qubit orientation (|+> or |0>, 
    |-> or |1> respectively). She sends these qubits to Bob via Eve 
    through an untrusted quantum channel, and directly communicates her 
    determined bases to Bob via a trusted classical channel.

    Arguments:
    n_qubits_to_send -- the number of qubits to prepare and send to Bob
    results -- np.ndarray to store bases and qubits
    """

    # Connect to network
    with CQCConnection("Alice") as Alice:
        logging.info("ALICE  : Alice Connceted.")

        n_qubits_sent = 0
        while n_qubits_sent < n_qubits_to_send:
            # random bits
            x = binomial(1, 0.5)  # 0 -> computational, 1 -> Hadamard
            a = binomial(1, 0.5)  # 0 -> |0> or |+>   , 1 -> |1> or |->
            # store for QBER estimation
            results[0,n_qubits_sent] = x  # basis
            results[1,n_qubits_sent] = a  # qubit

            # try to make a qubit
            try:
                q = qubit(Alice)  # |0>
                n_qubits_sent += 1
            except CQCNoQubitError:
                continue
            # if successful, encode accordingly
            if a:
                q.X()  # |1>
            if x:
                q.H()  # |+> or |->

            Alice.sendQubit(q, "Eve")
            Alice.sendClassical("Bob", x)
            
            logging.debug("ALICE  : state %s sent", STATES[x][a])

##########################################################################

##########################################################################
def bob(n_qubits_to_recieve, results):
    """
    Bob chooses a random bit y to determine a measurement basis 
    (computational or Hadamard) and uses this to measure the Qubit sent by
    Alice. If his bit matches the bit classically send by Alice, in the
    absence of any eveasdropping (which is the current scenario), he and
    Alice will share the same secret(ish) bit.
    """

    # Connect to network
    with CQCConnection("Bob") as Bob:
        logging.info("BOB    : Bob connected.")
        for i in range(0,n_qubits_to_recieve):
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

            # store for QBER estimation
            results[0,i] = y       # basis
            results[1,i] = b       # result
            results[2,i] = (y==x)  # basis match

            # debug
            logging.debug("BOB    : state %s measured", STATES[y][b])
        
##########################################################################

##########################################################################
def eve(n_qubits_to_recieve, eavesdrop=False):
    """
    Eve receives a qubit from Alice and passes it on to Bob. Eve can be
    set to eavesdrop (i.e. measure at random then send her resulting 
    state to Bob) or not.

    Arguments:
    n_qubits_to_recieve -- the number of qubits Eve is to expect
    easvedrop -- whether or not Eve will look at each state she recieve
    """

    # connect to network
    with CQCConnection("Eve") as Eve:
        logging.info("EVE    : Eve connected.")

        for _ in range(n_qubits_to_recieve):
            # recieve qubit from Alice
            q = Eve.recvQubit()

            if eavesdrop:
                # try to observe what Alice sent
                basis = binomial(1, 0.5)  # computational or Hadamard basis
                if basis:
                    q.H()
                result = q.measure()

                # pass on result to Bob
                q = qubit(Eve)
                if result:
                    q.X()  # |1>
                if basis:
                    q.H()  # |+> or |->

            # send qubit to Bob
            Eve.sendQubit(q, "Bob")

##########################################################################

##########################################################################
def generateKey(alice_results, bob_results, test_prob=None):
    """
    Generate the key from the results of Alice and Bob; namely where their
    bases agree return the corresponding qubits/measurements.

    Arguments:
    alice_results -- np.ndarray of Alice's randomly chosen bases and 
    qubits
    bob_results -- np.ndarray of Bob's randomly chosen bases and 
    corresponding measurements
    test_frac -- fraction of measurements to randomly select for 
    estimating QBER, the ``true'' QBER will be returned if not specified

    Returns:
    key -- the key generated by the BB84 protocol
    qber -- the estimated QBER
    """
    basis_match = bob_results[2].astype(bool)
    alice_key = alice_results[1][basis_match].astype(int)
    bob_key   =   bob_results[1][basis_match].astype(int)

    if test_prob is not None:
        test_idxs = binomial(1, test_prob, size=alice_key.shape).astype(bool)
        keep_idxs = np.logical_not(test_idxs)
        qber = estimateQBER(alice_key[test_idxs], bob_key[test_idxs])
        alice_key = alice_key[keep_idxs]
        bob_key   =   bob_key[keep_idxs]
    else:
        qber = estimateQBER(alice_key, bob_key)

    return (alice_key, bob_key, qber)

##########################################################################

##########################################################################
def estimateQBER(alice_key_sample, bob_key_sample):
    """
    Given equal sized samples of the keys generated for Alice and Bob, 
    estimate the QBER of the system.

    Arguments:
    alice_key_sample -- np.ndarray sampling Alice's key, drawn from 
    randomly chosen indices
    bob_key_sample -- np.ndarray sampling Bob's key, drawn from the same
    random indices

    Returns:
    qber -- the estimated QBER
    """
    logging.info("QBER   : Alice sample: %s", alice_key_sample)
    logging.info("QBER   :   Bob sample: %s",   bob_key_sample)

    n_in_agreement = np.sum(alice_key_sample != bob_key_sample)
    n_total = len(alice_key_sample)
    return n_in_agreement / n_total

##########################################################################


if __name__ == "__main__":
    logging.basicConfig(format=FORMAT, level=logging.INFO)

    n_qubits = int(sys.argv[1])

    thread_manager = ThreadManager(n_qubits)
    thread_manager.start()
    alice_results, bob_results = thread_manager.join()

    alice_key, bob_key, qber = generateKey(alice_results, bob_results, test_prob=0.3)
    logging.info("MAIN   : Alice's generated key: %s", alice_key)
    logging.info("MAIN   :   Bob's generated key: %s",   bob_key)
    logging.info("MAIN   : QBER estimate: %.3f", qber)
    
    

    
    