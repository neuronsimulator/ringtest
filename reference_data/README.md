# Reference output data

This repository also contains reference output from running the `ringtest.py`
script. This can be compared against NEURON and CoreNEURON results in
integration tests. At present there is just one reference file generated using
NEURON (`special -python ringtest.py -tstop 100`) with the contemporary
`master` commit b55c6e1630665a792ced67c6446ed4fb852c7f79.
