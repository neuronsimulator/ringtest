# Using CoreNEURON with NEURON

## Introduction

This tutorial shows how to build a simple network model using [NEURON](https://www.neuron.yale.edu/neuron/) and simulating it using [CoreNEURON](https://github.com/BlueBrain/CoreNeuron).

## Installation

For up to date NEURON installation instructions with CoreNEURON, see [documentation here](https://github.com/neuronsimulator/nrn/blob/master/docs/coreneuron/installation.rst). As CoreNEURON rely on auto-vectorisation compiler, make sure to use vendor compilers like Intel, Cray, AMD, NVIDIA HPC SDK.

Once NEURON is installed, and you set `PATH` and `PYTHONPATH` environmental variables then you should be able to do:

```
python -c "from neuron import h; from neuron import coreneuron"
```

If you get `ImportError` then make sure `PYTHONPATH` is set up correctly and `python` version is same as the one used for NEURON installation.

## Compile MOD files

Now we will start building the `ringtest` model. Clone the GitHub repository as:

```bash
git clone https://github.com/nrnhines/ringtest.git
cd ringtest
```

This repository contains a `mod` sub-directory which has MOD files (for the gap-junction related test). Using the standard NEURON workflow, we can build a `special` executable using `nrnivmodl` and `-coreneuron` option. Make sure to load necessary compiler and MPI modules:

```bash
nrnivmodl -coreneuron mod
```

This will create `x86_64/special` executable in the `ringtest` directory (where `x86_64` is platform architecture).


## Make Model CoreNEURON Compatible

As described in the [documentation here](https://github.com/neuronsimulator/nrn/blob/master/docs/coreneuron/how-to/coreneuron.md), one may have to make minor modifications to make a model compatible with CoreNEURON.
In `ringtest.py`, the relevant changes have already been made:
```python
h.cvode.cache_efficient(1)
if use_coreneuron:
    from neuron import coreneuron
    coreneuron.enable = True
    coreneuron.gpu = coreneuron_gpu
```
so the `-coreneuron` (`use_coreneuron`) and `-gpu` (`coreneuron_gpu`) arguments can be used to enable CoreNEURON.

By using `coreneuron` module, one can enable CoreNEURON as shown above. Note that CoreNEURON requires NEURON's internal data structures to be in cache efficient form and hence the `cvode.cache_efficient(1)` method must be executed prior to initialization of the model i.e. `h.stdinit()`.

## Running Simulation

We are ready to run this model using NEURON or CoreNEURON. To run with NEURON, you can do:

```bash
mpiexec -n 2 ./x86_64/special -mpi -python ringtest.py -tstop 100
```

This will run NEURON for `100 milliseconds` using 2 MPI processes and writes spike output to the `spk2.std` file. These are standard steps for running simulations with NEURON (which you are already familiar with).

Note that `ringtest.py` has a `prun` method which internally calls ` pc.psolve(tstop)`. If `coreneuron.enable` is set to `True` then NEURON will internally use CoreNEURON to simulate the model. We can now use `-coreneuron` CLI parameter to run the model using CoreNEURON as:

```bash
mpiexec -n 2 ./x86_64/special -mpi -python ringtest.py -tstop 100 -coreneuron
```

This will run simulation using CoreNEURON for `100 milliseconds` and writes spike output to the `spk2.std` file. If you compare the spikes generated by NEURON run and CoreNEURON run then should be identical. Make sure to sort spikes using `sortspike` command provided by NEURON:

```
sortspike spk2.std spk2.coreneuron.std
```

#### Running on GPUs

If you have compiled NEURON+CoreNEURON with GPU support, you can run the model on GPU using `-gpu` CLI option:

```bash
mpiexec -n 2 ./x86_64/special -mpi -python ringtest.py -tstop 100 -coreneuron -gpu
```

We typically use the number of MPI ranks per node equal to the number of GPUs per node. So, if you have `X` number of nodes where each node has `Y` GPUs then the total number of MPI ranks are `X x Y`.

#### Using Threads

NEURON uses `PThread` to support threading whereas CoreNEURON uses OpenMP. In order to enable thread usage you have to set appropriate number of threads using [ParallelContext.nthread()](https://www.neuron.yale.edu/neuron/static/py_doc/modelspec/programmatic/network/parcon.html#ParallelContext.nthread). With this, if you run simulation using CoreNEURON, for each thread on NEURON side CoreNEURON will create an equivalent OpenMP thread. With this ring test we have CLI option `-nt` that you can use to enable threads:

```bash
mpiexec -n 2 ./x86_64/special -mpi -python ringtest.py -tstop 100 -coreneuron -nt 2
```

With `-nt 2`, each MPI process will start 2 OpenMP threads on CoreNEURON side for simulation.


## Performance Benchmarking

Here are some additional points if you want to compare performance between NEURON and CoreNEURON :

* Make sure to use optimization flags depending upon your compiler suite (see [CoreNEURON page](https://github.com/BlueBrain/CoreNeuron))
* Prefer Intel/Cray/PGI compilers over GCC and Clang (specifically for CoreNEURON to enable vectorisation)
* In order to compare performance, your model should be sufficiently large (and not a trivial test). For example, in the above tutorial, we built a small network with 16 rings each with 8 cells. You can build a larger network using additional command line arguments as:

```bash
mpirun -n 4 ./x86_64/special -mpi -python ringtest.py -tstop 100 -nring 1024 -ncell 128 -branch 32 64
```

See command line arguments for more information about arguments:

```bash
→ python ringtest.py -h
usage: ringtest.py [-h] [-nring N] [-ncell N] [-npt N] [-branch N N]
                   [-compart N N] [-tstop float] [-gran N] [-rparm]
                   [-filemode] [-gpu] [-show] [-gap] [-coreneuron] [-nt N]
                   [-multisplit]

optional arguments:
  -h, --help    show this help message and exit
  -nring N      number of rings (default 16)
  -ncell N      number of cells per ring (default 8)
  -npt N        number of cells per type (default 8)
  -branch N N   range of branches per cell (default 10 20)
  -compart N N  range of compartments per branch (default [1,1])
  -tstop float  stop time (ms) (default 100.0)
  -gran N       global Random123 index (default 0)
  -rparm        randomize parameters
  -filemode     Run CoreNEURON with file mode
  -gpu          Run CoreNEURON on GPU
  -show         show type topologies
  -gap          use gap junctions
  -coreneuron   run coreneuron
  -nt N         nthread
  -multisplit   intra-rank thread balance. All pieces of cell on same rank.
```

##### Sample Performance Test

In order to compare the performance of NEURON and CoreNEURON, we compiled both simulators using Intel compilers. Note that the ringtest is not ideal for benchmarking due to low comutational complexity of each cell (`cell.hoc` uses `HH` channel in soma compartment).

**NOTE** : When you run simulation using NEURON and call `pc.psolve(tstop)`, it will directly start execution of timesteps. But in case of CoreNEURON, when you call `pc.psolve(tstop)`, NEURON will internally do the following steps:

1. Copy in-memory model to CoreNEURON
2. CoreNEURON will copy data to GPU if GPU is enabled
3. CoreNEURON will run timesteps
4. CoreNEURON will copy back results from CPU to GPU if GPU is enabled
5. NEURON will copy results back from CoreNEURON

These steps are typically fast but if you are running a very small model for short duration then you might see an overhead. So make sure to check timing stats printed by CoreNEURON. For example, CoreNEURON prints simulation time (i.e. Step 3) in the form of `Solver Time : X Seconds`.

For comparison of NEURON and CoreNEURON performance, here are some executions with NEURON and CoreNEURON running on single core:

```bash
# NEURON CPU Run
$ mpiexec -n 1 ./x86_64/special -mpi -python ringtest.py -tstop 10 -nring 128 -ncell 128 -branch 32 64
.........
runtime=20.86  load_balance=100.0%  avg_comp_time=20.8548
.......

# CoreNEURON CPU Run
$ mpiexec -n 1 ./x86_64/special -mpi -python ringtest.py -tstop 10 -nring 128 -ncell 128 -branch 32 64 -coreneuron
.........
Solver Time : 15.846
.........

# CoreNEURON GPU Run
$ mpiexec -n 1 ./x86_64/special -mpi -python ringtest.py -tstop 10 -nring 128 -ncell 128 -branch 32 64 -coreneuron -gpu
..........
Solver Time : 0.431226
..........
```

For above test the execution time is reduced from 174sec to 78sec for CPU and to 22.7sec for GPU. This speedup is still less than expected due to lower computational complexity of the model. But also note that we are running CPU execution with single core. Make sure to use all CPU resources for actual comparison. Try with your model and if you see any performance issues, please open an issue on [NEURON GitHub repository](https://github.com/neuronsimulator/nrn/issues/new).
