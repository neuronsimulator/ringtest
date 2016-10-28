import argparse
from commonutils import *

parser = argparse.ArgumentParser()

# command line arguments

parser.add_argument(
    "-nring", metavar='N',
    help="number of rings (default 16)",
    type=int, default=16)

parser.add_argument("-ncell",
                    metavar='N',
                    help="number of cells per ring (default 8)",
                    type=int,
                    default=8)

parser.add_argument(
    '-npt', metavar='N',
    help="number of cells per type (default 8)",
    type=int, default=8)

parser.add_argument("-branch",
                    metavar='N',
                    nargs=2,
                    help="range of branches per cell (default 10 20)",
                    type=int,
                    default=[10, 20])

parser.add_argument("-compart",
                    metavar='N',
                    nargs=2,
                    help="range of compartments per branch (default [1,1])",
                    type=int,
                    default=[1, 1])

parser.add_argument("-tstop",
                    metavar='float',
                    help="stop time (ms) (default 100.0)",
                    type=float,
                    default=100.)

parser.add_argument(
    "-gran", metavar='N',
    help="global Random123 index (default 0)",
    type=int, default=0)

parser.add_argument("-rparm",
                    dest='rparm',
                    action='store_true',
                    help="randomize parameters",
                    default=False)

parser.add_argument("-show", action='store_true', help="show type topologies", default=False)

parser.add_argument("-gap", action='store_true', help="use gap junctions", default=False)

parser.add_argument("-coredat",
                    metavar='path',
                    help="folder for bbcorewrite hashname folders (default coredat)",
                    default='coredat')

#option to append hash to coredat directory or not
feature_parser = parser.add_mutually_exclusive_group(required=False)
feature_parser.add_argument('--coredathash', dest='appendhash', action='store_true')
feature_parser.add_argument('--no-coredathash', dest='appendhash', action='store_false')
parser.set_defaults(appendhash=True)

args, unknown = parser.parse_known_args()

nring = args.nring
ncell = args.ncell    # number of cells per ring
ncell_per_type = args.npt

nbranch = args.branch    # min, max random number of dend sections (random tree topology)
ncompart = args.compart    # min, max random nseg for each branch

# number of distinct cell types (same branching and compartments)
#each cell has random type [0:ntype]
ntype = (nring * ncell - 1) / ncell_per_type + 1

#note that if branching is small and variation of nbranch and ncompart
#  is small then not all types may have distinct topologies
#  CoreNEURON will print number of distinct topologies.

usegap = args.gap

tstop = args.tstop
randomize_parameters = args.rparm
appendhash = args.appendhash

from neuron import h

h.Random().Random123_globalindex(args.gran)

h.load_file('stdgui.hoc')
pc = h.ParallelContext()
rank = int(pc.id())
nhost = int(pc.nhost())

if rank == 0:
    print nbranch, ncompart
    print "nring=%d\ncell per ring=%d\nncell_per_type=%d" % (nring, ncell, ncell_per_type)
    print "ntype=%d" % ntype

#from cell import BallStick
h.load_file("cell.hoc")


#for nhost independent type for gid
#shuffle elements of vec
def shuffle(vec, ran):
    n = len(vec) - 1
    for i in range(n + 1):
        ix = int(ran.discunif(i, n))
        vec[i], vec[ix] = vec[ix], vec[i]
    return vec


typecellcnt = [[i, 0] for i in range(ntype)]


def celltypeinfo(type, nbranch, ncompart):
    r = h.Random()
    r.Random123(type, 2)
    nb = int(r.discunif(nbranch[0], nbranch[1]))
    secpar = h.Vector(nb)
    segvec = h.Vector(nb)
    r.discunif(ncompart[0], ncompart[1])
    for i in range(nb):
        segvec.x[i] = int(r.repick())

    # nb branches and every branch has 0, 1, or 2 children
    # ie. no integer in secpar appears more than twice
    x = [[0, 0]]
    for i in range(1, nb):
        a = int(r.discunif(0, len(x) - 1))
        secpar.x[i] = x[a][0]
        x[a][1] += 1
        if x[a][1] > 1:
            x[a][0] = i
            x[a][1] = 0
        else:
            x.append([i, 0])

    #print type, secpar.to_python()
    return secpar, segvec


