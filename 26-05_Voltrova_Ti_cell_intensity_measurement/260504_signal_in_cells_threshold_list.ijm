/* 
 *  Script for batch processing of .ims z-stack images in a user-selected folder
 *  Loads images one-by-one, segments the actin channel using fixed threshold value,
 *  and measures the signal in the actin-positive areas (should correspond to cells). 
 *  
 *  Multiple values of threshold are tested, one-by-one.
 *  
 *  Saves the results table as .csv 
 *  plus the z-projected images with signal (cyan) and actin (magenta) channel as .png with mask outline. 
 *  
 *  Requires 3D ImageJ Suite toolbox!
 *  Install from here: https://mcib3d.frama.io/3d-suite-imagej/#installation
 *  
 *  
 *  Author: Iva Švecová (iva.svecova@iem.cas.cz)
 *  Created: 4.5.2026
 *  
 */
 

dir = getDirectory("Please find the directory with your images.");
filenames = getFileList(dir);

// ADJUSTABLE PARAMETERS HERE:
actinChannel = 1;		// CHECK ME - this has to be the channel number that contains actin
signalChannel = 2;		// CHECK ME - this has to be the channel number that contains signal to measure
threshold_list = newArray(130, 140, 150);	// CHANGE ME - list of fixed thresholds to try for the cytoskeleton channel
// Each threshold will get the outputs in its own folder.

// Start the 3D manager and set some global parameters
run("3D Manager Options", "volume mean_grey_value std_dev_grey_value");
run("3D Manager");
setOption("ScaleConversions", true);

