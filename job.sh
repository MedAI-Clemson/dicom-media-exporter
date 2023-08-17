# Job script for running Clemson University Palmettto Cluster
#PBS -N dme_test
#PBS -l select=1:ncpus=32:mem=128gb:interconnect=hdr,walltime=4:00:00
#PBS -j oe
#PBS -o logs/log.txt

module load anaconda3/2022.05-gcc
module load ffmpeg/4.4.1-gcc
source activate dme

cd ~/Code/dme
python dme.py config.yml