
"""
Need to Install in the Python Enviroment Beforehand:
    $ pip install BaselineRemoval
"""

# Import Basic Modules
import numpy as np
# Import Modules for Low Pass Filter
from scipy.signal import butter 
# Import Modules to Find Peak
import scipy.signal
from scipy.signal import savgol_filter
# Modules to Plot
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------------#
# --------------------- Specify/Find File Names -----------------------------#

class cvAnalysis():
    
    def __init__(self):
        self.lowPassCutoff = 100
            
    def findPeaks(self, xData, yData, plotResult = False):
        xData = np.array(xData)
        yData = np.array(yData)
        
        # ------------------------- Check if OX/Red ------------------------ #
        # Determine Whether the Data is Oxidative or Reductive
        numNegative = sum(1 for val in yData if val < 0)
        reductiveScan = numNegative > len(yData)/2
        
        # If reduction, temporarily analyze the data as oxidative
        if reductiveScan:
            xData = np.flip(xData)
            yData = yData*-1
        # ------------------------------------------------------------------ #

        # ------------------------- Filter the Data ------------------------ #
        # Apply a Low Pass Filter
        samplingFreq = abs(len(xData)/(xData[-1] - xData[0]))
        yData = self.butterFilter(yData, self.lowPassCutoff, samplingFreq, order = 3, filterType = 'low')
        
        # Apply smoothing
        yData = savgol_filter(yData, 101, 3)
        # ------------------------------------------------------------------ #

        # --------------------- Find the Chemical Peak --------------------- #
        # Initialize the constructor
        peakAnalysis = bestLinearFit()
        # Find Peaks in the Data
        chemicalPeakInd = peakAnalysis.findPeak(xData, yData)
        # Return None if No Peak Found
        if chemicalPeakInd == None:
            print("No Peak Found in Data")
            return [], -1, -1, np.array([np.nan, np.nan]), -1
        # ------------------------------------------------------------------ #
        
        # ------------------------ Find the Baseline ----------------------- #
        # Find the middle of the baseline
        firstDeriv = savgol_filter(np.gradient(yData, 2), 55, 3)
        midBaseline = peakAnalysis.findNearbyMinimum(firstDeriv, 0, 1)
        # Find the baseline
        leftBaselineInd, rightBaselineInd = peakAnalysis.findSmallestSlope(xData[0:chemicalPeakInd], yData[0:chemicalPeakInd], midBaseline, int(midBaseline/3))

        # Linear fit the baseline
        lineSlope, slopeIntercept = np.polyfit(xData[[leftBaselineInd, rightBaselineInd]], yData[[leftBaselineInd, rightBaselineInd]], 1)
        linearFit = lineSlope*xData + slopeIntercept
        
        # Readjust the chemical peak
        baselineData = yData - linearFit
        chemicalPeakInd = peakAnalysis.findClosestMax(baselineData, chemicalPeakInd, 5)
        
        # Check if the peak is cutoff
        if chemicalPeakInd == len(xData) - 1:
            print("Poor Peak Shape")
            return [], -1, -1, np.array([np.nan, np.nan]), -1
        # ------------------------------------------------------------------ #

        # -------------- If Reduction, Transform Analysis Back ------------- #
        # If reduction, temporarily analyze the data as oxidative
        if reductiveScan:
            # Reverse the x-axis
            xData = np.flip(xData)
            # Flip the y-axis
            linearFit = linearFit*-1
            yData = yData*-1
        # ------------------------------------------------------------------ #
        
        # ----------------------- Extract Information ---------------------- #
        peakPotential = xData[chemicalPeakInd]
        peakCurrent = yData[chemicalPeakInd] - linearFit[chemicalPeakInd]
        
        linearFitBounds = np.array([leftBaselineInd, chemicalPeakInd], dtype=object)
        
        if plotResult:
            peakAnalysis.plotLinearFit(xData, yData, linearFit, baselineData, chemicalPeakInd)
        # ------------------------------------------------------------------ #
        
        return linearFit, peakPotential, peakCurrent, linearFitBounds, reductiveScan
            
    def butterParams(self, cutoffFreq = [0.1, 7], samplingFreq = 800, order=3, filterType = 'low'):
        nyq = 0.5 * samplingFreq
        if filterType == "band":
            normal_cutoff = [freq/nyq for freq in cutoffFreq]
        else:
            normal_cutoff = cutoffFreq / nyq
        sos = butter(order, normal_cutoff, btype = filterType, analog = False, output='sos')
        return sos
    
    def butterFilter(self, data, cutoffFreq, samplingFreq, order = 3, filterType = 'band'):
        sos = self.butterParams(cutoffFreq, samplingFreq, order, filterType)
        return scipy.signal.sosfiltfilt(sos, data)
        

