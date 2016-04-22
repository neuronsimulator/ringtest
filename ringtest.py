nring=64
ncell=8 # number of cells per ring
ncell_per_type = 32

nbranch=[20, 20] # min, max random number of dend sections (random tree topology)
ncompart=[2, 2] # min, max random nseg for each branch

# number of distinct cell types (same branching and compartments)
#each cell has random type [0:ntype]
ntype=(nring*ncell - 1)/ncell_per_type + 1
#note that if branching is small and variation of nbranch and ncompart
#  is small then not all types may have distinct topologies
#  CoreNEURON will print number of distinct topologies.

print "nring=%d\ncell per ring=%d\nncell_per_type=%d"%(nring, ncell, ncell_per_type)
print "ntype=%d"%ntype

usegap = False

tstop=100
randomize_parameters = False

from neuron import h
h.load_file('nrngui.hoc')
pc = h.ParallelContext()
rank = int(pc.id())
nhost = int(pc.nhost())
#from cell import BallStick
h.load_file("cell.hoc")

typecellcnt = [[i, 0] for i in range(ntype)]

def celltypeinfo(gid, nbranch, ncompart, ntype):
  global typecellcnt
  r = h.Random()
  r.Random123(gid, 1)
  # every type has exactly ncell_per_type
  i = int(r.discunif(0, len(typecellcnt)-1))
  type = typecellcnt[i][0];
  typecellcnt[i][1] += 1
  if typecellcnt[i][1] >= ncell_per_type:
    typecellcnt.pop(i)

  #print "gid=%d type=%d"%(gid, type)
  
  r.Random123(type, 2)
  nb = int(r.discunif(nbranch[0], nbranch[1]))
  secpar = h.Vector(nb)
  segvec = h.Vector(nb)
  r.discunif(ncompart[0], ncompart[1])
  for i in range(nb):
    segvec.x[i] = int(r.repick())
  for i in range(1, nb):
    secpar.x[i] = int(r.discunif(0, i-1))

  return secpar, segvec

class Ring(object):

  def __init__(self, ncell, nbranch, ncompart, ntype, gidstart):
    #print "construct ", self
    if usegap:
      global nring
      self.sid_dend_start = nring*ncell
      self.halfgap_list = []
    self.gids = []
    self.delay = 1
    self.ncell = int(ncell)
    self.gidstart = gidstart
    self.mkring(self.ncell, nbranch, ncompart, ntype)
    self.mkstim()

  def mkring(self, ncell, nbranch, ncompart, ntype):
    self.mkcells(ncell, nbranch, ncompart, ntype)
    self.connectcells(ncell)

  def mkcells(self, ncell, nbranch, ncompart, ntype):
    global rank, nhost
    self.cells = []
    for i in range(rank + self.gidstart, ncell + self.gidstart, nhost):
      gid = i
      self.gids.append(gid)
      secpar, segvec = celltypeinfo(gid, nbranch, ncompart, ntype)
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
      targid = (i+1)%ncell + self.gidstart
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
    hg.g = 0.003 # do not randomize as must be same for other side of gap
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

def spikeout():
  #to out<nhost>.dat file
  global tvec, idvec
  pc.barrier()
  fname = 'out%d.dat'%nhost
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
    if rank == 0: print '%gs %s'%((x - _timeit), message)
    _timeit = x

if __name__ == '__main__':
  timeit(None)
  rings = [Ring(ncell, nbranch, ncompart, ntype, i*ncell) for i in range(nring)]
  print "typecellcnt [[type,cnt],...]", typecellcnt
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
  print "%d non-zero area compartments"%ns
  #h.topology()
  spike_record()
  if usegap:
    pc.setup_transfer()
  pc.set_maxstep(10)
  h.stdinit()
  timeit("initialized")
  pc.nrnbbcore_write("dat")
  timeit("wrote coreneuron data")
  pc.psolve(tstop)  
  timeit("run")
  spikeout()
  timeit("wrote %d spikes"%len(tvec))

  if nhost > 1:
    pc.barrier()
    h.quit()
