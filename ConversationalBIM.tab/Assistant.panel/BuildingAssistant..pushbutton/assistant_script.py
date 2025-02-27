"""Conversational building assistant for Revit."""
__title__ = 'Building\nAssistant'
__doc__ = 'Create building elements through natural language commands'

import clr
import re
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

# Get all levels directly
try:
    levels = {}
    level_collector = DB.FilteredElementCollector(doc).OfClass(DB.Level).ToElements()
    for level in level_collector:
        levels[level.Name] = level
    
    # Get default level - active view's level or first level
    default_level = None
    try:
        if hasattr(doc.ActiveView, 'GenLevel') and doc.ActiveView.GenLevel is not None:
            default_level = doc.ActiveView.GenLevel
        else:
            default_level = next(iter(levels.values()))
    except:
        # If active view doesn't have a level, use the first level
        if levels:
            default_level = next(iter(levels.values()))
except Exception as e:
    import traceback
    error_msg = 'Error getting levels: ' + str(e)
    forms.alert(error_msg, exitscript=True)

# Get all wall types with robust error handling
try:
    # Try a different approach for getting wall types
    collector = DB.FilteredElementCollector(doc)
    collector.OfCategory(DB.BuiltInCategory.OST_Walls)
    elements = collector.WhereElementIsElementType().ToElements()
    
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
        except:
            # Just skip this element and try the next
            continue
    
    # Get default wall type
    default_wall_type = next(iter(wall_type_dict.values()))
except Exception as e:
    import traceback
    error_msg = 'Error getting wall types: ' + str(e)
    forms.alert(error_msg, exitscript=True)

# Get all floor types - SIMPLIFIED
default_floor_type = None
try:
    collector = DB.FilteredElementCollector(doc)
    floor_types = collector.OfCategory(DB.BuiltInCategory.OST_Floors).WhereElementIsElementType().ToElements()
    
    if floor_types.Count > 0:
        # Get the first one
        enum = floor_types.GetEnumerator()
        if enum.MoveNext():
            default_floor_type = enum.Current
except:
    pass

# Natural language patterns - COMPREHENSIVE PATTERNS
patterns = {
    'wall': [
        r'create\s+(?:a\s+)?wall\s+from\s+\((-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\)\s+to\s+\((-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\)(?:\s+with\s+height\s+(-?\d+\.?\d*))?(?:\s+feet)?',
        r'add\s+(?:a\s+)?wall\s+(?:from\s+)?\((-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\)(?:\s+to\s+)?\((-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\)(?:\s+with\s+height\s+(-?\d+\.?\d*))?(?:\s+feet)?',
        r'wall\s+(?:from\s+)?\((-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\)(?:\s+to\s+)?\((-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\)(?:\s+with\s+height\s+(-?\d+\.?\d*))?(?:\s+feet)?',
    ],
    'floor': [
        # Simple size pattern
        r'(?:create\s+(?:a\s+)?)?floor\s+(\d+)(?:\s*x\s*(\d+))?',
        # Complex pattern with points
        r'(?:create\s+(?:a\s+)?)?floor\s+with\s+points\s+(.+)',
        # Alternative syntax
        r'add\s+(?:a\s+)?floor\s+(?:with\s+(?:size|dimensions)\s+)?(\d+)(?:\s*x\s*(\d+))?',
        r'add\s+(?:a\s+)?floor\s+with\s+points\s+(.+)',
    ],
    'help': [
        r'help',
        r'commands',
        r'examples',
        r'how\s+to',
        r'help\s+me',
        r'what\s+can\s+you\s+do',
        r'show\s+commands',
        r'show\s+help',
        r'list\s+commands',
        r'\?',  # Just a question mark also shows help
        r'^$',  # Empty string shows help too
    ]
}

def parse_command(text):
    """Parse a natural language command."""
    # Remove the initial hint text if it's still there
    hint_text = "Type 'help' to see available commands"
    if text.strip() == hint_text:
        text = ""
    
    text = text.lower().strip()
    
    # If the command is empty, show help
    if not text:
        return {'command': 'help', 'params': None, 'text': text}
    
    # Special case for "floor" command with simplified pattern matching
    if text.startswith("floor "):
        parts = text.split()
        if len(parts) >= 2:
            # Check for "floor 20" format
            try:
                size = int(parts[1])
                return {
                    'command': 'floor',
                    'params': (size, size),  # Make it a square by default
                    'text': text
                }
            except:
                pass
            
            # Check for "floor 20x30" format
            if 'x' in parts[1]:
                try:
                    dims = parts[1].split('x')
                    if len(dims) == 2:
                        width = int(dims[0])
                        height = int(dims[1])
                        return {
                            'command': 'floor',
                            'params': (width, height),
                            'text': text
                        }
                except:
                    pass
    
    # Try normal pattern matching
    for command_type, command_patterns in patterns.items():
        for pattern in command_patterns:
            match = re.search(pattern, text)
            if match:
                if command_type == 'floor' and match.groups()[0] and (len(match.groups()) < 2 or not match.groups()[1]):
                    # If only one dimension provided, make it a square
                    size = int(match.groups()[0])
                    return {
                        'command': command_type,
                        'params': (size, size),
                        'text': text
                    }
                else:
                    return {
                        'command': command_type,
                        'params': match.groups(),
                        'text': text
                    }
    
    return {'command': 'unknown', 'params': None, 'text': text}

