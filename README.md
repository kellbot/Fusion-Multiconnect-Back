# Autodesk Fusion Multiconnect Back Generator
I created this simple tool to quickly create Multiconnect backs in Fusion. This will create a new body with the specified dimensions.

## Installation
Download the source code and [install it manually](https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/How-to-install-an-ADD-IN-and-Script-in-Fusion-360.html) as an Add In

## Use
Go to Utilites > Multiconnect Back Generator and enter the desired dimensions. By default, it will create a new object for the back and cut out slots in it. If you would prefer to create the slots and cut them out of an existing object click "tools only"

### Options
* Center: this poorly named selector is a point which will be at the center bottom on the face (smooth side) of the generated connector
* Width: the overall width of the connector. Wide connectors will have multiple slots
* Height: the overall height of the connector. Tall connectors will have multiple "on ramps"
* Tool only: will only generate positives of the "slots", will not generate back

## Known bugs
For some reason the rectangular pattern feature creates dupilicate slots. These all get consumed when you cut them out of the back, but if you opt for "tools only" you'll end up with surplus objects.
