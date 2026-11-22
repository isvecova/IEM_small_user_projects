/* 
 *  Script for batch processing of .czi z-stack images in a user-selected folder
 *  Loads images one-by-one, segments the DAPI channel using fixed threshold value,
 *  and measures the signal in the DAPI-positive areas. 
 *  Saves the results table as .csv and the mask images with DAPI channel as .tif. 
 *  
 *  Requires 3D ImageJ Suite toolbox!
 *  Install from here: https://mcib3d.frama.io/3d-suite-imagej/#installation
 *  
 *  Author: Iva Švecová (iva.svecova@iem.cas.cz)
 *  Created: 12.4.2026
 *  
 */

dir = getDirectory("Please find the directory with your images.");
filenames = getFileList(dir);
Array.print(filenames);
outputDir = dir + File.separator + "output" + File.separator;

// Ensure that outputDir exists
File.makeDirectory(outputDir);

DAPIchannel = 2;		// CHECK ME - this has to be the channel number that contains DAPI
signalChannel = 3;		// CHECK ME - this has to be the channel number that contains signal to measure
threshold = 44;			// CHANGE ME - fixed threshold for the DAPI channel

run("3D Manager Options", "volume mean_grey_value std_dev_grey_value");
run("3D Manager");

for (imageIdx=0; imageIdx<filenames.length; imageIdx++) {
	filename = filenames[imageIdx];
	if (endsWith(filename, ".czi")){
		// Open the image, if it is .czi
		filepath = dir + File.separator + filename;
		run("Bio-Formats Importer", "open=[" + filepath + "] color_mode=Default view=Hyperstack stack_order=XYCZT");
		imageName = substring(filename, 0, lengthOf(filename)-4);
		
		// Duplicate the channel with DAPI (2nd channel by default)
		run("Duplicate...", "title=DAPI duplicate channels=" + DAPIchannel + "");
		
		// Apply 3D filter, set the sigma anisotropically for xy and z
		run("Median 3D...", "x=5 y=5 z=1");
		
		// Apply threshold using the 3D ImageJ Suite
		run("3D Simple Segmentation", "seeds=None low_threshold=" + threshold + " min_size=0 max_size=-1");
		selectImage("Bin");		// This is the channel where all foreground has the same value
		
		// Add the ROI to 3D Manager
		Ext.Manager3D_AddImage();
		// if list is not visible please refresh list by using Deselect
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
		selectImage(filename);
		run("Duplicate...", "title=signal duplicate channels=" + signalChannel + "");
		
		signalMean = newArray(nb);
		signalStd = newArray(nb);
		selectImage("signal");
		// loop over objects
		for(i=0;i<nb;i++){
			 Ext.Manager3D_Quantif3D(i,"Mean", meanValue); // quantification, use IntDen, Mean, Min,Max, Sigma
			 signalMean[i] = meanValue;
			 Ext.Manager3D_Quantif3D(i, "Sigma", stdValue); // quantification, use IntDen, Mean, Min,Max, Sigma
			 signalStd[i] = stdValue;
		}
		
		// create results Table
		for(i=0;i<nb;i++){
			resultsRow = nRes + i;
			setResult("image", resultsRow, filename);
			setResult("volume", resultsRow, vols[i]);
			setResult("signalMean", resultsRow, signalMean[i]);
			setResult("signalStd", resultsRow, signalStd[i]);
		}
		updateResults();
		
		// Merge and save the DAPI channel (as cyan) and the mask (as magenta) for control
		run("Merge Channels...", "c5=DAPI c6=Bin create ignore");
		saveAs("Tiff", outputDir + "mergedMask_" + imageName + ".tif");
		
		// Important to close the files with the standardized names
		// Otherwise, we will keep working with the first DAPI image if there are more of them
		close("Seg");
		close("Bin");
		close("DAPI");
		close("signal");
		close(filename);
		close("mergedMask_" + imageName + ".tif");
		
		// Clean the 3D Manager 
		Ext.Manager3D_DeselectAll;
		Ext.Manager3D_Delete;
	}
	
	// Save the results table
	saveAs("Results", outputDir + "measurements.csv");
}
