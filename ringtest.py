from args import *

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

# whether to create data disrectory with some hash name
appendhash = args.appendhash

# whether to dump section-segment mapping
secseg_mapping = args.secmapping

# number of distinct cell types (same branching and compartments)
# each cell has random type [0:ntype]
ntype = (nring * ncell - 1) / ncell_per_type + 1

from ring import *
from neuron import h
from commonutils import *
import settings

# initialize global variables
settings.init(usegap, nring)


# note that if branching is small and variation of nbranch and ncompart
# is small then not all types may have distinct topologies
# CoreNEURON will print number of distinct topologies.


h.Random().Random123_globalindex(args.gran)

h.load_file('stdgui.hoc')

pc = h.ParallelContext()

# set number of threads
pc.nthread(args.nt, 1)

if settings.rank == 0:
    print(nbranch, ncompart)
    print("nring=%d\ncell per ring=%d\nncell_per_type=%d" % (nring, ncell, ncell_per_type))
    print("ntype=%d" % ntype)

#from cell import BallStick
h.load_file("cell.hoc")

typecellcnt = [[i, 0] for i in range(int(ntype))]



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

    load_balance = avg_comp_time / max_cw_time

    # spike communication time
    spk_time = (pc.allreduce(wait, 2), pc.allreduce(wait, 3))

    # gap junction transfer time
    gap_time = (pc.allreduce(pc.vtransfer_time(), 2), pc.allreduce(pc.vtransfer_time(), 3))

    return runtime, load_balance, avg_comp_time, spk_time, gap_time

def multisplit():
    h.load_file("parcom.hoc")
    parcom = h.ParallelComputeTool()
    parcom.multisplit(1)
    if settings.rank == 0:
        lb = parcom.lb
        print ('multisplit rank 0: %d pieces  Load imbalance %.1f%%' % (lb.npiece, (lb.thread_cxbal_ -1)*100))

if __name__ == '__main__':

    # hash of the arguments for unique directory name
    arghash = str(args).__hash__() & 0xffffffffff

    # unique folder to write data for coreneuron
    if appendhash:
        bbcorewrite_folder = args.coredat + '/' + str(arghash)
    else:
        bbcorewrite_folder = args.coredat + '/'

    # only master rank creates directory and write hash dict
    # to file that records the args associated with the folder
    if settings.rank is 0:

        mkdir_p(bbcorewrite_folder)

        print('created', bbcorewrite_folder)

        f = open(args.coredat + '/dict', "a")
        f.write(str(arghash) + ' : "' + str(args) + '"\n')
        f.close()

    # wait for master to create directory
    pc.barrier()

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

    h.cvode.cache_efficient(1)

    # count total number of segments / compartments
    ns = 0
    for sec in h.allsec():
        ns += sec.nseg
    ns = pc.allreduce(ns, 1)

    if settings.rank == 0:
        print("%d non-zero area compartments" % ns)

    if args.multisplit:
        multisplit()

    if args.show:
        h.topology()


    spike_record()

    if usegap:
        pc.setup_transfer()

    # register section segment list
    if secseg_mapping:
        recordlist = setup_nrnbbcore_register_mapping(rings)

    pc.set_maxstep(10)

    h.stdinit()

    timeit("initialized", settings.rank)

    # write intermediate dataset for coreneuron
    if args.multisplit is False:
        pc.nrnbbcore_write(bbcorewrite_folder)
        timeit("wrote coreneuron data", settings.rank)

    # run simulation with NEURON
    # note that if you want to use CoreNEURON then you don't have to run with NEURON
    runtime, load_balance, avg_comp_time, spk_time, gap_time = prun(tstop)

    timeit("run", settings.rank)

    # write spike raster
    spikeout(bbcorewrite_folder)

    # print voltage recordings
    # if secseg_mapping:
    #    voltageout(bbcorewrite_folder, recordlist)

    if settings.rank == 0:

        print("runtime=%g  load_balance=%.1f%%  avg_comp_time=%g" %
              (runtime, load_balance * 100, avg_comp_time))
        print("spk_time max=%g min=%g" % (spk_time[0], spk_time[1]))
        print("gap_time max=%g min=%g" % (gap_time[0], gap_time[1]))

    if settings.nhost > 1:
        pc.barrier()

    h.quit()
