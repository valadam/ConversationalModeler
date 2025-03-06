#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Create hollow barrel vault section through a conversational interface."""
__title__ = 'Hollow\nVault'
__doc__ = 'Create hollow barrel vault section with interior arch'

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

def create_hollow_barrel_vault(doc, base_width, arch_height, vault_depth, wall_thickness, level):
    """Create a hollow barrel vault section with interior arch.
    
    Uses a different approach with two separate solids that are joined.
    
    Args:
        doc: Revit document
        base_width: Width of the vault base in meters
        arch_height: Height of the vault apex in meters
        vault_depth: Depth of the vault section in meters
        wall_thickness: Thickness of the vault walls in meters
        level: Revit level element
        
    Returns:
        DirectShape element representing the hollow barrel vault section
    """
    # Validate input dimensions
    if base_width <= 0 or arch_height <= 0 or vault_depth <= 0 or wall_thickness <= 0:
        raise ValueError("All dimensions must be positive values")
    
    if wall_thickness >= base_width/2 or wall_thickness >= arch_height:
        raise ValueError("Wall thickness is too large relative to vault dimensions")
        
    # Convert values to feet (Revit's internal unit)
    feet_base_width = base_width * 3.28084
    feet_arch_height = arch_height * 3.28084
    feet_vault_depth = vault_depth * 3.28084
    feet_wall_thickness = wall_thickness * 3.28084
    
    # Get level elevation
    level_elevation = level.Elevation
    
    try:
        # APPROACH: Create the full vault, then create and subtract an inner void
        
        # 1. First create the outer vault profile
        outer_profile = DB.CurveLoop()
        
        # Number of segments for smooth curves
        num_segments = 10
        
        # Base points
        p_left = DB.XYZ(0, 0, level_elevation)
        p_right = DB.XYZ(feet_base_width, 0, level_elevation)
        
        # Points for outer arch
        outer_points = [p_left]
        
        # Create outer arch curve
        for i in range(1, num_segments):
            # Position along width
            t = float(i) / float(num_segments)
            x = feet_base_width * t
            
            # Semi-circular arch formula: z = h * sin(θ)
            theta = t * math.pi
            z = feet_arch_height * math.sin(theta)
            
            arch_point = DB.XYZ(x, 0, level_elevation + z)
            outer_points.append(arch_point)
        
        outer_points.append(p_right)
        
        # Create outer profile curves
        min_curve_length = 0.05  # Minimum length in feet
        
        for i in range(len(outer_points) - 1):
            start_pt = outer_points[i]
            end_pt = outer_points[i + 1]
            
            if start_pt.DistanceTo(end_pt) >= min_curve_length:
                curve = DB.Line.CreateBound(start_pt, end_pt)
                outer_profile.Append(curve)
            else:
                print("Skipping short segment: {} feet".format(start_pt.DistanceTo(end_pt)))
        
        # Close the outer profile
        base_line = DB.Line.CreateBound(p_right, p_left)
        outer_profile.Append(base_line)
        
        # Verify outer profile is valid
        if outer_profile.IsOpen():
            raise ValueError("Failed to create a closed outer profile")
            
        if not outer_profile.HasPlane():
            raise ValueError("Outer profile is not planar")
        
        # Create outer profile list
        outer_profile_list = List[DB.CurveLoop]()
        outer_profile_list.Add(outer_profile)
        
        # Create the solid outer vault by extrusion
        outer_vault = DB.GeometryCreationUtilities.CreateExtrusionGeometry(
            outer_profile_list,
            DB.XYZ.BasisY,  # Extrude in Y direction
            feet_vault_depth
        )
        
        # 2. Now create the inner void profile (offset inward)
        inner_width = feet_base_width - (2 * feet_wall_thickness)
        inner_height = feet_arch_height - feet_wall_thickness
        inner_depth = feet_vault_depth - (2 * feet_wall_thickness)
        
        # Calculate inner curve start points
        p_left_inner = DB.XYZ(feet_wall_thickness, feet_wall_thickness, level_elevation + feet_wall_thickness)
        p_right_inner = DB.XYZ(feet_base_width - feet_wall_thickness, feet_wall_thickness, level_elevation + feet_wall_thickness)
        
        # Create inner profile
        inner_profile = DB.CurveLoop()
        
        # Points for inner arch
        inner_points = [p_left_inner]
        
        # Create inner arch curve
        for i in range(1, num_segments):
            # Position along width
            t = float(i) / float(num_segments)
            
            # Scale to inner width
            x = feet_wall_thickness + (inner_width * t)
            
            # Semi-circular arch formula for inner surface
            theta = t * math.pi
            z = level_elevation + feet_wall_thickness + (inner_height * math.sin(theta))
            
            inner_arch_point = DB.XYZ(x, feet_wall_thickness, z)
            inner_points.append(inner_arch_point)
        
        inner_points.append(p_right_inner)
        
        # Create inner profile curves
        for i in range(len(inner_points) - 1):
            start_pt = inner_points[i]
            end_pt = inner_points[i + 1]
            
            if start_pt.DistanceTo(end_pt) >= min_curve_length:
                curve = DB.Line.CreateBound(start_pt, end_pt)
                inner_profile.Append(curve)
            else:
                print("Skipping short inner segment: {} feet".format(start_pt.DistanceTo(end_pt)))
        
        # Close the inner profile
        inner_base_line = DB.Line.CreateBound(p_right_inner, p_left_inner)
        inner_profile.Append(inner_base_line)
        
        # Verify inner profile is valid
        if inner_profile.IsOpen():
            raise ValueError("Failed to create a closed inner profile")
            
        if not inner_profile.HasPlane():
            raise ValueError("Inner profile is not planar")
        
        # Create inner profile list
        inner_profile_list = List[DB.CurveLoop]()
        inner_profile_list.Add(inner_profile)
        
        # Create the inner void by extrusion (shorter depth)
        inner_void = DB.GeometryCreationUtilities.CreateExtrusionGeometry(
            inner_profile_list,
            DB.XYZ.BasisY,  # Extrude in Y direction
            inner_depth
        )
        
        # 3. Create a hollow vault by Boolean difference
        # First create a transform to position the inner void
        translation_vector = DB.XYZ(0, 0, 0)  # Already positioned correctly
        transform = DB.Transform.CreateTranslation(translation_vector)
        
        # Apply the transform to the inner void
        transformed_inner_void = DB.SolidUtils.CreateTransformed(inner_void, transform)
        
        # Create the hollow vault by subtracting the inner void from the outer vault
        hollow_vault = DB.BooleanOperationsUtils.ExecuteBooleanOperation(
            outer_vault,
            transformed_inner_void,
            DB.BooleanOperationsType.Difference
        )
        
        # Create direct shape element for the hollow vault
        category_id = DB.ElementId(DB.BuiltInCategory.OST_GenericModel)
        direct_shape = DB.DirectShape.CreateElement(doc, category_id)
        
        # Add geometry to direct shape
        direct_shape.SetShape([hollow_vault])
        
        # Set a meaningful name
        try:
            name_param = direct_shape.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK)
            if name_param and not name_param.IsReadOnly:
                name_param.Set("Hollow Barrel Vault {0}m x {1}m".format(base_width, arch_height))
        except:
            print("Could not set vault mark")
        
        return direct_shape
    except Exception as e:
        print("Error creating hollow vault: " + str(e))
        raise e

