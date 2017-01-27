class Data():
  def __init__(self, hash):
    self.hash = hash

data = []

f = open("temp", "r")
hashes = f.readline().split()
for i in hashes:
  data.append(Data(i))

for d in data:
  d.npt = int(f.readline().split()[1])

for d in data:
  d.fname = f.readline().split()[0]
  d.permute = int(f.readline().split()[1])
  assert(d.hash == f.readline().split()[1])
  d.solvetime = float(f.readline().split()[1])
  d.ncell = int(f.readline().split()[1])
  d.perf = f.readline()

f.close()

def select(x, y, sel):
  result = []
  for d in data:
    if eval(sel):
      result.append((eval(x), eval(y)))
  result.sort(cmp=lambda a,b: cmp(a[0], b[0]))

  return result

result = select("d.npt", "d.solvetime", "d.permute == 1")

from neuron import h, gui
from math import log
g = h.Graph()
def plot(result, g, mark):
  r = [(log(a, 2), b) for (a,b) in result]
  for p in r:
    g.mark(p[0], p[1], mark, 8)
  g.beginline(9,1)
  g.line(r[0][0], r[-1][1])
  g.line(r[-1][0], r[-1][1])
  g.flush()
  g.exec_menu("View = plot")
  g.size(0,5,0,25)

plot(result, g, "o")

result = select("d.npt", "float(d.perf.split()[1][0:-1])", "d.permute == 1")
plot(result, g, "O")

g2 = h.Graph()
plot(select("d.npt", "d.solvetime", "d.permute == 2"), g2, "o")
plot(select("d.npt", "float(d.perf.split()[1][0:-1])", "d.permute == 2"), g2, "O")

