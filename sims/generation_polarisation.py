import argparse
from cqc.pythonLib import CQCConnection, qubit
import numpy as np
from numpy.random import binomial
import logging
from threading import Barrier
import utils


""" Polarisation-based random number generation.

https://aip.scitation.org/doi/abs/10.1063/1.1150518

Passing a polarised photon through a polarisation filter at an angle of pi/4
from the photon's axis of polarisation places it in an equal superposition 
of two polarisation states. Measurement of a sequence of such photons therefore
forms a generator for random bits.

TODO:
    incorporate arbitrary rotation to form SV source?
    make distribution more similar to true laser properties?

"""

def generator(network, node, n_timesteps, results, p_emit):
    """ Produce photons one at a time.

    Mimic low-intensity photon source by releasing photons (qubits) with a
    exponential-decay distributed time delay. Apply Hadamard to mimic pi/4
    polarising filter. Measure and store result.

    Args:
        network (str): name of the network to connect to
        node (str): name of the node to connect to
        n_timesteps (int): number timesteps to simulate
        results (np.ndarray): array for storing results    
        p_emit (float): probability of photon emission per timestep
    """
    with CQCConnection(node, network_name=network) as Source:
        logging.info("GEN\t: Generator connected to node %s.", node)
        # Output signal state (0 = LO, 1 = HI)
        state = 0
        for i in range(n_timesteps):
            # If the source "emits" a photon, we measure
            emit = binomial(1, p_emit)
            if emit:
                q = qubit(Source)
                q.H()
                if q.measure():
                    state = 1
                else:
                    state = 0
            # Store results
            results[0,i] = emit
            results[1,i] = state


def main(args):
    logging.basicConfig(format=utils.LOG_FORMAT, level=utils.LOG_LEVEL)
    # Define network parameters
    network = {'name': 'gen_pol',
               'nodes': ['Gen'],
               }
    # Define required SimulaQron parameters
    backend = {'backend': 'stabilizer'}
    # Prepare bits'n'pieces
    results = -1 * np.ones((2,args.n_timesteps))
    p_emit = 0.05
    # Run the experiment
    em = utils.ExperimentManager(network, backend)
    em.start([(generator, [network['name'], 
                           network['nodes'][0], 
                           args.n_timesteps,
                           results, 
                           p_emit,
                           ]
               )
             ])
    em.join()

    np.save(args.outpath, results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Random number expansion certified by Bell's theorem.")
    parser.add_argument("n_timesteps", type=int,
                        help="number of timesteps to query measurement systems")
    parser.add_argument("--outpath", '-o', default="results",
                        help="path for storing results")
    args = parser.parse_args()
    main(args)