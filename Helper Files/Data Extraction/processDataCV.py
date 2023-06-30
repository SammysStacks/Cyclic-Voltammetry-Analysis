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
        for peakGroupInd in range(len(peakInfo_RedOx)):
            peaks = peakInfo_RedOx[peakGroupInd]
            
            # Add NAN as fillers for the missing values
            numMissing = cycleNum - len(peaks)
            if 0 < numMissing:
                peakInfo_RedOx[peakGroupInd].extend([[np.nan, np.nan, np.nan, []]]*numMissing)
        
        # Return the new peakInfo_RedOx with the value added
        return peakInfo_RedOx
        
    def addPeakInfo_toGroups(self, peakPotentialGroups, peakCurrentGroups, baselineBoundsGroups, 
                             baselineFitGroups, peakPotential, peakCurrent, linearFitBounds, linearFit, cycleNum):
        """
        peakInfo_RedOx: List of List of peakInds. 
        """
        peakGroupFound = False
        # For each set of peaks.
        for peakGroupInd in range(len(peakPotentialGroups)):
            peakPotentials = np.asarray(peakPotentialGroups[peakGroupInd])
            # Calculate the average potential for this peak (last 3 values)
            recentPeakPotentials = peakPotentials[~np.isnan(peakPotentials)][-3:]
                        
            # If there are recent peaks
            if len(recentPeakPotentials) != 0:
                # Take the average of the recent peak potentials
                peakPotentialAv = np.nanmean(recentPeakPotentials)
            else:
                # Else, take the average of all the peak ppoentials
                peakPotentialAv = np.nanmean(peakPotentials)
                
            # If the peakPotential is within range 
            if abs(peakPotential - peakPotentialAv) < self.maxPeakPotentialDeviation:
                peakGroupFound = True
                break

        # If no group was identified.
        if not peakGroupFound:
            # Make a new group.
            newGroupSingle = [np.nan] * cycleNum
            newGroupDouble = [[np.nan]*2] * cycleNum
            newGroupFull = [[np.nan]*len(linearFit)] * cycleNum
            # Add the group to the holders.
            baselineFitGroups.append(newGroupFull.copy())
            peakCurrentGroups.append(newGroupSingle.copy())
            peakPotentialGroups.append(newGroupSingle.copy())
            baselineBoundsGroups.append(newGroupDouble.copy())
            # Specify the group number
            peakGroupInd = -1

        
        # Then add the peak to this map
        baselineFitGroups[peakGroupInd].append(linearFit)
        peakCurrentGroups[peakGroupInd].append(peakCurrent)
        peakPotentialGroups[peakGroupInd].append(peakPotential)
        baselineBoundsGroups[peakGroupInd].append(linearFitBounds)
        
    def padAllGroups(self, peakPotentialGroups, peakCurrentGroups, baselineBoundsGroups, baselineFitGroups, cycleNum, numPoints):
        for groupInd in range(len(peakPotentialGroups)):
            if len(peakPotentialGroups[groupInd]) != cycleNum + 1:
                peakPotentialGroups[groupInd].append(np.nan)
                
            if len(peakCurrentGroups[groupInd]) != cycleNum + 1:
                peakCurrentGroups[groupInd].append(np.nan)
                
            if len(baselineBoundsGroups[groupInd]) != cycleNum + 1:
                baselineBoundsGroups[groupInd].append([np.nan]*2)
                
            if len(baselineFitGroups[groupInd]) != cycleNum + 1:
                baselineFitGroups[groupInd].append([np.nan]*numPoints)
        
    
# -------------------------------------------------------------------------- #
# ------------------------------ CV Extraction ----------------------------- #

