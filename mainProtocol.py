
"""
Need to Install in the Python Enviroment Beforehand:
    $ conda install openpyxl
    % conda install ffmpeg ffmpeg-python
"""

# -------------------------------------------------------------------------- #
# ----------------------------- Import Modules ----------------------------- #

# Basic Modules
import os
import sys


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
    
    dataDirectory = "/Users/samuelsolomon/Desktop/Gao Group/Projects/_notPublished/Stress Sensor/Prussian Blue/2020/12-3-2020 PB stability/"
    
    # dataDirectory = "./data/Jose/" # The Folder with the CV Files (TXT/CSV/XLS/XLSX)

    
    # Plotting flags
    showPeakCurrent = True          # Display Real-Time Peak Current Data on Right (ONLY IF Peak Current Exists)
    seePastCVData = True            # See All CSV Frames in the Background (with 10% opacity)
    showFullInfo = True             # Plot Peak Potential and See Coefficient of VariationList Plot for peak Current
    # Program flags
    useCHIPeaks = False             # Do not reanalyze the CV curves. Use CHI-given peaks.
    
    # Program 
    numInitCyclesToSkip = 1         # Number of Beginning Cycles to Skip (In the First Few Cycles the Electrode is Adapting).
    
    # Specify Which Files You Want to Read
    fileDoesntContain = "N/A"       # Substring that cannot be in analyze filenames.
    fileContains = ""               # Substring that must be in analyze filenames.
    
    # ---------------------------------------------------------------------- #
    # ------------------------- Preparation Steps -------------------------- #
    
    # Initialize analysis classes.
    saveData = excelProcessing.saveData()
    extractData = excelProcessing.processFiles()
    analyzeDataCV = processDataCV.processData(numInitCyclesToSkip, useCHIPeaks)
    
    # Get the files to analyze in sorted order
    cvFiles = extractData.getFiles(dataDirectory, fileDoesntContain, fileContains)
    
    # Create the output folder if the one the provided does not exist
    outputDirectory = dataDirectory +  "CV Analysis/"
    os.makedirs(outputDirectory, exist_ok = True)
    
    # ---------------------------------------------------------------------- #
    # ----------------------------- CV Program ----------------------------- #
    
    # For each CV file.
    for currentFile in cvFiles: 
        
        # ------------------------ Extract the Data ------------------------ #
        # Convert and read the data file in an XLSX format.
        dataFile = dataDirectory + currentFile
        fileName = os.path.splitext(currentFile)[0]
        xlWorksheet, xlWorkbook = extractData.getExcelFile(dataFile, outputDirectory, testSheetNum = 0, excelDelimiter = ",")
        # ------------------------------------------------------------------ # 

        # ------------------------ Analyze the Data ------------------------ #
        # Extract the information from the file
        bothPeakPotentialGroups, bothPeakCurrentGroups, bothBaselineBoundsGroups, bothBaselineFitGroups, \
            currentFrames, potentialFrames, timeFrames = analyzeDataCV.processCV(xlWorksheet, xlWorkbook)
        # ------------------------------------------------------------------ # 

        # --------------------- Plot and Save the Data --------------------- #
        # Plot the CV Data
        plotData = dataPlotting.plotDataCV(fileName, outputDirectory, showFullInfo, showPeakCurrent, useCHIPeaks, seePastCVData)
        plotData.plotCurves(potentialFrames, currentFrames, timeFrames, bothPeakPotentialGroups, 
                            bothPeakCurrentGroups, bothBaselineBoundsGroups, bothBaselineFitGroups)
        
        # Save the Data
        savePeakInfoFolder = outputDirectory + "Peak Information/"
        saveData.saveDataCV(bothPeakPotentialGroups, bothPeakCurrentGroups, bothBaselineBoundsGroups, bothBaselineFitGroups, \
                            savePeakInfoFolder, fileName + ".xlsx", sheetName = "CV Analysis")
        # ------------------------------------------------------------------ # 
        

