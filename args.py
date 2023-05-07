import argparse

parser = argparse.ArgumentParser()

# command line arguments

parser.add_argument("-nring",
                    metavar='N',
                    help="number of rings (default 16)",
                    type=int,
                    default=16)

parser.add_argument("-ncell",
                    metavar='N',
                    help="number of cells per ring (default 8)",
                    type=int,
                    default=8)

parser.add_argument('-npt',
                    metavar='N',
                    help="number of cells per type (default 8)",
                    type=int,
                    default=8)

parser.add_argument("-branch",
                    metavar='N',
                    nargs=2,
                    help="range of branches per cell (default 10 20)",
                    type=int,
                    default=[10, 20])

parser.add_argument("-compart",
                    metavar='N',
                    nargs=2,
                    help="range of compartments per branch (default [1,1])",
                    type=int,
                    default=[1, 1])

parser.add_argument("-outlier",
                    metavar='N',
                    nargs=2,
                    help="how many outliers with size scale (default [0,1])",
                    type=int,
                    default=[0, 1])

parser.add_argument("-tstop",
                    metavar='float',
                    help="stop time (ms) (default 100.0)",
                    type=float,
                    default=100.)

parser.add_argument("-gran",
                    metavar='N',
                    help="global Random123 index (default 0)",
                    type=int,
                    default=0)

parser.add_argument("-rparm",
                    dest='rparm',
                    action='store_true',
                    help="randomize parameters",
                    default=False)

parser.add_argument("-filemode",
                    dest='filemode',
                    action='store_true',
                    help="Run CoreNEURON with file mode",
                    default=False)

parser.add_argument("-dumpmodel",
                    dest='dumpmodel',
                    action='store_true',
                    help="Dump in memory model to file to coredat directory",
                    default=False)

parser.add_argument("-gpu",
                    dest='gpu',
                    action='store_true',
                    help="Run CoreNEURON on GPU",
                    default=False)

parser.add_argument('-permute',
                    metavar='N',
                    help="permute option for cell topology (default 0)",
                    type=int,
                    default=0)

parser.add_argument("-show", action='store_true', help="show type topologies", default=False)

parser.add_argument("-gap", action='store_true', help="use gap junctions", default=False)

parser.add_argument("-coreneuron", action='store_true', help="run coreneuron", default=False)

parser.add_argument("-nt", metavar='N', help="nthread", type=int, default=1)

parser.add_argument("-multisplit", action='store_true', default=False,
                   help="intra-rank thread balance. All pieces of cell on same rank.")

parser.add_argument("-loadbal", action='store_true', default=False,
                   help="whole cell mpi and thread balance")
