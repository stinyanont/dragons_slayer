#Primarily copied from https://dragons.readthedocs.io/_/downloads/niriimg-drtutorial/en/stable/pdf/
import glob, os, argparse
import numpy as np, pdb

#Import DRAGONS.
try:
    import astrodata
    import gemini_instruments
    from recipe_system.reduction.coreReduce import Reduce
    from recipe_system import cal_service
    from gempy.adlibrary import dataselect
    # from geminidr.f2.recipes.sq import recipes_FLAT_IMAGE
    import geminidr
except:
    print("Run this from the dragons environment or check your dragons installation.")
    exit()

########arguments
parser = argparse.ArgumentParser(description=\
        '''
        Run DRAGONS on the current raw directory
        
        Usage: python dragons_slayer.py 
            
        ''', formatter_class=argparse.RawTextHelpFormatter)

# parser = argparse.ArgumentParser()
parser.add_argument("--kskyflat", action="store_true",
                    help="Use sky flat in K band")
args = parser.parse_args()
K_sky_flat = args.kskyflat
# print(K_sky_flat)


########TO DO. Add a flag to skip redoing the calibrations. 

#Setup a logger
from gempy.utils import logutils
logutils.config(file_name='dragons.log')

#Setup the path for the Local Calibration Manager to the current path
file_dir = os.path.expanduser('~/.geminidr/rsys.cfg')
f = open(file_dir, 'w')
f.write('[calibs]\nstandalone = True\ndatabase_dir = %s/'%(os.getcwdb().decode('utf-8')))
f.close()

#Set up the calibration service
caldb = cal_service.CalibrationService()
caldb.config()
caldb.init()
cal_service.set_calservice()


#Create a bunch of list files. Modify this to account for different objects/bands

#First, grab all fits files in the directory. Unzip the bz2 before running this!
#bz2 files will work in the beginning, but will crash DRAGONS later. 
all_files = glob.glob('*.fits')
all_files.sort()

#Idea here is that we loop through all files once
#First round, separate the files into 4 categories: Darks, FLats, Science, and Standards
    #For Darks, look for a "DARK" tag, write file name along with exp_time and coadds
    #For Flats, look for a "FLAT" tag (Lamp on/off is fine)
    #For Science, look for an "IMAGE" tag
#Second round, we separate the following:
    #darks into different unique exp_time/coadds combo
    #flats into different filters
    #science into different object name

all_dark = []
all_flat = []
all_sci = []
# all_std = []

#Loop through, organize files into different lists. 
for file in all_files:
    ad = astrodata.open(file)
    # pdb.set_trace()
    print(file, ad.tags, ad.exposure_time(), ad.coadds(), ad.filter_name(), ad.well_depth_setting()) #TO DO. Print more useful information here? Exp time, coadds, filter, etc?
    if "PREPARED" in ad.tags:
        print("Processed file. Skipped.")
    elif ad.well_depth_setting() == "Deep":
        print("Deep well images. Somehow?")
    elif "DARK" in ad.tags:
        all_dark += [ [file, [ad.phu['EXPTIME'], ad.phu['COADDS']]] ]
        print("This is DARK.")
    elif "FLAT" in ad.tags:
        all_flat +=[ [file, ad.filter_name()] ]
        print("This is FLAT.")
    elif "IMAGE" in ad.tags and "ACQUISITION" not in ad.tags: #FLATS won't be in here.
        all_sci +=[ [file, [ad.object(), ad.filter_name()], [ad.phu["POFFSET"], ad.phu["QOFFSET"]]] ]
        print("This is SCIENCE.")
    elif "IMAGE" in ad.tags and "ACQUISITION" in ad.tags: #Acquisition images. Ignore them. 
        print("This is an ACQUISITION image. Ignore.")    
    else:
        print("Type Unknown")

#Deal with DARKS: 
#Unique sets of exp_time coadd combo
dark_exp_times =[list(x) for x in set(tuple(x) for x in np.array(all_dark, dtype = 'object')[:,1])]

min_dark_ind = np.argmin(np.array(dark_exp_times)[:,0]*np.array(dark_exp_times)[:,1]) #exp_time * coadds
print(min_dark_ind, dark_exp_times[min_dark_ind])

#create a list of lists with the same length as unique exp times.
#each element is a list of files with that unique exp time. 
dark_list_unique_time = [[] for x in range(len(dark_exp_times))]
for dark in all_dark:
    idx = dark_exp_times.index(dark[1])
    dark_list_unique_time[idx].append(dark[0])

print("###########################################")
print("##########DARKS AVAILABLE:#################")
print("###########################################")
for idx, i in enumerate(dark_exp_times):
    print("Exp time: %.3f s, %d coadds"%(i[0], i[1]))
    print(dark_list_unique_time[idx])
    # fn = 'dark_%.3f_%d.lis'%(i[0], i[1])

