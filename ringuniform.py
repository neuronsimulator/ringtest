nring=64
ncell=8 # number of cells per ring

nsomachild = 16
nbranch = 64 

print "nring=%d\ncell per ring=%d"%(nring, ncell)

tstop=100
randomize_parameters = False

from neuron import h
h.load_file('nrngui.hoc')
pc = h.ParallelContext()
rank = int(pc.id())
nhost = int(pc.nhost())
#from cell import BallStick
h.load_file("celluniform.hoc")

class Ring(object):

  def __init__(self, ncell, nbranch, gidstart):
    #print "construct ", self
    self.gids = []
    self.delay = 1
    self.ncell = int(ncell)
    self.gidstart = gidstart
    self.mkring(self.ncell, nbranch, nsomachild)
    self.mkstim()

  def mkring(self, ncell, nbranch, nsomachild):
    self.mkcells(ncell, nbranch, nsomachild)
    self.connectcells(ncell)

  def mkcells(self, ncell, nbranch, nsomachild):
    global rank, nhost
    self.cells = []
    for i in range(rank + self.gidstart, ncell + self.gidstart, nhost):
      gid = i
      self.gids.append(gid)
      cell = h.B_BallStick(nbranch, nsomachild)
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
      self.mk_con(gid, targid)

  def mk_con(self, gid, targid):
    if pc.gid_exists(targid):
      target = pc.gid2cell(targid)
      syn = target.synlist[0]
      nc = pc.gid_connect(gid, syn)
      self.nclist.append(nc)
      nc.delay = self.delay
      nc.weight[0] = 0.01

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
  rings = [Ring(ncell, nbranch, i*ncell) for i in range(nring)]
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
