"""Create floors through a conversational interface."""
__title__ = 'Floor\nCreator'
__doc__ = 'Create floors through a dialog-based interface'

import clr
import sys
import os

# Add references to Revit API
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')

# Add path to library
from pyrevit import revit, forms, script
from System.Collections.Generic import List
import Autodesk.Revit.DB as DB


# Get current document
doc = revit.doc

# Get all levels directly without utility function first
try:
    levels = {}
    level_collector = DB.FilteredElementCollector(doc).OfClass(DB.Level).ToElements()
    for level in level_collector:
        levels[level.Name] = level
    level_names = sorted(levels.keys())
except Exception as e:
    forms.alert('Error getting levels: ' + str(e), exitscript=True)

# Get all floor types - ALTERNATIVE APPROACH
try:
    # Try a different approach - first check if we can get ANY floor types
    collector = DB.FilteredElementCollector(doc)
    collector.OfCategory(DB.BuiltInCategory.OST_Floors)
    elements = collector.WhereElementIsElementType().ToElements()
    
    # See if we have any elements
    if elements.Count == 0:
        forms.alert("No floor types found in the document.", exitscript=True)
    
    # Try to get floor types
    floor_type_dict = {}
    
    # Method 1: Using built-in parameter
    for element in elements:
        try:
            # Try to get name using parameter
            name_param = element.get_Parameter(DB.BuiltInParameter.ALL_MODEL_TYPE_NAME)
            if name_param:
                name = name_param.AsString()
                floor_type_dict[name] = element
        except:
            pass
    
    # Method 2: Check if we have any types, if not, try direct approach
    if not floor_type_dict:
        for element in elements:
            try:
                # Try a direct property access
                id_value = element.Id.IntegerValue
                # Use ID as name if we can't get the actual name
                name = "Floor Type " + str(id_value)
                floor_type_dict[name] = element
            except:
                pass
    
    # If we still don't have any types, try one more approach
    if not floor_type_dict:
        # Get default floor type
        default_floor_type_id = DB.ElementId(DB.BuiltInCategory.OST_Floors)
        if default_floor_type_id:
            floor_type_dict["Default Floor"] = doc.GetElement(default_floor_type_id)
    
    # Check if we found any floor types
    if not floor_type_dict:
        forms.alert("Could not retrieve floor types. Please check your Revit document.", exitscript=True)
    
    # Get the names and sort them
    floor_type_names = sorted(floor_type_dict.keys())
    
except Exception as e:
    forms.alert('Error getting floor types: ' + str(e), exitscript=True)

# Get user inputs through forms
try:
    # Check if forms.CommandSwitchWindow exists
    if hasattr(forms, 'CommandSwitchWindow'):
        selected_level = forms.CommandSwitchWindow.show(
            level_names,
            message='Select level for floor:'
        )
    else:
        # Alternative form if CommandSwitchWindow doesn't exist
        selected_level = forms.select_from_list(
            level_names,
            title='Select level for floor',
            message='Select level'
        )
    
    if selected_level:
        if hasattr(forms, 'CommandSwitchWindow'):
            selected_floor_type = forms.CommandSwitchWindow.show(
                floor_type_names,
                message='Select floor type:'
            )
        else:
            selected_floor_type = forms.select_from_list(
                floor_type_names,
                title='Select floor type',
                message='Select floor type'
            )
        
        if selected_floor_type:
            coords = forms.ask_for_string(
                default='0,0 20,0 20,20 0,20',  # Increased size to avoid tolerance issues
                prompt='Enter boundary points (x,y x,y ...):',
                title='Floor Boundary'
            )
            
            if coords:
                try:
                    # Parse points without utility function
                    boundary_points = []
                    
                    # Clean up the input
                    coords = coords.strip()
                    
                    # Parse coordinates
                    for point_str in coords.split():
                        coords_parts = [float(x) for x in point_str.split(',')]
                        if len(coords_parts) >= 2:
                            boundary_points.append(DB.XYZ(coords_parts[0], coords_parts[1], 0))
                    
                    # Ensure we have at least 3 points to create a valid floor
                    if len(boundary_points) < 3:
                        forms.alert("Need at least 3 points to create a floor boundary.")
                        raise ValueError("Not enough points")
                        
                    # Check for minimum distance between points
                    min_distance = 0.3  # Revit's tolerance in feet
                    valid_points = [boundary_points[0]]
                    
                    for i in range(1, len(boundary_points)):
                        current = boundary_points[i]
                        last = valid_points[-1]
                        
                        # Calculate distance between points
                        distance = current.DistanceTo(last)
                        
                        # Only add point if distance is greater than minimum
                        if distance >= min_distance:
                            valid_points.append(current)
                    
                    # If we don't have enough valid points, use a default rectangle
                    if len(valid_points) < 3:
                        valid_points = [
                            DB.XYZ(0, 0, 0),
                            DB.XYZ(20, 0, 0),
                            DB.XYZ(20, 20, 0),
                            DB.XYZ(0, 20, 0)
                        ]
                    
                    # Create curve loop for floor boundary
                    curve_loop = DB.CurveLoop()
                    for i in range(len(valid_points)):
                        start_pt = valid_points[i]
                        end_pt = valid_points[(i + 1) % len(valid_points)]
                        
                        # Only create curve if distance between points is sufficient
                        distance = start_pt.DistanceTo(end_pt)
                        if distance >= min_distance:
                            curve = DB.Line.CreateBound(start_pt, end_pt)
                            curve_loop.Append(curve)
                    
                    # Create list of curve loops
                    curve_loops = List[DB.CurveLoop]()
                    curve_loops.Add(curve_loop)
                    
                    # Create floor
                    with revit.Transaction('Create Floor'):
                        floor = DB.Floor.Create(
                            doc, 
                            curve_loops, 
                            floor_type_dict[selected_floor_type].Id, 
                            levels[selected_level].Id
                        )
                        
                        if floor:
                            forms.alert('Floor created successfully!', title='Success')
                except Exception as e:
                    forms.alert('Error creating floor: ' + str(e))
except Exception as e:
    forms.alert('Error in form processing: ' + str(e))