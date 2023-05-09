#f = open("perf-ncell-80-hh2.dat", "r")
f = open("temp", "r")
lines = f.read().splitlines()
f.close()
runtime=[]
nhost=[]
nthread=[]
corenrn = []
version = []
for line in lines:
    field = line.split()
    if "NEURON" in line:
        ver="master" if "master" in line else "soa"

    if "runtime" in line:
        runtime.append(float(field[-1].split("=")[1]))
        nhost.append(int(field[0]))
        nthread.append(int(field[1]))
        corenrn.append(1 if field[2] == "-coreneuron" else 0)
        version.append(ver)

table = {i:[i[0],i[1],0,0,0] for i in [(1,1), (1,2), (2,1), (1,4), (2,2), (4,1)]}

for i in range(len(runtime)):
    nh=nhost[i]
    nt = nthread[i]
    cn = corenrn[i]
    ver = version[i]
    rt = runtime[i]
    if cn == 1 and ver == "soa":
        continue
    if cn == 1:
        table[(nh,nt)][4] = rt
    elif ver == "soa":
        table[(nh,nt)][3] = rt
    elif ver == "master":
        table[(nh,nt)][2] = rt

print("nhost nthread master    soa     corenrn")
for i in table:
    val = table[i]
    print("  %d      %d    %-5g    %-5g     %-5g"
      %(val[0], val[1], val[2], val[3], val[4]))
