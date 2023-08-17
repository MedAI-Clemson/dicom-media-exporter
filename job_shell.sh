#!/bin/bash

jobname=dcm2vid_shell
logfile=${jobname}.log
wrkdir=/home/$USER/Code/dcm2vid
ncpus=4
mem="16gb"
interconnect='hdr'
wt="01:00:00"

# With oversampling training data, lower weight decay
qsub -I -N $jobname -v WD=$wrkdir -l select=1:ncpus=$ncpus:mem=$mem:interconnect=$interconnect,walltime=$wt