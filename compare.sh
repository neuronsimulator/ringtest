#!/bin/sh
sortspike $1 temp1
sortspike $2 temp2
diff -w temp1 temp2
