
# -------------------------------------------------------------------------- #
# ---------------------------- Imported Modules ---------------------------- #

# General
import scipy
import numpy as np
# Import Modules to Find Peak
import scipy.signal
# Modules to Plot
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------#
# ---------------------- Linear Baseline Subtraction  ---------------------- #

class bestLinearFit:
    
    def __init__(self, samplingFreq):
        # Specify peak parameters.
        self.minPeakDistance = samplingFreq*0.1
        self.samplingFreq = samplingFreq
        self.ignoredBoundaryPoints = 10
        self.minLeftBoundaryInd = 100
        self.minPeakDuration = samplingFreq*0.02
    
    # ---------------------------------------------------------------------- #
    # ------------------------------ Find Peak ----------------------------- #
    
    def findPeaks(self, xData, yData, deriv = False):
        # Find All Peaks in the Data
        peakInfo = scipy.signal.find_peaks(yData, prominence=10E-10, width=20, distance = self.minPeakDistance)
        
        # Extract the peak information
        peakProminences = peakInfo[1]['prominences']
        peakIndices = peakInfo[0]
        # Remove peaks near boundaries
        goodIndicesMask = np.logical_and(peakIndices < len(xData) - self.ignoredBoundaryPoints, peakIndices >= self.ignoredBoundaryPoints)
        peakProminences = peakProminences[goodIndicesMask]
        peakIndices = peakIndices[goodIndicesMask]
        
        # If peaks are found in the data
        if len(peakIndices) == 0 and not deriv:
            # Analyze the peaks in the first derivative.
            filteredVelocity = scipy.signal.savgol_filter(yData, 55, 3, deriv=1)
            return self.findPeaks(xData, filteredVelocity, deriv = True)
        # If no peaks found, return an empty list.
        return peakIndices
    
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
        for rightInd in range(midLineInd+1, len(yData), 1):
            for leftInd in range(midLineInd-1, -1, -1):
                if rightInd-leftInd < minLength:
                    continue
                
                # Draw a Linear Line Between the Points
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
    # ------------------------- Data Visualization ------------------------- #   
    
    def plotLinearFit(self, potential, current, allLinearFits, allBaselineData, finalPeaks):
        plt.figure()
        # Plot the signal data
        plt.plot(potential, current, 'k-', linewidth= 2)
        # Plot the linear fits
        for linearFit in allLinearFits:
            plt.plot(potential, linearFit, 'tab:red', '-', linewidth= 0.4)
        # Plot the baseline data
        for baselineData in allBaselineData:
            plt.plot(potential, baselineData, 'tab:blue', '-', linewidth= 2, alpha = 0.4)
        # Plot the peaks
        for peakInd in finalPeaks:
            plt.plot(potential[[peakInd, peakInd]], [linearFit[peakInd], current[peakInd]], 'tab:purple', '-', linewidth= 2, alpha = 0.7)
        plt.show()


