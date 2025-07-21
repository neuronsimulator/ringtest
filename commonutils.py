import errno
import os
from neuron import h
from pathlib import Path
from typing import List, Literal

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:    # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def voltageout(foldername, recordlist):
    for vec in recordlist:
        #print only last recorded
        print ("%s %g" % (vec.label(), vec.x[int(vec.size()) - 1]))
        #vec.printf()


def celltypeinfo(type, nbranch, ncompart):

    r = h.Random()
    r.Random123(type, 2)
    nb = int(r.discunif(nbranch[0], nbranch[1]))
    secpar = h.Vector(nb)
    segvec = h.Vector(nb)
    r.discunif(ncompart[0], ncompart[1])
    for i in range(nb):
        segvec.x[i] = int(r.repick())

    # nb branches and every branch has 0, 1, or 2 children
    # ie. no integer in secpar appears more than twice
    x = [[0, 0]]
    for i in range(1, nb):
        a = int(r.discunif(0, len(x) - 1))
        secpar.x[i] = x[a][0]
        x[a][1] += 1
        if x[a][1] > 1:
            x[a][0] = i
            x[a][1] = 0
        else:
            x.append([i, 0])

    #print type, secpar.to_python()
    return secpar, segvec

# for nhost independent type for gid
# shuffle elements of vec
def shuffle(vec, ran):
    n = len(vec) - 1
    for i in range(n + 1):
        ix = int(ran.discunif(i, n))
        vec[i], vec[ix] = vec[ix], vec[i]
    return vec


def spike_record():
    global tvec, idvec
    pc = h.ParallelContext()
    tvec = h.Vector(1000000)
    idvec = h.Vector(1000000)
    pc.spike_record(-1, tvec, idvec)


def spikeout(folder):
    #to out<nhost>.dat file
    global tvec, idvec
    pc = h.ParallelContext()
    rank = int(pc.id())
    nhost = int(pc.nhost())

    pc.barrier()

    fname = folder + '/spk%d.std' % nhost

    if rank == 0:
        f = open(fname, 'w')
        f.close()
    for r in range(nhost):
        if r == rank:
            f = open(fname, 'a')
            for i in range(len(tvec)):
                f.write('%g %d\n' % (tvec.x[i], int(idvec.x[i])))
            f.close()
        pc.barrier()


    timeit("wrote %d spikes%s" % (int(pc.allreduce(tvec.size(), 1)),
                                  ("" if nhost == 1 else " (unsorted)")), rank)


def timeit(message, rank):
    global _timeit
    if message == None:
        _timeit = h.startsw()
    else:
        x = h.startsw()
        if rank == 0:
            print ('%gs %s' % ((x - _timeit), message))
        _timeit = x


# function to register section-segment mapping with bbcore write
def setup_nrnbbcore_register_mapping(rings):

    #for recording
    recordlist = []

    pc = h.ParallelContext()

    #all rings in the simulation
    for ring in rings:

        #every gid in the ring
        for gid in ring.gids:

            #vector for soma sections and segment
            somasec = h.Vector()
            somaseg = h.Vector()

            #vector for dendrite sections and segment
            densec = h.Vector()
            denseg = h.Vector()

            #if gid exist on rank
            if (pc.gid_exists(gid)):

                #get cell instance
                cell = pc.gid2cell(gid)
                isec = 0

                #soma section, only pne
                for sec in [cell.soma]:
                    for seg in sec:
                        #get section and segment index
                        somasec.append(isec)
                        somaseg.append(seg.node_index())

                        #vector for recording
                        v = h.Vector()
                        v.record(seg._ref_v)
                        v.label("soma %d %d" % (isec, seg.node_index()))
                        recordlist.append(v)
                isec += 1

                #for sections in dendrite
                for sec in cell.den:
                    for seg in sec:
                        densec.append(isec)
                        denseg.append(seg.node_index())

                        #for recordings
                        v = h.Vector()
                        v.record(seg._ref_v)
                        v.label("dend %d %d" % (isec, seg.node_index()))
                        recordlist.append(v)
                    isec += 1

                #register soma section list
                pc.nrnbbcore_register_mapping(gid, "soma", somasec, somaseg)

                #register dend section list
                pc.nrnbbcore_register_mapping(gid, "dend", densec, denseg)

    return recordlist

def write_report_config(output_file, report_name, target_name, report_type, report_variable,
                        unit, report_format, target_type, dt, start_time, end_time, gids,
                        buffer_size=8, scaling: Literal["none", "area"] = "area"):
    """
    Writes the configuration for a report to a file. Check the docs here:
    
    https://sonata-extension.readthedocs.io/en/latest/sonata_simulation.html#reports
    """
    import struct
    num_gids = len(gids)
    report_conf = Path(output_file)
    report_conf.parent.mkdir(parents=True, exist_ok=True)
    with report_conf.open("wb") as fp:
        # Write the formatted string to the file
        fp.write(b"1\n")
        fp.write(("%s %s %s %s %s %s %d %lf %lf %lf %d %d %s\n" % (
            report_name,
            target_name,
            report_type,
            report_variable,
            unit,
            report_format,
            target_type,
            dt,
            start_time,
            end_time,
            num_gids,
            buffer_size,
            scaling
        )).encode())
        # Write the array of integers to the file in binary format
        fp.write(struct.pack(f'{num_gids}i', *gids))
        fp.write(b'\n')

def write_spike_config(output_file: str, spike_filename: str,
                       population_names: List[str], population_offsets: List[int]):
    report_conf = Path(output_file)
    num_population = len(population_names)
    with report_conf.open("a") as fp:
        fp.write(f"{num_population}\n")
        for pop_name, offset in zip(population_names, population_offsets):
            fp.write(f"{pop_name} {offset}\n")
        fp.write(f"{spike_filename}\n")

def write_sim_config(output_file, coredata_dir, report_conf, tstop):
    sim_conf = Path(output_file)
    sim_conf.parent.mkdir(parents=True, exist_ok=True)
    os.makedirs(coredata_dir, exist_ok=True)
    with sim_conf.open("w") as fp:
        fp.write("outpath=./\n")
        fp.write(f"datpath=./{coredata_dir}\n")
        fp.write(f"tstop={tstop}\n")
        fp.write(f"report-conf='{report_conf}'\n")
        fp.write("mpi=true\n")
