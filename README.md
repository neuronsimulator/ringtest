# Using CoreNEURON with NEURON

## Introduction

This tutorial shows how to build a simple network model using [NEURON](https://www.neuron.yale.edu/neuron/) and simulating it using [CoreNEURON](https://github.com/BlueBrain/CoreNeuron).

## Features
Type of simulations currently supported by CoreNEURON :

* todo 1
* todo 2
* todo 3

##### Goals of CoreNEURON
* Simulating larger network models on modern supercomputing platforms
* Reduce memory footprint (5x-7x lower memory usage)
* Support for GPUs using OpenACC
* Efficient vectorisation and Memory layout support (AoS/SoA)
* todo 1

##### Limitations

* Only supports fixed time-step (no variable time-step support)
* No support for multi-split
* No support for HOC/Python scripting during execution time (you can use HOC/Python from NEURON to build models)
* todo 1

## Installation

This section provide instructions to install NEURON, CoreNEURON and dependencies. Note that these instructions are for standard `x86-linux` platform. See [CoreNEURON page](https://github.com/BlueBrain/CoreNeuron) and [NEURON page](http://neuron.yale.edu/neuron/download/getdevel) for information about other architectures like BG-Q, GPU etc.

#### Cloning repositories
In order to use NEURON and CoreNEURON together we have to download following repositories:

* [NEURON](https://github.com/nrnhines/nrn)
* [CoreNEURON](https://github.com/BlueBrain/CoreNeuron)
* [MOD2C](http://github.com/BlueBrain/mod2c)

Below are additional package dependecies :

* [CMake 2.8.12+](https://cmake.org) (3.5 for GPU systems)
* [MPI 2.0+](http://mpich.org) [optional, for parallel simulations]
* [PGI OpenACC Compiler >=16.3](https://www.pgroup.com/resources/accel.htm) [optional, for GPU systems]
* [CUDA >=6.0](https://developer.nvidia.com/cuda-toolkit-60) [optional, for GPU systems]


Here are github repositories:

```bash
https://github.com/BlueBrain/CoreNeuron.git
https://github.com/BlueBrain/mod2c.git
https://github.com/nrnhines/nrn.git
```

Note that we are using the NEURON github mirror repository. You can also clone using a mercurial repository from
[bitbucket](https://bitbucket.org/nrnhines/nrn) or [neuron.yale.edu](http://neuron.yale.edu/neuron/download/getdevel).  The latter often lags a few changesets behinde the former.

###### Changes in NEURON
For this tutorial, in order to support GPU platforms, we have to modify the Hodgkin–Huxley model in NEURON (**i.e. hh.mod**). (note that this doesn't change any behaviour of model itself).

```bash
cd nrn
sed -i -e 's/GLOBAL minf/RANGE minf/g' src/nrnoc/hh.mod
sed -i -e 's/TABLE minf/:TABLE minf/g' src/nrnoc/hh.mod
```
> NOTE : We are disabling use of **TABLE** statements and replacing **GLOBAL** variables with **RANGE**). This will be transparently handle by NEURON and CoreNEURON in the near future.

##### Installation

Once you clone the repositories and made the above mentioned changes, you can install NEURON, MOD2C and CoreNEURON as described below. Make sure to have MPI installed (or in $PATH) if you want to enable the parallel version.

> NOTE : full installation script is provided at the end of this section.

We will use following directory structure for installation :

```bash
export BASE_DIR=$HOME/coreneuron_tutorial
export INSTALL_DIR=$BASE_DIR/install
export SOURCE_DIR=$BASE_DIR/sources

# create directories
mkdir -p $INSTALL_DIR $SOURCE_DIR
```

Clone repositories as:

```bash
cd $SOURCE_DIR
git clone https://github.com/BlueBrain/CoreNeuron.git
git clone https://github.com/BlueBrain/mod2c.git
git clone https://github.com/nrnhines/nrn.git
```

###### Install NEURON

Install NEURON using standard instructions provided on [neuron.yale.edu](http://neuron.yale.edu/neuron/download/getdevel). For example, typical neuron installation without GUI is:

```bash
cd $SOURCE_DIR/nrn
sed -i -e 's/GLOBAL minf/RANGE minf/g' src/nrnoc/hh.mod
sed -i -e 's/TABLE minf/:TABLE minf/g' src/nrnoc/hh.mod
./build.sh
./configure --prefix=$INSTALL_DIR --without-iv --with-paranrn --with-nrnpython=`which python`
make && make install
```
For more information see [instructions](http://neuron.yale.edu/neuron/download/getdevel) on [neuron.yale.edu](http://neuron.yale.edu/neuron/).


###### Install MOD2C

```bash
cd $SOURCE_DIR/mod2c
mkdir -p build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$INSTALL_DIR
make && make install
```

Once above packages are installed, be sure to set `PATH` and `MODLUNIT` environmental variables:

```
export PATH=$INSTALL_DIR/x86_64/bin:$INSTALL_DIR/bin:$PATH
export MODLUNIT=$INSTALL_DIR/share/nrnunits.lib
```

Now we will start building the `ringtest` model. Clone the github repository as:

```bash
cd $SOURCE_DIR
git clone https://github.com/pramodk/ringtest.git
cd ringtest && git checkout tutorial
```

This repository contains a `mod` sub-directory which has MOD files (for the gap-junction related test). Using the standard NEURON workflow, we can build a `special` executable using `nrnivmodl` as:

```bash
cd $SOURCE_DIR/ringtest
nrnivmodl mod
```

This will create `x86_64/special` executable in the `ringtest` directory.

Now we are ready to run this model using `NEURON` as:

```bash
cd $SOURCE_DIR/ringtest
./x86_64/special -python ringtest.py -tstop 100 -coredat coreneuron_data
```

This will run NEURON for `100 milliseconds` and writes spike output to the `coreneuron_data/spk1.std` file.

These are standard steps for running simulations with NEURON (which you are already familiar with). We will now look into additional details for using CoreNEURON.

The `ringtest.py` has following code section :

```
# write intermediate dataset for coreneuron
pc.nrnbbcore_write(folder)

# run simulation using NEURON
runtime, load_balance, avg_comp_time, spk_time, gap_time = prun(tstop)
```

The `ParallelContext` object in NEURON has a new method called `nrnbbcore_write`. We have to call this method once we build the model using `Python` / `HOC` interface of NEURON. The `nrnbbcore_write` method dumps a copy of the in-memory network model to binary files in the specified directory (`coreneuron_data ` in previous command). Once this model is dumped to file, CoreNEURON can read and continue simulation of the model.

> Note : `nrnbbcore_write` requires that the NEURON's internal data structures be in cache efficient form and hence the `cvode.cache_efficient(1)` method must be executed prior to initialization of the model.

> NOTE : typically the only change in your existing Python / HOC scripts will be an additional call to pc.nrnbbcore\_write("directory_name").

> NOTE : you should comment out the call to pc.psolve(time) (unless you want to run simulations using NEURON and compare the results with CoreNEURON).

Note that `ringtest.py` has a `prun` method which internally calls ` pc.psolve(tstop)`. This will simulate the model using `NEURON`. If you just want to build the  model using NEURON and simulate with `CoreNEURON` then you can comment out `prun` function call (and `print` messages at the end of the file).

Once you run NEURON and the data files needed by CoreNEURON are generated, we can run CoreNEURON for simulating the model.

Similar to `special` in NEURON, we have to build CoreNEURON executable:

```bash
cd $SOURCE_DIR/ringtest
mkdir -p coreneuron_x86 && cd coreneuron_x86
cmake $BASE_DIR/sources/CoreNeuron -DADDITIONAL_MECHPATH=$SOURCE_DIR/ringtest/mod
make -j
```

This will create a `coreneuron_exec` executable under `coreneuron_x86/bin/`. Note that we have to use `-DADDITIONAL_MECHPATH` argument with the directory path for `mod` files (otherwise CoreNEURON will be built with only internal MOD files).

> NOTE : If MOD files, or any CoreNEURON files are change, coreneuron_exec needs to be recompiled and linked using
the `make` command. If MOD files are added rebuild using `cmake ; make`. This is similar to building a new `special` with `nrnivmodl`.

Now we can run the simulation using `CoreNEURON` as:

```bash
cd $SOURCE_DIR/ringtest
./coreneuron_x86/bin/coreneuron_exec -e 100 -d coreneuron_data
```

The `-e` specifies the stop time for a simulation in milliseconds and `-d` is the path to the intermediate model files dumped by `NEURON` when the `nrnbbcore_write` method was executed. The spike output will be written to an `out0.dat` file.

If you have run the model with NEURON, you can compare `NEURON` and `CoreNEURON` spikes as :

```bash
diff -w out0.dat coreneuron_data/spk1.std
```
The spikes should be identical between NEURON and CoreNEURON.

Here is the complete build and run script that we use for testing :

```bash
#!/bin/bash

# stop on error
set -e

# load required modiles on your cluster
# module load mpich cmake

export BASE_DIR=$HOME/coreneuron_tutorial
export INSTALL_DIR=$BASE_DIR/install
export SOURCE_DIR=$BASE_DIR/sources

# create directories
mkdir -p $INSTALL_DIR $SOURCE_DIR

# clone repositories

cd $SOURCE_DIR
git clone https://github.com/BlueBrain/CoreNeuron.git
git clone https://github.com/BlueBrain/mod2c.git
git clone https://github.com/nrnhines/nrn.git

# install neuron
cd $SOURCE_DIR/nrn
sed -i -e 's/GLOBAL minf/RANGE minf/g' src/nrnoc/hh.mod
sed -i -e 's/TABLE minf/:TABLE minf/g' src/nrnoc/hh.mod
./build.sh
./configure --prefix=$INSTALL_DIR --without-iv --with-paranrn --with-nrnpython=`which python`
make -j && make install

# install mod2c
cd $SOURCE_DIR/mod2c
mkdir -p build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$INSTALL_DIR
make -j && make install

# set path
export PATH=$INSTALL_DIR/x86_64/bin:$INSTALL_DIR/bin:$PATH
export MODLUNIT=$INSTALL_DIR/share/nrnunits.lib

# clone ring test
cd $SOURCE_DIR
git clone https://github.com/pramodk/ringtest.git
cd ringtest && git checkout tutorial

# build special executable with neuron
cd $SOURCE_DIR/ringtest
nrnivmodl mod

# build coreneuron executable
cd $SOURCE_DIR/ringtest
mkdir -p coreneuron_x86 && cd coreneuron_x86
cmake $BASE_DIR/sources/CoreNeuron -DADDITIONAL_MECHPATH=$SOURCE_DIR/ringtest/mod
make -j


# run simulation using neuron
cd $SOURCE_DIR/ringtest
./x86_64/special -python ringtest.py -tstop 100 -coredat coreneuron_data

# run simulation using coreneuron

cd $SOURCE_DIR/ringtest
./coreneuron_x86/bin/coreneuron_exec -e 100 -d coreneuron_data

# compare spike output between neuron and coreneuron
diff -w out0.dat coreneuron_data/spk1.std
```

## Building CoreNEURON with GPU support

CoreNEURON has support for GPU execution using OpenACC programming model when enabled with `-DENABLE_OPENACC=ON`. Note that you need working installation of PGI compiler with OpenACC support.
Here are the steps to compile with PGI compiler:

```bash
module purge                                #remove conflicting modules if any
module load pgi/pgi64/16.5 pgi/mpich/16.5   #change PGI / CUDA versions
module load cuda/6.0
export CC=mpicc
export CXX=mpicxx

cd $SOURCE_DIR/ringtest
mkdir -p coreneuron_x86_gpu && cd coreneuron_x86_gpu
cmake $BASE_DIR/sources/CoreNeuron -DADDITIONAL_MECHPATH=$SOURCE_DIR/ringtest/mod -DCMAKE_C_FLAGS:STRING="-O2" -DCMAKE_CXX_FLAGS:STRING="-O2" -DCOMPILE_LIBRARY_TYPE=STATIC -DCUDA_HOST_COMPILER=`which gcc` -DCUDA_PROPAGATE_HOST_FLAGS=OFF -DENABLE_SELECTIVE_GPU_PROFILING=ON -DENABLE_OPENACC=ON
make VERBOSE=1 -j
```

Note that the CUDA version should be compatible with PGI compiler. Otherwise you have to add extra C/C++ flags through CMake. For example, If we are using CUDA 7.5 but PGI default target is CUDA 7.0 then we add :

```bash
-DCMAKE_C_FLAGS:STRING="-O2 -ta=tesla:cuda7.5" -DCMAKE_CXX_FLAGS:STRING="-O2 -ta=tesla:cuda7.5"
```


## Running Parallel Simulations

For running simulations on a cluster or supercomputing platform, the workflow remains the same (described above). But you have to consider some additional details described below:

* Suppose you want to use `N` cores on your cluster.
* Run NEURON with `N` mpi ranks (this will generate `N` sub-datasets inside specific directory)
* Now launch CoreNEURON with `N` mpi ranks and `1` OpenMP thread per rank (`pure-mpi` mode). OR, you can launch `X` threads per rank and `N`/ `X` MPI ranks.


For example, if we launch a parallel simulation using `4 mpi ranks` with NEURON as :

```bash
mpirun -n 4 ./x86_64/special -mpi -python ringtest.py -tstop 100 -coredat coreneuron_data
```
Now launch CoreNEURON in `pure-mpi` mode as:

```
export OMP_NUM_THREADS=1
mpiexec -n 4 ./coreneuron_x86/bin/coreneuron_exec -e 100 -d coreneuron_data/ -mpi

```

Or with 2 `ranks` and 2 OpenMP `threads per mpi rank` as :

```
export OMP_NUM_THREADS=2
mpiexec -n 2 ./coreneuron_x86/bin/coreneuron_exec -e 100 -d coreneuron_data/ -mpi
```

Note that each rank of CoreNEURON writes a separate spike output file. You have to combine and sort the spikes :

```
cat out[0-9]*.dat | sort -k 1n,1n -k 2n,2n > out.spk.coreneuron
```

And compare spikes between NEURON and CoreNEURON :

```
# first sort neuron spikes
cat coreneuron_data/spk4.std | sort -k 1n,1n -k 2n,2n > out.spk.neuron

# compare neuron and coreneuron
diff -w out.spk.neuron out.spk.coreneuron

```

> NOTE : Make sure to delete all intermediate spike output files before starting a new simulation.

## Common Errors

###### If you see below error :

```
hh prop sizes differ psize 25 19   dpsize 6 6
Error: hh is different version of MOD file than the one used by NEURON!
```
This means your `hh.mod` is different between NEURON and CoreNEURON. Make sure to update `hh.mod` as described in `Installation` section.

###### If you see below error :

```
Set a MODLUNIT environment variable path to the units table file
Cant open units table in either of:
/usr/local/nrn/share/nrn/lib/nrnunits.lib../../share/lib/nrnunits.lib at line 13 in file stim.mod
UNITS {
```

This means you haven't set `MODLUNIT` environment variable. See Installation section.

###### If you see below error :

```
hoc.HocObject' has no attribute 'nrnbbcore_write
```

This means you are using older version of NEURON which doesn't support CoreNEURON. Download latest version from Github and compiler from source.

###### If you see below error :

```
Assertion failed: file nrnpy_nrn.cpp, line XXXX
/Users/wchen/coreneuron_tutorial/install/x86_64/bin/nrniv: sym && sym->type == RANGEVAR
```

Most likely multiple incompatible versions of NEURON are installed. Set `PYTHONPATH` or `LD_LIBRARY_PATH` correctly.

###### If you see compilation / runtime errors

Some models (MOD files) need slight modifications if they are using certain constructs (e.g. use of **POINTER** variables). We will be happy to have a look and help you get started. Send an email to Michael Hines and Pramod Kumbhar.


## Performance Benchmarking

Here are some additional points if you want to compare performance between NEURON and CoreNEURON :

* Make sure to use optimization flags depending upon your compiler suite (see [CoreNEURON page](https://github.com/BlueBrain/CoreNeuron))
* Prefer Intel/Cray/PGI compilers over GCC (specifically for CoreNEURON to enable vectorisation and other optimizations)
* Your problem should be sufficiently large and not just a small trivial test. For example, in the above tutorial, we built a small network with 16 rings each with 8 cells. You can build a larger network using additonal command line arguments as :
```
mpirun -n 4 ./x86_64/special -mpi -python ringtest.py -tstop 100 -coredat coreneuron_data -nring 1024 -ncell 128 -branch 32 64
```

See command line arguments for more information about arguments :

```

$ python ringtest.py -h
usage: ringtest.py [-h] [-nring N] [-ncell N] [-npt N] [-branch N N]
                   [-compart N N] [-tstop float] [-gran N] [-rparm]
                   [-secmapping] [-show] [-gap] [-nt N] [-coredat path]
                   [-coredathash]

optional arguments:
  -h, --help     show this help message and exit
  -nring N       number of rings (default 16)
  -ncell N       number of cells per ring (default 8)
  -npt N         number of cells per type (default 8)
  -branch N N    range of branches per cell (default 10 20)
  -compart N N   range of compartments per branch (default [1,1])
  -tstop float   stop time (ms) (default 100.0)
  -gran N        global Random123 index (default 0)
  -rparm         randomize parameters
  -secmapping    store section segment mapping
  -show          show type topologies
  -gap           use gap junctions
  -nt N          nthread
  -coredat path  folder for bbcorewrite hashname folders (default coredat)
  -coredathash   append argument's hash as a sub-directory to coredat
                 directory
```

##### Sample Performance Test

In order to compare the performance of NEURON and CoreNEURON, we compiled both simulators using Intel compilers. Note that the ringtest is not `ideal` for benchmarking due to low comutational complexity. Here are execution timings for running test on single core :

```bash

# NEURON CPU Run
$ ./x86_64/special -python ringtest.py -tstop 10 -coredat coreneuron_data -nring 128 -ncell 128 -branch 32 64
.........
runtime=174.74  load_balance=100.0%  avg_comp_time=174.746
.......

# CoreNEURON CPU Run
$ export OMP_NUM_THREADS=1
$ ./coreneuron_x86_cpu/bin/coreneuron_exec -e 10 -d coreneuron_data
.........
Solver Time : 78.0866
.........

# CoreNEURON GPU Run
$ ./coreneuron_x86_gpu/bin/coreneuron_exec -e 10 -d coreneuron_data --gpu --cell_permute=1
..........
Solver Time : 22.7115
..........
```

For above test the execution time is reduced from 174sec to 78sec for CPU and to 22.7sec for GPU. This speedup is still less than expected due to lower computational complexity of the model. (With the vectorization and efficient memory layout, we ideally expect about 4x speedup). Try with your model and if you see any performance issues, let us know.

> NOTE : Apart from execution time speedup, major advantage of CoreNEURON is reduction in memory usage. Depending upon model, CoreNEURON could run simulation with 5-7x less memory than NEURON.