class bestLinearFit:
    
    def __init__(self):
        self.minLeftBoundaryInd = 100
        self.minPeakDuration = 10
        
    # ---------------------------------------------------------------------- #
    # ---------------------------- Find Baseline --------------------------- #
    
    def findLinearBaseline(self, xData, yData, peakInd):
        # Define a threshold for distinguishing good/bad lines
        maxBadPointsTotal = int(len(xData)/10)
        # Store Possibly Good Tangent Indexes
        goodTangentInd = [[] for _ in range(maxBadPointsTotal)]
        
        # For Each Index Pair on the Left and Right of the Peak
        for rightInd in range(peakInd+2, len(yData), 1):
            for leftInd in range(peakInd-2, self.minLeftBoundaryInd, -1):
                
                # Initialize range of data to check
                checkPeakBuffer = int((rightInd - leftInd)/4)
                xDataCut = xData[max(0, leftInd - checkPeakBuffer):rightInd + checkPeakBuffer]
                yDataCut = yData[max(0, leftInd - checkPeakBuffer):rightInd + checkPeakBuffer]
                
                # Draw a Linear Line Between the Points
                lineSlope = (yData[leftInd] - yData[rightInd])/(xData[leftInd] - xData[rightInd])
                slopeIntercept = yData[leftInd] - lineSlope*xData[leftInd]
                linearFit = lineSlope*xDataCut + slopeIntercept

                # Find the Number of Points Above the Tangent Line
                numWrongSideOfTangent = len(linearFit[linearFit - yDataCut > 0])
                
                # If a Tangent Line is Drawn Correctly, Return the Tangent Points' Indexes
                # if numWrongSideOfTangent == 0 and rightInd - leftInd > self.minPeakDuration:
                #     return (leftInd, rightInd)
                # Define a threshold for distinguishing good/bad lines
                maxBadPoints = int(len(linearFit)/10) # Minimum 1/6
                if numWrongSideOfTangent < maxBadPoints and rightInd - leftInd > self.minPeakDuration:
                    goodTangentInd[numWrongSideOfTangent].append((leftInd, rightInd))
                    
        # If Nothing Found, Try and Return a Semi-Optimal Tangent Position
        for goodInd in range(maxBadPointsTotal):
            if len(goodTangentInd[goodInd]) != 0:
                return max(goodTangentInd[goodInd], key=lambda tangentPair: tangentPair[1]-tangentPair[0])
        return None, None
    
    def findSmallestSlope(self, xData, yData, midLineInd, minLength):
        leftIndBest = midLineInd-1; rightIndBest = midLineInd+1
        smallestSlope = (yData[-1] - yData[0])/(xData[-1] - xData[0])
        
        # For Each Index Pair on the Left and Right of the Peak
        for rightInd in range(midLineInd, len(yData), 1):
            for leftInd in range(midLineInd, -1, -1):
                if rightInd-leftInd < minLength:
                    continue
            
                # Get the slope of the line
                lineSlope = (yData[leftInd] - yData[rightInd])/(xData[leftInd] - xData[rightInd])
                if lineSlope < 0:
                    continue
                
                # Take the smallest slope
                if lineSlope < smallestSlope:
                    smallestSlope = lineSlope
                    leftIndBest = leftInd
                    rightIndBest = rightInd
                elif lineSlope == smallestSlope and rightIndBest-leftIndBest < rightInd-leftInd:
                    leftIndBest = leftInd
                    rightIndBest = rightInd  
        
        return leftIndBest, rightIndBest
                
                
    # ---------------------------------------------------------------------- #
    # ------------------------------ Find Peak ----------------------------- #
    
    def findClosestMax(self, data, xPointer, binarySearchWindow = 1, maxPointsSearch = 500):
        newPointer_Left = self.findNearbyMaximum(data, xPointer, -binarySearchWindow, maxPointsSearch)
        newPointer_Right = self.findNearbyMaximum(data, xPointer, binarySearchWindow, maxPointsSearch)
        if newPointer_Right == xPointer and newPointer_Left == xPointer:
            if binarySearchWindow > 10:
                return xPointer
            return self.findClosestMax(data, xPointer, binarySearchWindow*2, maxPointsSearch)
        if newPointer_Right == xPointer:
            return newPointer_Left
        elif newPointer_Left == xPointer:
            return newPointer_Right
        else:
            return max([newPointer_Left, newPointer_Right], key = lambda ind: data[ind])  
    
    def findNearbyMinimum(self, data, xPointer, binarySearchWindow = 5, maxPointsSearch = 500):
        """
        Search Right: binarySearchWindow > 0
        Search Left: binarySearchWindow < 0
        """
        # Base Case
        if abs(binarySearchWindow) < 1 or maxPointsSearch == 0:
            searchSegment = data[max(0,xPointer-1):min(xPointer+2, len(data))]
            xPointer -= np.where(searchSegment==data[xPointer])[0][0]
            return xPointer + np.argmin(searchSegment) 
        
        maxHeightPointer = xPointer
        maxHeight = data[xPointer]; searchDirection = binarySearchWindow//abs(binarySearchWindow)
        # Binary Search Data to Find the Minimum (Skip Over Minor Fluctuations)
        for dataPointer in range(max(xPointer, 0), max(0, min(xPointer + searchDirection*maxPointsSearch, len(data))), binarySearchWindow):
            # If the Next Point is Greater Than the Previous, Take a Step Back
            if data[dataPointer] >= maxHeight and xPointer != dataPointer:
                return self.findNearbyMinimum(data, dataPointer - binarySearchWindow, round(binarySearchWindow/4), maxPointsSearch - searchDirection*(abs(dataPointer - binarySearchWindow)) - xPointer)
            # Else, Continue Searching
            else:
                maxHeightPointer = dataPointer
                maxHeight = data[dataPointer]

        # If Your Binary Search is Too Large, Reduce it
        return self.findNearbyMinimum(data, maxHeightPointer, round(binarySearchWindow/2), maxPointsSearch-1)
    

    def findNearbyMaximum(self, data, xPointer, binarySearchWindow = 5, maxPointsSearch = 500):
        """
        Search Right: binarySearchWindow > 0
        Search Left: binarySearchWindow < 0
        """
        # Base Case
        xPointer = min(max(xPointer, 0), len(data)-1)
        if abs(binarySearchWindow) < 1 or maxPointsSearch == 0:
            searchSegment = data[max(0,xPointer-1):min(xPointer+2, len(data))]
            xPointer -= np.where(searchSegment==data[xPointer])[0][0]
            return xPointer + np.argmax(searchSegment)
        
        minHeightPointer = xPointer; minHeight = data[xPointer];
        searchDirection = binarySearchWindow//abs(binarySearchWindow)
        # Binary Search Data to Find the Minimum (Skip Over Minor Fluctuations)
        for dataPointer in range(xPointer, max(0, min(xPointer + searchDirection*maxPointsSearch, len(data))), binarySearchWindow):
            # If the Next Point is Greater Than the Previous, Take a Step Back
            if data[dataPointer] < minHeight and xPointer != dataPointer:
                return self.findNearbyMaximum(data, dataPointer - binarySearchWindow, round(binarySearchWindow/2), maxPointsSearch - searchDirection*(abs(dataPointer - binarySearchWindow)) - xPointer)
            # Else, Continue Searching
            else:
                minHeightPointer = dataPointer
                minHeight = data[dataPointer]

        # If Your Binary Search is Too Large, Reduce it
        return self.findNearbyMaximum(data, minHeightPointer, round(binarySearchWindow/2), maxPointsSearch-1)
    
    
    def findPeak(self, xData, yData, ignoredBoundaryPoints = 10, deriv = False):
        # Find All Peaks in the Data
        peakInfo = scipy.signal.find_peaks(yData, prominence=10E-10, width=20, distance = 20)
        # Extract the Peak Information
        peakProminences = peakInfo[1]['prominences']
        peakIndices = peakInfo[0]
        
        # Remove Peaks Nearby Boundaries
        allProminences = peakProminences[np.logical_and(peakIndices < len(xData) - ignoredBoundaryPoints, peakIndices >= ignoredBoundaryPoints)]
        peakIndices = peakIndices[np.logical_and(peakIndices < len(xData) - ignoredBoundaryPoints, peakIndices >= ignoredBoundaryPoints)]
        # If Peaks are Found
        if len(peakIndices) > 0:
            # Take the Most Prominent Peak
            bestPeak = allProminences.argmax()
            peakInd = peakIndices[bestPeak]
            return self.findClosestMax(yData, peakInd, binarySearchWindow = 5)
        elif not deriv:
            filteredVelocity = savgol_filter(np.gradient(yData), 55, 3)
            peakInd = self.findPeak(xData, filteredVelocity, deriv = True)
            if peakInd != None:
                return self.findClosestMax(yData, peakInd, binarySearchWindow = 5)
            return peakInd
        # If No Peak is Found, Return None
        return None

    
    def plotLinearFit(self, potential, current, linearFit, baselineData, peakInd):
        plt.figure()
        # filteredVelocity = savgol_filter(np.gradient(current), 55, 3)
        # filteredAccel = savgol_filter(np.gradient(filteredVelocity), 55, 3)
        # plt.plot(potential, filteredVelocity/max(filteredVelocity))

        plt.plot(potential, current, 'k-', linewidth= 2)
        plt.plot(potential, linearFit, 'tab:red', '-', linewidth= 0.4)
        plt.plot(potential, baselineData, 'tab:blue', '-', linewidth= 2, alpha = 0.4)
        plt.plot(potential[[peakInd, peakInd]], [linearFit[peakInd], current[peakInd]], 'tab:purple', '-', linewidth= 2, alpha = 0.7)
        plt.show()


