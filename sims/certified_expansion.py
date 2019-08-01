import argparse
from cqc.pythonLib import CQCConnection, qubit
import numpy as np
import logging
from threading import Barrier
import utils

""" Random number expansion certified by Bell's theorem.

https://www.nature.com/articles/nature09008

Using two untrusted devices (system_A and system_B), an initial private string
can be exapanded to a longer string whose privacy is bounded. The bound is
determined from an estimate of how much the systems violate the CHSH 
inequality.

TODO:
    move network setup into config file?
    move SimQ setup to command line for experiment control?
"""
def generator(network, node, n_runs, target_A, target_B, barrier):
    """ Generate an EPR pair and share with measurement systems.
    
    Generate a maximally entangled EPR state and send it to the systems located
    at the specified targets:

    Args:
        network (str): name of the network to connect to
        node (str): name of the node to connect to
        n_runs (int): number of EPR pairs to generate
        target_A (str): name of the first target node
        target_B (str): name of the second target node
    """
    with CQCConnection(node, network_name=network) as Generator:
        logging.info("GEN\t: Generator connected to node %s.", node)
        for _ in range(n_runs):
            # Wait until all parties are ready for another qubit
            barrier.wait()
            # Share qubits with targets
            q = Generator.createEPR(target_A)
            Generator.sendQubit(q, target_B)

def measurement(network, node, n_runs, seed, results, bases, recvEPR, barrier):
    """ Recieve entangled qubit and perform random basis measurement.

    Recieves one of the EPR qubits from the generator and performs one of two
    specified basis measurements as decided by the next bit in the seed. Stores
    each measurement result, basis and qubit EPR ID as it goes.

    Args:
        network (str): name of the network to connect to
        node (str): name of the node to connect to
        n_runs (int): number of qubits to measure
        seed (iterable): list-type object containing a set of random bits to be
            used as measurement bases
        results (np.ndarray): array for storing measurement bases, results 
            and qubit IDs
        basis (tuple): pair of lists of rotations to apply to set up the 
            required measurement bases
        recv_EPR (bool): will this node be recieving an EPR pair?
    """
    with CQCConnection(node, network_name=network) as Meas:
        logging.info("MEAS\t: Measurement connected to node %s.", node)
        for i in range(n_runs):
            x = seed[i]
            # Wait until all parties are ready for another qubit
            barrier.wait()
            # Get qubit from generator
            if recvEPR:
                q = Meas.recvEPR()
            else:
                q = Meas.recvQubit()
            # Apply rotations
            utils.change_basis(q, bases[x])
            
            results[i] = q.measure()

def calculate_statistical_correction(n, alpha):
    """ Determine finite stastistics correction factor.

    Args:
        n (int): number of qubits measured
        alpha (float): confidence with which determined bound is correct.
    """
    
    return 4*np.sqrt(-1/n * (2+np.sqrt(2)) * np.log(1-alpha))

def calculate_min_entropy_bound(n, I_est, epsilon):
    """ Bound on the min-entropy of the system given a Bell violation.

    Using the analytical formula determined in the paper, for a given Bell
    inequality violation, return a value bounding the min-entropy of the 
    output string.

    Args:
        n (int): number of qubits measured
        I_est (float): estimate of Bell inequality violation.
        epsilon (float): value to correct for finite statistical effects.
    """
    x = I_est - epsilon
    f = -np.log2(1 - np.log2(1 + np.sqrt(2 - x*x/4)))
    return n * f


def main(args):
    logging.basicConfig(format=utils.LOG_FORMAT, level=utils.LOG_LEVEL)
    # Define network parameters
    network = {'name': 'cert_exp',
               'nodes': ['Gen', 'SysA', 'SysB'],
               'topology': {'Gen' : ['SysA', 'SysB'], 
                            'SysA' : [], 
                            'SysB' : []
                            }
               }
    # Define required SimulaQron parameters
    backend = {'backend': 'projectq',
               'noisy_qubits': False
              }
    # Process input seed
    with open(args.seed_source, 'r') as f:
        seed = np.array(list(f.read())).astype(int)
    seed_A = seed[0:2*args.n_runs:2]
    seed_B = seed[1:2*args.n_runs:2]
    # Prepare bits'n'pieces
    results_A = -1 * np.ones(args.n_runs)
    results_B = -1 * np.ones(args.n_runs)
    qubit_control_barrier = Barrier(len(network['nodes']))
    # Run the experiment
    em = utils.ExperimentManager(network, backend)
    em.start([(generator, [network['name'], 
                           network['nodes'][0], 
                           args.n_runs,
                           network['nodes'][1], 
                           network['nodes'][2],
                           qubit_control_barrier
                           ]
               ),
               (measurement, [network['name'],
                              network['nodes'][1],
                              args.n_runs,
                              seed_A, results_A, 
                              ('X','Z'), True,
                              qubit_control_barrier]
               ),
               (measurement, [network['name'],
                              network['nodes'][2],
                              args.n_runs,
                              seed_B, results_B, 
                              ('X+Z','X-Z'), False,
                              qubit_control_barrier]
               )
             ])
    em.join()

    I_est = utils.estimate_CHSH(seed_A, seed_B, results_A, results_B)
    epsilon = calculate_statistical_correction(args.n_runs, args.alpha)
    H_est = calculate_min_entropy_bound(args.n_runs, I_est, epsilon)

    logging.info("MAIN\t: Estimated CHSH correlation: %.3f", I_est)
    logging.info("MAIN\t: Estimated statistical correciton: %.3f", epsilon)
    logging.info("MAIN\t: Estimated min-entropy bound: %.3f", H_est)

    np.save(args.outpath, np.concatenate((results_A, results_B), axis=0))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Random number expansion certified by Bell's theorem.")
    parser.add_argument("n_runs", type=int,
                        help="number of times to query measurement systems")
    parser.add_argument("alpha", type=float,
                        help="confidence in correction of min-entropy bound")
    parser.add_argument("--seed_source", '-s', default="anu_seed.txt",
                        help="source file for random seed")
    parser.add_argument("--outpath", '-o', default="results",
                        help="path for storing results")
    args = parser.parse_args()
    main(args)
    