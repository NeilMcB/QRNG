from cqc.pythonLib import qubit
import json
import logging
import numpy as np
import os
from simulaqron.network import Network
from simulaqron.settings import simulaqron_settings
from threading import Thread

""" Some helpful functions for running SimulaQron experiments

TODO:
    Describe neatly what U0 and U1 do
"""

# Some useful variables
LOG_FORMAT = "%(levelname)s: %(message)s"
LOG_LEVEL = logging.INFO

class ExperimentManager:
    """ Manage the setup, running and clean-up of SimulaQron experiments.
    """
    def __init__(self, usr_network_params=None, usr_simQ_params=None):
        """ Prepare experiment environment.

        Load config file, pass specified settings to simulaQron backend and
        initialise the simulaQron network to be used in the experiment.

        Args:
            network_params (dict): Parameters to be used in network setup. 
                Defaults to None. Defaults in config file used if so.
            simQ_params (dict): Parameters to be passed to SimulaQron backend.
                Defaults to None. Defaults in config file used if so.           
        
        Attributes:
            config (dict): Configuration file read in to dictionary.
            params (dict): Dictionary of parameters used in experiment.
            network (simulaqron.network.Network): pointer to simulaqron 
                network started by the ExperimentManager.
            threads (list): List for storing all managed experiment threads.
        """
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        with open(config_path, 'r') as cfg:
            self.config = json.load(cfg)
        
        self.params = self.config['defaults']
        self.parse_params('network_params', usr_network_params)
        self.parse_params('simQ_params', usr_simQ_params)

        setup_simQ(self.params['simQ_params'])
        self.network = setup_network(self.params['network_params'])

        self.threads = []

    def parse_params(self, location, usr_params):
        """ Compare passed parameters to defaults and update where required.

        Args:
            location (str): Location (network/simQ) of parameters to update.
            params (dict): Parameters to be parsed.
        """
        if usr_params is not None:
            for param, value in usr_params.items():
                self.update_param(location, param, value)
        else:
            logging.info("EM\t: Applying default parameters to %s.", location)

    def update_param(self, location, param, value):
        """ Update stored parameter.

        Args:
            location (str): Location (network/simQ) of parameter to update.
            param (str): Name of parameter to update.
            value (var): Value of parameter to be stored.
        """
        self.params[location][param] = value
        logging.info("EM\t: Updating %s.%s to %s.", location, param, value)

    def start(self, threads):
        """ Start all experiment threads.

        Args:
            threads (list): Tuples of function and arguments pairs
                corresponding to each party in the protocol.
        """
        for func, args in threads:
            logging.info("EM\t: Starting thread for target %s.", func.__name__)
            thread = Thread(target=func, args=args)
            thread.start()
            self.threads.append(thread)

    def join(self):
        """ Gracefully finish the experiment.

        Wait for all threads to finish and clean up the SimulaQron backend
        and network.

        Return:
            (list): list of return values from each thread.
        """
        logging.info("EM\t: Joining threads.")

        for thread in self.threads:
            thread.join()

        self.network.stop()
        simulaqron_settings.default_settings()
        
def setup_simQ(params):
    """ Setup SimulaQron backend with required parameters.

    Reset the SimulaQron backend to have default parameters to avoid erroneous
    settings then update with specified parameters.

    Args:
        params (dict): Parameters to be applied.
    """
    for param, value in params.items():
        setattr(simulaqron_settings, param, value)
    logging.info("EM\t: SimulaQron setup complete.")

def setup_network(params):
    """ Setup new Simulaqron network. 

    Args:
        params (dict): Network parameters to be used.

    Return:
        network (simulaqron.network.Network): Pointer to started network.
    """
    network = Network(**params)
    network.start()
    logging.info("EM\t: Network setup complete.")

    return network

def change_basis(qubit, basis):
    """ Apply specified basis transformation to qubit.

    Args:
        qubit (cqc.pythonLib.qubit): qubit to transform
        basis (str): basis to transform to
    """
    if basis == 'Z':
        qubit.I()
    elif basis == 'X':
        qubit.H()
    elif basis == 'X+Z':
        qubit.rot_Z(128)
        qubit.rot_Y(32)  
        qubit.rot_Z(128) 
    elif basis == 'X-Z':
        qubit.rot_Z(128)
        qubit.rot_Y(96)  
        qubit.rot_Z(128) 
    else:
        raise ValueError('Valid bases are Z, X, X+Z and X-Z.')

def estimate_CHSH(bases_A, bases_B, results_A, results_B, px=0.5, py=0.5):
    """ Estimate the CHSH correlation function.

    Args:
        bases_A (iterable): binary list of measurement bases for system A
        bases_B (iterable): binary list of measurement bases for system B
        results_A (iterable): binary list of measurement results for system A
        results_B (iterable): binary list of measurement results for system B
    """
    I = 0
    for i, (x, y) in enumerate(zip(bases_A, bases_B)):
        a = results_A[i]
        b = results_B[i]
        I += (-1)**(x*y) * ((int(a==b) - int(a!=b)) / 0.25)
    return I/len(bases_A)

def estimate_FPB(bases, results):
    """ Estimate the four-partite Bell inequality violation.

    Args:
        bases (np.ndarray): array of bases used in each measurement.
        results (np.ndarray): array of results obtained in each measurement.
    """
    U0 = ['[1 0 0 0]', '[0 1 0 0]', '[0 0 1 0]', '[0 0 0 1]']
    U1 = ['[1 0 0 0]', '[0 1 0 0]', '[0 0 1 0]', '[0 0 0 1]']
    B = 0
    for i in range(bases.shape[1]):
        u = str(bases[:,i])
        x = str(results[:,i])
        if u in U0:
            if x in U1:
                B += 1
        elif u in U1:
            if x in U0:
                B += 1
    return B/bases.shape[1]

def carter_wegman_extractor(source, seed, k, epsilon):
	""" A Carter-Wegman hashing based randomness extractor.

	http://users.cms.caltech.edu/~vidick/teaching/120_qcrypto/LN_Week4.pdf

	A (k, epsilon)-strong randmoness extractor based on Carter-Wegman hashing.
	Note that as the extractor is strong, the seed can be appended to its
	output without compromising the uniformity of the final string. The seed
	must be two-times the length of the source.

	In the finite field F_q where q=2^n, f_{a,b}(x)=ax+b, (a,b) in F_q^2. 

	Args:
		source (np.ndarray): string of bits from a source of known min-entropy.
		seed (np.ndarray): string of bits from uniformly random source.
		k (float): (lower bound on) the min-entropy of the source.
		epsilon (float): distance from uniform randomness accepted.

	Returns:
		(np.ndarray): random string of reduced length epsilon-close to uniform
			randomness.
	"""
	d = len(seed)
	n = len(source)
	m = (int) (k - 2*np.log2(1/epsilon))
	if (d < 2*n):
		raise ValueError("Seed must have length two times that of source.")
	# apply hash function by "sampling" from family of functions using seed
	a = seed[:n]
	b = seed[n:2*n]
	f = np.logical_xor(np.logical_and(a, source), b)
	# discard bits to satisfy leftover hash lemma 
	return f[:m]



