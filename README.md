# Autodesk Fusion Multiconnect Back Generator
I created this simple tool to quickly create Multiconnect backs in Fusion. This will create a new body with the specified dimensions.

## Installation
Download the source code and [install it manually](https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/How-to-install-an-ADD-IN-and-Script-in-Fusion-360.html) as an Add In

## Use
Go to Create > Multiconnect Back Generator and enter the desired dimensions. By default, it will create a new object for the back and cut out slots in it. If you would prefer to create the slots and cut them out of an existing object click "tools only"

### Options
* Center: this poorly named selector is a point which will be at the center bottom on the face (smooth side) of the generated connector
* Plane: This is the plane along which the slots and back will be generated. It must be vertical or things won't work correctly
* Width: the overall width of the connector. Wide connectors will have multiple slots
* Height: the overall height of the connector. Tall connectors will have multiple "on ramps"
* Tool only: will only generate positives of the "slots", will not generate back

## Known bugs and limitations
* The plane must be aligned on the Z axis for it to work.
* It probably doesn't play well inside components where the origin is in a different location than the root origin