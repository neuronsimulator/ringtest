# proportionally randomize all range parameters, weights, delays ...

from neuron import h
pc = h.ParallelContext()

def cellran(gid, nclist):
  r = h.Random()
  r.Random123(gid)
  r.uniform(1.0, 1.1)
  cell = pc.gid2cell(gid)

  for sec in cell.all:
    sec.L *= r.repick()
    for seg in sec:
      seg.diam *= r.repick()
      seg.cm *= r.repick()
      #print 'diam ', seg.diam, 'cm ', seg.cm

      #mechanism variables
      for mech in seg:
        ms = h.MechanismStandard(mech.name(), 1)
        for i in range(int(ms.count())):
          varname = h.ref("")
          sz = ms.name(varname, i)
          n = varname[0]
          x = seg.__getattribute__(n)
          seg.__setattr__(n, x * r.repick())
          #print n, seg.__getattribute__(n)

      #point process parameters
      for p in seg.point_processes():
        n = p.hname()
        n = n[:n.index('[')]
        ms = h.MechanismStandard(n, 1)
        for i in range(int(ms.count())):
          varname = h.ref("")
          ms.name(varname, i)
          x = p.__getattribute__(varname[0])
          p.__setattr__(varname[0], x * r.repick())
          #print varname[0], p.__getattribute__(varname[0])
  
  #netcons targeting the cell
  for nc in nclist:
    if nc.postcell() == cell:
      nc.weight[0] *= r.repick()
      nc.delay *= r.repick()


