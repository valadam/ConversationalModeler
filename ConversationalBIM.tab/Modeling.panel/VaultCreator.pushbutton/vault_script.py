#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Create a sectioned barrel vault curve matching the reference image."""
__title__ = 'Vault\nSection'
__doc__ = 'Create barrel vault section with visible cut face'

import clr
import sys
import os
import math
import traceback

# Add references to Revit API
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')

# Add path to library
from pyrevit import revit, forms, script
from System.Collections.Generic import List
import Autodesk.Revit.DB as DB

# Get current document
doc = revit.doc

# Get all levels
try:
    levels = {}
    level_collector = DB.FilteredElementCollector(doc).OfClass(DB.Level).ToElements()
    for level in level_collector:
        levels[level.Name] = level
    level_names = sorted(levels.keys())
except Exception as e:
    forms.alert('Error getting levels: ' + str(e), exitscript=True)

def create_vault_section(doc, width, height, depth, thickness, level):
    """Create a vault section showing the curved surface with a cut face.
    
    Args:
        doc: Revit document
        width: Width of the vault section in meters
        height: Height of the vault in meters
        depth: Depth of the vault section in meters
        thickness: Thickness of the vault wall in meters
        level: Revit level element
        
    Returns:
        DirectShape element representing the vault section
    """
    # Convert values to feet (Revit's internal unit)
    feet_width = width * 3.28084
    feet_height = height * 3.28084
    feet_depth = depth * 3.28084
    feet_thickness = thickness * 3.28084
    
    # Get level elevation
    level_elevation = level.Elevation
    
    try:
        # Create the vault section as a single solid
        
        # 1. Create the outer curved surface profile
        outer_profile = DB.CurveLoop()
        
        # Number of segments for a smooth curve
        num_segments = 24
        
        # Create points for the curved profile
        outer_points = []
        
        # Create arch curve points
        for i in range(num_segments + 1):
            # Position along the curve (0 to 90 degrees)
            angle_rad = (i * math.pi/2) / num_segments
            
            # Calculate point coordinates for quarter circle
            x = feet_width * math.cos(angle_rad)
            z = feet_height * math.sin(angle_rad)
            
            # Add point (starting from bottom-right, going up)
            outer_points.append(DB.XYZ(x, 0, level_elevation + z))
        
        # Create the curves for the outer profile
        for i in range(len(outer_points) - 1):
            line = DB.Line.CreateBound(outer_points[i], outer_points[i+1])
            outer_profile.Append(line)
        
        # 2. Create the inner curved surface profile (offset by thickness)
        inner_profile = DB.CurveLoop()
        inner_points = []
        
        # Create inner arch curve points
        for i in range(num_segments + 1):
            # Position along the curve (0 to 90 degrees)
            angle_rad = (i * math.pi/2) / num_segments
            
            # Calculate point coordinates with offset for thickness
            x = (feet_width - feet_thickness) * math.cos(angle_rad)
            z = (feet_height - feet_thickness) * math.sin(angle_rad)
            
            # Add point (starting from bottom-right, going up)
            inner_points.append(DB.XYZ(x, 0, level_elevation + z))
        
        # Create the curves for the inner profile
        for i in range(len(inner_points) - 1):
            line = DB.Line.CreateBound(inner_points[i], inner_points[i+1])
            inner_profile.Append(line)
        
        # 3. Connect the ends of the profiles to create a closed loop
        
        # Connect top ends
        top_outer = outer_points[-1]
        top_inner = inner_points[-1]
        top_line = DB.Line.CreateBound(top_outer, top_inner)
        outer_profile.Append(top_line)
        
        # Connect the inner profile in reverse direction
        for i in range(len(inner_points) - 1, 0, -1):
            line = DB.Line.CreateBound(inner_points[i], inner_points[i-1])
            outer_profile.Append(line)
        
        # Connect bottom ends
        bottom_outer = outer_points[0]
        bottom_inner = inner_points[0]
        bottom_line = DB.Line.CreateBound(bottom_inner, bottom_outer)
        outer_profile.Append(bottom_line)
        
        # Create profile list
        profile_list = List[DB.CurveLoop]()
        profile_list.Add(outer_profile)
        
        # Extrude the profile to create the vault section
        vault_section = DB.GeometryCreationUtilities.CreateExtrusionGeometry(
            profile_list,
            DB.XYZ.BasisY,  # Extrude in Y direction (depth)
            feet_depth
        )
        
        # Create direct shape element
        category_id = DB.ElementId(DB.BuiltInCategory.OST_GenericModel)
        direct_shape = DB.DirectShape.CreateElement(doc, category_id)
        
        # Add geometry to direct shape
        direct_shape.SetShape([vault_section])
        
        # Set a meaningful name
        try:
            name_param = direct_shape.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK)
            if name_param and not name_param.IsReadOnly:
                name_param.Set("Vault Section {}m x {}m".format(width, height))
        except:
            print("Could not set vault section mark")
        
        # Add texture grid lines to match the image (as separate geometry)
        try:
            # Create grid on the curved surface
            grid_u_count = 8  # Number of vertical grid lines
            grid_v_count = 8  # Number of horizontal grid lines
            
            grid_line_solids = []
            
            # Create vertical grid lines
            for i in range(1, grid_u_count):
                fraction = i / float(grid_u_count)
                grid_profile = DB.CurveLoop()
                
                grid_points = []
                for j in range(num_segments + 1):
                    angle_rad = (j * math.pi/2) / num_segments
                    
                    # Interpolate between outer and inner profiles
                    x_outer = feet_width * math.cos(angle_rad)
                    z_outer = feet_height * math.sin(angle_rad)
                    
                    x_inner = (feet_width - feet_thickness) * math.cos(angle_rad)
                    z_inner = (feet_height - feet_thickness) * math.sin(angle_rad)
                    
                    # Position along the width of the wall
                    x = x_outer - fraction * (x_outer - x_inner)
                    z = z_outer - fraction * (z_outer - z_inner)
                    
                    grid_points.append(DB.XYZ(x, 0, level_elevation + z))
                
                # Create line segments
                for j in range(len(grid_points) - 1):
                    line = DB.Line.CreateBound(grid_points[j], grid_points[j+1])
                    grid_profile.Append(line)
                
                grid_profiles = List[DB.CurveLoop]()
                grid_profiles.Add(grid_profile)
                
                # Create a thin extrusion for the grid line
                grid_line = DB.GeometryCreationUtilities.CreateExtrusionGeometry(
                    grid_profiles,
                    DB.XYZ.BasisY,
                    feet_depth
                )
                
                grid_line_solids.append(grid_line)
            
            # Create horizontal grid lines (along the depth)
            for i in range(1, grid_v_count):
                y_pos = (i * feet_depth) / grid_v_count
                
                # Create line at each angular position
                for j in range(0, num_segments, 3):  # Skip some points for efficiency
                    angle_rad = (j * math.pi/2) / num_segments
                    
                    # Calculate points on outer and inner surfaces
                    x_outer = feet_width * math.cos(angle_rad)
                    z_outer = feet_height * math.sin(angle_rad)
                    
                    x_inner = (feet_width - feet_thickness) * math.cos(angle_rad)
                    z_inner = (feet_height - feet_thickness) * math.sin(angle_rad)
                    
                    # Create line between outer and inner surfaces
                    outer_point = DB.XYZ(x_outer, y_pos, level_elevation + z_outer)
                    inner_point = DB.XYZ(x_inner, y_pos, level_elevation + z_inner)
                    
                    grid_line_profile = DB.CurveLoop()
                    grid_line_profile.Append(DB.Line.CreateBound(outer_point, inner_point))
                    
                    grid_profiles = List[DB.CurveLoop]()
                    grid_profiles.Add(grid_line_profile)
                    
                    # Create a thin extrusion for the grid line
                    grid_line = DB.GeometryCreationUtilities.CreateExtrusionGeometry(
                        grid_profiles,
                        DB.XYZ(0, 0.01, 0),  # Very thin extrusion
                        0.02 * 3.28084  # Thin grid line (2cm)
                    )
                    
                    grid_line_solids.append(grid_line)
            
            # Create a second direct shape for the grid lines
            grid_shape = DB.DirectShape.CreateElement(doc, category_id)
            grid_shape.SetShape(grid_line_solids)
            
            # Try to set grid line material to black
            try:
                materials = DB.FilteredElementCollector(doc).OfClass(DB.Material).ToElements()
                for material in materials:
                    material_name = material.Name.lower()
                    if "black" in material_name:
                        material_param = grid_shape.get_Parameter(DB.BuiltInParameter.MATERIAL_ID_PARAM)
                        if material_param and not material_param.IsReadOnly:
                            material_param.Set(material.Id)
                            break
            except:
                pass
        except Exception as grid_error:
            print("Non-critical error creating grid lines: " + str(grid_error))
        
        return direct_shape
        
    except Exception as e:
        print("Error creating vault section: " + str(e))
        raise e

