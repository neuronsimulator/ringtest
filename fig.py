from select import data, select, select_metric, args

#print select('d.npt', 'd.solvetime', "d.permute == 1")
#print select('d.npt', 'd.solvetime', "d.permute == 2")

from neuron import h, gui
from math import log

def mk(args):
  mlist = args.m.split('|') if args.m != None else []
  klist = args.k.split('|') if args.k != None else []
  x = args.x
  selwords = args.sel.split() if args.sel else [d.permute, 1, 2]
  sellist = ["%s==%s"%(selwords[0], i) for i in selwords[1:]]
  
  results = []
  for m in mlist:
    for k in klist:
      for sel in sellist:
        result = select_metric(x, k, m, sel)
        if result != None:
          results.append(((x, k, m, sel), result))
        else:
          print "no result for ", x, k, m, sel
  return results

results = mk(args)
for r in results: print r[0]

def plot(result, g, mark, labels=[]):
  r = [(log(a, 2), b) for (a,b) in result]
  g.label(.3,.9,"", 2)
  for label in labels:
    g.label(label)
  for p in r:
    g.mark(p[0], p[1][2], mark, 8)
    g.mark(p[0], p[1][0], '-', 10, 1, 3)
    g.mark(p[0], p[1][1], '-', 10, 1, 3)
    if True:
      g.beginline(1,2)
      g.line(p[0], p[1][0])
      g.line(p[0], p[1][1])
      g.flush()
  g.exec_menu("View = plot")
  #g.size(0,5,0,20)


graphs = []
for r in  results:
  g = h.Graph()
  plot(r[1], g, "O", r[0])
  graphs.append(g)
