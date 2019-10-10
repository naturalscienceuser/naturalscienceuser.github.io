import arcpy
import csv
import os
import shutil
arcpy.env.overwriteOutput = True


class Toolbox(object):
    def __init__(self):
        self.label = "Batch sample rasters"
        self.alias = "sample"
        self.tools = [BatchSampleRasters]


class BatchSampleRasters(object):
    def __init__(self):
        self.label = "Batch sample rasters"
        self.description = "Samples TIFF rasters and outputs a CSV with lat/long coordinates and raster values"

    def getParameterInfo(self):
        root = arcpy.Parameter(
            displayName="TIFF Folder",
            name="tiff_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="input"
        )

        outputTablePath = arcpy.Parameter(
            displayName="Output CSV Folder",
            name="output_csv_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="input"
        )

        outTableName = arcpy.Parameter(
            displayName="Output CSV Name",
            name = "output_csv_name",
            datatype="GPString",
            parameterType="Required",
            direction="input"
        )

        nullValueReplacement = arcpy.Parameter(
            displayName="Replace null values with: ",
            name="null_replacement",
            datatype="GPLong",
            parameterType="Optional",
            direction="input"
        )
        parameters = [root, outputTablePath, outTableName, nullValueReplacement]
        return parameters

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        root = parameters[0].valueAsText
        outputLocation = parameters[1].valueAsText
        outTableName = parameters[2].valueAsText
        nullValueReplacement = parameters[3].valueAsText
        outputTablePath = outputLocation + "\\" + outTableName
        arcpy.env.workspace = root
        tiffs = arcpy.ListRasters()

        if nullValueReplacement not in ["#", "", None]:
            arcpy.CreateFileGDB_management(root, "gdb.gdb")
            gdbPath = root + "\\gdb.gdb"

            # Copy tiffs to gdb since they must be in a geodatabase to run the Con tool, which we use to change null values
            for tiff in tiffs:
                # Add letters at the start, because if the name starts with a number it is invalid in a gdb
                gdbRasterName = "raster" + tiff[:-4]  # [:-4] Removes .tif extension
                arcpy.CopyRaster_management(tiff, gdbPath + "\\" + gdbRasterName)

            arcpy.env.workspace = gdbPath
            gdbRasters = arcpy.ListRasters()

            for raster in gdbRasters:
                arcpy.gp.IsNull_sa(raster, "nullRaster")
                arcpy.gp.Con_sa("nullRaster", nullValueReplacement, raster + "1", raster, "")
                tiffName = raster[6:] + ".tif"  # Remove "raster" at start and add .tif extension
                arcpy.CopyRaster_management(raster + "1", root + "\\" + tiffName)

            arcpy.env.workspace = root

        tiffNumbers = []
        for tiff in tiffs:
            tiffNumber = tiff[:-4]
            tiffNumbers.append(tiffNumber)

        lastRaster = max(tiffNumbers) + ".tif"
        basePointsPath = outputLocation + "\\basepoints.shp"
        arcpy.RasterToPoint_conversion(lastRaster, basePointsPath)
        arcpy.AddXY_management(basePointsPath)
        finalTablePath = outputLocation + "\\finalTable"
        arcpy.sa.Sample(tiffs, basePointsPath, finalTablePath)
        arcpy.TableToTable_conversion(finalTablePath, outputLocation, "finalTable.csv")
        # Remove first two columns since they don't contain important information
        with open(finalTablePath + ".csv", "r") as fileIn:
            with open(outputTablePath, "w") as fileOut:
                writer = csv.writer(fileOut)
                for row in csv.reader(fileIn):
                    writer.writerow(row[2:])

        arcpy.Delete_management(basePointsPath)
        try:
            arcpy.Delete_management(gdbPath)
        except:
            pass
        arcpy.Delete_management(finalTablePath)
        os.remove(finalTablePath + ".csv")
        os.remove(finalTablePath + ".txt.xml")
        os.remove(outputLocation + "\\log")
        os.remove(outputLocation + "\\schema.ini")
        shutil.rmtree(outputLocation + "\\info")