# Main script execution
try:
    # Select level
    if hasattr(forms, 'CommandSwitchWindow'):
        selected_level = forms.CommandSwitchWindow.show(
            level_names,
            message='Select level for vault section:'
        )
    else:
        # Alternative approach if CommandSwitchWindow is not available
        selected_level = level_names[0]  # Use first level as default
        forms.alert('Using default level: ' + selected_level)
    
    if selected_level:
        # Get vault width
        vault_width = forms.ask_for_string(
            default='1.0',
            prompt='Enter vault width (meters):',
            title='Vault Width'
        )
        
        if vault_width:
            try:
                width = float(vault_width)
                if width <= 0:
                    forms.alert('Width must be a positive number.', title='Invalid Input')
                    sys.exit()
                
                # Get vault height
                vault_height = forms.ask_for_string(
                    default=str(width),  # Default height equals width for a quarter circle
                    prompt='Enter vault height (meters):',
                    title='Vault Height'
                )
                
                if vault_height:
                    try:
                        height = float(vault_height)
                        if height <= 0:
                            forms.alert('Height must be a positive number.', title='Invalid Input')
                            sys.exit()
                        
                        # Get vault depth
                        vault_depth = forms.ask_for_string(
                            default=str(width * 1.5),  # Default depth is 1.5x width
                            prompt='Enter vault section depth (meters):',
                            title='Vault Depth'
                        )
                        
                        if vault_depth:
                            try:
                                depth = float(vault_depth)
                                if depth <= 0:
                                    forms.alert('Depth must be a positive number.', title='Invalid Input')
                                    sys.exit()
                                
                                # Get wall thickness
                                wall_thickness = forms.ask_for_string(
                                    default='0.1',  # Default 10cm thickness
                                    prompt='Enter vault wall thickness (meters):',
                                    title='Wall Thickness'
                                )
                                
                                if wall_thickness:
                                    try:
                                        thickness = float(wall_thickness)
                                        if thickness <= 0:
                                            forms.alert('Thickness must be a positive number.', title='Invalid Input')
                                            sys.exit()
                                        
                                        if thickness >= width/2 or thickness >= height/2:
                                            forms.alert('Thickness is too large for vault dimensions.', title='Invalid Input')
                                            sys.exit()
                                        
                                        # Create the vault section
                                        with revit.Transaction('Create Vault Section'):
                                            vault_section = create_vault_section(
                                                doc, width, height, depth, thickness, levels[selected_level]
                                            )
                                            
                                            forms.alert(
                                                'Vault Section created successfully!',
                                                title='Success'
                                            )
                                    except ValueError as ve:
                                        forms.alert('Invalid thickness: ' + str(ve), title='Error')
                            except ValueError as ve:
                                forms.alert('Invalid depth: ' + str(ve), title='Error')
                    except ValueError as ve:
                        forms.alert('Invalid height: ' + str(ve), title='Error')
            except ValueError as ve:
                forms.alert('Invalid width: ' + str(ve), title='Error')
except Exception as e:
    error_details = str(e) + "\n\n" + traceback.format_exc()
    forms.alert('Error in script: ' + error_details)