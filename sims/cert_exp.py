from threading import Event
import numpy as np
from numpy.random import binomial
import utils
from cqc.pythonLib import CQCConnection, qubit
import logging


"""A simulatedion of randomness expansion certified by Bell's theorem.


TODO:
    think about what entangled state they share? How does this change things?
    moving logging setup into config file?
"""
def system_A(N_QUBITS, A_RESULTS):
    with CQCConnection("Alice") as Alice:
        logging.info("ALICE  : Alice connceted.")
        for i in range(N_QUBITS):
            # Wait until Bob is ready for a new qubit
            QUBIT_RECV_EVENT.wait()
            QUBIT_RECV_EVENT.clear()
            # Create and send entangled pair
            q = Alice.createEPR("Bob")
            QUBIT_SENT_EVENT.set()
            # Measure 
            x = binomial(1, 0.5)
            #if x:
            #    q.H()  # X basis (else Z basis)
            a = q.measure()
            # Store results
            #logging.info("ALICE  : x=%s, a=%s", x, a)
            A_RESULTS[0,i] = x
            A_RESULTS[1,i] = a
            A_RESULTS[2,i] = q.get_entInfo().id_AB


def system_B(N_QUBITS, B_RESULTS):
    with CQCConnection("Bob") as Bob:
        logging.info("BOB    : Bob connceted.")
        for i in range(N_QUBITS):
            # Wait until Alice has sent new qubit
            QUBIT_SENT_EVENT.wait()
            QUBIT_SENT_EVENT.clear()
            # Recieve entangled qubit
            q = Bob.recvEPR()
            QUBIT_RECV_EVENT.set()
            # Measure
            y = binomial(1, 0.5)
            #if y:
            #    q.rot_Y(96)  # 1/sqrt(2) (X - Z) basis
            #else:
            #    q.rot_Y(32)  # 1/sqrt(2) (X + Z) basis
            b = q.measure()
            # Store results
            #logging.info("BOB    : y=%s, b=%s", y, b)
            B_RESULTS[0,i] = y
            B_RESULTS[1,i] = b
            B_RESULTS[2,i] = q.get_entInfo().id_AB

            if (i%100==0):
            	logging.info("BOB     : Measured qubit %d", i)


def calculate_I(A_RESULTS, B_RESULTS, N_QUBITS):
    I = 0
    for i in range(N_QUBITS):
        x, a, qid_a = A_RESULTS[:,i]
        y, b, qid_b = B_RESULTS[:,i]
        I += (-1)**(x*y) * ((int(a==b) - int(a!=b)) / 0.25)
    return I/N_QUBITS

QUBIT_SENT_EVENT = Event()
QUBIT_RECV_EVENT = Event()
QUBIT_SENT_EVENT.set()
QUBIT_RECV_EVENT.set()

FORMAT = "%(levelname)s: %(message)s"

N_QUBITS = 1000

if __name__ == "__main__":
    logging.basicConfig(format=FORMAT, level=logging.INFO)
    em = utils.ExperimentManager(usr_simQ_params={'backend': 'stabilizer'})

    A_RESULTS = -1 * np.ones((3,N_QUBITS))
    B_RESULTS = -1 * np.ones((3,N_QUBITS))

    em.start({system_A: (N_QUBITS,A_RESULTS,),
              system_B: (N_QUBITS,B_RESULTS,)
              })

    em.join()

    print(A_RESULTS)
    print(B_RESULTS)

    I = calculate_I(A_RESULTS, B_RESULTS, N_QUBITS)
    print(I)

    np.save("A_RESULTS.npy", A_RESULTS)
    np.save("B_RESULTS.npy", B_RESULTS)
