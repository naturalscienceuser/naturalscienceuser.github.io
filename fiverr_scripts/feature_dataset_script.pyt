import arcpy


class Toolbox(object):  # We first create a Toolbox class so that ArcGIS recognizes this script as a Python toolbox
    def __init__(self):
        self.label = "Shapefiles to featuredataset Toolbox"
        self.alias = "Shapefiles to featuredataset Toolbox"
        self.tools = [ShpToDataset]  # self.tools includes the tools in the toolbox; in this case, we only need one


class ShpToDataset(object):  # This class is the tool we are adding to our Python toolbox
    def __init__(self):
        self.label = "Shapefiles to featuredataset tool"
        self.description = "Exports shapefiles to a featuredataset and " \
                           "creates a new field concatenating OBJECTID and source fields (SOURCE1, SOURCE2). " \
                           "Make sure your data is NOT open in ArcMap before you run this tool, because ArcMap" \
                           " will lock the files and prevent them from being edited."

    # This function creates tool parameters. The user's input is saved to a corresponding variable.
    # These variables are then returned in a list, which we will use as input for the "execute" function just below
    def getParameterInfo(self):
        featureDataset = arcpy.Parameter(
            displayName="Feature Dataset",
            name="feature_dataset",
            datatype="DEFeatureDataset",
            parameterType="Required",
            direction="input"
        )

        shapefileFolder = arcpy.Parameter(
            displayName="Folder with Shapefiles",
            name="shapefile_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="input"
        )

        newFieldName = arcpy.Parameter(
            displayName="Name of new Field",
            name="new_field",
            datatype="GPString",
            parameterType="Required",
            direction="input"
        )
        parameters = [featureDataset, shapefileFolder, newFieldName]
        return parameters

    # This function runs once the user inputs their parameters and runs the tool
    def execute(self, parameters, messages):
        # Get the parameter values as text so that we can work with them
        featureDataset = parameters[0].valueAsText
        shapefileFolder = parameters[1].valueAsText
        newFieldName = parameters[2].valueAsText

        # By setting our workspace to the folder with the shapefiles and then running arcpy.ListFeatureClasses()
        # we get a list of the shapefiles in the shapefile folder
        arcpy.env.workspace = shapefileFolder
        shapefiles = arcpy.ListFeatureClasses()

        # Export our shapefiles to the feature dataset
        arcpy.FeatureClassToGeodatabase_conversion(shapefiles, featureDataset)

        # Change workspace and get a list of the featureClasses we just exported to the feature dataset
        arcpy.env.workspace = featureDataset
        featureClasses = arcpy.ListFeatureClasses()

        # Create a Python expression that means:
        # "concatenate OBJECTID and the fields named SOURCE1 and SOURCE2, with underscores in between"
        # The str() function converts the OBJECTID to a string so that it can be concatenated with other strings
        expression = 'str(!OBJECTID!) + "_" + !SOURCE1! + "_" + !SOURCE2!'

        # For each feature class in the dataset, we add a new field with the user-specified name, then we
        # use our expression in the field calculator to populate that field
        for featureClass in featureClasses:
            arcpy.AddField_management(featureClass, newFieldName, "TEXT")
            arcpy.CalculateField_management(featureClass, newFieldName, expression, expression_type="PYTHON_9.3")
            arcpy.Rename_management(featureClass, "New_" + featureClass)  # Add "New_" to the feature class name
