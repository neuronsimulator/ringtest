## Old Instructions

These are old instructions for Lugano Vizcluster at BBP :

```
nrniv -python ringtest.py # one thread
mpiexec -n 4 nrniv -mpi -python ringtest.py # 4 threads

nrngui spkplt.hoc #plots out.std

# coreneuron build
cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/bb/install -DENABLE_OPENACC=OFF

export PATH=$HOME/bb/install/bin:$PATH
export LD_LIBRARY_PATH=$HOME/bb/install/lib

# run as
coreneuron_exec -d dat --celsius=6.3 --tstop=100 --cell_permute
```


#### For vizcluster with GPU and PG compiler

* Allocate node on vizcluster (need to use perfengineering queue) which
has PGI compiler license that I have installed:
```
salloc --reservation perftest --account=proj16 -N 1 -n 2 --time=9:00:00 --nodelist=bbpviz036 -p interactive
```
* Remove all modules and use the PGI module that I have installed:
```
module purge
export MODULEPATH=/gpfs/bbp.cscs.ch/home/kumbhar/workarena/systems/lugviz/softwares/install/compilers/modulefiles:$MODULEPATH 
module load PrgEnv-pgi/16.4
```

* Install mod2c
* I have forked sandbox/hines/pg-acc and made some modifications in: sandbox/kumbhar/pg-acc
* Build and install the mod2c sandbox/kumbhar/pg-acc branch using default compilers (gcc)
* Install CoreNeuron
* I forked sandbox/hines/pg-acc and made some modifications: sandbox/kumbhar/pg-acc

```
export CC=mpicc
export CXX=mpicxx

cmake ..  -DCMAKE_INSTALL_PREFIX=/gpfs/bbp.cscs.ch/home/hines/bbgpu/install_viz \
--DCMAKE_C_FLAGS:STRING="-I/gpfs/bbp.cscs.ch/apps/viz/tools/pgi/15.10/linux86-64/2015/include -acc -Minfo=acc -Minline=size:200,levels:10  -O3 -DSWAP_ENDIAN_DISABLE_ASM -DLAYOUT=0 -DDISABLE_HOC_EXP" -DCMAKE_CXX_FLAGS:STRING="-I/gpfs/bbp.cscs.ch/apps/viz/tools/pgi/15.10/linux86-64/2015/include -acc -Minfo=acc -Minline=size:200,levels:10 -O3 -DSWAP_ENDIAN_DISABLE_ASM -DLAYOUT=0 -DDISABLE_HOC_EXP" -DCOMPILE_LIBRARY_TYPE=STATIC
make && make install
```

There are two gpus on this node. So, if you set :

```
export CUDA_VISIBLE_DEVICES=0
export PGI_ACC_TIME=1 # print timeing
export PGI_ACC_TIME=0 # disable timing
export PGI_ACC_NOTIFY=1 # print kernel launch notifications at run time, 2 means when data movement
mpirun -n 1 coreneuron_exec -d tests/integration/ring -e 1 --gpu -r -mpi
```

http://www.pgroup.com/doc/openacc_gs.pdf  page 36