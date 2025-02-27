# Revit Building Assistant

A conversational interface for Revit that allows architects and engineers to create building elements using natural language commands. This pyRevit extension provides an intuitive command-line interface for quickly creating walls and floors without having to navigate through Revit's menu system.

## Features

- Create walls using simple text commands like `create a wall from (0,0) to (20,0) with height 10 feet`
- Generate floors with commands such as `floor 20x30` or with custom points
- Built-in help system that guides new users through available commands
- Auto-clearing command hints that make the tool easy to use for first-time users

## Examples

```
# Create a basic wall
wall (0,0) to (20,0) with height 10 feet

# Create a square floor
floor 20

# Create a rectangular floor
floor 30x40

# Create a custom floor
add a floor with points (0,0), (20,0), (20,20), (0,20)
```

## Requirements

- Revit 2021 or newer
- pyRevit 4.8 or newer

## Installation

1. Install [pyRevit](https://github.com/eirannejad/pyRevit) if you haven't already
2. Clone this repository or download the files
3. Place the files in your pyRevit extensions folder (typically `%appdata%\pyRevit\Extensions`)
4. Restart Revit or reload pyRevit

## Usage

1. Click on the "Building Assistant" button in the pyRevit tab
2. Enter your command in the dialog box
3. Type `help` to see all available commands

## Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/yourusername/revit-building-assistant/issues).

## License

This project is [MIT](LICENSE) licensed.

## Acknowledgments

- Thanks to [pyRevit](https://github.com/eirannejad/pyRevit) for making Revit extensions easier
- Inspired by natural language interfaces in modern design tools