# Main script
try:
    # Select level
    if hasattr(forms, 'CommandSwitchWindow'):
        selected_level = forms.CommandSwitchWindow.show(
            level_names,
            message='Select level for hollow vault:'
        )
    else:
        # Alternative approach if CommandSwitchWindow is not available
        selected_level = level_names[0]  # Use first level as default
        forms.alert('Using default level: ' + selected_level)
    
    if selected_level:
        # Get vault base width
        vault_width = forms.ask_for_string(
            default='1.0',
            prompt='Enter vault span width (meters):',
            title='Vault Span Width'
        )
        
        if vault_width:
            try:
                # Validate width
                width = float(vault_width)
                if width <= 0:
                    forms.alert('Width must be a positive number.', title='Invalid Input')
                    sys.exit()
                
                # Get vault height
                vault_height = forms.ask_for_string(
                    default=str(width/2),  # Default height is half the width for a semicircular arch
                    prompt='Enter vault rise height (meters):',
                    title='Vault Rise Height'
                )
                
                if vault_height:
                    try:
                        # Validate height
                        height = float(vault_height)
                        if height <= 0:
                            forms.alert('Height must be a positive number.', title='Invalid Input')
                            sys.exit()
                        
                        # Get vault depth
                        vault_depth = forms.ask_for_string(
                            default=str(width),  # Default depth equals width
                            prompt='Enter vault section depth (meters):',
                            title='Vault Section Depth'
                        )
                        
                        if vault_depth:
                            try:
                                # Validate depth
                                depth = float(vault_depth)
                                if depth <= 0:
                                    forms.alert('Depth must be a positive number.', title='Invalid Input')
                                    sys.exit()
                                
                                # Get wall thickness
                                wall_thickness = forms.ask_for_string(
                                    default=str(0.1),  # Default 10cm thickness
                                    prompt='Enter vault wall thickness (meters):',
                                    title='Wall Thickness'
                                )
                                
                                if wall_thickness:
                                    try:
                                        # Validate thickness
                                        thickness = float(wall_thickness)
                                        if thickness <= 0:
                                            forms.alert('Thickness must be a positive number.', title='Invalid Input')
                                            sys.exit()
                                        
                                        if thickness >= width/2 or thickness >= height:
                                            forms.alert('Thickness is too large for vault dimensions.', title='Invalid Input')
                                            sys.exit()
                                        
                                        # Create the hollow barrel vault section
                                        with revit.Transaction('Create Hollow Barrel Vault'):
                                            try:
                                                vault_section = create_hollow_barrel_vault(
                                                    doc, width, height, depth, thickness, levels[selected_level]
                                                )
                                                forms.alert(
                                                    'Hollow Barrel Vault created successfully!',
                                                    title='Success'
                                                )
                                            except Exception as inner_e:
                                                forms.alert('Error creating vault: ' + str(inner_e), title='Error')
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