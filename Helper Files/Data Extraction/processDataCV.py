#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Need to Install on the Anaconda Prompt:
    $ pip install pyexcel
"""

# -------------------------------------------------------------------------- #
# ----------------------------- Import Modules ----------------------------- #

# Basic Modules
import re
import sys
import math
import numpy as np

# Import Analysis Files
sys.path.append('./Helper Files/Analysis Protocols/')
import cvAnalysis

# -------------------------------------------------------------------------- #
# ------------------------------- CV Analysis ------------------------------ #

class generalAnalysis():
    
    def __init__(self):
        # deltaV (Potential) Difference that Defines a New Peak (For Peak Labeling)
        self.maxPeakPotentialDeviation = 0.07
    
    def populateNullPeaks(self, peakInfo_RedOx, cycleNum):
        """
        cycleNum: 1-indexed integer representing the current cycle
        """
        # Loop through each availible peak
        for peakNum in range(len(peakInfo_RedOx)):
            peaks = peakInfo_RedOx[peakNum]
            
            # Add NAN as fillers for the missing values
            numMissing = cycleNum - len(peaks)
            if 0 < numMissing:
                peakInfo_RedOx[peakNum].extend([[np.nan, np.nan, np.nan, []]]*numMissing)
        
        # Return the new peakInfo_RedOx with the value added
        return peakInfo_RedOx
        
    def addPeakInfo_SearchEp(self, peakInfo_RedOx, peakPotential, peakCurrent, linearFitBounds, linearFit, cycleNum):
        foundPeak = False
        # Loop through each availible peak
        for peakNum in range(len(peakInfo_RedOx)):
            peaks = peakInfo_RedOx[peakNum]
            
            # Calculate the average potential for this peak (last 3 values)
            peakPotentials = np.array(np.array(peaks, dtype=object)[:,0], dtype=float)
            peakPotentials = peakPotentials[~np.isnan(peakPotentials)][-3:]
            if len(peakPotentials) != 0:
                peakPotentialAv = np.nanmean(peakPotentials)
                
                # If the peakPotential is within range 
                if abs(peakPotential - peakPotentialAv) < self.maxPeakPotentialDeviation:
                    # Then add the peak to this map
                    peakInfo_RedOx[peakNum].append([peakPotential, peakCurrent, linearFitBounds, linearFit])
                    foundPeak = True
                    break
            
        if not foundPeak:
            peakInfo_RedOx.append([])
            peakInfo_RedOx = self.populateNullPeaks(peakInfo_RedOx, cycleNum)
            peakInfo_RedOx[-1].append([peakPotential, peakCurrent, linearFitBounds, linearFit])
        
        # Return the new peakInfo_RedOx with the value added
        return peakInfo_RedOx
    
# -------------------------------------------------------------------------- #
# ------------------------------ CV Extraction ----------------------------- #

class processData(generalAnalysis):
    
    def __init__(self, numInitCyclesToSkip, useCHIPeaks):
        super().__init__()
        # Initialize CV analysis
        self.analyzeCV = cvAnalysis.cvAnalysis()
        # Specify analysis paramaeters.
        self.useCHIPeaks = useCHIPeaks
        self.numInitCyclesToSkip = numInitCyclesToSkip

        # General Parameters
        self.scaleCurrent = 10**6

    def extractCHIData(self, chiWorksheet, startRow, scanRate, pointsPerScan):        
        # Get the Data
        current = []; potential = []; time = [0]
        currentFrames = []; potentialFrames = []; timeFrames = []
        for rowA, rowB in chiWorksheet.iter_rows(min_col=1, min_row=startRow, max_col=2, max_row=chiWorksheet.max_row):
            # Get Potential and Current Data Points
            potentialVal = rowA.value
            currentVal = rowB.value
            
            # If There is No More Data, Stop Recording
            if potentialVal == None:
                break
            
            # Add Data to Current Frame
            potential.append(float(potentialVal))
            current.append(float(currentVal)*self.scaleCurrent)
            if len(potential) > 1:
                timeGap =  abs(potential[-1] - potential[-2]) / scanRate
                time.append(time[-1] + timeGap)
            
            # If Done Collecting Data, Collect as Frame and Start a New Frame
            if len(potential) >= pointsPerScan:
                # Add Current Frame
                potentialFrames.append(potential)
                currentFrames.append(current)
                timeFrames.append(time)
                # Reset for New Frame
                current = []; potential = []; time = [time[-1] + timeGap]
        
        return currentFrames, potentialFrames, timeFrames
    
    def getRunInfo(self, chiWorksheet):
        # Set Initial Variables from last Run to Zero
        scanRate = None; sampleInterval = None; highVolt = None; lowVolt = None; startRow = None
        # Loop Through the Info Section and Extract the Needxed Run Info from Excel
        for cell in chiWorksheet.rows:
            cell = cell[0]
            # Get Cell Value
            cellVal = cell.value
            if cellVal == None:
                continue
            
            # Find the Scan Rate (Volts/Second)
            if cellVal.startswith("Scan Rate (V/s) = "):
                scanRate = float(cellVal.split(" = ")[-1])
            # Find the Sample Interval (Voltage Different Between Points)
            elif cellVal.startswith("Sample Interval (V) = "):
                sampleInterval = float(cellVal.split(" = ")[-1])
            # Find the Highest Voltage
            elif cellVal.startswith("High E (V) = "):
                highVolt = float(cellVal.split(" = ")[-1])
            # Find the Lowest Voltage
            elif cellVal.startswith("Low E (V) = "):
                lowVolt = float(cellVal.split(" = ")[-1])
            elif cellVal == "Segment 1:":
                startSegment = cell.row
            elif cellVal == "Potential/V":
                startRow = cell.row + 2
                break
        # Find the X Axis Width
        xRange = (highVolt - lowVolt)*2
        # Find Point/Scan
        pointsPerScan = int(xRange/sampleInterval)
        pointsPerSegment = int(pointsPerScan/2)
        # Adjust Which Cycle you Start at
        skipOffset = int(self.numInitCyclesToSkip*pointsPerScan)
        startRow += skipOffset
        # Total Frames (Will Round Down to Remove Incomplete Scans); Frame = Cycle = 2 Segments
        totalFrames = math.floor((chiWorksheet.max_row - startRow + 1)/pointsPerScan)
        numberOfSegments = totalFrames*2

        # Return all the CV information.
        return startRow, scanRate, pointsPerScan, pointsPerSegment, startSegment, numberOfSegments, skipOffset
    
    def getPeaksCHI(self, chiWorksheet, startRow, startSegment, skipOffset, numberOfSegments):
        # Create data structures to hold information: [OXIDATION, REDUCTION]
        peakInfoHolder = [[], []]
        
        cycleNum = 0
        for rowA in chiWorksheet.iter_rows(min_col=1, min_row=startSegment, max_col=1, max_row=startRow - 4 - skipOffset):
            cellVal = rowA[0].value
            if cellVal == None:
                continue
        
            # Skip Over Bad Segments
            if self.numInitCyclesToSkip > 0:
                if rowA[0].row == startSegment:
                    continue
                if cellVal.startswith("Segment "):
                    segment = float(cellVal[:-1].split("Segment ")[-1])
                    self.numInitCyclesToSkip -= 0.5
                if self.numInitCyclesToSkip != 0:
                    continue
            
            # Find the Current Segment
            if cellVal.startswith("Segment "): 
                # Extract Segment Info
                segment = float(cellVal[:-1].split("Segment ")[-1])
                
                # Finish the cycle giving every peak we are tracking a value
                reductiveScan = not (segment%2 == 1)
                peakInfoHolder[reductiveScan] = self.populateNullPeaks(peakInfoHolder[reductiveScan], cycleNum)
                
                # It is a New Cycle Everytime we Scan Forwards
                if segment%2 == 1:
                    cycleNum += 1
                # Stop if Next is Incomplete Segment; Else Continue Looping
                if cycleNum*2 == numberOfSegments+1:
                    print("HERE")
                    break
                continue
            elif cellVal.startswith("Ep = "):
                Ep = [float(x.split(":")[0]) for x in re.findall("-?\d+.?\d*(?:[Ee]-\d+)?", cellVal)][0]
            # find the Peak Current in the Segment
            elif cellVal.startswith("ip = "):
                Ip = [float(x.split(":")[0]) for x in re.findall("-?\d+.?\d*(?:[Ee]-\d+)?", cellVal)][0]
                
                # Check if the scan is reductive or oxidative
                reductiveScan = not (segment%2 == 1)
                # Check if this is the first peak in the cycle
                if len(peakInfoHolder[reductiveScan]) == cycleNum:
                    peakInfoHolder[reductiveScan].append([])
                # Add the peaks to the cycle
                peakInfoHolder[reductiveScan] = self.addPeakInfo_SearchEp(peakInfoHolder[reductiveScan], Ep, Ip, np.nan, [], cycleNum-1)
        
        # Add the peaks to the cycle
        peakInfoHolder[0] = self.populateNullPeaks(peakInfoHolder[0], cycleNum)
        peakInfoHolder[1] = self.populateNullPeaks(peakInfoHolder[1], cycleNum)

        return peakInfoHolder
    
    def getPeaks(self, potentialFrames, currentFrames, pointsPerSegment):        
        # Create data structures to hold information: [OXIDATION, REDUCTION]
        peakInfoHolder = [[], []]
        
        # Loop through each CV cycle
        for cycleNum in range(len(potentialFrames)):
            # Extract the Potential and the Current
            potentialFull = potentialFrames[cycleNum]
            currentFull = currentFrames[cycleNum]
            
            # Extract each segment in the scan
            for segmentScale in range(2):
                potential = potentialFull[segmentScale*pointsPerSegment:(segmentScale+1)*pointsPerSegment]
                current = currentFull[segmentScale*pointsPerSegment:(segmentScale+1)*pointsPerSegment]

                # Analyze each segment
                linearFit, peakPotential, peakCurrent, linearFitBounds, reductiveScan = self.analyzeCV.findPeaks(potential, current)

                # If a peak was found
                if len(linearFit) != 0:
                    # Store the data as reductive or oxidative
                    linearFitBounds += segmentScale*pointsPerSegment
                    linearFit = np.concatenate((([0]*segmentScale*pointsPerSegment), linearFit))
                    peakInfoHolder[reductiveScan] = self.addPeakInfo_SearchEp(peakInfoHolder[reductiveScan], peakPotential, peakCurrent, linearFitBounds, linearFit, cycleNum)
                # Finish the cycle giving every peak we are tracking a value
                peakInfoHolder[reductiveScan] = self.populateNullPeaks(peakInfoHolder[reductiveScan], cycleNum+1)
        
        # Add the peaks to the cycle
        peakInfoHolder[0] = self.populateNullPeaks(peakInfoHolder[0], cycleNum+1)
        peakInfoHolder[1] = self.populateNullPeaks(peakInfoHolder[1], cycleNum+1)

        return peakInfoHolder
            
    def processCV(self, xlWorksheet, xlWorkbook):  
        # Get the details about the the CV program
        startRow, scanRate, pointsPerScan, pointsPerSegment, startSegment, numberOfSegments, skipOffset = self.getRunInfo(xlWorksheet)
        
        # Get the Current/Potential/Times of each CV scan.
        currentFrames, potentialFrames, timeFrames = self.extractCHIData(xlWorksheet, startRow, scanRate, pointsPerScan)
        print("\tFinished Data Extraction");
        
        # Find the peaks in each CV scan
        if self.useCHIPeaks:
            peakInfoHolder = self.getPeaksCHI(xlWorksheet, startRow, startSegment, skipOffset, numberOfSegments)
        else:
            peakInfoHolder = self.getPeaks(potentialFrames, currentFrames, pointsPerSegment)
            
        # Finished Data Collection: Close Workbook and Return Data to User
        xlWorkbook.close()
        print("\tFinished Data Analysis");
        return peakInfoHolder, currentFrames, potentialFrames, timeFrames

    
    
    