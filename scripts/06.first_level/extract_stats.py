"""
Script to mask the contrast maps generated in firstlevel pipeline and extract mean or voxelwise stats

More information on what this script is doing - beyond the commented code - is provided on the lab's github wiki page

"""
import pandas as pd
import numpy as np
import argparse
import scipy.stats
from scipy.spatial import distance
import matplotlib.pyplot as plt
import os.path as op
import os
import glob
import shutil
import datetime
import math
from nilearn import plotting
from nilearn import image
from nilearn import masking
from nilearn.maskers import NiftiMasker
import nilearn
import shutil

def process_subject(projDir, sharedDir, resultsDir, sub, runs, task, contrast_opts, splithalves, mask_opts, match_events, template, extract_opt):
    
    # make output stats directory
    statsDir = op.join(resultsDir, '{}'.format(sub), 'stats')
    os.makedirs(statsDir, exist_ok=True)
    
    # create output file name
    stats_file = op.join(statsDir, '{}_task-{}_{}_ROI_magnitudes.csv'.format(sub, task, extract_opt))

    # delete output file if it already exists (to ensure stats aren't appended to pre-existing files)
    if os.path.isfile(stats_file):
        os.remove(stats_file)
            
    # for each run
    for run_id in runs:
        # for each splithalf
        for splithalf_id in splithalves:

            # grab roi file for each mask requested
            roi_masks = list()
            for m in mask_opts:
                if 'fROI' in m:
                    if splithalf_id != 0:
                        # grab mni file (used only if resampling is required)
                        mni_file = glob.glob(op.join(resultsDir, '{}'.format(sub), 'preproc', 'run{}_splithalf{}'.format(run_id, splithalf_id), '*preproc_bold.nii.gz'))
                        modelDir = op.join(resultsDir, '{}'.format(sub), 'model', 'run{}_splithalf{}'.format(run_id, splithalf_id))

                        # ensure that the fROI from the *opposite* splithalf is picked up for timecourse extraction (e.g., timecourse from splithalf1 is extracted from fROI defined in splithalf2)
                        if splithalf_id == 1:
                            print('Will skip stats extraction in splithalf{} for any fROIs defined in splithalf{}'.format(splithalf_id, splithalf_id))
                            froi_prefix = op.join(resultsDir, '{}'.format(sub), 'frois', 'run{}_splithalf2'.format(run_id))
                            
                        if splithalf_id == 2:
                            print('Will skip signal extraction in splithalf{} for any fROIs defined in splithalf{}'.format(splithalf_id, splithalf_id))
                            froi_prefix = op.join(resultsDir, '{}'.format(sub), 'frois', 'run{}_splithalf1'.format(run_id))
                    else:
                        # grab mni file (used only if resampling is required)
                        mni_file = glob.glob(op.join(resultsDir, '{}'.format(sub), 'preproc', 'run{}'.format(run_id), '*preproc_bold.nii.gz'))
                        modelDir = op.join(resultsDir, '{}'.format(sub), 'model', 'run{}'.format(run_id))
                        froi_prefix = op.join(resultsDir, '{}'.format(sub), 'frois', 'run{}'.format(run_id), '{}_task-{}_run-{:03d}'.format(sub, task, run_id))
                    
                    if not froi_prefix:
                        print('ERROR: unable to locate fROI file. Make sure a resultsDir is provided in the config file!')
                    else:
                        roi_name = m.split('-')[1]
                        roi_file = glob.glob(op.join('{}'.format(froi_prefix),'*{}*.nii.gz'.format(roi_name)))
                        roi_masks.append(roi_file)
                        print('Using {} fROI file from {}'.format(roi_name, roi_file))
                
                else: # if fROI not specified
                    if splithalf_id != 0:
                        # grab mni file (used only if resampling is required)
                        mni_file = glob.glob(op.join(resultsDir, '{}'.format(sub), 'preproc', 'run{}_splithalf{}'.format(run_id, splithalf_id), '*preproc_bold.nii.gz'))
                        modelDir = op.join(resultsDir, '{}'.format(sub), 'model', 'run{}_splithalf{}'.format(run_id, splithalf_id))
                    else:
                        # grab mni file (used only if resampling is required)              
                        mni_file = glob.glob(op.join(resultsDir, '{}'.format(sub), 'preproc', 'run{}'.format(run_id), '*preproc_bold.nii.gz'))
                        modelDir = op.join(resultsDir, '{}'.format(sub), 'model', 'run{}'.format(run_id))

                    if template is not None:
                        template_name = template.split('_')[0] # take full template name
                        roi_file = glob.glob(op.join(sharedDir, 'ROIs', '{}'.format(template_name), '{}*.nii.gz'.format(m)))[0]
                    else:
                        roi_file = glob.glob(op.join(sharedDir, 'ROIs', '{}*.nii.gz'.format(m)))[0]
                    
                    roi_masks.append(roi_file)
                    print('Using {} ROI file from {}'.format(m, roi_file)) 
    
            # for each ROI search space
            for r, roi in enumerate(roi_masks):
                # load and binarize mni file
                mni_img = image.load_img(mni_file)
                mni_bin = mni_img.get_fdata() # get image data (as floating point data)
                mni_bin[mni_bin >= 1] = 1 # for values equal to or greater than 1, make 1 (values less than 1 are already 0)
                mni_bin = image.new_img_like(mni_img, mni_bin) # create a new image of the same class as the initial image
                
                # load roi mask
                mask_img = image.load_img(roi)
                mask_bin = mask_img.get_fdata()
                
                # ensure that mask/ROI is binarized
                mask_bin[mask_bin >= 1] = 1 # for values equal to or greater than 1, make 1 (values less than 1 are already 0)
                mask_bin = image.new_img_like(mask_img, mask_bin) # create a new image of the same class as the initial image
                
                # the masks should already be resampled, but check if this is true and resample if not
                if mni_img.shape[0:3] != mask_bin.shape[0:3]:
                    print('WARNING: the search space provided has different dimensions than the functional data!')
                    
                    # make directory to save resampled rois
                    roiDir = op.join(resultsDir, 'resampled_rois')
                    os.makedirs(roiDir, exist_ok=True)
                    
                    # extract file name
                    roi_name = str(roi).replace('/','-').split('-')[-1]                    
                    
                    roi_name = roi_name.split('.nii')[0]
                    resampled_file = op.join(roiDir, '{}_resampled.nii.gz'.format(roi_name))
                    
                    # check if file already exists
                    if os.path.isfile(resampled_file):
                        print('Found previously resampled {} ROI in output directory'.format(roi_name[r]))
                        mask_bin = image.load_img(resampled_file)
                    else:
                        # resample image
                        print('Resampling {} search space to match functional data'.format(roi_name[r]))
                        mask_bin = image.resample_to_img(mask_bin, mni_img, interpolation='nearest')
                        mask_bin.to_filename(resampled_file)

                # for each contrast
                for c in contrast_opts:
                    # extract mask name in a format that will match contrast naming
                    if 'fROI' in mask_opts[r]:
                        mask_name = mask_opts[r].split('-')[1].lower()
                    else:
                        mask_name = mask_opts[r]

                    if match_events == 'yes' and mask_name not in c: # if the search space (lowercase) is contained within the contrast_opts specified
                        print('Skipping {} search space for the {} contrast'.format(mask_opts[r], c))
                    else: 
                        print('Extracting stats from {} mask within {} contrast'.format(mask_opts[r], c))
                        cope_file = glob.glob(op.join(modelDir, '*{}_zstat.nii.gz'.format(c)))
                        cope_img = image.load_img(cope_file)

                        # squeeze the statistical map to remove the 4th singleton dimension is using anatomical/atlas ROI
                        # this dimension is not adding any information, so this is fine to do; the 3D map of stats values is preserved.
                        # this step isn't necessary for fROIs because they were defined using the functional data and also have a 4th singleton dimension
                        if not 'fROI' in mask_opts[r]:
                            cope_img = image.math_img('np.squeeze(img)', img=cope_img)
                                                
                        # mask and extract values depending on extract_opt
                        if extract_opt == 'mean': # if mean requested
                            # mask contrast image with roi image
                            masked_img = image.math_img('img1 * img2', img1 = cope_img, img2 = mask_bin)
                            masked_data = masked_img.get_fdata()
                            
                            # take the mean of voxels within mask
                            mean_val = np.nanmean(masked_data)
                        
                            if splithalf_id != 0:
                                df_row = pd.DataFrame({'sub': sub,
                                                       'task' : task,
                                                       'run' : run_id,
                                                       'half' : splithalf_id,
                                                       'mask': mask_opts[r],
                                                       'roi_file' : roi,
                                                       'contrast' : c, 
                                                       'mean_val' : mean_val}, index=[0])
                            else:
                                df_row = pd.DataFrame({'sub': sub,
                                                       'task' : task,
                                                       'run' : run_id,
                                                       'mask': mask_opts[r],
                                                       'roi_file' : roi,
                                                       'contrast' : c, 
                                                       'mean_val' : mean_val}, index=[0])
                            
                            if not os.path.isfile(stats_file): # if the stats output file doesn't exist
                                # save current row as file
                                df_row.to_csv(stats_file, index=False, header='column_names')
                            else: # if the stats output file exists
                                # append current row without header labels
                                df_row.to_csv(stats_file, mode='a', index=False, header=False)

                        # return voxelwise values
                        else:
                            # mask contrast image with roi image and return 2D array
                            masker = NiftiMasker(mask_img=mask_bin)
                            masked_data = masker.fit_transform(cope_img)
                            
                            # convert to data frame
                            masked_df = pd.DataFrame(masked_data).transpose()
                            
                            # add columns with run, split, and mask info
                            masked_df.insert(loc=0, column='voxel_index', value=range(len(masked_df)))
                            masked_df.insert(loc=0, column='mask', value=mask_opts[r])
                            masked_df.insert(loc=0, column='contrast', value=c)
                            if splithalf_id != 0:
                                masked_df.insert(loc=0, column='half', value=splithalf_id)
                            masked_df.insert(loc=0, column='run', value=run_id)
                            masked_df.insert(loc=0, column='sub', value='{}'.format(sub))
                            
                            if not os.path.isfile(stats_file): # if the stats output file doesn't exist
                                # save dataframe
                                masked_df.to_csv(stats_file, index=False, header='column_names')
                            else:
                                # append current row without header labels
                                masked_df.to_csv(stats_file, mode='a', index=False, header=False)
                                
