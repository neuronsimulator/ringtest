#!/bin/sh
sortspike $1 temp
diff -w $2/spk1.std temp
