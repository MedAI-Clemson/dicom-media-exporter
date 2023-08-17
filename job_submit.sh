#!/bin/bash

jobname=dcm2vid_test
logfile=${jobname}.log
wrkdir=/home/$USER/Code/dcm2vid
ncpus=32
mem="125gb"
interconnect="hdr"
wt="02:00:00"

# With oversampling training data, lower weight decay
qsub -N $jobname -l select=1:ncpus=$ncpus:mem=$mem:interconnect=$interconnect,walltime=$wt \
    -j oe -o $wrkdir/$logfile \
    -- /bin/bash $wrkdir/job_def.sh --overwrite