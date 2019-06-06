A single-qubit implementation of QKD, based heavily off of https://github.com/SoftwareQuTech/CQC-Python/tree/master/examples/pythonLib/programming_q_network.

Usage:
	start.sh   -- sets up SimulaQron network for BB84
	run.sh n   -- perform n iterations of BB84 QKD (can be repeated)
	stop.sh    -- shuts down SimulaQron network

	OR

	python BB84_QKD.py n -- does all of the above in one go (can be unreliable, if timeout error appears just run again - to be fixed), and generates key and associated QBER estimate.