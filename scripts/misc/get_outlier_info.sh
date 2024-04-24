#!/bin/bash

################################################################################
# GET OUTLIER INFORMATION FOR EACH FUNCTIONAL RUN
#
# Participant scans files are updated with outlier information after running
# the motion exclusions script. These files are picked up in the first-level 
# analysis to decide which participants to exclude. For data checking purposes
# it might be helpful to extract this info for a list of participants to quickly
# get a sense of how much useable data is available and how many participants are
# being flagged for exclusion. This script will extract that information into a 
# group_scans.tsv file.
#
# This script must be run AFTER the motion exclusions scripts.
################################################################################

# usage documentation - shown if no text file is provided or if script is run outside EBC directory
Usage() {
    echo
	echo
    echo "Usage:"
    echo "./get_outlier_info.sh <list of subjects>"
    echo
    echo "Example:"
    echo "./get_outlier_info.sh list.txt"
    echo
    echo "list.txt is a file containing the participants to check:"
    echo "001"
    echo "002"
	echo "..."
    echo
	echo
	echo "This script must be run within the /EBC/ directory on the server due to space requirements."
	echo "The script will terminiate if run outside of the /EBC/ directory."
	echo
    echo "Script created by Melissa Thye"
    echo
    exit
}
[ "$1" = "" ] && Usage

# if the script is run outside of the EBC directory (e.g., in home directory where space is limited), terminate the script and show usage documentation
if [[ ! "$PWD" =~ "/EBC/" ]]
then Usage
fi

# define session (should always be 01 for EBC data, could alternatively put 'no' for non-EBC data)
ses=01

# define directories
projDir=`cat ../../PATHS.txt`
singularityDir="${projDir}/singularity_images"
qcDir="${projDir}/analysis/data_checking"

# extract sample from list of subjects filename (i.e., are these pilot or HV subjs)
sample=` basename $1 | cut -d '-' -f 3 | cut -d '.' -f 1 `
cohort=` basename $1 | cut -d '_' -f 1 `

# define data directories depending on sample information
if [[ ${sample} == 'pilot' ]]
then
	derivDir="/EBC/preprocessedData/${cohort}/derivatives/pilot"
elif [[ ${sample} == 'HV' ]]
then
	derivDir="/EBC/preprocessedData/${cohort}-adultpilot/derivatives"
else
	derivDir="/EBC/preprocessedData/${cohort}/derivatives"
fi

# print confirmation of sample and directory
echo "Getting outlier information for" ${sample} "participants..."

# create data checking directory if it doesn't exist
if [ ! -d ${qcDir} ]
then 
	mkdir -p ${qcDir}
fi

# delete data checking scans-group.tsv file if it already exists
if [ -f ${qcDir}/scans-group.tsv ]
then 
	rm ${qcDir}/scans-group.tsv
fi

# iterate over subjects
while read p
do
	sub=$(echo ${p} | awk '{print $1}')
	
	echo "Getting outlier information for ${sub}"
	
	# define subject directory depending on whether data are organized in session folders
	if [[ ${sessions} != 'no' ]]
	then
		subDir="${derivDir}/sub-${sub}/ses-01/func"
	else
		subDir="${derivDir}/sub-${sub}/func"
	fi
	
	scan_file=`ls ${subDir}/*_scans.tsv`

	# add scan information to data checking scans file
	if [ ! -f ${qcDir}/scans-group.tsv ] # on first loop, take header information from first subject
	then
		awk 'NR>0' ${scan_file} >> ${qcDir}/scans-group.tsv
	else
		awk 'NR>1' ${scan_file} >> ${qcDir}/scans-group.tsv
	fi

done <$1
