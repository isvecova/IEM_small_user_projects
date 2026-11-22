// WARNING - THE NEW CLASSIFIER IS QUITE BIG (2GB), SO IT WILL PROBABLY BE VERY SLOW
// Set paths
modelPath = "C:\\Users\\iva.svecova\\Documents\\classifierNew.model"; // !! CHANGE ME: SPECIFY THE WHOLE PATH TO CLASSIFIER.MODEL
imageFolder = "L:\\Andor_BC43\\430\\RawDataTest"; // !! CHANGE ME: SPECIFY, WHERE YOUR IMAGES ARE
outputFolder = "C:\\Users\\iva.svecova\\Documents\\SpheriodResults" // !! CHANGE ME: SPECIFY, WHERE TO PUT THE OUTPUTS (OVERLAYED IMAGES + TABLE) 

// Ensure that the outputFolder exists
File.makeDirectory(outputFolder);

// !! CHECK: parameters for spots detection 
minROIsize = 10000;
minCircularity = 0.1;

// Output table path
outputTable = outputFolder + File.separator + "organoid_analysis_results.csv";

// Ensure the model file exists
if (!File.exists(modelPath)) {
    print("Error: Model file not found!");
    exit();
}

// Get list of .ims images
list = getFileList(imageFolder);

// Create results arrays
imageNames = newArray();
areasROI = newArray();
areasEllipse = newArray();
majorAxes = newArray();
minorAxes = newArray();

// Set what to measure
run("Set Measurements...", "area mean fit shape skewness decimal=1");

// Loop through all images
for (i = 0; i < lengthOf(list); i++) {
    filename = list[i];
    if (!endsWith(filename, ".ims")) continue; // Process only .ims files

    print("Processing: " + filename);
    
    // Clean up before running next image
    roiManager("reset");
    run("Clear Results");

    // Open .ims image using Bio-Formats headless mode
    run("Bio-Formats Importer", "open=[" + imageFolder + File.separator + filename + "] autoscale color_mode=Default view=Hyperstack stack_order=XYCZT quiet");

    // Ensure the correct image is selected
    selectImage(filename);
    
	// start plugin
	run("Trainable Weka Segmentation");
	
	// wait for the plugin to load
	wait(3000);
    // Load WEKA classifier
	call("trainableSegmentation.Weka_Segmentation.loadClassifier", modelPath);
	// wait(2000);

    // Apply Weka classifier
    call("trainableSegmentation.Weka_Segmentation.applyClassifier", imageFolder, filename, "showResults=true", "storeResults=false", "probabilityMaps=false", "");
    // wait(5000); // Allow processing time

	selectImage("Classification result");
	
	// Convert to binary
	setThreshold(0, 0);
	run("Convert to Mask");

	// Run binary operations to get rid of unwanted things and compact the main ROI
	// THIS IS THE ONLY DIFFERENT THING FROM THE PREVIOUS VERSION, TOGETHER WITH THE CLASSIFIER NAME
	run("Fill Holes");
	run("Dilate");
	run("Fill Holes");
	run("Erode");
	run("Fill Holes");
	run("Dilate");
	run("Fill Holes");
	run("Erode");

    // Analyze particles
    run("Analyze Particles...", "size=" + minROIsize + "-Infinity circularity=" + minCircularity + "-1.00 display exclude overlay add");

    // Get all ROIs and find the largest one
    roiManager("Deselect");
    roiCount = roiManager("Count");

    if (roiCount == 0) {
        print("No objects found in " + filename);
        continue;
    }

    maxArea = 0;
    maxIndex = -1;

    for (j = 0; j < roiCount; j++) {
        roiManager("Select", j);
        run("Measure");
        area = getResult("Area", j);
        
        if (area > maxArea) {
            maxArea = area;
            maxIndex = j;
        }
    }

	// Extract measurements for the largest ROI from the default Results Table
	majorAxis = getResult("Major", maxIndex);
	minorAxis = getResult("Minor", maxIndex);
	finalArea = getResult("Area", maxIndex);
	
	// Store the values in the arrays, that will be later saved to table
    imageNames = Array.concat(imageNames, filename);
    areasROI = Array.concat(areasROI, maxArea);
    areasEllipse = Array.concat(areasEllipse,finalArea);
    majorAxes = Array.concat(majorAxes, majorAxis);
    minorAxes = Array.concat(minorAxes, minorAxis);
    
	// Select the original image
	selectImage(filename);
	
	// Sharpen the image for better visualization
	roiManager("Deselect");
	run("Unsharp Mask...", "radius=2 mask=0.70");
	
	// Delete all the other ROIs before saving the images
	roiCount = roiManager("Count");
	
	for (j = roiCount - 1; j >= 0; j--) { // Loop backwards to avoid index shifting
	    if (j != maxIndex) {
	        roiManager("Select", j);
	        roiManager("Delete");
	    }
	}
	
	// Overlay the largest ROI
	roiManager("Select", 0);
	roiManager("Add & Draw");
	
	// Overlay the fitted ellipse
	run("Fit Ellipse");
	roiManager("Add & Draw");
	
	// Save the overlayed image
	outputImagePath = outputFolder + File.separator + replace(filename, ".ims", "_overlay.tif");
	saveAs("Tiff", outputImagePath);
	
	print("Overlay saved: " + outputImagePath);
	
	// Save the overlayed image
	selectImage("Classification result");
	outputImagePath = outputFolder + File.separator + replace(filename, ".ims", "_clasResult.tif");
	saveAs("Tiff", outputImagePath);


    // Close images
    close("*");
}

Table.create("Organoid Analysis");

Table.setColumn("Image name", imageNames);
Table.setColumn("Area ROI", areasROI);
Table.setColumn("Area ellipse", areasEllipse);
Table.setColumn("Major axis", majorAxes);
Table.setColumn("Minor axis", minorAxes);


// Save results
Table.save(outputTable);
print("Processing completed. Results saved to: " + outputTable);