class Ring(object):

    counter = 0

    def __init__(self, ncell, nbranch, ncompart, gidstart, types):
        #print "construct ", self
        if usegap:
            global nring
            self.sid_dend_start = nring * ncell
            self.halfgap_list = []
        self.gids = []
        self.delay = 1
        self.ncell = int(ncell)
        self.gidstart = gidstart
        self.mkring(self.ncell, nbranch, ncompart, types)
        self.mkstim()

        Ring.counter += 1
        if 1:
            import sys
            print "%d\r" % Ring.counter,
            sys.stdout.flush()

    def mkring(self, ncell, nbranch, ncompart, types):
        self.mkcells(ncell, nbranch, ncompart, types)
        self.connectcells(ncell)

    def mkcells(self, ncell, nbranch, ncompart, types):
        global rank, nhost
        self.cells = []
        for i in range(rank + self.gidstart, ncell + self.gidstart, nhost):
            gid = i
            type = types[gid]
            self.gids.append(gid)
            secpar, segvec = celltypeinfo(type, nbranch, ncompart)
            cell = h.B_BallStick(secpar, segvec)
            self.cells.append(cell)
            pc.set_gid2node(gid, rank)
            nc = cell.connect2target(None)
            pc.cell(gid, nc)

    def connectcells(self, ncell):
        global rank, nhost
        self.nclist = []
        # not efficient but demonstrates use of pc.gid_exists
        for i in range(ncell):
            gid = i + self.gidstart
            targid = (i + 1) % ncell + self.gidstart
            if usegap:
                self.mk_gap(gid, targid)
            else:
                self.mk_con(gid, targid)

    def mk_con(self, gid, targid):
        if pc.gid_exists(targid):
            target = pc.gid2cell(targid)
            syn = target.synlist[0]
            nc = pc.gid_connect(gid, syn)
            self.nclist.append(nc)
            nc.delay = self.delay
            nc.weight[0] = 0.01

    def mk_gap(self, gid_soma, gid_dend):
        #gap between soma and dend
        # soma voltages have sid = gid_soma
        # dendrite voltages have sid = gid_dend + nring*ncell
        sid_soma = gid_soma
        sid_dend = gid_dend + self.sid_dend_start
        if pc.gid_exists(gid_dend):
            self.mk_halfgap(sid_dend, sid_soma, pc.gid2cell(gid_dend).dend[0](.5))
        if pc.gid_exists(gid_soma):
            self.mk_halfgap(sid_soma, sid_dend, pc.gid2cell(gid_soma).soma(.5))

    def mk_halfgap(self, sid_tar, sid_src, seg):
        # target exists
        pc.source_var(seg._ref_v, sid_tar, sec=seg.sec)
        hg = h.HalfGap(seg)
        pc.target_var(hg, hg._ref_vgap, sid_src)
        hg.g = 0.04    # do not randomize as must be same for other side of gap
        self.halfgap_list.append(hg)

    #Instrumentation - stimulation and recording
    def mkstim(self):
        if not pc.gid_exists(0):
            return
        self.stim = h.NetStim()
        self.stim.number = 1
        self.stim.start = 0
        ncstim = h.NetCon(self.stim, pc.gid2cell(self.gidstart).synlist[0])
        ncstim.delay = 1
        ncstim.weight[0] = 0.01
        self.nclist.append(ncstim)


def spike_record():
    global tvec, idvec
    tvec = h.Vector(1000000)
    idvec = h.Vector(1000000)
    pc.spike_record(-1, tvec, idvec)


def spikeout(folder):
    #to out<nhost>.dat file
    global tvec, idvec
    pc.barrier()
    fname = folder + '/spk%d.std' % nhost
    if rank == 0:
        f = open(fname, 'w')
        f.close()
    for r in range(nhost):
        if r == rank:
            f = open(fname, 'a')
            for i in range(len(tvec)):
                f.write('%g %d\n' % (tvec.x[i], int(idvec.x[i])))
            f.close()
        pc.barrier()


