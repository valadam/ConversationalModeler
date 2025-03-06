"""Create classical flower pillar columns."""
__title__ = 'Column\nCreator'
__doc__ = 'Create flower columns with smooth concave fluting (units in meters)'

import clr
import sys
import os
import traceback
import math
##New comment

# Add references to Revit API
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')

# Add path to library
from pyrevit import revit, forms, script
from System.Collections.Generic import List
import Autodesk.Revit.DB as DB

# Get current document
doc = revit.doc

def create_flower_pillar_column(doc, x, y, diameter, height, level, num_petals=8):
    """Create a flower-shaped column with 8 rounded petals."""
    # Convert from meters to feet
    feet_height = height * 3.28084
    feet_diameter = diameter * 3.28084
    
    # Get level elevation
    level_elevation = level.Elevation
    
    # Calculate profile coordinates
    radius = feet_diameter / 2
    center_x = x * 3.28084
    center_y = y * 3.28084
    
    # Create the flower profile
    profile = DB.CurveLoop()
    
    # More points for a smoother shape
    num_points = 48  # Multiple of 8 for 8 petals
    
    # Create points for flower shape
    points = []
    for i in range(num_points):
        angle = 2 * math.pi * i / num_points
        
        # Add a subtle petal effect with sine wave, 8 petals
        # Use a smaller amplitude (0.08) for a subtle effect
        petal_effect = 1.0 + 0.08 * math.sin(angle * num_petals)
        
        # Calculate point with petal effect
        x_pt = center_x + radius * petal_effect * math.cos(angle)
        y_pt = center_y + radius * petal_effect * math.sin(angle)
        
        points.append(DB.XYZ(x_pt, y_pt, level_elevation))
    
    # Create lines between points
    for i in range(num_points):
        start_pt = points[i]
        end_pt = points[(i + 1) % num_points]
        line = DB.Line.CreateBound(start_pt, end_pt)
        profile.Append(line)
    
    # Create profile list
    profile_list = List[DB.CurveLoop]()
    profile_list.Add(profile)
    
    # Create extrusion
    solid = DB.GeometryCreationUtilities.CreateExtrusionGeometry(
        profile_list, 
        DB.XYZ.BasisZ, 
        feet_height
    )
    
    # Create direct shape
    category_id = DB.ElementId(DB.BuiltInCategory.OST_Columns)
    direct_shape = DB.DirectShape.CreateElement(doc, category_id)
    
    # Add geometry to direct shape
    direct_shape.SetShape([solid])
    
    # Set a meaningful name for the column
    try:
        name_param = direct_shape.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK)
        if name_param and not name_param.IsReadOnly:
            name_param.Set("Flower Column {}cm diameter".format(int(diameter * 100)))
    except:
        print("Could not set column mark")
    
    return direct_shape

# Get all levels
try:
    levels = {}
    level_collector = DB.FilteredElementCollector(doc).OfClass(DB.Level).ToElements()
    for level in level_collector:
        levels[level.Name] = level
    level_names = sorted(levels.keys())
except Exception as e:
    forms.alert('Error getting levels: ' + str(e), exitscript=True)

# Main script
try:
    # Select level
    if hasattr(forms, 'CommandSwitchWindow'):
        selected_level = forms.CommandSwitchWindow.show(
            level_names,
            message='Select level for pillar column:'
        )
    else:
        # Alternative approach if CommandSwitchWindow is not available
        selected_level = level_names[0]  # Use first level as default
        forms.alert('Using default level: ' + selected_level)
    
    if selected_level:
        # Get column height (default 4.0 meters)
        column_height = forms.ask_for_string(
            default='4.0',
            prompt='Enter pillar height (meters):',
            title='Pillar Height'
        )
        
        if column_height:
            try:
                height = float(column_height)
                
                # Default column diameter (34.4 cm)
                default_diameter = 0.344  # 34.4 cm based on your image
                
                # Ask for column diameter
                column_diameter = forms.ask_for_string(
                    default=str(default_diameter),
                    prompt='Enter pillar diameter in meters (default: 0.344 m = 34.4 cm):',
                    title='Pillar Diameter'
                )
                
                if column_diameter:
                    diameter = float(column_diameter)
                    
                    # Ask for column location
                    coords = forms.ask_for_string(
                        default='0,0',
                        prompt='Enter pillar location (x,y) in meters:',
                        title='Pillar Location'
                    )
                    
                    if coords:
                        try:
                            # Parse coordinates
                            parts = coords.split(',')
                            if len(parts) < 2:
                                raise ValueError("Invalid coordinates format. Use x,y")
                            
                            x = float(parts[0])
                            y = float(parts[1])
                            
                            # Create the flower pillar column
                            with revit.Transaction('Create Pillar Column'):
                                column = create_flower_pillar_column(
                                    doc, x, y, diameter, height, levels[selected_level]
                                )
                                
                                # Try to assign iron material - simplified approach
                                try:
                                    materials = DB.FilteredElementCollector(doc).OfClass(DB.Material).ToElements()
                                    for material in materials:
                                        material_name = material.Name.lower()
                                        if "iron" in material_name or "metal" in material_name:
                                            material_param = column.get_Parameter(DB.BuiltInParameter.MATERIAL_ID_PARAM)
                                            if material_param and not material_param.IsReadOnly:
                                                material_param.Set(material.Id)
                                                break
                                except:
                                    # If material setting fails, just continue
                                    pass
                                
                                forms.alert(
                                    'Pillar Column ({0} cm diameter) created successfully at ({1}, {2}) with height {3} m!'.format(
                                        int(diameter * 100), x, y, height
                                    ), 
                                    title='Success'
                                )
                        except ValueError as e:
                            forms.alert('Invalid input: ' + str(e))
            except ValueError:
                forms.alert('Please enter a valid number for height.')
except Exception as e:
    error_details = str(e) + "\n\n" + traceback.format_exc()
    forms.alert('Error in script: ' + error_details)