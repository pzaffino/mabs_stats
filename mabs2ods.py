#!/usr/bin/env python

# 12-12-2014

import argparse
from copy import deepcopy
from ezodf import newdoc, Sheet
import numpy as np
import os
import sys

### UTILITY FUNCTIONS - BEGIN - ###
def dir_list(path):
    return [d for d in os.listdir(path) if os.path.isdir(d)]

def excel_style(row, col):
    """ Convert given row and column number to an Excel-style cell name. """
    quot, rem = divmod(col-1, 26) 
    return((chr(quot-1 + ord('A')) if quot else '') + (chr(rem + ord('A')) + str(row)))

def str_or_float(s):
    try: return float(s)
    except ValueError: return s
### UTILITY FUNCTIONS - END - ###

## Parser settings
parser = argparse.ArgumentParser(description='MABS seg_dice.csv to ods file')
parser.add_argument('--root_dir', help='Root directory', type=str, required=True)
parser.add_argument('--structures', help='Subset of structures to analyze. String as "stru1 stru2"', type=str, required=False)
parser.add_argument('--thresholds', help='Subset of thresholds to analyze. String as "thr1 thr2"', type=str, required=False)
parser.add_argument('--print_stats', help='Print statistics', action='store_true')
args = parser.parse_args()

os.chdir(args.root_dir)
used_atlases = [int(i.split("_")[-1]) for i in dir_list(".")]
used_atlases.sort()

# OPEN ODS FILE
ods = newdoc(doctype='ods', filename='../%s_stats.ods' % args.root_dir)
gap=80