class processData(generalAnalysis):
    
    def __init__(self, numInitCyclesToSkip, useCHIPeaks):
        super().__init__()
        # Initialize CV analysis
        self.analyzeCV = cvAnalysis.cvProtocol()
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
                assert False
                peakInfoHolder[reductiveScan] = self.addPeakInfo_toGroups(peakInfoHolder[reductiveScan], Ep, Ip, np.nan, [], cycleNum-1)
        
        # Add the peaks to the cycle
        peakInfoHolder[0] = self.populateNullPeaks(peakInfoHolder[0], cycleNum)
        peakInfoHolder[1] = self.populateNullPeaks(peakInfoHolder[1], cycleNum)

        return peakInfoHolder
    
    def getPeaks(self, potentialFrames, currentFrames, pointsPerSegment):        
        # Create data structures to hold information: [OXIDATION, REDUCTION]
        bothPeakPotentialGroups, bothPeakCurrentGroups = [[], []], [[], []]
        bothBaselineBoundsGroups, bothBaselineFitGroups = [[], []], [[], []]
                
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
                allLinearFits, peakPotentials, peakCurrents, allLinearFitBounds, reductiveScan = self.analyzeCV.analyzeData(potential, current)

                # For each peak found in the data.
                for fitInd in range(len(allLinearFits)):
                    linearFit, linearFitBounds = allLinearFits[fitInd], allLinearFitBounds[fitInd]
                    peakPotential, peakCurrent = peakPotentials[fitInd], peakCurrents[fitInd]
                    
                    # Compile all the data collected for this peak.
                    self.addPeakInfo_toGroups(bothPeakPotentialGroups[reductiveScan], bothPeakCurrentGroups[reductiveScan], 
                                              bothBaselineBoundsGroups[reductiveScan], bothBaselineFitGroups[reductiveScan], 
                                              peakPotential, peakCurrent, linearFitBounds, linearFit, cycleNum)
                
                self.padAllGroups(bothPeakPotentialGroups[reductiveScan], bothPeakCurrentGroups[reductiveScan], 
                                  bothBaselineBoundsGroups[reductiveScan], bothBaselineFitGroups[reductiveScan], cycleNum, len(potential))
                
        # bothBaselineFitGroups Dim: 2, # groups, # frames, # points per red/ox
        # bothPeakCurrentGroups Dim: 2, # groups, # frames
        # bothPeakPotentialGroups Dim: 2, # groups, # frames
        # bothBaselineBoundsGroups Dim: 2, # groups, # frames, # points per red/ox
        # Convert to numpy arrays.
        bothBaselineFitGroups[0] = np.asarray(bothBaselineFitGroups[0])
        bothPeakCurrentGroups[0] = np.asarray(bothPeakCurrentGroups[0])
        bothPeakPotentialGroups[0] = np.asarray(bothPeakPotentialGroups[0])
        bothBaselineBoundsGroups[0] = np.asarray(bothBaselineBoundsGroups[0])
        # Convert to numpy arrays.
        bothBaselineFitGroups[1] = np.asarray(bothBaselineFitGroups[1])
        bothPeakCurrentGroups[1] = np.asarray(bothPeakCurrentGroups[1])
        bothPeakPotentialGroups[1] = np.asarray(bothPeakPotentialGroups[1])
        bothBaselineBoundsGroups[1] = np.asarray(bothBaselineBoundsGroups[1])
        
        # Assert the integrity of all the data
        self.assertHolderIntegrity(bothPeakPotentialGroups[0], bothPeakCurrentGroups[0], bothBaselineBoundsGroups[0], bothBaselineFitGroups[0], len(potentialFrames), len(potential))
        self.assertHolderIntegrity(bothPeakPotentialGroups[1], bothPeakCurrentGroups[1], bothBaselineBoundsGroups[1], bothBaselineFitGroups[1], len(potentialFrames), len(potential))

        return bothPeakPotentialGroups, bothPeakCurrentGroups, bothBaselineBoundsGroups, bothBaselineFitGroups
            
    def assertHolderIntegrity(self, peakPotentialGroups, peakCurrentGroups, baselineBoundsGroups, baselineFitGroups, numFrames, numPoints):
        numGroups = len(peakPotentialGroups)
        if numGroups != 0:
            # Assert that the holders have the correct shape.
            assert peakCurrentGroups.shape == (numGroups, numFrames), peakCurrentGroups.shape
            assert peakPotentialGroups.shape == (numGroups, numFrames), peakPotentialGroups.shape
            assert baselineBoundsGroups.shape == (numGroups, numFrames, 2), baselineBoundsGroups.shape
            assert baselineFitGroups.shape == (numGroups, numFrames, numPoints), baselineFitGroups.shape
        else:
            # Assert that the holders have the correct shape.
            assert peakCurrentGroups.shape == (0,), peakCurrentGroups.shape
            assert peakPotentialGroups.shape == (0,), peakPotentialGroups.shape
            assert baselineBoundsGroups.shape == (0,), baselineBoundsGroups.shape
            assert baselineFitGroups.shape == (0,), baselineFitGroups.shape

    def processCV(self, xlWorksheet, xlWorkbook):  
        # Get the details about the the CV program
        startRow, scanRate, pointsPerScan, pointsPerSegment, startSegment, numberOfSegments, skipOffset = self.getRunInfo(xlWorksheet)
        
        # Get the Current/Potential/Times of each CV scan.
        currentFrames, potentialFrames, timeFrames = self.extractCHIData(xlWorksheet, startRow, scanRate, pointsPerScan)
        print("\tFinished Data Extraction");
        
        # Find the peaks in each CV scan
        if self.useCHIPeaks:
            bothPeakPotentialGroups, bothPeakCurrentGroups, bothBaselineBoundsGroups, bothBaselineFitGroups = self.getPeaksCHI(xlWorksheet, startRow, startSegment, skipOffset, numberOfSegments)
        else:
            bothPeakPotentialGroups, bothPeakCurrentGroups, bothBaselineBoundsGroups, bothBaselineFitGroups = self.getPeaks(potentialFrames, currentFrames, pointsPerSegment)
            
        # Finished Data Collection: Close Workbook and Return Data to User
        xlWorkbook.close()
        print("\tFinished Data Analysis");
        return bothPeakPotentialGroups, bothPeakCurrentGroups, bothBaselineBoundsGroups, bothBaselineFitGroups, currentFrames, potentialFrames, timeFrames

    
    
    