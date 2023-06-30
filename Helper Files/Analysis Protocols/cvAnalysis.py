
# -------------------------------------------------------------------------- #
# ---------------------------- Imported Modules ---------------------------- #

# Import Basic Modules
import numpy as np
# Import Modules to Find Peak
import scipy.signal
from scipy.signal import savgol_filter
# Modules to Plot
import matplotlib.pyplot as plt

# Import filtering file
import _baselineProtocols   # Import class with baseline methods.
import _filteringProtocols  # Import class with filtering methods.
import _universalProtocols

# -------------------------------------------------------------------------- #
# ------------------------------ CV Protocol ------------------------------- #

class cvProtocol():
    
    def __init__(self):
        # CV parameters.
        self.lowPassCutoff = 100
        
        # Initialize baseline subtraction classes.
        self.linearBaselineFit = _baselineProtocols.bestLinearFit()
        
        # Define general classes to process data.
        self.filteringMethods = _filteringProtocols.filteringMethods()
        self.universalMethods = _universalProtocols.universalMethods()
        
    def isReductiveScan(self, firstDeriv, samplingFreq):
        # See if the first derivative of the initial points are positive or negative.
        initialScanDeriv = firstDeriv[0:int(samplingFreq*0.1)]
        if len(initialScanDeriv)/2 < (initialScanDeriv > 0).sum():
            return False
        return True
            
    def flipReductiveData(self, potential = [], allCurrents =  []):
        # Flip the reductive scan in the positive direction.
        if len(potential) != 0:
            potential = np.flip(potential)
            
        if len(allCurrents) != 0:
            for dataInd in range(len(allCurrents)):
                allCurrents[dataInd] = -allCurrents[dataInd]
        
        return potential, allCurrents
            
    def findLinearFit(self, xData, yData, leftInd, rightInd):
        # Draw a Linear Line Between the Points
        lineSlope = (yData[leftInd] - yData[rightInd])/(xData[leftInd] - xData[rightInd])
        slopeIntercept = yData[leftInd] - lineSlope*xData[leftInd]
        linearFit = lineSlope*xData + slopeIntercept
        
        return linearFit
    
    def analyzeData(self, potential, current, plotResult = False):
        potential = np.asarray(potential)
        current = np.asarray(current)

        # ------------------------- Filter the Data ------------------------ #
        # Apply a Low Pass Filter
        samplingFreq = abs(len(potential)/(potential[-1] - potential[0]))
        current = self.filteringMethods.bandPassFilter.butterFilter(current, self.lowPassCutoff, samplingFreq, order = 3, filterType = 'low')

        # Apply smoothing
        current = savgol_filter(current, max(5, int(samplingFreq*0.01)), 3)
        # ------------------------------------------------------------------ #
        
        # ------------------------- Check if OX/Red ------------------------ #
        # Calculate the derivative of the CV curve.
        firstDeriv = savgol_filter(current, int(samplingFreq*0.1), 3, deriv = 1)
        
        # Check if the data is oxidative or reductive.
        reductiveScan = self.isReductiveScan(firstDeriv, samplingFreq)
        
        # If reduction.
        if reductiveScan:
            # Analyze the data as oxidative.
            potential, [firstDeriv, current] = self.flipReductiveData(potential, [firstDeriv, current])
        # ------------------------------------------------------------------ #

        # --------------------- Find the Chemical Peak --------------------- #
        # Find Peaks in the Data
        peakIndices = self.linearBaselineFit.findPeaks(potential, current)
        # Return None if No Peak Found
        if len(peakIndices) == 0:
            print("\tNo Peak Found in Data")
            return [], [], [], [], -1
        
        # ----------------------------------------------------s-------------- #
        
        # ------------------------ Find the Baseline ----------------------- #        
        # Estimate where the baseline points are near.
        midBaselineInd = self.universalMethods.findNearbyMinimum(firstDeriv, 0, binarySearchWindow = int(samplingFreq*0.01))
        # Setup the data collectio parameters.
        sortedPeaks = sorted(peakIndices)
        allLinearFitBounds = []
        allBaselineData = []
        peakPotentials = []
        allLinearFits = []
        peakCurrents = []
        lastPeakInd = 0
        finalPeaks = []
        
        # For each peak found.
        for sortedPeakInd in range(len(sortedPeaks)):
            peakInd = sortedPeaks[sortedPeakInd]
            
            # Find the baseline and perform a linear baseline fit.
            leftBaselineInd, rightBaselineInd = self.linearBaselineFit.findSmallestSlope(potential[lastPeakInd:peakInd], current[lastPeakInd:peakInd], midBaselineInd, int(peakInd - lastPeakInd/3))
            linearFit = self.findLinearFit(potential, current, leftBaselineInd, rightBaselineInd)

            # Readjust the chemical peak
            baselineData = current - linearFit
            peakInd = self.universalMethods.findLocalMax(baselineData, peakInd, binarySearchWindow = 5)
            
            # Ignore bad peaks.
            if peakInd == len(potential) - 1:
                continue
            lastPeakInd = peakInd
            
            # If there is another peak to analyze
            if sortedPeakInd < len(sortedPeaks) - 1:
                nextPeakInd = sortedPeaks[sortedPeakInd+1]
                # Check if we need to recalibrate the baseline
                intervalPoints = baselineData[peakInd:nextPeakInd]
                if samplingFreq*0.03 < (intervalPoints < 0).sum():
                    print("HERE")
                    # Find the baseline from both sides of the peak.
                    midBaselineInd_Left = self.universalMethods.findNearbyMinimum(baselineData, peakInd, 1)
                    midBaselineInd_Right = self.universalMethods.findNearbyMinimum(baselineData, nextPeakInd, -1)
                    # Use the middle between both of the baselines.
                    midBaselineInd = int((midBaselineInd_Left + midBaselineInd_Right)/2)
            
            # Organize the variables.
            peakCurrent = baselineData[peakInd]
            # Acount for flipped data.
            if reductiveScan:
                # Flip the data.
                flippedPotential, [baselineData, linearFit] = self.flipReductiveData(potential.copy(), [baselineData, linearFit])
                # Get the peak potential
                peakPotential = flippedPotential[peakInd]
            else:
                peakPotential = potential[peakInd]
                
            # Organize the peak information.
            finalPeaks.append(peakInd)
            allLinearFits.append(linearFit)
            peakCurrents.append(peakCurrent)
            peakPotentials.append(peakPotential)
            allBaselineData.append(baselineData)
            allLinearFitBounds.append([leftBaselineInd, peakInd])
            
        # If reduction.
        if reductiveScan:
            # Convert the data back to reductive.
            potential, [current] = self.flipReductiveData(potential, [current])
        # ------------------------------------------------------------------ #
        
        # ----------------------- Extract Information ---------------------- #
        allLinearFitBounds = np.array(allLinearFitBounds)
        
        if plotResult:
            self.linearBaselineFit.plotLinearFit(potential, current, allLinearFits, allBaselineData, finalPeaks)
        # ------------------------------------------------------------------ #
        
        return allLinearFits, peakPotentials, peakCurrents, allLinearFitBounds, reductiveScan