def timeit(message):
    global _timeit
    if message == None:
        _timeit = h.startsw()
    else:
        x = h.startsw()
        if rank == 0:
            print '%gs %s' % ((x - _timeit), message)
        _timeit = x


# function to register section-segment with bbcore write
def setup_nrnbbcore_register_mapping(rings):

    #for recording
    recordlist = []

    #vector for soma sections and segment
    somasec = h.Vector()
    somaseg = h.Vector()

    #vector for dendrite sections and segment
    densec = h.Vector()
    denseg = h.Vector()

    #all rings in the simulation
    for ring in rings:

        #every gid in the ring
        for gid in ring.gids:

            #clear previous vector if any
            somasec.size(0)
            somaseg.size(0)
            densec.size(0)
            denseg.size(0)

            #if gid exist on rank
            if (pc.gid_exists(gid)):

                #get cell instance
                cell = pc.gid2cell(gid)
                isec = 0

                #soma section, only pne
                for sec in [cell.soma]:
                    for seg in sec:
                        #get section and segment index
                        somasec.append(isec)
                        somaseg.append(seg.node_index())

                        #vector for recording
                        v = h.Vector()
                        v.record(seg._ref_v)
                        v.label("soma %d %d" % (isec, seg.node_index()))
                        recordlist.append(v)
                isec += 1

                #for sections in dendrite
                for sec in cell.den:
                    for seg in sec:
                        densec.append(isec)
                        denseg.append(seg.node_index())

                        #for recordings
                        v = h.Vector()
                        v.record(seg._ref_v)
                        v.label("dend %d %d" % (isec, seg.node_index()))
                        recordlist.append(v)
                    isec += 1

        #register soma section list
        pc.nrnbbcore_register_mapping(gid, "soma", somasec, somaseg)

        #register dend section list
        pc.nrnbbcore_register_mapping(gid, "dend", densec, denseg)

    return recordlist


#print voltages
def voltageout(foldername, recordlist):
    for vec in recordlist:
        #print only last record
        print vec.label(), vec.x[int(vec.size()) - 1]
        #vec.printf()


if __name__ == '__main__':

    # unique folder for nrnbbcore_write data and a
    # add it to a dict file that records the args associated
    # with the folder
    arghash = str(args).__hash__() & 0xffffffffff
    if appendhash:
        bbcorewrite_folder = args.coredat + '/' + str(arghash)
    else:
        bbcorewrite_folder = args.coredat + '/'

    if rank is 0:
        mkdir_p(bbcorewrite_folder)
        print 'created', bbcorewrite_folder
        f = open(args.coredat + '/dict', "a")
        f.write(str(arghash) + ' : "' + str(args) + '"\n')
        f.close()
    pc.barrier()

    timeit(None)
    ran = h.Random()
    ran.Random123(0, 1)
    types = shuffle([i % ntype for i in range(ncell * nring)], ran)
    rings = [Ring(ncell, nbranch, ncompart, i * ncell, types) for i in range(nring)]
    timeit("created rings")
    if randomize_parameters:
        from ranparm import cellran
        for ring in rings:
            for gid in ring.gids:
                if pc.gid_exists(gid):
                    cellran(gid, ring.nclist)
        timeit("randomized parameters")
    h.cvode.cache_efficient(1)
    ns = 0
    for sec in h.allsec():
        ns += sec.nseg
    ns = pc.allreduce(ns, 1)
    if rank == 0:
        print "%d non-zero area compartments" % ns
    if args.show:
        h.topology()
    spike_record()
    if usegap:
        pc.setup_transfer()

    #register section segment list
    recordlist = setup_nrnbbcore_register_mapping(rings)

    pc.set_maxstep(10)
    h.stdinit()
    timeit("initialized")

    pc.nrnbbcore_write(bbcorewrite_folder)

    timeit("wrote coreneuron data")
    pc.psolve(tstop)
    timeit("run")
    spikeout(bbcorewrite_folder)

    #print voltages
    #voltageout(bbcorewrite_folder, recordlist)

    timeit("wrote %d spikes%s" % (int(pc.allreduce(tvec.size(), 1)),
                                  ("" if nhost == 1 else " (unsorted)")))

    if nhost > 1:
        pc.barrier()
    h.quit()
