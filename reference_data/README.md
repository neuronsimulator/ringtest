# Reference output data

This repository also contains reference output from running the `ringtest.py`
script. This can be compared against NEURON and CoreNEURON results in
integration tests.

* spk1.100ms.std.ref : generated using NEURON (`special -python ringtest.py -tstop 100`) with the contemporary
`master` commit b55c6e1630665a792ced67c6446ed4fb852c7f79.
* soma.h5 : generated using CORENEURON (`LIBSONATA_ZERO_BASED_GIDS=1 special -mpi -python ringtest.py -tstop 100 -coreneuron -registermapping`)
