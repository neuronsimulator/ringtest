#!/bin/bash
set -e

function run() { # nhost nthread coreneuron
    cmd="mpiexec -n $1 nrniv -mpi -python ringtest.py -nt $2 $3 tstop 200 \
 -npt 1000000 -branch 20 20 -permute 1 -nring 16 -ncell 80"
    echo "$cmd"
    $cmd >& temp1
    rtime=`sed -n "/^runtime=/s/^/$1 $2 $3 /p" < temp1`
    echo "$rtime"
    echo "$rtime" >> temp
}

function runbunch() {
    rm -r -f arm64
    nrnivmodl -coreneuron mod
    nrniv --version >> temp
    for nhost in 1 2 4 ; do
        for nthread in 1 2 4 ; do
            let "a = $nhost * $nthread"
            if (( $a > 4 )) ; then
                continue
            fi
            for coreneuron in "" "-coreneuron" ; do
                run "$nhost" "$nthread" "$coreneuron"
            done
        done
    done
}

rm -f temp

function runall() {
    for v in "nrn" "datahandle" ; do
        source $HOME/neuron/prefixenv $v/build/install
        runbunch
    done
    python3 perfanal.py
}

runall
