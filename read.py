import sys, traceback
from glob import glob

def readall(Data, pat):
  data = []
  files = glob(pat)
  for fname in files:
    f = open(fname)
    lines = f.readlines()
    f.close()
    d = Data()
    d.fname = fname
    d.lines = lines
    data.append(d)
  return data

def get(data, pattern, typ, windex, st=0):
  x = None
  for line in data.lines:
    if pattern in line:
      try:
        x = line.split()[windex]
        if st < 0:
          x = x[0:st]
        else:
          x = x[st:]
        x = typ(x)
      except:
        print line.split()
        print x, st
        print sys.exc_info()[1]
        traceback.print_tb(sys.exc_info()[2])
        quit()
      return x
  return x

def ibegin(data, pattern):
  i = 0
  for line in data.lines:
    if pattern in line:
      break
    i += 1;
  return i

def get_metrics(data):
  result=[]
  i = ibegin(data, "Metric result:")
  prev = None
  kernel = None
  for line in data.lines[i+3:]:
    if len(line) < 2: break
    if 'Kernel:' in line:
      if prev != None:
        result.append([kernel, prev])
        prev = None
      kernel = line.split()[1]
    elif kernel != None:
      if prev == None:
        prev = []

      words = line.split()
      metric = [words[1]]

      for sval in words[-3:]:
        x = 0
        sval = sval.strip('smu%GB/')
        try:
          x = int(sval)
        except:
          x = float(sval)
        metric.append(x)

      prev.append(metric)

  if kernel != None and prev != None:
    result.append([kernel, prev])

  return result

def get_profile(data):
  result = {}
  i = ibegin(data, "Profiling result:")
  for line in data.lines[i+2]:
    words = line.split()
    if len(words) < 6:
      break
    kernel = " ".join(words[6:])
    sval = words[1]
    val = 0.0;
    if 'us' in sval:
      val = 1e-6*float(sval[0:-2])
    elif 'ms' in sval:
      val = 1e-3*float(sval[0:-2])
    else:
      val = 1e-3*float(sval[0:-1])
    result[kernel] = val;

  return result
