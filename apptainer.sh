SCRIPT_DIR="/home/dane2/Code/dcm2vid"
cd $SCRIPT_DIR
module load cuda/12.0.1-gcc
ls
apptainer exec --nv --bind \
    /project/rcde,/scratch/$USER,/zfs/wficai \
    /software/containers/pytorch/pytorch-ffmpeg_latest.sif \
    /bin/bash