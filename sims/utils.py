import json
import logging
import os
from simulaqron.network import Network
from simulaqron.settings import simulaqron_settings
from threading import Thread

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
			threads (dict): Function (key) and arguments (value) pairs
				corresponding to each party in the protocol.
		"""
		for func, args in threads.items():
			logging.info("EM\t: Starting thread for target %s.", func.__name__)
			thread = Thread(target=func, args=args)
			thread.start()
			self.threads.append(thread)

	def join(self):
		""" Gracefully finish the experiment.

		Wait for all threads to finish and clean up the SimulaQron backend
		and network.

		Return:
			results (list): list of return values from each thread.
		"""
		logging.info("EM\t: Joining threads.")

		for thread in self.threads:
			thread.join()

		self.network.stop()
		simulaqron_settings.update_settings(default=True)
		
def setup_simQ(params):
	""" Setup SimulaQron backend with required parameters.

	Reset the SimulaQron backend to have default parameters to avoid erroneous
	settings then update with specified parameters.

	Args:
		params (dict): Parameters to be applied.
	"""
	simulaqron_settings.update_settings(default=True)  # Reset simQ to defaults
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
