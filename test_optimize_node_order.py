from neuron import h
import ringtest as rt

pc = rt.pc


def tst_optimize_node_order():
    model = rt.create_rings()

    from commonutils import tvec, idvec

    spikes = []
    for i in range(3):
        pc.optimize_node_order(i)
        h.stdinit()
        rt.runsim()
        spikes.append((tvec.c(), idvec.c()))
    print("nspike ", spikes[0][0].size())
    for i in range(1, 3):
        for j in range(2):
            assert spikes[i][j].eq(spikes[0][j])
    pc.optimize_node_order(0)


if __name__ == "__main__":
    tst_optimize_node_order()
    quit()
