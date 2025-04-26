#!/usr/bin/env bash

zfor=0
if [ "$1" == "zfor" ]; then
  zfor=1
fi

nrn_trace=1

mfile="hh2.cpp"
mfiles="$mfile"
arch="$(uname -m)"

# Decide whether SPLITFOR or NRN_TRACE need changing in hh2.cpp.
# if so change all the mfiles and run nrnivmodl

grep -q "#define SPLITFOR $zfor" $arch/$mfile
zfor_ok=$?
grep -q "#define NRN_TRACE 1" $arch/$mfile
trace_ok=$?

# sed -i slightly different between linux and darwin
if [[ $(uname -s) == "Darwin" ]]; then
  SEDI='sed -i ""'
else
  SEDI='sed -i'
fi
  
echo "SEDI |$SEDI|"

if [[ "$zfor_ok" == "1" || "$trace_ok" == "1" ]]; then
  for mf in $mfiles ; do
    echo "need to update $arch/$mf"
    $SEDI "s/#define SPLITFOR ./#define SPLITFOR $zfor/" $arch/$mf
    $SEDI "s/#define NRN_TRACE ./#define NRN_TRACE 1/" $arch/$mf
  done
  nrnivmodl mod
fi

`which nrniv` -python ringtest.py -npt 1 -compart 1 3 -nring 32 -rparm -nt 1
if [ "$zfor" == "1" ]; then
  cp spk1.std spk1.std.zfor
  cp temp.trace temp.trace.zfor
else
  cp spk1.std spk1.std.nozfor
  cp temp.trace temp.trace.nozfor
fi
