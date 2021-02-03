from args import *

# parse CLI arguments
args, unknown = parser.parse_known_args()

# number of rings
nring = args.nring

# number of cells per ring
ncell = args.ncell

# number of cells per type
ncell_per_type = args.npt

# min, max random number of dend sections (random tree topology)
nbranch = args.branch

# min, max random nseg for each branch
ncompart = args.compart

# if use gap junctions
usegap = args.gap

# stop time of simulation
tstop = args.tstop

# whether to randomize cell parameters
randomize_parameters = args.rparm

# number of distinct cell types (same branching and compartments)
# each cell has random type [0:ntype]
ntype = int((nring * ncell - 1) / ncell_per_type + 1)

# whether to run via in-memory transfer mode or file mode
# Of filemode is true then model is dumped to file and then
# passed to coreneuron. In in-memory mode model is passed to
# coreneuron via in-memory copy.
coreneuron_file_mode = args.filemode

# whether to run coreneuron or neuron
use_coreneuron = args.coreneuron

# whether to run coreneuron on GPU
coreneuron_gpu = args.gpu

from ring import *
from neuron import h
from commonutils import *
import settings

# initialize global variables
settings.init(usegap, nring)

# note that if branching is small and variation of nbranch and ncompart
# is small then not all types may have distinct topologies
# CoreNEURON will print number of distinct topologies.

# initialize seed
h.Random().Random123_globalindex(args.gran)

h.load_file('stdgui.hoc')

pc = h.ParallelContext()

# set number of threads
pc.nthread(args.nt, 1)

if settings.rank == 0:
    print ("%s %s" % (str(nbranch), str(ncompart)))
    print ("nring=%d\ncell per ring=%d\nncell_per_type=%d" % (nring, ncell, ncell_per_type))
    print ("ntype=%d" % ntype)

#from cell import BallStick
h.load_file("cell.hoc")

typecellcnt = [[i, 0] for i in range(ntype)]


def multisplit():
    h.load_file("parcom.hoc")
    parcom = h.ParallelComputeTool()
    parcom.multisplit(1)
    if settings.rank == 0:
        lb = parcom.lb
        print ('multisplit rank 0: %d pieces  Load imbalance %.1f%%' % (lb.npiece, (lb.thread_cxbal_ -1)*100))


def prun(tstop):
    runtime = h.startsw()
    wait = pc.wait_time()

    # run simulation
    pc.psolve(tstop)

    # calculate various time statistics for profiling/debugging

    wait = pc.wait_time() - wait
    runtime = h.startsw() - runtime

    computation_time = pc.step_time()

    cw_time = computation_time + pc.step_wait()
    max_cw_time = pc.allreduce(cw_time, 2)

    avg_comp_time = pc.allreduce(computation_time, 1) / settings.nhost

    if max_cw_time == 0:
        load_balance = 0
    else:
        load_balance = avg_comp_time / max_cw_time

    # spike communication time
    spk_time = (pc.allreduce(wait, 2), pc.allreduce(wait, 3))

    # gap junction transfer time
    gap_time = (pc.allreduce(pc.vtransfer_time(), 2), pc.allreduce(pc.vtransfer_time(), 3))

    return runtime, load_balance, avg_comp_time, spk_time, gap_time


def network():
    # create network / ring of cells
    ran = h.Random()
    ran.Random123(0, 1)
    types = shuffle([i % ntype for i in range(ncell * nring)], ran)
    rings = [Ring(ncell, nbranch, ncompart, i * ncell, types) for i in range(nring)]

    return rings

def randomize(rings):
    # randomize parameters if asked
    if randomize_parameters:
        from ranparm import cellran
        for ring in rings:
            for gid in ring.gids:
                if pc.gid_exists(gid):
                    cellran(gid, ring.nclist)

if __name__ == '__main__':

    ## Create all rings ##

    timeit(None, settings.rank)

    rings = network()
    timeit("created rings", settings.rank)
    if randomize_parameters:
        randomize(rings)    
        timeit("randomized parameters", settings.rank)

    ## CoreNEURON setting ##

    h.cvode.cache_efficient(1)

    if use_coreneuron:
        from neuron import coreneuron
        coreneuron.enable = True
        coreneuron.file_mode = coreneuron_file_mode
        coreneuron.gpu = coreneuron_gpu

        if args.multisplit is True:
            print("Error: multi-split is not supported with CoreNEURON\n")
            quit()

    ## Record spikes ##

    spike_record()

    ## Various CLI options ##

    if args.multisplit:
        multisplit()

    if args.show:
        h.topology()

    if usegap:
        pc.setup_transfer()

    ## Initialize ##

    pc.set_maxstep(10)
    h.stdinit()
    timeit("initialized", settings.rank)


    ## Dump model to file ##

    if args.dumpmodel:
        pc.nrnbbcore_write("coredat")


    ##  Run simulation ##

    runtime, load_balance, avg_comp_time, spk_time, gap_time = prun(tstop)
    timeit("run", settings.rank)

    ## Write spike raster ##

    spikeout(".")

    ## Print stats ##

    pc.barrier()
    if settings.rank == 0:
        print("runtime=%g  load_balance=%.1f%%  avg_comp_time=%g" %
              (runtime, load_balance * 100, avg_comp_time))
        print("spk_time max=%g min=%g" % (spk_time[0], spk_time[1]))
        print("gap_time max=%g min=%g" % (gap_time[0], gap_time[1]))

    h.quit()
