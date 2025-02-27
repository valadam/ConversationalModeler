"""Create walls through a conversational interface."""
__title__ = 'Wall\nCreator'
__doc__ = 'Create walls through a dialog-based interface'

import clr
import sys
import os

# Add references to Revit API
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')

# Add path to library
from pyrevit import revit, forms, script
import Autodesk.Revit.DB as DB

# Get current document
doc = revit.doc

# Get all levels directly without utility function
try:
    levels = {}
    level_collector = DB.FilteredElementCollector(doc).OfClass(DB.Level).ToElements()
    for level in level_collector:
        levels[level.Name] = level
    level_names = sorted(levels.keys())
except Exception as e:
    forms.alert('Error getting levels: ' + str(e), exitscript=True)

# Get all wall types - Directly without utility function with better error handling
try:
    # Try a different approach for getting wall types
    collector = DB.FilteredElementCollector(doc)
    collector.OfCategory(DB.BuiltInCategory.OST_Walls)
    elements = collector.WhereElementIsElementType().ToElements()
    
    # See if we have any elements
    if elements.Count == 0:
        forms.alert("No wall types found in the document.", exitscript=True)
    
    # Try to get wall types with error handling for each element
    wall_type_dict = {}
    
    # Method 1: Using built-in parameter
    for element in elements:
        try:
            # Try to get name using parameter
            name_param = element.get_Parameter(DB.BuiltInParameter.ALL_MODEL_TYPE_NAME)
            if name_param:
                name = name_param.AsString()
                wall_type_dict[name] = element
            else:
                # Fallback to using the ID as name
                id_value = element.Id.IntegerValue
                name = "Wall Type " + str(id_value)
                wall_type_dict[name] = element
        except Exception as inner_e:
            # Just skip this element and try the next
            continue
    
    # If we still don't have any types, try one more approach
    if not wall_type_dict:
        # Try different category or method
        default_wall_cat = DB.ElementId(DB.BuiltInCategory.OST_Walls)
        if default_wall_cat:
            wall_type_dict["Default Wall"] = doc.GetElement(default_wall_cat)
    
    # Check if we found any wall types
    if not wall_type_dict:
        forms.alert("Could not retrieve wall types. Please check your Revit document.", exitscript=True)
    
    # Get the names and sort them
    wall_type_names = sorted(wall_type_dict.keys())
except Exception as e:
    import traceback
    error_msg = 'Error getting wall types: ' + str(e) + "\n" + traceback.format_exc() 
    forms.alert(error_msg, exitscript=True)

# Get user inputs through forms
try:
    # Check if forms.CommandSwitchWindow exists
    if hasattr(forms, 'CommandSwitchWindow'):
        selected_level = forms.CommandSwitchWindow.show(
            level_names,
            message='Select level for wall:'
        )
    else:
        # Alternative form if CommandSwitchWindow doesn't exist
        selected_level = forms.select_from_list(
            level_names,
            title='Select level for wall',
            message='Select level'
        )
    
    if selected_level:
        if hasattr(forms, 'CommandSwitchWindow'):
            selected_wall_type = forms.CommandSwitchWindow.show(
                wall_type_names,
                message='Select wall type:'
            )
        else:
            selected_wall_type = forms.select_from_list(
                wall_type_names,
                title='Select wall type',
                message='Select wall type'
            )
        
        if selected_wall_type:
            wall_height = forms.ask_for_string(
                default='10.0',
                prompt='Enter wall height (feet):',
                title='Wall Height'
            )
            
            if wall_height:
                try:
                    height = float(wall_height)
                    
                    coords = forms.ask_for_string(
                        default='0,0 10,0',
                        prompt='Enter wall start and end points (x,y x,y):',
                        title='Wall Coordinates'
                    )
                    
                    if coords:
                        # Parse points without utility function
                        try:
                            points = coords.split()
                            if len(points) != 2:
                                forms.alert('Please provide exactly two points.')
                            else:
                                # Parse start coordinates
                                start_parts = points[0].split(',')
                                if len(start_parts) < 2:
                                    raise ValueError("Invalid start coordinates format. Use x,y")
                                start_x = float(start_parts[0])
                                start_y = float(start_parts[1])
                                start_coords = DB.XYZ(start_x, start_y, 0)
                                
                                # Parse end coordinates
                                end_parts = points[1].split(',')
                                if len(end_parts) < 2:
                                    raise ValueError("Invalid end coordinates format. Use x,y")
                                end_x = float(end_parts[0])
                                end_y = float(end_parts[1])
                                end_coords = DB.XYZ(end_x, end_y, 0)
                                
                                # Create the wall directly without utility function
                                with revit.Transaction('Create Wall'):
                                    # Get level elevation
                                    level_elevation = levels[selected_level].Elevation
                                    
                                    # Create curve for wall path
                                    wall_curve = DB.Line.CreateBound(
                                        DB.XYZ(start_coords.X, start_coords.Y, level_elevation),
                                        DB.XYZ(end_coords.X, end_coords.Y, level_elevation)
                                    )
                                    
                                    # Create wall
                                    wall = DB.Wall.Create(
                                        doc,
                                        wall_curve,
                                        wall_type_dict[selected_wall_type].Id,
                                        levels[selected_level].Id,
                                        height,
                                        0.0,  # offset from level
                                        False,  # flip orientation
                                        True  # structural
                                    )
                                    
                                    if wall:
                                        forms.alert('Wall created successfully!', title='Success')
                        except Exception as e:
                            forms.alert('Error creating wall: ' + str(e))
                except ValueError:
                    forms.alert('Please enter a valid number for height.')
except Exception as e:
    forms.alert('Error in form processing: ' + str(e))