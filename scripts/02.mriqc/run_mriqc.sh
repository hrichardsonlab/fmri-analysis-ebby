#!/bin/bash

################################################################################
# RUN MRIQC ON BIDS FORMATTED DATA
#
# The MRIQC singularity was installed using the following code:
# 	SINGULARITY_TMPDIR=/RichardsonLab/processing SINGULARITY_CACHEDIR=/RichardsonLab/processing sudo singularity build /RichardsonLab/processing/singularity_images/mriqc-24.0.0.simg docker://nipreps/mriqc:24.0.0
#
################################################################################

# usage documentation - shown if no text file is provided or if script is run outside RichardsonLab directory
Usage() {
	echo
	echo
	echo "Usage:"
	echo "./run_mriqc.sh <list of subjects>"
	echo
	echo "Example:"
	echo "./run_mriqc.sh KMVPA_subjs.txt"
	echo
	echo "KMVPA_subjs.txt is a file containing the participants to run MRIQC on:"
	echo "001"
	echo "002"
	echo "..."
	echo
	echo
	echo "This script must be run within the /RichardsonLab/ directory on the server due to space requirements."
	echo "The script will terminiate if run outside of the /RichardsonLab/ directory."
	echo
	echo "Script created by Melissa Thye"
	echo
	exit
}
[ "$1" = "" ] && Usage

# if the script is run outside of the RichardsonLab directory (e.g., in home directory where space is limited), terminate the script and show usage documentation
if [[ ! "$PWD" =~ "/RichardsonLab/" ]]; 
then Usage
fi

# define directories
projDir=`cat ../../PATHS.txt`
singularityDir="${projDir}/singularity_images"

# define subjects from text document
subjs=$(cat $1) 

# extract study name from list of subjects filename
study=` basename $1 | cut -d '_' -f 1 `

# define data directories depending on study information
bidsDir="/RichardsonLab/preprocessedData/${study}"
qcDir="${bidsDir}/derivatives/mriqc"

# create QCdirectory if they don't exist
if [ ! -d ${qcDir} ]
then 
	mkdir -p ${qcDir}
fi

# change the location of the singularity cache ($HOME/.singularity/cache by default, but limited space in this directory)
export SINGULARITY_TMPDIR=${singularityDir}
export SINGULARITY_CACHEDIR=${singularityDir}
unset PYTHONPATH

# display subjects
echo
echo "Running MRIQC for..."
echo "${subjs}"

# run MRIQC (https://mriqc.readthedocs.io/en/latest/running.html#singularity-containers)
## generate subject reports
singularity run -B /RichardsonLab:/RichardsonLab	\
${singularityDir}/mriqc-24.0.0.simg					\
${bidsDir} ${qcDir}									\
participant											\
--participant_label ${subjs}						\
--no-sub 											\
--fd_thres 1										\
-m T1w bold 										\
-w ${singularityDir}

## generate group reports
singularity run -B /RichardsonLab:/RichardsonLab	\
${singularityDir}/mriqc-24.0.0.simg					\
${bidsDir} ${qcDir}									\
group 												\
-m T1w bold

# remove hidden files in singularity directory to avoid space issues
# rm -r ${singularityDir}/.bids*

