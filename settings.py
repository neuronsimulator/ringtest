from neuron import h

# global variables used by other modules / files

def init(gap_, nring_):

    global pc, rank, nhost, usegap, nring

    pc = h.ParallelContext()
    rank = int(pc.id())
    nhost = int(pc.nhost())
    usegap = gap_
    nring = nring_