def execute_wall_command(params):
    """Execute a wall creation command."""
    if not params or len(params) < 4:
        return "I need more information to create a wall. Please provide start and end coordinates."
    
    start_x = float(params[0])
    start_y = float(params[1])
    end_x = float(params[2])
    end_y = float(params[3])
    
    # Default height if not specified
    height = 10.0
    if len(params) >= 5 and params[4]:
        height = float(params[4])
    
    # Create wall
    try:
        # Get level elevation
        level_elevation = default_level.Elevation
        
        # Create start and end points with proper elevation
        start_point = DB.XYZ(start_x, start_y, level_elevation)
        end_point = DB.XYZ(end_x, end_y, level_elevation)
        
        # Create curve for wall path
        wall_curve = DB.Line.CreateBound(start_point, end_point)
        
        # Create wall
        with revit.Transaction('Create Wall'):
            wall = DB.Wall.Create(
                doc,
                wall_curve,
                default_wall_type.Id,
                default_level.Id,
                height,
                0.0,
                False,
                True
            )
            
            return "Wall created successfully from ({0}, {1}) to ({2}, {3}) with height {4} feet.".format(start_x, start_y, end_x, end_y, height)
    except Exception as e:
        return "Error creating wall: {}".format(str(e))

def execute_floor_command(params):
    """Execute a floor creation command."""
    if not params or len(params) < 2:
        if isinstance(params, tuple) and len(params) > 0 and 'points' in str(params[0]).lower():
            return "Please provide at least 3 points for the floor in the format (x,y), (x,y), (x,y)."
        else:
            return "I need dimensions to create a floor. Please specify like 'floor 20' or 'floor 20x30'."
    
    # Check if floor type exists
    if default_floor_type is None:
        return "No floor types available in this document. Please create a floor type first."
    
    try:
        # First, determine if this is a simple dimensions command or a points command
        if isinstance(params[0], str) and 'points' in params[0].lower():
            # This is a points-based floor
            points_text = params[0]
            
            # Extract coordinates in format (x,y) (x,y) ...
            coordinates = re.findall(r'\((-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\)', points_text)
            
            if not coordinates or len(coordinates) < 3:
                return "I need at least 3 points to create a floor boundary."
            
            # Create XYZ points
            boundary_points = [DB.XYZ(float(x), float(y), 0) for x, y in coordinates]
        else:
            # This is a dimensions-based floor
            width = float(params[0])
            height = float(params[1])
            
            # Create rectangle coordinates
            boundary_points = [
                DB.XYZ(0, 0, 0),
                DB.XYZ(width, 0, 0),
                DB.XYZ(width, height, 0),
                DB.XYZ(0, height, 0)
            ]
        
        # Create curve loop
        curve_loop = DB.CurveLoop()
        for i in range(len(boundary_points)):
            start_pt = boundary_points[i]
            end_pt = boundary_points[(i + 1) % len(boundary_points)]
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
                default_floor_type.Id, 
                default_level.Id
            )
            
            # Format the success message based on input type
            if isinstance(params[0], str) and 'points' in params[0].lower():
                points_str = ", ".join(["({},{})".format(x, y) for x, y in coordinates])
                return "Floor created successfully with points {}!".format(points_str)
            else:
                return "Floor created successfully with dimensions {}x{}!".format(params[0], params[1])
    except Exception as e:
        return "Error creating floor: {}".format(str(e))

def show_help():
    """Show comprehensive help information."""
    help_text = """Building Assistant Commands:

WALL COMMANDS:
- create a wall from (x,y) to (x,y) [with height h [feet]]
- add a wall from (x,y) to (x,y) [with height h [feet]]
- wall (x,y) to (x,y) [with height h [feet]]

Examples:
  create a wall from (0,0) to (20,0) with height 10 feet
  add a wall (0,0) to (0,20) with height 12
  wall (10,10) to (30,10)

FLOOR COMMANDS:
- floor [size]                     (creates a square floor)
- floor [width]x[height]           (creates a rectangular floor)
- create a floor [size]            (creates a square floor)
- create a floor [width]x[height]  (creates a rectangular floor)
- add a floor with points (x,y), (x,y), (x,y), ...  (creates a custom floor)
- floor with points (x,y) (x,y) (x,y) ...          (creates a custom floor)

Examples:
  floor 20                        (creates a 20x20 square floor)
  create a floor 30x40            (creates a 30x40 rectangular floor)
  add a floor with points (0,0), (20,0), (20,20), (0,20)  (creates a custom floor)

HELP COMMANDS:
- help
- commands
- ?
- (press Enter with no command)

Note: All coordinates are in feet and use the origin (0,0) as reference.
"""
    return help_text

# Main loop to keep the dialog open
while True:
    # Use a custom dialog to ensure the hint is shown and the default text clears on click
    command = forms.ask_for_string(
        default="Type 'help' to see available commands",  # Default text that clears on click
        prompt='Enter your building command:',
        title='Conversational Building Assistant',
        width=600,  # Adjust the width to fit the help text
        height=150,  # Adjust the height to make the box slightly larger
        hint='Try: wall (0,0) to (20,0) | floor 20x30 | help'  # Hint text below the input box
    )

    if command is None:
        break  # Exit the loop if the user closes the dialog

    parsed = parse_command(command)
    
    if parsed['command'] == 'wall':
        result = execute_wall_command(parsed['params'])
    elif parsed['command'] == 'floor':
        result = execute_floor_command(parsed['params'])
    elif parsed['command'] == 'help':
        result = show_help()
    else:
        result = "I don't understand that command. Type 'help' to see available commands."
    
    # Show the result in an alert dialog
    forms.alert(result, title='Building Assistant Result')