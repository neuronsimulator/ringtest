#!/bin/bash
set -e -x

# nrnivmodl mod
# nrniv -python  ringtest.py -rparm
# cmake .. -DADDITIONAL_MECHPATH=$HOME/models/ringtest/mod
# make -j

P='mpiexec -n 6 bin/coreneuron_exec -mpi'
P='bin/coreneuron_exec'
M=$HOME/models/ringtest

t_end=100
t_chkpt=50

CP=1

# standard spikes in $t_end ms
rm -rf out*.dat
$P -e $t_end -d $M/coredat --cell-permute $CP
cat out*.dat > temp
sortspike temp std${t_end}
diff -w $M/coredat/spk1.std std${t_end}

# checkpoint at $t_chkpt
rm -rf out*.dat
rm -rf checkpoint/*
$P -e $t_chkpt -d $M/coredat --cell-permute $CP --checkpoint checkpoint
cat out*.dat > temp
sortspike temp temp${t_chkpt}

# run checkpoint to $t_end
rm -rf out*.dat
$P -e $t_end -d $M/coredat --restore checkpoint --cell-permute $CP
cat out*.dat > temp
sortspike temp temp${t_chkpt}-${t_end}
cat temp${t_chkpt} temp${t_chkpt}-${t_end} > temp0-${t_end}
meld std${t_end} temp0-${t_end}