for test_index, used_atlas in enumerate(used_atlases):

    test_index += 1

    if used_atlas < 100: used_atlas_str = "0"+str(used_atlas)
    elif used_atlas >= 100: used_atlas_str = str(used_atlas)

    # Read data from file
    seg_dice = open("mabs-train_" + str(used_atlas_str) + os.sep + "seg_dice.csv")
    raw_lines = [l.strip().split(",") for l in seg_dice.readlines()]
    seg_dice.close()


    # Make a list of all the patients
    patients=[]
    for line in raw_lines:
        if line[0] not in patients: patients.append(line[0])

    # Organize the data
    data=dict()
    for patient in patients:
        data[patient]=[]

    for line in raw_lines:
        patient = line[0]
        line_dict = dict()
        for field in line[1:]:
            key, value = field.split("=")
            key, value = key.strip(), str_or_float(value.strip())
            line_dict[key]=value
        data[patient].append(deepcopy(line_dict))

    # Extract structures and thresholds
    structures = []
    thresholds = []

    for patient in patients:
        patient_data = data[patient]
        for entry in patient_data:
            if entry["struct"] not in structures:
                structures.append(entry["struct"])
            if "thresh" in entry and "gaussian_%f" % entry["thresh"] not in thresholds:
                thresholds.append("gaussian_%f" % entry["thresh"])
            if "confidence_weight" in entry and "staple_%f" % entry["confidence_weight"] not in thresholds:
                thresholds.append("staple_%.9f" % entry["confidence_weight"])
            
    structures = set(structures)
    thresholds = set(thresholds)

    # Filter data using input parameters
    if args.thresholds != None:
        args_thresholds_splitted = args.thresholds.split(" ")
        filtered_thresholds = []
    
        # Check for "full range" thresholds (something like "staple*" or "gaussian*")
        full_range_thresholds = []
        for arg in args_thresholds_splitted:
            if "*" in arg:
                fusion_criterion = arg.split("*")[0]
                if fusion_criterion not in full_range_thresholds: full_range_thresholds.append(fusion_criterion)
    
        # Set the "well defined" thresholds
        for input_threshold in args_thresholds_splitted:
            if len(input_threshold.split("_")) == 2:
                fusion, thr = input_threshold.split("_")[0], float(input_threshold.split("_")[1])
                filtered_thresholds.append("%s_%.9f" % (fusion, thr))
    
        # Set the "full range" thresholds
        for full_range_of_threshold in full_range_thresholds:
            for threshold in thresholds:
                if full_range_of_threshold in threshold: filtered_thresholds.append(threshold)
    
        selected_thresholds = thresholds.intersection(filtered_thresholds)
    else:
        selected_thresholds = thresholds

    if args.structures != None:
        selected_structures = structures.intersection(args.structures.split(" "))
    else:
        selected_structures = structures

    # Create data structures
    # eg:
    # stats_left_parotid (dict) -
    #                            | --> dice_04 (list)
    #                            | --> dice_05 (list)
    #                            | --> b_avg_dist_04 (list)
    #                            | --> b_avg_dist_05 (list)
    #                            | --> b_95_dist_04 (list)
    #                            | --> b_95_dist_05 (list)
    for structure in structures:
        vars()["stats_%s" % structure] = {}
        for threshold in thresholds:
            thr = str(threshold).replace(".", "")
            vars()["stats_%s" % structure]["dice_%s" % thr] = []
            vars()["stats_%s" % structure]["b_avg_dist_%s" % thr] = []
            vars()["stats_%s" % structure]["b_95_dist_%s" % thr] = []

    # Insert data inside the structure
    for patient in patients:
        patient_data = data[patient]
        for entry in patient_data:
            if "thresh" in entry:
                thr = "gaussian_%f" % entry["thresh"]
            elif "confidence_weight" in entry:
                thr = "staple_%.9f" % entry["confidence_weight"]
            thr = thr.replace(".", "")
            stru = entry["struct"]
            dice = entry["dice"]
            b_avg_dist = entry["abhd"]
            b_95_dist = entry["95bhd"]
        
            vars()["stats_%s" % stru]["dice_%s" % thr].append(dice)
            vars()["stats_%s" % stru]["b_avg_dist_%s" % thr].append(b_avg_dist)
            vars()["stats_%s" % stru]["b_95_dist_%s" % thr].append(b_95_dist)

    # Medians and percentiles
    for structure in structures:
        for threshold in thresholds:
            thr = str(threshold).replace(".", "")
            vars()["median_dice_%s_%s" % (structure, thr)] = np.median(vars()["stats_%s" % structure]["dice_%s" % thr])
            vars()["95th_perc_dice_%s_%s" % (structure, thr)] = np.percentile(vars()["stats_%s" % structure]["dice_%s" % thr], 95)
            vars()["5th_perc_dice_%s_%s" % (structure, thr)] = np.percentile(vars()["stats_%s" % structure]["dice_%s" % thr], 5)

            vars()["median_b_avg_dist_%s_%s" % (structure, thr)] = np.median(vars()["stats_%s" % structure]["b_avg_dist_%s" % thr])
            vars()["95th_perc_b_avg_dist_%s_%s" % (structure, thr)] = np.percentile(vars()["stats_%s" % structure]["b_avg_dist_%s" % thr], 95)
            vars()["5th_perc_b_avg_dist_%s_%s" % (structure, thr)] = np.percentile(vars()["stats_%s" % structure]["b_avg_dist_%s" % thr], 5)

            vars()["median_b_95_dist_%s_%s" % (structure, thr)] = np.median(vars()["stats_%s" % structure]["b_95_dist_%s" % thr])
            vars()["95th_perc_b_95_dist_%s_%s" % (structure, thr)] = np.percentile(vars()["stats_%s" % structure]["b_95_dist_%s" % thr], 95)
            vars()["5th_perc_b_95_dist_%s_%s" % (structure, thr)] = np.percentile(vars()["stats_%s" % structure]["b_95_dist_%s" % thr], 5)

    # Print results
    if args.print_stats:
        for structure in selected_structures:
            for threshold in selected_thresholds:
                threshold_str = str(threshold).replace(".", "")
                print("Structure = %s" % structure)
                print("  threshold = %s" % threshold)
                print("    dice = median %s  5th_perc %s  95th_perc %s" % (str(vars()["median_dice_%s_%s" % (structure, threshold_str)]).replace(".", ","),
                    str(vars()["5th_perc_dice_%s_%s" % (structure, threshold_str)]).replace(".", ","),
                    str(vars()["95th_perc_dice_%s_%s" % (structure, threshold_str)]).replace(".", ",")))
                print("    average boundary distance = median %s  5th_perc %s  95th_perc %s" % (str(vars()["median_b_avg_dist_%s_%s" % (structure, threshold_str)]).replace(".", ","),
                    str(vars()["5th_perc_b_avg_dist_%s_%s" % (structure, threshold_str)]).replace(".", ","),
                    str(vars()["95th_perc_b_avg_dist_%s_%s" % (structure, threshold_str)]).replace(".", ",")))
                print("    95th percentile boundary distance = median %s  5th_perc %s  95th_perc %s" % (str(vars()["median_b_95_dist_%s_%s" % (structure, threshold_str)]).replace(".", ","),
                    str(vars()["5th_perc_b_95_dist_%s_%s" % (structure, threshold_str)]).replace(".", ","),
                    str(vars()["95th_perc_b_95_dist_%s_%s" % (structure, threshold_str)]).replace(".", ",")))

    # Fill ods file
    for threshold in selected_thresholds:
        threshold_str = str(threshold).replace(".", "")

        if  test_index == 1: #"thr_%s" % threshold_str not in vars():
            vars()["thr_%s" % threshold_str] = Sheet("thr_%s" % threshold_str, size=(600, 600))
            ods.sheets += vars()["thr_%s" % threshold_str]

        col = 0

        for structure in selected_structures:
        
            vars()["thr_%s" % threshold_str][excel_style(1,col+1)].set_value(structure)
            vars()["thr_%s" % threshold_str][excel_style(2,col+1)].set_value("# atlases")
            vars()["thr_%s" % threshold_str][excel_style(2,col+2)].set_value("Dice")
            vars()["thr_%s" % threshold_str][excel_style(2,col+3)].set_value("Min Dice")
            vars()["thr_%s" % threshold_str][excel_style(2,col+4)].set_value("Max dice")
            vars()["thr_%s" % threshold_str][excel_style(2,col+5)].set_value("Average HD")
            vars()["thr_%s" % threshold_str][excel_style(2,col+6)].set_value("Min Average HD")
            vars()["thr_%s" % threshold_str][excel_style(2,col+7)].set_value("Max Average HD")
            vars()["thr_%s" % threshold_str][excel_style(2,col+8)].set_value("95 perc HD")
            vars()["thr_%s" % threshold_str][excel_style(2,col+9)].set_value("Min 95 perc HD")
            vars()["thr_%s" % threshold_str][excel_style(2,col+10)].set_value("Max 95 perc HD")

            vars()["thr_%s" % threshold_str][excel_style((test_index+2), col+1)].set_value(used_atlas)

            vars()["thr_%s" % threshold_str][excel_style((test_index+2), col+2)].set_value(vars()["median_dice_%s_%s" % (structure, threshold_str)]) # median dice
            vars()["thr_%s" % threshold_str][excel_style((test_index+2), col+3)].set_value(vars()["5th_perc_dice_%s_%s" % (structure, threshold_str)]) # 5th_perc dice
            vars()["thr_%s" % threshold_str][excel_style((test_index+2), col+4)].set_value(vars()["95th_perc_dice_%s_%s" % (structure, threshold_str)]) # 95th_perc dice

            vars()["thr_%s" % threshold_str][excel_style((test_index+2), col+5)].set_value(vars()["median_b_avg_dist_%s_%s" % (structure, threshold_str)]) # median mean HD
            vars()["thr_%s" % threshold_str][excel_style((test_index+2), col+6)].set_value(vars()["5th_perc_b_avg_dist_%s_%s" % (structure, threshold_str)]) # 5th_perc mean HD
            vars()["thr_%s" % threshold_str][excel_style((test_index+2), col+7)].set_value(vars()["95th_perc_b_avg_dist_%s_%s" % (structure, threshold_str)]) # 95th_perc mean HD

            vars()["thr_%s" % threshold_str][excel_style((test_index+2), col+8)].set_value(vars()["median_b_95_dist_%s_%s" % (structure, threshold_str)]) # mdian 95 perc HD
            vars()["thr_%s" % threshold_str][excel_style((test_index+2), col+9)].set_value(vars()["5th_perc_b_95_dist_%s_%s" % (structure, threshold_str)]) # 5th_perc 95 perc HD
            vars()["thr_%s" % threshold_str][excel_style((test_index+2), col+10)].set_value(vars()["95th_perc_b_95_dist_%s_%s" % (structure, threshold_str)]) # 95th_perc 95 perc HD
            
            # Data for error bar plot 
            vars()["thr_%s" % threshold_str][excel_style((2+gap), col+2)].set_value("Data for error bar plot")
            vars()["thr_%s" % threshold_str][excel_style((2+gap+1), col+2)].set_value(structure)
            
            vars()["thr_%s" % threshold_str][excel_style((2+gap+2), col+2)].set_value("low dice")
            vars()["thr_%s" % threshold_str][excel_style((2+gap+2), col+3)].set_value("high dice")
            vars()["thr_%s" % threshold_str][excel_style((2+gap+2), col+4)].set_value("low avg HD")
            vars()["thr_%s" % threshold_str][excel_style((2+gap+2), col+5)].set_value("high avg HD")
            vars()["thr_%s" % threshold_str][excel_style((2+gap+2), col+6)].set_value("low 95 perc HD")
            vars()["thr_%s" % threshold_str][excel_style((2+gap+2), col+7)].set_value("high 95 perc HD")
          
            vars()["thr_%s" % threshold_str][excel_style((test_index+2+gap+2), col+2)].set_value(vars()["median_dice_%s_%s" % (structure, threshold_str)]- 
                                                                                              vars()["5th_perc_dice_%s_%s" % (structure, threshold_str)])
            vars()["thr_%s" % threshold_str][excel_style((test_index+2+gap+2), col+3)].set_value(vars()["95th_perc_dice_%s_%s" % (structure, threshold_str)]- 
                                                                                              vars()["median_dice_%s_%s" % (structure, threshold_str)])
            vars()["thr_%s" % threshold_str][excel_style((test_index+2+gap+2), col+4)].set_value(vars()["median_b_avg_dist_%s_%s" % (structure, threshold_str)]- 
                                                                                              vars()["5th_perc_b_avg_dist_%s_%s" % (structure, threshold_str)])
            vars()["thr_%s" % threshold_str][excel_style((test_index+2+gap+2), col+5)].set_value(vars()["95th_perc_b_avg_dist_%s_%s" % (structure, threshold_str)]- 
                                                                                              vars()["median_b_avg_dist_%s_%s" % (structure, threshold_str)])
            vars()["thr_%s" % threshold_str][excel_style((test_index+2+gap+2), col+6)].set_value(vars()["median_b_95_dist_%s_%s" % (structure, threshold_str)]- 
                                                                                              vars()["5th_perc_b_95_dist_%s_%s" % (structure, threshold_str)])
            vars()["thr_%s" % threshold_str][excel_style((test_index+2+gap+2), col+7)].set_value(vars()["95th_perc_b_95_dist_%s_%s" % (structure, threshold_str)]- 
                                                                                              vars()["median_b_95_dist_%s_%s" % (structure, threshold_str)])

            col = col + 11

ods.save()

