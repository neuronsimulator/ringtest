# Example of how to construct a model as a series of submodels. Each
# submodel is built, CoreNEURON data is written, and the submodel
# is destroyed. This file can be run with
#    python test_submodel.py -rparm
# which writes data to the coredat folder. That folder can be compared to
# the corenrn_data folder written by
#    mpiexec -n 4 nrniv -python -mpi -rparm -coreneuron -filemode ringtest.py
#    diff -r coredat corenrn_data
# Note: -rparm is used for a more substantive test in that all the cells are
# distinct with differt parameters.

# The overall strategy for a ringtest model relies on the fact that it is
# already does parallel setup so that there are pc.nhost() submodels,
# one built on each rank, pc.id(). This setup did not use pc.nhost() or
# pc.id() directly but stored those values in the global variables nhost and
# rank respectively. So it is an easy matter to subvert that slightly and
# run with a single process and iterate over range(nsubmodel) and for each
# merely set rank and nhost to the proper values. The one exception to this
# in the ringtest setup was the call to pc.set_gid2node(gid, rank) which was
# changed to pc.set_gid2node(gid, pc.id()) since that function requires the
# true rank of this process to function correctly. The other ringtest
# transformation that was required was to factor out the ring build and
# randomization into functions that are callable from here as well as in
# the original ringtest.py .

from neuron import h
pc = h.ParallelContext()
cvode = h.CVode()

import ringtest

def test_submodel(nsubmodel):
  coredat = "./coredat"
  cvode.cache_efficient(1)
  gidgroups = [h.Vector() for _ in range(nsubmodel)] # used to write files.dat at end
  for isubmodel in range(nsubmodel):
    submodel = build_submodel(isubmodel, nsubmodel) # just like a single rank on an nhost cluster
    pc.nrnbbcore_write("./coredat",  gidgroups[isubmodel])
    teardown()
    submodel = None

    # verify no netcons or sections. Ready to go on to next submodel
    assert (h.List("NetCon").count() == 0)
    assert (len([s for s in h.allsec()]) == 0)

  write_files_dat(coredat, gidgroups)

def build_submodel(isubmodel, nsubmodel):
  # fake nhost and rank
  ringtest.settings.nhost = nsubmodel
  ringtest.settings.rank = isubmodel

  # broke into two parts to avoid timeit problems.
  rings= ringtest.network()
  ringtest.randomize(rings)

  # same initialization as ringtest
  pc.set_maxstep(10)
  h.stdinit()

  return rings

def teardown():
  pc.gid_clear()
  # delete your NetCons list
  # delete your Cells list
  # unfortunately, cannot delete submodel here as there is reference to it
  # in test_submodel(nsubmodel)

# write out the files.dat file
def write_files_dat(coredat, gidgroups):
  f = open(coredat+"/files.dat", "w")
  f.write("1.4\n") # CoreNEURON data version

  ng = sum(len(g) for g in gidgroups)
  f.write(str(ng) + '\n') # number of groups

  for gidgroup in gidgroups:
    for x in gidgroup:
      f.write(str(int(x)) + '\n') # group id

  f.close()

if __name__ == "__main__":
  test_submodel(4)
