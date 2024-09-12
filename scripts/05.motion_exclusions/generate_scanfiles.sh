#!/bin/bash

################################################################################
# GENERATE THE SCANS.TSV FILE THAT WILL BE USED TO MARK RUN EXCLUSIONS
# 
# More information on these files: 
#	https://bids-specification.readthedocs.io/en/stable/modality-agnostic-files.html#scans-file
################################################################################

# usage documentation - shown if no text file is provided
Usage() {
	echo
	echo "Usage:"
	echo "./generate_scanfiles.sh <list of subjects>"
	echo
	echo "Example:"
	echo "./generate_scanfiles.sh KMVPA_subjs.txt"
	echo 
	echo "KMVPA_subjs.txt is a file containing the participants to generate the scans.tsv file for:"
	echo "001"
	echo "002"
	echo "..."
	echo
	echo
	echo "Script created by Melissa Thye"
	echo
	exit
}
[ "$1" = "" ] && Usage

# indicate whether session folders are used (always 'yes' for EBC data)
sessions='no'

# extract study name from list of subjects filename
study=` basename $1 | cut -d '_' -f 1 `

# define data directories depending on study information
bidsDir="/RichardsonLab/preprocessedData/${study}"
derivDir="${bidsDir}/derivatives"

# print confirmation of study and directory
echo 'Generating scans.tsv files for' ${study} 'data in' ${derivDir}

# iterate over subjects
while read p
do
	sub=$(echo ${p} |awk '{print $1}')
	
	# define subject derivatives directory depending on whether data are organized in session folders
	if [[ ${sessions} == 'yes' ]]
	then
		subDir_bids="${bidsDir}/sub-${sub}/ses-01/func"
		subDir_deriv="${derivDir}/sub-${sub}/ses-01/func"
		scan_file="sub-${sub}_ses-01_scans.tsv"
	else
		subDir_bids="${bidsDir}/sub-${sub}/func"
		subDir_deriv="${derivDir}/sub-${sub}/func"
		scan_file="sub-${sub}_scans.tsv"
	fi

	# create scan.tsv file for each subject who has functional data
	if [ -d ${subDir_bids} ] # if the subject has a functional data folder
	then
		echo "Generating scans.tsv file for ${sub}"

		# delete scans.tsv file if it already exists
		if [ -f ${subDir_bids}/${scan_file} ] || [ -f ${subDir_deriv}/${scan_file} ] 
		then 
			rm ${subDir_bids}/${scan_file}
			rm ${subDir_deriv}/${scan_file}
		fi
		
		# print run info to scan.tsv file
		printf "filename" >>  ${subDir_bids}/${scan_file}
	
		# list of functional files
		files=(`ls ${subDir_bids}/*nii.gz`)
		
		# for each file in the func directory, add filename to scans.tsv file
		for f in ${files[@]}
		do
			# extract file name (remove full path)
			current=`basename ${f}`
		
			# add file name (with directory) to scans.tsv file
			name=""
			name='\nfunc/'${current}
			printf ${name} >> ${subDir_bids}/${scan_file}
		
		done

	fi
	
	# copy scans.tsv to derivDir
	cp ${subDir_bids}/${scan_file} ${subDir_deriv}/${scan_file}
	
done <$1

