import argparse
import read 
from math import *

parser = argparse.ArgumentParser()

#some nrniv args need to be ignored
parser = argparse.ArgumentParser()
parser.add_argument("-g", metavar="'6/stdout*'", help='glob file pattern', required=True)
parser.add_argument("-x", metavar="'log(d.npt,2'", help='x parameter', required=True)
parser.add_argument("-k", metavar="'interleave'", help='| separated list of kernel patterns', default=None)
parser.add_argument("-m", metavar="metrics", help='| separated list of metrics', default=None)
parser.add_argument("-sel", metavar="'d.permute 1 2'", help='selector expression values', default=None)
args, unknown = parser.parse_known_args()

class Data():
  def __init__(self):
    pass

data = read.readall(Data, args.g)
for d in data:
  d.ntree = read.get(d, 'distinct tree topologies', int, 0)
  d.ncell = read.get(d, 'Number of cells', int, 3)
  d.solvetime = read.get(d, 'Solver Time', float, 3)
  d.permute = read.get(d, 'cell_permute:', int , 7, -1)
  d.nwarp = read.get(d, 'nwarp:', int , 9)
  d.npt = d.ncell/d.ntree

for d in data:
  d.metrics = read.get_metrics(d)
  d.profile = read.get_profile(d)

#list of (x,y) satisfying sel in increasing order of x
def select(x, y, sel):
  result = []
  for d in data:
    if eval(sel):
      result.append((eval(x), eval(y)))
  result.sort(cmp=lambda a,b: cmp(a[0], b[0]))
  return result

#list of (x,[min,max,avg]) for a specific kernal and metric
# that satisfies sel in increasing order of x
# error if kpat and mpat do not uniquely identify the kernal and metric
# name in a given data item.
def select_metric(x, kpat, mpat, sel):
  result = []
  for d in data:
    found=False
    if eval(sel):
      for k in d.metrics:
        if kpat in k[0]:
          for m in k[1]:
            if mpat == m[0]:
              if found:
                print "multiple selection in %s for %s and %s" % (d.fname,kpat,mpat)
                raise Exception
              found = True
              result.append((eval(x), m[1:]))
  result.sort(cmp=lambda a,b: cmp(a[0], b[0]))
  return result
