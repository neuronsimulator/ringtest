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

# Which integration method to use
method = args.method

# Cvode threshold detection --- first or second order
condition_order = 2 if args.thresh_order2 else 1

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

# cell permutation type
coreneuron_permute = args.permute

# permute type is default 0 for GPU then choose type 2
if coreneuron_gpu and coreneuron_permute == 0:
    coreneuron_permute = 2

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
    methname=["fixed", "global vardt, ", "local vardt, "]
    co = "condition_order="+str(condition_order) if method else ""
    print ("method = %s %s" % (methname[method], co))

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

    # Load balance is average computation time / max computation time
    computation_time = pc.step_time()

    avg_comp_time = pc.allreduce(computation_time, 1) / settings.nhost
    max_comp_time = pc.allreduce(computation_time, 2)

    load_balance = (avg_comp_time / max_comp_time) if max_comp_time else 0.0

    # spike communication time
    spk_time = (pc.allreduce(wait, 2), pc.allreduce(wait, 3))

    # gap junction transfer time
    gap_time = (pc.allreduce(pc.vtransfer_time(), 2), pc.allreduce(pc.vtransfer_time(), 3))

    return runtime, load_balance, avg_comp_time, spk_time, gap_time


def create_rings():

    ## Create all rings ##

    timeit(None, settings.rank)

    # create network / ring of cells
    ran = h.Random()
    ran.Random123(0, 1)
    types = shuffle([i % ntype for i in range(ncell * nring)], ran)
    rings = [Ring(ncell, nbranch, ncompart, i * ncell, types) for i in range(nring)]

    timeit("created rings", settings.rank)

    # randomize parameters if asked
    if randomize_parameters:
        from ranparm import cellran
        for ring in rings:
            for gid in ring.gids:
                if pc.gid_exists(gid):
                    cellran(gid, ring.nclist)
        timeit("randomized parameters", settings.rank)


    ## CoreNEURON setting ##

    h.cvode.cache_efficient(1)

    if use_coreneuron:
        from neuron import coreneuron
        coreneuron.enable = True
        coreneuron.file_mode = coreneuron_file_mode
        coreneuron.gpu = coreneuron_gpu
        coreneuron.cell_permute = coreneuron_permute

        if args.multisplit is True:
            print("Error: multi-split is not supported with CoreNEURON\n")
            quit()

        if args.register_mapping:
            setup_nrnbbcore_register_mapping(rings)
            report_conf_file = "report.conf"
            sim_conf_file = "sim.conf"
            if settings.rank == 0:
                write_report_config(report_conf_file, "soma.h5", "Mosaic", "compartment", "v",
                                    "mV", "SONATA", 2, 1, 0, tstop, list(range(ncell)))
                write_spike_config(report_conf_file, "spikes.h5", ["default"], [0])
                write_sim_config(sim_conf_file, "corenrn_data", report_conf_file, tstop)
            coreneuron.sim_config=sim_conf_file

    ## Record spikes ##

    spike_record()

    ## Various CLI options ##

    if args.multisplit:
        multisplit()

    if args.show:
        h.topology()

    if usegap:
        pc.setup_transfer()

    # register section/segment mapping
    if args.dumpmodel:
        recordlist = setup_nrnbbcore_register_mapping(rings)
        # NOTE: once simulation finishes, one can print
        # voltages as below
        # voltageout("coredat", recordlist)

    ## Initialize ##

    if method > 0:
        h.cvode.condition_order(condition_order)
        h.cvode.active(1)
        if method == 2:
            h.cvode.use_local_dt(1)
    pc.set_maxstep(10)
    h.stdinit()
    timeit("initialized", settings.rank)


    ## Dump model to file ##

    if args.dumpmodel:
        pc.nrnbbcore_write("coredat")

    return types, rings

def runsim():
    ##  Run simulation ##

    runtime, load_balance, avg_comp_time, spk_time, gap_time = prun(tstop)
    timeit("run", settings.rank)

    ## Print stats ##

    pc.barrier()
    if settings.rank == 0:
        print("runtime=%g  load_balance=%.1f%%  avg_comp_time=%g" %
              (runtime, load_balance * 100, avg_comp_time))
        print("spk_time max=%g min=%g" % (spk_time[0], spk_time[1]))
        print("gap_time max=%g min=%g" % (gap_time[0], gap_time[1]))


if __name__ == '__main__':

    model = create_rings()

    ## Run Simulation ##
    runsim()

    ## Write spike raster ##
    spikeout(".")

    h.quit()