// Go through each threshold value and process all the files for each
for (threshold_idx=0; threshold_idx<threshold_list.length; threshold_idx++) {
	threshold = threshold_list[threshold_idx];	// threshold is taken from the list defined above
	
	// The output will be saved in a folder called output<thresholdValue>
	outputDir = dir + File.separator + "output" + threshold + File.separator;

	// Ensure that outputDir exists
	File.makeDirectory(outputDir);
	// Clean up before running the macro
	run("Clear Results");
	// Clean the 3D Manager 
	Ext.Manager3D_DeselectAll;
	Ext.Manager3D_Delete;
	roiManager("reset");
	
	// Process each image one-by-one, but only if it is in an .ims format
	for (imageIdx=0; imageIdx<filenames.length; imageIdx++) {
		filename = filenames[imageIdx];
		
		if (endsWith(filename, ".ims")){
			// Open the image, if it is .ims
			filepath = dir + File.separator + filename;
			
			// Bio-Formats is used to open the most detailed image from the pyramid
			run("Bio-Formats Importer", "open=" + filepath + " series_1");
			imageName = substring(filename, 0, lengthOf(filename)-4);
			fullName = get();
			
		    // Check number of channels - there should be 3
		    Stack.getDimensions(width, height, channels, slices, frames);
		
		    if (channels != 3) {
		        // log and skip
		        print("Skipping " + imageName + " (channels=" + channels + ")");
		        close();
		        continue;
		    }
			
			// Duplicate the channel with actin (1st channel by default)
			run("Duplicate...", "title=actin duplicate channels=" + actinChannel + "");
			
			// Apply 3D filter, set the sigma for xy and z
			run("Median 3D...", "x=2 y=2 z=2");
			
			// Apply threshold using the 3D ImageJ Suite
			run("3D Simple Segmentation", "seeds=None low_threshold=" + threshold + " min_size=0 max_size=-1");
			selectImage("Bin");		// This is the channel where all foreground has the same value
			
			// Add the ROI to 3D Manager
			Ext.Manager3D_AddImage();
			// if list is not visible refresh list by using Deselect
			Ext.Manager3D_Select(0);
			Ext.Manager3D_DeselectAll();
			
			Ext.Manager3D_Count(nb);	// nb is number of ROIs (should be 1, because we do not distinguish objects)
			nRes = nResults;	// Number of entries in the results table
			
			// get object volume
			vols=newArray(nb);
			// loop over objects
			for(i=0;i<nb;i++){
				Ext.Manager3D_Measure3D(i, "Vol", vol); // volume
				vols[i]=vol;
			}
			
			// Duplicate the channel with signal and measure the intensity
			selectImage(fullName);
			run("Duplicate...", "title=signal duplicate channels=" + signalChannel + "");
			
			signalMean = newArray(nb);
			signalStd = newArray(nb);
			selectImage("signal");
			// loop over objects
			for(i=0;i<nb;i++){
				 Ext.Manager3D_Quantif3D(i,"Mean", meanValue); // quantification, use IntDen, Mean, Min,Max, Sigma
				 signalMean[i] = meanValue;
				 Ext.Manager3D_Quantif3D(i, "Sigma", stdValue);
				 signalStd[i] = stdValue;
			}
			
			// Measure also the intensity of actin just to have a control 
			actinMean = newArray(nb);
			actinStd = newArray(nb);
			selectImage("actin");
			// loop over objects
			for(i=0;i<nb;i++){
				 Ext.Manager3D_Quantif3D(i,"Mean", meanValue);
				 actinMean[i] = meanValue;
				 Ext.Manager3D_Quantif3D(i, "Sigma", stdValue);
				 actinStd[i] = stdValue;
			}
			
			// Measure also the values from the binary mask 
			// This is for control - all the pixels should be foreground = value 255
			binMean = newArray(nb);
			binStd = newArray(nb);
			selectImage("Bin");
			// loop over objects
			for(i=0;i<nb;i++){
				 Ext.Manager3D_Quantif3D(i,"Mean", meanValue);
				 binMean[i] = meanValue;
				 Ext.Manager3D_Quantif3D(i, "Sigma", stdValue);
				 binStd[i] = stdValue;
			}
			
			// Extract the info about the sample from the name
			parts = split(filename, "_");
			
			// check length to avoid errors
			if (parts.length < 2) {
			    print("Filename does not contain enough parts: " + filename);
			    firstPart = "";
			    secondPart = "";
			} else {
			    firstPart = parts[0];
			    secondPart = parts[1];
			}
			
			
			// create results Table and store all the measured information
			for(i=0;i<nb;i++){
				resultsRow = nRes + i;
				setResult("image", resultsRow, filename);
				setResult("sampleType", resultsRow, firstPart);
				setResult("sampleReplicate", resultsRow, secondPart);
				setResult("volume", resultsRow, vols[i]);
				setResult("signalMean", resultsRow, signalMean[i]);
				setResult("signalStd", resultsRow, signalStd[i]);
				setResult("actinMean", resultsRow, actinMean[i]);
				setResult("actinStd", resultsRow, actinStd[i]);
				setResult("binMean", resultsRow, binMean[i]);
				setResult("binStd", resultsRow, binStd[i]);
			}
			updateResults();
			
			// Z-project and merge the actin channel (as magenta) and the signal (as cyan)
			// Z-project also the segmentation, store the ROIs and flatten them to the image as a yellow outline
			// Save the merged image as png for visual control
			
			selectImage("actin");
			run("Z Project...", "projection=[Max Intensity]");
			setMinAndMax(100, 1000);	// ADJUST IF NEEDED
			run("8-bit");
			
			selectImage("signal");
			run("Z Project...", "projection=[Max Intensity]");
			setMinAndMax(100, 500);		// ADJUST IF NEEDED
			run("8-bit");
			
			selectImage("Bin");
			run("Z Project...", "projection=[Max Intensity]");
			run("ROI Manager...");
			run("Analyze Particles...", "add composite");
	
			run("Merge Channels...", "c5=MAX_signal c6=MAX_actin create ignore");
			rename("mergedImage");		
			roiManager("Show All without labels");
			run("Flatten");
			saveAs("png", outputDir + "mergedMask_" + imageName + ".png");
			rename("mergedPng");
			
			// Important to close the files with the standardized names
			// Otherwise, we will keep working with the first actin image if there are more of them
			close("Seg");
			close("Bin");
			close("signal");
			close(fullName);
			close("MAX_signal");
			close("MAX_actin");
			close("MAX_Bin");
			close("actin");
			close("mergedImage");
			close("mergedImage-1");
			close("mergedPng");
			
			// Clean the 3D Manager 
			Ext.Manager3D_DeselectAll;
			Ext.Manager3D_Delete;
			roiManager("reset");
		}
		
		// Save the results table - done for each threshold
		saveAs("Results", outputDir + "measurements.csv");
	}
}
