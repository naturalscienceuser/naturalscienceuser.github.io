import argparse
import arcpy
import numpy
import math

# If you want to run this tool outside the command line, remove the 4 lines below and assign DEMPath to wherever your
# DEM is
parser = argparse.ArgumentParser()
parser.add_argument("DEM", help="Path to DEM")
args = parser.parse_args()
DEMPath = args.DEM

KERNELSIZE = 5  # 5 means 5x5 cell kernel, 6 means 6x6 cell kernel, etc.

slopeRaster = arcpy.sa.Slope(DEMPath, "DEGREE")
array = arcpy.RasterToNumPyArray(slopeRaster)
rowNumberStart = 0
rowNumberEnd = KERNELSIZE
# We start to the left of the raster because the start of the upcoming loop moves the kernel to the right
columnNumberStart = -KERNELSIZE
columnNumberEnd = 0
meanRatios = minRatios = maxRatios = []
AREA2D = 25  # For 5x5 meter cells--if cells are different resolution, this parameter would need to change
meanArea3D = minArea3D = maxArea3D = 0

# arraySubset contains the cells in our 5x5 kernel
arraySubset = array[rowNumberStart:rowNumberEnd, columnNumberStart:columnNumberEnd]

while True:
    # move kernel to the right
    columnNumberStart += KERNELSIZE
    columnNumberEnd += KERNELSIZE
    arraySubset = array[rowNumberStart:rowNumberEnd, columnNumberStart:columnNumberEnd]
    # If we move past the edge of the raster, array subset will contain fewer cells
    if arraySubset.size < KERNELSIZE**2:  # If out of columns, move down and back to the left (like reading a book)
        columnNumberStart = 0
        columnNumberEnd = KERNELSIZE
        rowNumberStart += KERNELSIZE
        rowNumberEnd += KERNELSIZE
        arraySubset = array[rowNumberStart:rowNumberEnd, columnNumberStart:columnNumberEnd]
        if arraySubset.size < KERNELSIZE**2:  # If we run out of rows, we are done
            print("Done")
            break
    subsetMean = numpy.mean(arraySubset)
    subsetMin = numpy.min(arraySubset)
    subsetMax = numpy.max(arraySubset)
    # If the kernel contains null cells, the mean becomes -inf, in which case we skip that location
    if subsetMean == float("-inf"):
        continue
    meanArea3D = AREA2D / math.cos(math.radians(subsetMean))  # cos function only works on radians
    minArea3D = AREA2D / math.cos(math.radians(subsetMin))
    maxArea3D = AREA2D / math.cos(math.radians(subsetMax))
    meanRatios.append(AREA2D / meanArea3D)
    minRatios.append(AREA2D / minArea3D)
    maxRatios.append(AREA2D / maxArea3D)

# 2D:3D area ratios are contained in the lists "meanRatios", "minRatios", and "maxRatios"

