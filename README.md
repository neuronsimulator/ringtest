# Using CoreNEURON with NEURON

## Introduction

This tutorial shows how to build simple network model using [NEURON](https://www.neuron.yale.edu/neuron/) and simulating it using [CoreNEURON](https://github.com/BlueBrain/CoreNeuron).

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

Note that we are using NEURON github mirror repository. You can also clone mercurial repository from [neuron.yale.edu](http://neuron.yale.edu/neuron/download/getdevel).

###### Changes in NEURON
For this tutorial, in order to support GPU platform, we have to modify Hodgkin–Huxley model in NEURON (**i.e. hh.mod**). (note that this doesn't change any behaviour of model itself).

```bash
cd nrn
sed -i -e 's/GLOBAL minf/RANGE minf/g' src/nrnoc/hh.mod
sed -i -e 's/TABLE minf/:TABLE minf/g' src/nrnoc/hh.mod
```
> NOTE : We are disabling use of **TABLE** statements and replacing **GLOBAL** variables with **RANGE**). This will be transparently handle by NEURON and CoreNEURON in near future.

##### Installation

Once you clone the repositories and made above mentioned changes, you can install NEURON, MOD2C and CoreNEURON as described below. Make sure to have MPI installed (or in $PATH) if you want to enable parallel version.

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

Install NEURON with standard instructions provided on [neuron.yale.edu](http://neuron.yale.edu/neuron/download/getdevel). For example, typical neuron installation without GUI is:

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

Once above packages are installed make sure to set `PATH` and `MODLUNIT` environmental variables:

```
export PATH=$INSTALL_DIR/x86_64/bin:$INSTALL_DIR/bin:$PATH
export MODLUNIT=$INSTALL_DIR/share/nrnunits.lib
```

Now we will start building `ringtest` model. Clone the github repository as:

```bash
cd $SOURCE_DIR
git clone https://github.com/pramodk/ringtest.git
cd ringtest && git checkout tutorial
```

This repository contains `mod` sub-directory which has MOD files (for gap-juction related test). Using standard NEURON workflow, we can build `special` executable using `nrnivmodl` as:

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

This will run NEURON for `100 milliseconds` and writes spike output to `coreneuron_data/spk1.std` file.

These are standard steps for running simulations with NEURON (which you are already familiar with). We will now look into additional details for using CoreNEURON.

The `ringtest.py` has following code section :

```
# write intermediate dataset for coreneuron
pc.nrnbbcore_write(folder)

# run simulation using NEURON
runtime, load_balance, avg_comp_time, spk_time, gap_time = prun(tstop)
```

`ParallelContext` object in NEURON has new method called `nrnbbcore_write`. We have to call this method once we build the model using `Python` / `HOC` interface of NEURON. `nrnbbcore_write` method dumps in-memory network model to binary files in specified directory (`coreneuron_data ` in previous command). Once this model is dumped to file, CoreNEURON can read and continue simulation of the model.

> NOTE : typically only change in your exisiting Python / HOC scripts will be an additional call to pc.nrnbbcore\_write("directory_name"). 

> NOTE : you should comment out call to pc.psolve(time) (unless you want to run simulations using NEURON and compare the results with CoreNEURON).

Note that in `ringtest.py` has `prun` method which internally calls ` pc.psolve(tstop)`. This will simulate model using `NEURON`. If you just want to build model using NEURON and simulate with `CoreNEURON` then you can comment out `prun` function call (and `print` messages at the end of the file).

Once you run NEURON and dataset is generated, we can run CoreNEURON for simulating the model.

Similar to `special` in NEURON, we have to build CoreNEURON executable:

```bash
cd $SOURCE_DIR/ringtest
mkdir -p coreneuron_x86 && cd coreneuron_x86
cmake $BASE_DIR/sources/CoreNeuron -DADDITIONAL_MECHPATH=`pwd`/mod
make -j
```

This will create `coreneuron_exec ` executable under `coreneuron_x86/bin/`. Note that we have to use `-DADDITIONAL_MECHPATH` argument with the directory path of `mod` files (otherwise CoreNEURON will be built with only internal MOD files).

> NOTE : You have to recompile CoreNEURON (using `cmake` / `make`) if you change/add MOD files. This is similar to building new `special` with `nrnivmodl`.

Now we can run simulation using `CoreNEURON` as:

```bash
cd $SOURCE_DIR/ringtest
./coreneuron_x86/bin/coreneuron_exec -e 100 -d coreneuron_data
```

The `-e` specify stop time for simulation in milliseconds and `-d` is path for intermediate model dumped by `NEURON`. The spike output will be written to `out0.dat` file.

If you have run model with NEURON, you can compare `NEURON` and `CoreNEURON` spikes as :

```bash
diff -w out0.dat coreneuron_data/spk1.std
```
The spikes should be identical between NEURON and CoreNEURON.

Here is complete build and run script that we used for testing :

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
cmake $BASE_DIR/sources/CoreNeuron -DADDITIONAL_MECHPATH=`pwd`/mod
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


## Running Parallel Simulations

For running simulations on cluster or supercomputing platform, the workflow remains same (described above). But you have to consider some additional details described below:

* Suppose you want to use `N` cores on your cluster.
* Run NEURON with `N` mpi ranks (this will generate `N` sub-datasets inside specific directory)
* Now launch CoreNEURON with `N` mpi ranks and `1` OpenMP thread per rank (`pure-mpi` mode). OR, you can launch `X` threads per rank and `N`/ `X` MPI ranks.


For example, we launch parallel simulation using `4 mpi ranks` with NEURON as :

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

Note that each rank of CoreNEURON writes separate spike output file. You have to combine and sort the spikes :

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

> NOTE : Make sure to delete all intermediate spike output files before starting new simulation.

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

###### If you see compilation / runtime errors

Some models (MOD files) need slight modifications if they are using certain constructs (e.g. use of **POINTER** variables). We will be happy to have a look and help you get started. Send an email to Michael Hines and Pramod Kumbhar.


## Performance Benchmarking

Here are some additional points if you want to compare performance between NEURON and CoreNEURON :

* Make sure to use optimization flags depending upon your compiler suite (see [CoreNEURON page](https://github.com/BlueBrain/CoreNeuron))
* Prefer Intel/Cray/PGI compilers over GCC (specifically for CoreNEURON to enable vectorisation and other optimizations)
* Your problem should be sufficiently large and not just small trivial test. For example, in the above tutorial, we built small network with 16 rings each with 8 cells. You can build larger network using additonal command line arguments as :
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