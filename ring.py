from commonutils import *
from neuron import h
import settings

class Ring(object):

    counter = 0

    def __init__(self, ncell, nbranch, ncompart, gidstart, types):

        if settings.usegap:
            self.sid_dend_start = settings.nring * ncell
            self.halfgap_list = []

        self.gids = []
        self.delay = 1
        self.ncell = int(ncell)
        self.gidstart = gidstart

        self.mkring(self.ncell, nbranch, ncompart, types)
        self.mkstim()

        Ring.counter += 1

        # show number of cells created
        import sys
        sys.stdout.write("%d\r" % Ring.counter)
        sys.stdout.flush()


    def mkring(self, ncell, nbranch, ncompart, types):
        self.mkcells(ncell, nbranch, ncompart, types)
        self.connectcells(ncell)


    def mkcells(self, ncell, nbranch, ncompart, types):
        self.cells = []

        for i in range(self.gidstart, ncell + self.gidstart):

            if (i % settings.nhost) != settings.rank:
                continue

            gid = i
            type = types[gid]
            self.gids.append(gid)
            secpar, segvec = celltypeinfo(type, nbranch, ncompart)
            cell = h.B_BallStick(secpar, segvec)
            self.cells.append(cell)
            settings.pc.set_gid2node(gid, settings.rank)
            nc = cell.connect2target(None)
            settings.pc.cell(gid, nc)

    def connectcells(self, ncell):

        self.nclist = []

        # not efficient but demonstrates use of settings.pc.gid_exists
        for i in range(ncell):
            gid = i + self.gidstart
            targid = (i + 1) % ncell + self.gidstart

            if settings.usegap:
                self.mk_gap(gid, targid)
            else:
                self.mk_con(gid, targid)

    def mk_con(self, gid, targid):

        if settings.pc.gid_exists(targid):
            target = settings.pc.gid2cell(targid)
            syn = target.synlist[0]
            nc = settings.pc.gid_connect(gid, syn)
            self.nclist.append(nc)
            nc.delay = self.delay
            nc.weight[0] = 0.01

    def mk_gap(self, gid_soma, gid_dend):
        # gap between soma and dend
        # soma voltages have sid = gid_soma
        # dendrite voltages have sid = gid_dend + nring*ncell
        sid_soma = gid_soma
        sid_dend = gid_dend + self.sid_dend_start

        if settings.pc.gid_exists(gid_dend):
            self.mk_halfgap(sid_dend, sid_soma, settings.pc.gid2cell(gid_dend).dend[0](.5))

        if settings.pc.gid_exists(gid_soma):
            self.mk_halfgap(sid_soma, sid_dend, settings.pc.gid2cell(gid_soma).soma(.5))

    def mk_halfgap(self, sid_tar, sid_src, seg):

        # target exists
        settings.pc.source_var(seg._ref_v, sid_tar, sec=seg.sec)
        hg = h.HalfGap(seg)
        settings.pc.target_var(hg, hg._ref_vgap, sid_src)
        hg.g = 0.04    # do not randomize as must be same for other side of gap
        self.halfgap_list.append(hg)

    #Instrumentation - stimulation and recording
    def mkstim(self):

        if not settings.pc.gid_exists(self.gidstart):
            return

        self.stim = h.NetStim()
        self.stim.number = 1
        self.stim.start = 0
        ncstim = h.NetCon(self.stim, settings.pc.gid2cell(self.gidstart).synlist[0])
        ncstim.delay = 1
        ncstim.weight[0] = 0.01
        self.nclist.append(ncstim)


class HHRing(Ring):

    def __init__(self, ncell, connection_percentage, gidstart):

        self.gids = []
        self.delay = 1
        self.ncell = int(ncell)
        self.gidstart = gidstart

        self.mkring(self.ncell, connection_percentage)
        self.mkstim()

        Ring.counter += 1

        # show number of cells created
        import sys
        sys.stdout.write("%d\r" % Ring.counter)
        sys.stdout.flush()


    def mkring(self, ncell, connection_percentage):
        self.mkcells(ncell)
        self.connectcells(ncell, connection_percentage)


    def mkcells(self, ncell):
        self.cells = {}

        for i in range(self.gidstart, ncell + self.gidstart):

            if (i % settings.nhost) != settings.rank:
                continue

            gid = i
            self.gids.append(gid)
            soma = h.Section('soma')

            soma.cm = 1
            soma.L = 10.0
            soma.diam = 10.0

            soma.insert('hh')
            soma.gnabar_hh = 0.1
            soma.gkbar_hh = 0.035

            self.cells[gid] = soma
            settings.pc.set_gid2node(gid, settings.rank)
            nc = h.NetCon(soma(0.5)._ref_v, None, sec=soma)
            settings.pc.cell(gid, nc)


    def mkstim(self):
        for gid in self.gids:

            if not settings.pc.gid_exists(gid):
                continue

            iclamp = h.IClamp(settings.pc.gid2cell(gid)(0.5))
            iclamp.amp = 0.05

            iclamp.delay = 50
            iclamp.dur = 100


    def connectcells(self, ncell, connection_percentage):

        self.nclist = []
        connections_per_cell = ncell*connection_percentage
        print("Connections per cell {}".format(connections_per_cell))
        for gid in self.gids:
        # not efficient but demonstrates use of settings.pc.gid_exists
            for i in range(gid, gid+int(connections_per_cell)):
                if gid != i:
                    print("Creating connection for sgid {} tgid {}".format(i, gid))
                    self.mk_con(i, gid)


    def mk_con(self, gid, targid):

        if settings.pc.gid_exists(targid):
            target = self.cells[targid]
            nc = settings.pc.gid_connect(gid, target)
            self.nclist.append(nc)
            nc.delay = self.delay
            nc.weight[0] = 0.01
