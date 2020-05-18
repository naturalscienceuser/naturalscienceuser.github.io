import arcpy
import os

arcpy.env.overwriteOutput = True


class Toolbox(object):
    def __init__(self):
        self.label = "Clip Unsuitable Areas"
        self.alias = "Clip Unsuitable Areas"
        self.tools = [ClipUnsuitableAreas]


class ClipUnsuitableAreas(object):
    def __init__(self):
        self.label = "Clip Unsuitable Areas"
        self.description = "Clips areas that are not suitable for building windmills"

    def getParameterInfo(self):
        project_area = arcpy.Parameter(
            displayName="Project Area",
            name="project_area",
            datatype="DEShapefile",
            parameterType="Required",
            direction="input"
        )

        coordinate_system = arcpy.Parameter(
            displayName="Coordinate System to Project to",
            name="coordinate_system",
            datatype="GPSpatialReference",
            parameterType="Required",
            direction="input"
        )

        input_layers = arcpy.Parameter(
            displayName="Input Layers",
            name="input_layers",
            datatype="GPValueTable",
            parameterType="Required",
            direction="input",
        )

        input_layers.columns = [
            ["DEShapefile", "Shapefile"], ["String", "Type"], ["GPDouble", "Buffer multiplier (optional)"],
            ["GPLinearUnit", "Buffer distance (optional)"]
            ]
        input_layers.filters[1].type = "ValueList"
        input_layers.filters[1].list = [
            "Center_Pivot_Irrigation", "City_Limits", "Cotton_Gin", "County_Road", "Divided_Highway", "Easement_Areas",
            "Existing_Turbines", "Houses", "Leased_Property_Lines", "Unleased_Parcels", "Water_Bodies", "Water_Draw",
            "Unspecified"
            ]

        tip_height = arcpy.Parameter(
            displayName="Tip Height",
            name="tip_height",
            datatype="GPLinearUnit",
            parameterType="Required",
            direction="input"
        )

        blade_length = arcpy.Parameter(
            displayName="Blade Length",
            name="blade_length",
            datatype="GPLinearUnit",
            parameterType="Required",
            direction="input"
        )

        rotor_diameter = arcpy.Parameter(
            displayName="Rotor Diameter",
            name="rotor_diameter",
            datatype="GPLinearUnit",
            parameterType="Required",
            direction="input"
        )

        output_shapefile = arcpy.Parameter(
            displayName="Output Shapefile",
            name="output_shapefile",
            datatype="DEShapefile",
            parameterType="Required",
            direction="output"
        )

        cleanup = arcpy.Parameter(
            displayName="Delete intermediate files",
            name="cleanup",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="input"
        )
        cleanup.value = True

        parameters = [
            project_area, coordinate_system, input_layers, tip_height, blade_length, rotor_diameter, output_shapefile,
            cleanup
            ]

        return parameters

    def execute(self, parameters, messages):
        values = [param.valueAsText for param in parameters]
        project_area, coordinate_system, layer_strs, tip_height, blade_length, rotor_diameter, output_shapefile, cleanup = values
        layer_strs = layer_strs.split(";")
        wd = os.path.dirname(os.path.realpath(__file__))
        # The line below is normally how I would do it, but we need to account for spaces in filepath
        # layer_strs = [layer_str.split(" ") for layer_str in layer_strs]  # list of lists

        # This is how we do it without assuming there are no spaces in the path
        new_layer_strs = []
        for layer_str in layer_strs:
            path_end = layer_str.find(".shp") + 4
            # start at index 1 because the string actually includes real single quotes at the beginning and end (that was tricky to debug)
            path = layer_str[1:path_end]
            other_vals = layer_str.split(" ")[-3:]
            new_layer_strs.append([path] + other_vals)
        layer_strs = new_layer_strs

        arcpy.CreateFileGDB_management(wd, "temp.gdb")
        dump = wd + "\\temp.gdb"

        # Reproject project area
        proj_area_reproj = dump + "\\proj_area_reproj"
        arcpy.Project_management(project_area, proj_area_reproj, coordinate_system)

        # Buffer project area
        proj_area_buffer = dump + "\\proj_area_buffer"
        arcpy.Buffer_analysis(proj_area_reproj, proj_area_buffer, "1000 Meters")

        buffered_layers_to_merge = []
        for i, layer_string in enumerate(layer_strs):
            # Clip to buffered project boundary
            clipped_layer = dump + "\\layer%s" % i
            arcpy.Clip_analysis(layer_string[0], proj_area_buffer, clipped_layer)
            layer_string[0] = clipped_layer

            # Reproject
            reproj_layer = dump + "\\reproj%s" % i
            arcpy.Project_management(layer_string[0], reproj_layer, coordinate_system)
            layer_string[0] = reproj_layer

            # Buffer time
            defaults_with_multipliers = {
                "Cotton_Gin": [tip_height, 1.5], "County_Road": [tip_height, 1.1],
                "Divided_Highway": [tip_height, 1.25], "Easement_Areas": [blade_length, 1.1],
                "Existing_Turbines": [rotor_diameter, 15], "Leased_Property_Lines": [blade_length, 1.1],
                "Unleased_Parcels": [tip_height, 1.1]
                }

            fixed_defaults = {
                "Center_Pivot_Irrigation": "60 Feet", "City_Limits": "0.5 Miles", "Houses": "1500 Feet",
                "Water_Bodies": "100 Meters", "Water_Draw": "100 Meters"
                }
            # determine distance for buffer
            if layer_string[3] not in ("#", ""):  # If distance was provided
                distance = layer_string[3]
            elif layer_string[2] not in ("#", ""):  # if multiplier was provided
                multiplier = float(layer_string[2])
                raw_dist = defaults_with_multipliers[layer_string[1]][0]
                raw_dist_num, units = float(raw_dist.split(" ")[0]), raw_dist.split(" ")[1]
                distance_num = raw_dist_num * multiplier
                distance = "%s %s" % (distance_num, units)
            else:  # if nothing was provided
                if layer_string[1] in fixed_defaults:
                    distance = fixed_defaults[layer_string[1]]
                else:
                    raw_dist, multiplier = defaults_with_multipliers[layer_string[1]]  # 60 Feet, 1.5
                    raw_dist_num, units = float(raw_dist.split(" ")[0]), raw_dist.split(" ")[1]
                    distance_num = raw_dist_num * multiplier
                    distance = "%s %s" % (distance_num, units)
            # do the buffer
            buffered_layer = dump + "\\buffer%s" % i
            arcpy.Buffer_analysis(clipped_layer, buffered_layer, distance)
            layer_string[0] = buffered_layer
            buffered_layers_to_merge.append(layer_string[0])

        # Merge buffers
        merged_layer = dump + "\\merged"
        arcpy.Merge_management(buffered_layers_to_merge, merged_layer)

        # Erase merged buffer from project area
        arcpy.Erase_analysis(proj_area_reproj, merged_layer, output_shapefile)

        # Optionally delete intermediates
        if cleanup == "true":
            arcpy.Delete_management(dump)

        # NOTE: BUFF_DIST field is in units of whatever it was reprojected to