print("###########################################")


#Deal with DOME FLATS:
flat_filters = list(set(np.array(all_flat, dtype = 'object')[:,1]))
#create a list of lists to group flats with different filters.
flat_list_unique_filter = [[] for x in range(len(flat_filters))]
for flat in all_flat:
    idx = flat_filters.index(flat[1])
    flat_list_unique_filter[idx].append(flat[0])
# print(flat_list_unique_filter)

print("###########################################")
print("##########FLATS AVAILABLE:#################")
print("###########################################")
for idx, i in enumerate(flat_filters):
    print("Filter: %s"%(i))
    print(flat_list_unique_filter[idx])
print("###########################################")

#Deal with Science:
# all_sci = np.array(all_sci)
# ignore_band = 'Kshort_G0205'
# all_sci = all_sci[all_sci[:,1]!=ignore_band]

science_objects_filters = [list(x) for x in set(tuple(x) for x in np.array(all_sci, dtype = 'object')[:,1])]

#create a list of lists to group science with different filters.
sci_list_unique_obj_filter = [[] for x in range(len(science_objects_filters))]
for science in all_sci:
    idx = science_objects_filters.index(science[1])
    sci_list_unique_obj_filter[idx].append(science[0])


print("###########################################")
print("########SCI TARGETS AVAILABLE:#############")
print("###########################################")
for idx, i in enumerate(science_objects_filters):
    print("Object: %s, Filter: %s"%(i[0],i[1]))
    print(sci_list_unique_obj_filter[idx])
print(science_objects_filters)
print("###########################################")



#Save some numpy objects
# np.save('dark_fn.npy', dark_list_unique_time)
# np.save('dark_exp.npy', dark_exp_times)
# np.save('flat_fn.npy', flat_list_unique_filter)
# np.save('flat_filter.npy', flat_filters)
# np.save('sci_fn.npy', sci_list_unique_obj_filter)
# np.save('sci_obj_filter.npy', science_objects_filters)


#Run dark calibrations
for ind, dark_group in enumerate(dark_list_unique_time):
    print("Processing Darks with exposure time/coadds: ", dark_exp_times[ind])
    reduce_darks = Reduce()
    reduce_darks.files.extend(dark_group)
    reduce_darks.runr()
    caldb.add_cal(reduce_darks.output_filenames[0])

#Make a new bad pixel map, temporary. Fix this.
reduce_bpm = Reduce()
reduce_bpm.files.extend(flat_list_unique_filter[0])
reduce_bpm.files.extend(dark_list_unique_time[min_dark_ind]) #Using dark with min time. 
reduce_bpm.recipename = 'makeProcessedBPM'
reduce_bpm.runr()

bpm = reduce_bpm.output_filenames[0]

#Run flat calibrations
for ind, flat_group in enumerate(flat_list_unique_filter):
    if ('K' in flat_filters[ind]) and K_sky_flat:
        print("Processing Flats with filter: . USE SKY FLAT HERE.", flat_filters[ind])
        reduce_sky_flats = Reduce()
        # print(reduce_sky_flats.recipename)
        # reduce_sky_flats.recipename = recipes_FLAT_IMAGE.makeProcessedFlat
        reduce_sky_flats.recipename = "makeSkyFlat"
        reduce_sky_flats.files.extend(sci_list_unique_obj_filter[ind])
        # reduce_sky_flats.uparms = [('addDQ:user_bpm', bpm)]
        reduce_sky_flats.runr()

        caldb.add_cal(reduce_sky_flats.output_filenames[0])
    else:
        print("Processing Flats with filter: ", flat_filters[ind])
        reduce_flats = Reduce()
        reduce_flats.files.extend(flat_group)
        # reduce_flats.uparms = [('addDQ:user_bpm', bpm)]
        reduce_flats.runr()

        caldb.add_cal(reduce_flats.output_filenames[0])

#Run science calibrations
for ind, science_group in enumerate(sci_list_unique_obj_filter):
    print("Processing this science target/filter combination: ", science_objects_filters[ind])
    reduce_target = Reduce()
    reduce_target.files.extend(science_group)
    reduce_target.uparms = [('addDQ:user_bpm', bpm)]
    # reduce_target.uparms.append(('skyCorrect:scale_sky', False))
    if (astrodata.open(science_group[0])).object() == 'SN2022jzc' or (astrodata.open(science_group[0])).object() == 'SN2022oey':
        reduce_target.uparms.append(('skyCorrect:nlow', 0)) #######################HARD CODE. CHANGE THIS. OR FIX SOURCE CODE. 
    reduce_target.runr()



