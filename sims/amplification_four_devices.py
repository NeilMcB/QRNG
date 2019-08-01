import argparse
from cqc.pythonLib import CQCConnection, qubit
import numpy as np
from numpy.random import binomial
import logging
from threading import Barrier
import utils

""" Randomness amplification using four measurement devices.

https://www.nature.com/articles/ncomms11345

Classical randomness extractors exist which require two indendenct (weak)
sources of randomness to output an arbitrarily strong random string. By using 
a weak source to determine measurement basis of a Bell inequality violation 
experiment, this protocol converts this single source into two independent
sources, which can then be passed to a classical randomness extractor.

The strength of the inequality violation provides assurances about the noise
tolerated by the protocol.

TODO:
    improve this blurb
"""

def generator(network, node, n_runs, targets, barrier):
    """ Generate a four-partite entangled state and send to experiment.

    Construct the required quantum state (see paper supplementary information
    equation 8) and pass to all measurement systems. Note: createEPR cannot be
    used as control gates must be performed within same CQCConnection.

    Args:
        network (str): name of the network to connect to
        node (str): name of the node to connect to
        n_runs (int): number of experiments to prepare states for
        targets (iterable): name of the target nodes
        barrier (threading.Barrier): control qubit flow
    """
    with CQCConnection(node, network_name=network) as Generator:
        logging.info("GEN\t: Generator connected to node %s.", node)
        for i in range(n_runs):
            # Prepare entangled state
            # \ket{\Psi_0} = \ket{0000}
            qs = [qubit(Generator) for _ in range(4)]
            # \ket{\Psi_1} = \ket{\phi_+}\ket{\phi_+} 
            #              = \frac{1}{2}(\ket{00}+\ket{11})(\ket{00}+\ket{00})
            qs[0].H()
            qs[0].cnot(qs[1])
            qs[2].H()               
            qs[2].cnot(qs[3])
            # \ket{\Psi_2} = \frac{1}{2}(\ket{\phi_-}\ket{\tilde{\phi}_+}+\ket{\psi_+}\ket{\tilde{\phi}_+})
            #              = \frac{1}{4}((\ket{00}-\ket{11})(\ket{0+}+\ket{1-})+(\ket{01}+\ket{10})(\ket{0+}+\ket{1-}))
            qs[1].H()
            qs[3].H()
            # \ket{\Psi_3} = \frac{1}{2}(\ket{\phi_-}\ket{\tilde{\phi}_+}+\ket{\psi_+}\ket{\tilde{\psi}_+})
            #              = \frac{1}{4}((\ket{00}-\ket{11})(\ket{0+}+\ket{1-})+(\ket{01}+\ket{10})(\ket{0-}+\ket{1+}))
            qs[0].cnot(qs[3])
            qs[1].cnot(qs[3])
            # \ket{\Psi_4} = \frac{1}{2}(\ket{\phi_-}\ket{\tilde{\phi}_+}+\ket{\psi_+}\ket{\tilde{\psi}_-})
            #              = \frac{1}{4}((\ket{00}-\ket{11})(\ket{0+}+\ket{1-})+(\ket{01}+\ket{10})(\ket{0-}-\ket{1+}))
            qs[0].cphase(qs[2])
            qs[1].cphase(qs[2])

            # Wait until all parties are ready for another qubit
            barrier.wait()
            # Share qubits with targets
            for target, q in zip(targets, qs):
                Generator.sendQubit(q, target)

            if n_runs < 10:
                logging.info("GEN\t: %d of %d sent.", i, n_runs)
            elif i % (n_runs // 8) == 0:
                logging.info("GEN\t: %d of %d sent.", i, n_runs)

def measurement(network, node, n_runs, seed, results, bases, barrier):
    """ Recieve entangled qubit and perform random basis measurement.

    Recieves one of the entanbled qubits from the generator and performs one of 
    two specified basis measurements as decided by the next bit in the seed. 
    Stores each measurement result and basis as it goes.

    Args:
        network (str): name of the network to connect to
        node (str): name of the node to connect to
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
            q = Meas.recvQubit()
            # Apply rotations
            utils.change_basis(q, bases[x])
            
            results[0,i] = x
            results[1,i] = q.measure()

def main(args):
    logging.basicConfig(format=utils.LOG_FORMAT, level=utils.LOG_LEVEL)
    # Define network parameters
    network = {'name': 'rand_amp_4',
               'nodes': ['Gen', 'SysA', 'SysB', 'SysC', 'SysD'],
               'topology': {'Gen': ['SysA', 'SysB', 'SysC', 'SysD'],
                            'SysA': [],
                            'SysB': [],
                            'SysC': [],
                            'SysD': []
                           }
               }
    # Define required SimulaQron parameters
    #backend = {}
    with open(args.seed_source, 'r') as f:
        seed = np.array(list(f.read())).astype(int)
    seeds = [seed[i:4*args.n_runs:4] for i in range(4)]
    # Prepare bits'n'pieces
    results = [-1*np.ones((2, args.n_runs)) for _ in range(4)]
    qubit_control_barrier = Barrier(len(network['nodes']))
    # Run the experiment
    em = utils.ExperimentManager(network)#, backend)
    em.start([(generator, [network['name'], 
                           network['nodes'][0], 
                           args.n_runs,
                           network['nodes'][1:],
                           qubit_control_barrier
                          ]
               ),
               (measurement, [network['name'],
                              network['nodes'][1],
                              args.n_runs,
                              seeds[0], results[0], 
                              ('X','Z'),
                              qubit_control_barrier]
               ),
               (measurement, [network['name'],
                              network['nodes'][2],
                              args.n_runs,
                              seeds[1], results[1], 
                              ('X','Z'),
                              qubit_control_barrier]
               ),
               (measurement, [network['name'],
                              network['nodes'][3],
                              args.n_runs,
                              seeds[2], results[2], 
                              ('X','Z'),
                              qubit_control_barrier]
               ),
               (measurement, [network['name'],
                              network['nodes'][4],
                              args.n_runs,
                              seeds[3], results[3], 
                              ('X','Z'),
                              qubit_control_barrier]
               )
             ])
    em.join()

    results = np.stack(results)

    print(utils.estimate_FPB(results[:,0,:], results[:,1,:]))
    np.save(args.outpath, results)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Random number expansion certified by Bell's theorem.")
    parser.add_argument("n_runs", type=int,
                        help="number of times to query measurement systems")
    parser.add_argument("--seed_source", '-s', default="anu_seed.txt",
                        help="source file for random seed")
    parser.add_argument("--outpath", '-o', default="results",
                        help="path for storing results")
    args = parser.parse_args()
    main(args)
    
