"""Utility functions for conversational building modeling."""
import clr

# Add references to Revit API
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')

# Import Revit API
from Autodesk.Revit.DB import XYZ, Level, FloorType, WallType, Line, Wall, Floor, FilteredElementCollector, CurveLoop
from System.Collections.Generic import List

def get_all_levels(doc):
    """Get all levels in the document."""
    collector = FilteredElementCollector(doc).OfClass(Level).ToElements()
    return {level.Name: level for level in collector}

def get_all_wall_types(doc):
    """Get all wall types in the document."""
    collector = FilteredElementCollector(doc).OfClass(WallType).ToElements()
    return {wt.Name: wt for wt in collector}

def create_wall(doc, start_point, end_point, wall_type_id, level_id, height=10.0):
    """Create a wall between two points."""
    curve = Line.CreateBound(start_point, end_point)
    
    # Wall.Create expects to be within a transaction, but we'll manage that in the calling code
    wall = Wall.Create(
        doc,
        curve,
        wall_type_id,
        level_id,
        height,
        0.0,
        False,
        True
    )
    return wall

def create_floor(doc, profile, floor_type_id, level_id):
    """Create a floor with the given profile."""
    # Floor.Create expects to be within a transaction, but we'll manage that in the calling code
    floor = Floor.Create(doc, profile, floor_type_id, level_id)
    return floor

def parse_point_input(point_str):
    """Parse a string like "0,0" into an XYZ point."""
    coords = [float(x) for x in point_str.split(',')]
    if len(coords) == 2:
        return XYZ(coords[0], coords[1], 0)
    elif len(coords) == 3:
        return XYZ(coords[0], coords[1], coords[2])
    else:
        raise ValueError("Point string should be in format 'x,y' or 'x,y,z'")

def parse_points_input(points_str):
    """Parse a string of multiple points like "0,0 1,1 2,2" into a list of XYZ points."""
    points = points_str.split()
    return [parse_point_input(p) for p in points]