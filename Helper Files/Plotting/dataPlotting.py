
# -------------------------------------------------------------------------- #
# ------------------------- Imported Modules --------------------------------#

# Basic Modules
import sys
import numpy as np
# Modules to Plot
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.animation as manimation

# -------------------------------------------------------------------------- #
# ------------------------- Plotting Functions ------------------------------#

class plotDataCV:
    
    def __init__(self, filename, outputDirectory, showFullInfo, showPeakCurrent, useCHIPeaks, seePastCVData):
        # Protocol Flags
        self.useCHIPeaks = useCHIPeaks
        self.showFullInfo = showFullInfo
        self.seePastCVData = seePastCVData
        self.showPeakCurrent = showPeakCurrent
        
        # Specify file information
        self.outputDirectory = outputDirectory
        
        # Initialize axes
        self.figure = None
        self.axLeft = None
        self.axRight = None
        self.axLowerLeft = None
        self.axLowerRight = None
        
        # Specify figure aesthetics
        self.title = filename
        self.figureWidth = 20; self.figureHeight = 8
        
        # Specify the colors to plot each peak current: OXIDATION, REDUCTION
        self.peakCurrentColorOrder = [
            ["tab:red", "tab:blue", "tab:orange", "tab:green", "black"],
            ["tab:brown", "tab:purple", "tab:pink", "tab:cyan", "tab:gray"]]
    
    def plotCurves(self, potentialFrames, currentFrames, timeFrames, peakInfoHolder):
        print("\tPlotting the Data")
        # Initialize the canvas for plotting
        self.initializeFigure(peakInfoHolder)
        self.initializePlots(peakInfoHolder, potentialFrames, currentFrames)
        
        # Plot the data
        self.plotMovieCV(potentialFrames, currentFrames, timeFrames, peakInfoHolder)
        
    def addAxisPlots(self, ax, peakInfoHolder):
        peakPlots = [[], []]  # OXIDATION, REDUCTION
        # For Oxidation and Reduction peaks
        for reductionScan in range(2):
            # Initialize a plot for every peak possible inside one CV scan
            for peakNum in range(len(peakInfoHolder[reductionScan])):
                peakPlots[reductionScan].append(ax.plot([], [], '-o', c=self.peakCurrentColorOrder[reductionScan][peakNum%len(self.peakCurrentColorOrder[reductionScan])], linewidth=1)[0])
        return peakPlots
        
    def initializeFigure(self, peakInfoHolder):
        # Initialize Plot Figure (Must be BEFORE MovieWriter Initialization)
        if self.showPeakCurrent and (len(peakInfoHolder[0]) != 0 or len(peakInfoHolder[1]) != 0):
            if self.showFullInfo:
                self.figure, ax = plt.subplots(2, 2, sharey=False, sharex = False, figsize=(self.figureWidth,self.figureHeight))
                self.axLeft = ax[0,0]; self.axRight = ax[0,1]
                self.axLowerLeft = ax[1,0]; self.axLowerRight = ax[1,1]
            else:
                self.figure, ax = plt.subplots(1, 2, sharey=False, sharex = False, figsize=(self.figureWidth,self.figureHeight))
                self.axLeft = ax[0]; self.axRight = ax[1]
        else:
            self.figure, self.axLeft = plt.subplots(1, 1, sharey=False, sharex = False, figsize=(self.figureWidth/2,self.figureHeight))

    def initializePlots(self, peakInfoHolder, potentialFrames, currentFrames):
        # Initialize Movie Writer for Plots
        metadata = dict(title=self.title, artist='Matplotlib', comment='Movie support!')
        self.writer = matplotlib.animation.FFMpegWriter(fps=7, metadata=metadata)
        self.movieGraphLeftCurrent = self.axLeft.plot([0], [0], 'tab:blue', '-', linewidth=1, alpha = 1)[0]
        if self.seePastCVData:
            self.movieGraphLeftPrev = self.axLeft.plot([0], [0], 'tab:blue', '-', linewidth=1, alpha = 0.1)[0]
        if not self.useCHIPeaks:
            # Create lines to show the peak detection for the reduction segment
            movieGraphLeftBaseline_Red = self.axLeft.plot([0], [0], 'tab:red', '-', linewidth=1, alpha = 1)[0]
            movieGraphLeftPeak_Red = self.axLeft.plot([0], [0], 'black', '-', linewidth=1, alpha = 1)[0]
            # Create lines to show the peak detection for the reduction segment
            movieGraphLeftBaseline_Ox = self.axLeft.plot([0], [0], 'tab:red', '-', linewidth=1, alpha = 1)[0]
            movieGraphLeftPeak_Ox = self.axLeft.plot([0], [0], 'black', '-', linewidth=1, alpha = 1)[0]
            # Combine them into one data structure
            self.movieGraphLeftBaseline_RedOx = [movieGraphLeftBaseline_Red, movieGraphLeftBaseline_Ox]
            self.movieGraphLeftPeak_RedOx = [movieGraphLeftPeak_Red, movieGraphLeftPeak_Ox]

        # Get the global bounds for the plots
        axLeft_yMin, axLeft_yMax, axRight_yMin, axRight_yMax, axLowerLeft_yMin, axLowerLeft_yMax = self.calculatePlotBounds(peakInfoHolder, currentFrames)
            
        # Set Axis X,Y Limits
        pointsPerScan = len(potentialFrames[0])
        self.axLeft.set_xlim(potentialFrames[0][0], potentialFrames[0][int(pointsPerScan/2)])
        self.axLeft.set_ylim(axLeft_yMin, axLeft_yMax)
        # Label Axis + Add Title
        self.axLeft.set_title("CV Scan over Time")
        self.axLeft.set_xlabel("Potential (Volts)")
        self.axLeft.set_ylabel("Current (uAmps)")
                
        if self.showPeakCurrent and (len(peakInfoHolder[0]) != 0 or len(peakInfoHolder[1]) != 0):
            
            # Set Axis X,Y Limits for the peakCurrent (right axis)
            self.axRight.set_xlim(0, len(potentialFrames))
            self.axRight.set_ylim(axRight_yMin, axRight_yMax)
            # Set figure labels
            self.axRight.set_title("Peak Current Stability over Time")
            self.axRight.set_xlabel("Cycle Number")
            self.axRight.set_ylabel("Peak Current (uAmps)")
            # Set the right axis: plotting peak current for every scan
            self.peakCurrentPlots = self.addAxisPlots(self.axRight, peakInfoHolder)
            
            # If Adding Potential and Standard Deviation
            if self.showFullInfo:
                # Set Axis X,Y Limits for the peakCurrent (right axis)
                self.axLowerLeft.set_xlim(0, len(potentialFrames))
                self.axLowerLeft.set_ylim(axLowerLeft_yMin, axLowerLeft_yMax)
                # Set figure labels
                self.axLowerLeft.set_title("Peak Potential Stability over Time")
                self.axLowerLeft.set_xlabel("Cycle Number")
                self.axLowerLeft.set_ylabel("Peak Potential (Volts)")
                # Set the lower left axis: plotting peak potential for every scan
                self.peakPotentialPlots = self.addAxisPlots(self.axLowerLeft, peakInfoHolder)
                
                # Set Axis X,Y Limits for the peakCurrent (right axis)
                self.axLowerRight.set_xlim(0, len(potentialFrames))
                self.axLowerRight.set_ylim(0, 30)
                # Set the lower right axis: plotting running coefficient of variation of the peak current
                self.axLowerRight.set_title("Coefficient of Variation of Peak Current")
                self.axLowerRight.set_xlabel("Cycle Number")
                self.axLowerRight.set_ylabel("Coefficient of Variation (%)")
                # Set the lower left axis: plotting peak potential for every scan
                self.peakCoVPlots = self.addAxisPlots(self.axLowerRight, peakInfoHolder)
        # Add padding to the figure
        self.figure.tight_layout(pad=2.0)
            
    def plotMovieCV(self, potentialFrames, currentFrames, timeFrames, peakInfoHolder):

        # Open Movie Writer and Add Data
        with self.writer.saving(self.figure, self.outputDirectory + self.title + ".mp4", 300):
            # Add Frames in the Order for Showing
            for frameNum in range(len(potentialFrames)):
                # Set Left Side
                x = np.array(potentialFrames[frameNum])
                y = np.array(currentFrames[frameNum])
                t = timeFrames[frameNum]
                self.axLeft.legend(["RunTime = " + str(round(t[0],2)) + " Seconds"], loc="upper left")
                self.movieGraphLeftCurrent.set_data(x, y)
                if self.seePastCVData and frameNum != 0:
                    self.movieGraphLeftPrev.set_data(np.array(potentialFrames[:frameNum]).flatten(), np.array(currentFrames[:frameNum]).flatten())
            
                # Set Right Side
                if self.showPeakCurrent and (len(peakInfoHolder[0]) != 0 or len(peakInfoHolder[1]) != 0):
                    legendListRight = []
                    # Loop through the oxidation and reduction plots
                    for reductiveScan in range(len(self.peakCurrentPlots)):                        
                        # Set scan type
                        if reductiveScan == 0:
                            scanDirection = "Oxidation Peak ("
                        elif reductiveScan == 1:
                            scanDirection = "Reduction Peak ("
                        else:
                            sys.exit("Something went wrong with peakInfoHolder")
                            
                        if not self.useCHIPeaks:
                            self.movieGraphLeftBaseline_RedOx[reductiveScan].set_data([], [])
                            self.movieGraphLeftPeak_RedOx[reductiveScan].set_data([], [])

                        # For each peak found in the frame
                        for peakNum in range(len(peakInfoHolder[reductiveScan])):
                            peakInfo_AllFrames = peakInfoHolder[reductiveScan][peakNum]
                            
                            # Extract the peak information for the current frame
                            peakInfo_CurrentFrame = peakInfo_AllFrames[frameNum]
                            peakPotential, peakCurrent, linearFitBounds, linearFit = peakInfo_CurrentFrame
                            
                            # If the peak was not found in this frame
                            if np.isnan(peakPotential):
                                # Label the peak as empty
                                legendListRight.append(scanDirection + str(peakNum+1) + "):      \n" +
                                                   "       Ep = NA\n" +
                                                   "       Ip = NA\n" +
                                                   "       CoV = NA")
                                continue
                                
                            # Get all the peak current and potentials
                            Ip_fromPreviousFrames = np.array(np.array(peakInfoHolder[reductiveScan][peakNum], dtype=object)[:frameNum+1, 1], dtype=float)
                            Ep_fromPreviousFrames = np.array(np.array(peakInfoHolder[reductiveScan][peakNum], dtype=object)[:frameNum+1, 0], dtype=float)
                            # Get a list of the current frames: x-axis
                            listOfFrames = np.arange(1,len(Ip_fromPreviousFrames)+1)
                            
                            CoefficientofVariationList = []
                            # Get Statistics of Peak Current.
                            for peakCurrentInd in range(len(Ip_fromPreviousFrames)):
                                currentsUpToFrame = Ip_fromPreviousFrames[:peakCurrentInd + 1]
                                if np.isnan(currentsUpToFrame[peakCurrentInd]):
                                    CoefficientofVariationList.append(np.nan)
                                elif len(currentsUpToFrame) - 1 <= np.sum(np.isnan(currentsUpToFrame)):
                                    CoefficientofVariationList.append(0)
                                else:
                                    # Calculate the CoV of the peak current
                                    peakSTD = np.nanstd(currentsUpToFrame, ddof=1)
                                    peakMean = abs(np.nanmean(currentsUpToFrame))
                                    CoefficientofVariation = (peakSTD/peakMean)*100
                                    CoefficientofVariationList.append(CoefficientofVariation)
                            
                            # Plot the peak currents for every CV segment; right plot
                            self.movieGraphRight = self.peakCurrentPlots[reductiveScan][peakNum]
                            legendListRight.append(scanDirection + str(peakNum+1) + "):      \n" +
                                                   "       Ep = " + "%.3g"%peakPotential + " Volts\n" +
                                                   "       Ip = " + "%.4g"%peakCurrent + " uAmps\n" +
                                                   "       CoV = " + "%.3g"%CoefficientofVariationList[-1] + "%")
                            self.movieGraphRight.set_data(listOfFrames, Ip_fromPreviousFrames)
                            
                            if not self.useCHIPeaks:
                                self.movieGraphLeftBaseline_RedOx[reductiveScan].set_data(x[linearFitBounds[0]:linearFitBounds[1]], linearFit[linearFitBounds[0]:linearFitBounds[1]])
                                self.movieGraphLeftPeak_RedOx[reductiveScan].set_data(x[ [linearFitBounds[1], linearFitBounds[1]] ], [ linearFit[linearFitBounds[1]], y[linearFitBounds[1]] ])
                            if self.showFullInfo:
                                # Plot the peak potential for every CV segment; lower left plot
                                self.movieGraphLowerLeft = self.peakPotentialPlots[reductiveScan][peakNum]
                                self.movieGraphLowerLeft.set_data(listOfFrames, Ep_fromPreviousFrames)
                                # ---------------------------------------- #
                                # Get Plot for Coefficient of VariationList
                                self.movieGraphLowerRight = self.peakCoVPlots[reductiveScan][peakNum]
                                # Plot the Data
                                self.movieGraphLowerRight.set_data(listOfFrames, CoefficientofVariationList)
                        self.axRight.legend(legendListRight, bbox_to_anchor=(1.025, 1.025), loc='upper left')
                        # figLegend = self.figure.legend(legendListRight, bbox_to_anchor=(1.0, 0.95), loc='upper left')
                        # figLegend.set_in_layout(True)
                        self.figure.tight_layout(pad=2.0)
                # Write to Video
                self.writer.grab_frame()
        plt.show()
    
    def calculatePlotBounds(self, peakInfoHolder, currentFrames):
        # Set the CV y-Limits
        smallestCurrent_CV = min(np.array(currentFrames).flatten())
        largestCurrent_CV = max(np.array(currentFrames).flatten())
        yMargins = abs(largestCurrent_CV - smallestCurrent_CV)*0.05
        smallestCurrent_CV -= yMargins
        largestCurrent_CV += yMargins
        
        # Get the bounds on the peak current
        largestPeakCurrent = np.nan; smallestPeakCurrent = np.nan
        largestPeakPotential = np.nan; smallestPeakPotential = np.nan
        for reductiveScan in range(2):
            for peakList in peakInfoHolder[reductiveScan]:
                for peak in peakList:
                    # Find the bounds on peak current
                    largestPeakCurrent = np.nanmax([largestPeakCurrent, peak[1]])
                    smallestPeakCurrent = np.nanmin([smallestPeakCurrent, peak[1]])
                    # Find the bounds on peak potential
                    largestPeakPotential = np.nanmax([largestPeakPotential, peak[0]])
                    smallestPeakPotential = np.nanmin([smallestPeakPotential, peak[0]])
                    
        yMargins = abs(largestPeakCurrent - smallestPeakCurrent) * 0.05 # plt.margins()[1], 0.05
        smallestPeakCurrent -= yMargins
        largestPeakCurrent += yMargins
        
        yMargins = abs(largestPeakPotential - smallestPeakPotential) * 0.05 # plt.margins()[1], 0.05
        smallestPeakPotential -= yMargins
        largestPeakPotential += yMargins
        
        return smallestCurrent_CV, largestCurrent_CV, smallestPeakCurrent, largestPeakCurrent, smallestPeakPotential, largestPeakPotential
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    