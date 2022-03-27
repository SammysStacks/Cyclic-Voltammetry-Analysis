
"""
Need to Install in the Python Enviroment Beforehand:
    $ conda install openpyxl
    % conda install ffmpeg
"""

# -------------------------------------------------------------------------- #
# ----------------------------- Import Modules ----------------------------- #

# Basic Modules
import os
import sys
# Modules to Sort Files in Order
from natsort import natsorted

# Import Helper Files
sys.path.append('./Helper Files/')

#Import Plotting Files
sys.path.append('./Helper Files/Plotting/')
import dataPlotting

# Import Python Files for Data Extraction
sys.path.append('./Helper Files/Data Extraction/')
import excelProcessing
import processDataCV

# ---------------------------------------------------------------------------#
# ------------------------------ Program Begins -----------------------------#

if __name__ == "__main__":
    # ---------------------------------------------------------------------- #
    #    User Parameters to Edit (More Complex Edits are Inside the Files)   #
    # ---------------------------------------------------------------------- #

    # Specify the Directory with All the Data (CSV Files Exported from CHI)
    dataDirectory = "./data/2022-03-23 MQ HCF/" # The Folder with the CV Files (TXT/CSV/XLS/XLSX)
    
    # Flags Specifying the Analysis
    skipIfDataAlreadyExcel = False  # Skip Over Data if CSV->Excel has Already Been Done (No Graphs!)
    useAllFolderFiles = True        # If False, Populate the cvFile_List Yourself (Choose Your Files Below)
    showPeakCurrent = True          # Display Real-Time Peak Current Data on Right (ONLY IF Peak Current Exists)
    seePastCVData = True            # See All CSV Frames in the Background (with 10% opacity)
    showFullInfo = True             # Plot Peak Potential and See Coefficient of VariationList Plot for peak Current
    useCHIPeaks = False
    
    # Edit Data
    numInitCyclesToSkip = 1         # Number of Beginning Cycles to Skip (In the First Few Cycles the Electrode is Adapting).
    
    if useAllFolderFiles:
        # Specify Which Files You Want to Read
        fileDoesntContain = "N/A"
        fileContains = ""
    else:
        cvFiles = []
    
    # ---------------------------------------------------------------------- #
    # ------------------------- Preparation Steps -------------------------- #
    
    # Initialize analysis files
    extractData = excelProcessing.processFiles()
    analyzeDataCV = processDataCV.processData(numInitCyclesToSkip, useCHIPeaks)
    
    # Get the files to analyze
    if useAllFolderFiles:
        cvFiles = extractData.getFiles(dataDirectory, fileDoesntContain, fileContains)
    # Process files in a sorted order
    cvFiles = natsorted(cvFiles)
    
    # Create the output folder if the one the provided does not exist
    outputDirectory = dataDirectory +  "CV Analysis/"
    os.makedirs(outputDirectory, exist_ok = True)
    
    # ---------------------------------------------------------------------- #
    # ----------------------------- CV Program ----------------------------- #
    
    # For each file, extract the data and plot the results
    for currentFile in cvFiles: 
        
        # ------------------------ Extract the Data ------------------------ #
        # Convert and read the data file in an XLSX format.
        dataFile = dataDirectory + currentFile
        fileName = os.path.splitext(currentFile)[0]
        xlWorksheet, xlWorkbook = extractData.getExcelFile(dataFile, outputDirectory, testSheetNum = 0, excelDelimiter = ",")
        # ------------------------------------------------------------------ # 

        # ------------------------ Analyze the Data ------------------------ #
        # Extract the information from the file
        peakInfoHolder, currentFrames, potentialFrames, timeFrames = analyzeDataCV.processCV(xlWorksheet, xlWorkbook)
        # ------------------------------------------------------------------ # 

        # --------------------- Plot and Save the Data --------------------- #
        # Plot the CV Data
        plotData = dataPlotting.plotDataCV(fileName, outputDirectory, showFullInfo, showPeakCurrent, useCHIPeaks, seePastCVData)
        plotData.plotCurves(potentialFrames, currentFrames, timeFrames, peakInfoHolder)
        
        # Save the Data
        saveData = excelProcessing.saveData()
        savePeakInfoFolder = outputDirectory + "Peak Information/"
        saveData.saveDataCV(peakInfoHolder, savePeakInfoFolder, fileName, sheetName = "CV Analysis")
        # ------------------------------------------------------------------ # 
        

