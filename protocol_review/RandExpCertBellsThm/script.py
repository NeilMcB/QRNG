from cqc.pythonLib import CQCConnection, CQCNoQubitError, qubit
import logging
import sys
from threading import Thread
sys.path.append('/Users/Neil/Documents/Uni/MSc/thesis/QRNG/utils')
import utils


FORMAT = "%(levelname)s: %(message)s"

def alice(network_name):
    # initialise connection
    logging.info("ALICE\t: Alice started.")
    with CQCConnection("Alice", network_name=network_name) as Alice:
        logging.info("ALICE\t: Alice connected.")
        # create EPR pair
        q = Alice.createEPR("Bob")

        # Measure qubit
        m=q.measure()
        to_print="App {}: Measurement outcome is: {}".format(Alice.name,m)
        print("|"+"-"*(len(to_print)+2)+"|")
        print("| "+to_print+" |")
        print("|"+"-"*(len(to_print)+2)+"|")


def bob(network_name):
    # initialise connection
    logging.info("Bob\t: Bob started.")
    with CQCConnection("Bob", network_name=network_name) as Bob:
        logging.info("BOB\t: Bob connected.")
        # recieve EPR pair
        q = Bob.recvEPR()
        # Measure qubit
        m=q.measure()
        to_print="App {}: Measurement outcome is: {}".format(Bob.name,m)
        print("|"+"-"*(len(to_print)+2)+"|")
        print("| "+to_print+" |")
        print("|"+"-"*(len(to_print)+2)+"|")

def main():
    network_name = "test"

    logging.basicConfig(format=FORMAT, level=logging.INFO)

    network_params = {"nodes": ["Alice", "Bob"],
                      "topology": {"Alice": "Bob", "Bob": "Alice"},
                      "name": network_name}

    em = utils.ExperimentManager(network_params)

    threads = {alice: (network_name,), bob: (network_name,)}
    em.start(threads)

    em.join()

if __name__ == '__main__':
    main()