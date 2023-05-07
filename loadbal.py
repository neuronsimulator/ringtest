# Utilities for (mostly thread) load balance

from neuron import h

pc = h.ParallelContext()

h.load_file("loadbal.hoc")
lb = h.LoadBalance()


def write_exper_mech_complex():
    """Create mcomplex.dat file that contains relative performance
    weights ("hh" is 5) for empty compartment, POINT_PROCESS, and SUFFIX
    mechanisms to aid in calculation of expected relative cell simulation
    time for load balance. This method destroys existing Sections!
    """
    lb.ExperimentalMechComplex()  # destroys existing Sections!


def read_exper_mech_complex():
    """Read mcomplex.dat file for use as complexity proxy for load balance.
    Without this the complexity proxy for a cell is approximately the number
    of compartments, mechanism states, and ions in a cell.
    """
    try:
        f = open("mcomplex.dat", "r")
        f.close()
        lb.read_mcomplex()
    except:
        if pc.id() == 0:
            print(
                'No (valid) mcomplex.dat file. Using number of state as complexity proxy. Run "python loadbal.py"'
            )


def do_whole_cell_thread_balance():
    """For all cells on this rank, partition them in a load balanced
    fashion on the pc.nthread() threads.
    """
    # Following is not normal use of h.LoadBalance.
    # Need to set lb.srlist to a List of this ranks root sections
    # in order to call lb.thread_partition
    sl = h.SectionList()
    sl.allroots()
    srlist = h.List()
    for s in sl:
        srlist.append(h.SectionRef(sec=s))
    lb.srlist = srlist

    lb.thread_partition(0)  # 1 would print some results

    print(
        "LPT rank %d: %d pieces  expected balance %.1f%%"
        % (pc.id(), lb.npiece_, (1.0 / lb.thread_cxbal_) * 100)
    )
    return lb


def expected_whole_cell_thread_balance():
    """For the existing thread partitions, what is the expected balance."""
    h.finitialize()  # make sure thread partitions defined
    nhost = pc.nhost()
    nth = pc.nthread()
    # threads for this rank
    cxpart = [0.0 for _ in range(nth)]
    sl = [pc.get_partition(i) for i in range(nth)]
    cxmax = 0
    ncell = 0
    for ith, seclist in enumerate(sl):
        for i, sec in enumerate(seclist):
            cx = lb.cell_complexity(sec=sec)
            cxpart[ith] += cx
            cxmax = cx if cxmax < cx else cxmax
            ncell += 1

    # gather cxpart, etc from all ranks onto rank 0
    info = pc.py_gather((cxpart, cxmax, ncell, nth), 0)
    if info is not None:
        nth = 0
        ncell = 0
        cxmax = 0
        cxpart = []
        for i in info:
            nth += i[3]
            ncell += i[2]
            cxmax = i[1] if cxmax < i[1] else cxmax
            cxpart.extend(i[0])

        avgcell = sum(cxpart) / ncell
        maxcell = cxmax
        avgpart = sum(cxpart) / nth
        maxpart = max(cxpart)
        bal = avgpart / maxpart if maxpart else 1.0

    if pc.id() == 0:
        print(
            "For existing thread partitions, expected load balance is %.1f%%"
            % (bal * 100,)
        )
        print("    %d nhost  total %d threads  %d pieces" % (nhost, nth, ncell))
        print("    cell   complexity average=%g   max=%g" % (avgcell, maxcell))
        print("    thread complexity average=%g   max=%g" % (avgpart, maxpart))


def act(args):
    read_exper_mech_complex()
    if pc.nhost() > 1:
        # the complicated case. Requires figuring out the proper rank
        # partitions and rebuilding the network. But at least can
        # figure out the expected round-robin balance.
        expected_whole_cell_thread_balance()
    elif pc.nthread() > 1:
        # what is the present round-robin balance
        expected_whole_cell_thread_balance()
        # repartition the threads for loadbalance
        do_whole_cell_thread_balance()


def load_balance():
    # load balance defined as avgtime/maxtime
    thread_times = [pc.thread_ctime(i) for i in range(pc.nthread())]
    sum_thread_time = sum(thread_times)
    max_thread_time = max(thread_times)
    num_threads = pc.nthread()

    sum_thread_time = pc.allreduce(sum_thread_time, 1)
    max_thread_time = pc.allreduce(max_thread_time, 2)
    num_threads = pc.allreduce(num_threads, 1)

    avg_thread_time = sum_thread_time / num_threads
    ldbal = avg_thread_time / (max_thread_time if max_thread_time else 1.0)

    if pc.id() == 0:
        print(
            "%d total threads: bal=%.1f%% avg=%gs max=%gs"
            % (num_threads, ldbal * 100, avg_thread_time, max_thread_time)
        )


if __name__ == "__main__":
    write_exper_mech_complex()