# define command line parser function
def argparser():
    # create an instance of ArgumentParser
    parser = argparse.ArgumentParser()
    # attach argument specifications to the parser
    parser.add_argument('-p', dest='projDir',
                        help='Project directory')
    parser.add_argument('-w', dest='workDir', default=os.getcwd(),
                        help='Working directory')
    parser.add_argument('-o', dest='outDir', default=os.getcwd(),
                        help='Output directory')
    parser.add_argument('-s', dest='subjects', nargs='*',
                        help='List of subjects to process (default: all)')
    parser.add_argument('-r', dest='runs', nargs='*',
                        help='List of runs for each subject')    
    parser.add_argument('-c', dest='config',
                        help='Configuration file')                                            
    parser.add_argument('-sparse', action='store_true',
                        help='Specify a sparse model')
    parser.add_argument('-m', dest='plugin',
                        help='Nipype plugin to use (default: MultiProc)')
    return parser

# define main function that parses the config file and runs the functions defined above
def main(argv=None):
    # call argparser function that defines command line inputs
    parser = argparser()
    args = parser.parse_args(argv) 

    # print if the project directory is not found
    if not op.exists(args.projDir):
        raise IOError('Project directory {} not found.'.format(args.projDir))    
    
    # print if config file is not found
    if not op.exists(args.config):
        raise IOError('Configuration file {} not found. Make sure it is saved in your project directory!'.format(args.config))
    
    # read in configuration file and parse inputs
    config_file=pd.read_csv(args.config, sep='\t', header=None, index_col=0).replace({np.nan: None})
    sharedDir=config_file.loc['sharedDir',1]
    resultsDir=config_file.loc['resultsDir',1]
    task=config_file.loc['task',1]
    splithalf=config_file.loc['splithalf',1]
    contrast_opts=config_file.loc['contrast',1].replace(' ','').split(',')
    mask_opts=config_file.loc['mask',1].replace(' ','').split(',')
    match_events=config_file.loc['match_events',1]
    template=config_file.loc['template',1]
    extract_opt=config_file.loc['extract',1]
    
    # lowercase contrast_opts to avoid case errors - allows flexibility in how users specify contrasts in config and contrasts files
    contrast_opts = [c.lower() for c in contrast_opts]
    
    if splithalf == 'yes':
        splithalves = [1,2]
    else:
        splithalves = [0]

    # print if results directory is not specified or found
    if resultsDir == None:
        raise IOError('No resultsDir was specified in config file, but is required to define fROIs!')
    
    if not op.exists(resultsDir):
        raise IOError('Results directory {} not found.'.format(resultsDir))
        
    # for each subject in the list of subjects
    for index, sub in enumerate(args.subjects):
        print('Extracting stats for {}'.format(sub))
        # pass runs for this sub
        sub_runs=args.runs[index]
        sub_runs=sub_runs.replace(' ','').split(',') # split runs by separators
        if sub_runs == ['NA']: # if run info isn't used in file names
            sub_runs = 1 # make this '1' instead of '0' because results were output with 'run1' label
        else:
            sub_runs=list(map(int, sub_runs)) # convert to integers
            
        # create a process_subject workflow with the inputs defined above
        process_subject(args.projDir, sharedDir, resultsDir, sub, sub_runs, task, contrast_opts, splithalves, mask_opts, match_events, template, extract_opt)

# execute code when file is run as script (the conditional statement is TRUE when script is run in python)
if __name__ == '__main__':
    main()