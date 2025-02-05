import adsk.core, traceback
import os
from ...lib import fusionAddInUtils as futil
from ... import config
import math
app = adsk.core.Application.get()
ui = app.userInterface



# TODO move these into the command dialog
onRampEveryXSlots = 1
distanceBetweenSlots = 2.5
baseThickness = 0.3
totalHeight = 2.5
computeCut = False


# TODO *** Specify the command identity information. ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_cmdDialog'
CMD_NAME = 'Multiconnect Back Genrator'
CMD_Description = 'A Fusion Add-in to create Multiconnect compatible backs'

# Specify that the command will be promoted to the panel.
IS_PROMOTED = True

# TODO *** Define the location where the command button will be created. ***
# This is done by specifying the workspace, the tab, and the panel, and the 
# command it will be inserted beside. Not providing the command to position it
# will insert it at the end.
WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidScriptsAddinsPanel'
COMMAND_BESIDE_ID = 'ScriptsManagerCommand'

# Resource location for command icons, here we assume a sub folder in this directory named "resources".
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []


# Executed when add-in is run.
def start():

    # Create a command Definition.
    cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_Description, ICON_FOLDER)

    # Define an event handler for the command created event. It will be called when the button is clicked.
    futil.add_handler(cmd_def.commandCreated, command_created)

    # ******** Add a button into the UI so the user can run the command. ********
    # Get the target workspace the button will be created in.
    workspace = ui.workspaces.itemById(WORKSPACE_ID)

    # Get the panel the button will be created in.
    panel = workspace.toolbarPanels.itemById(PANEL_ID)

    # Create the button command control in the UI after the specified existing command.
    control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)

    # Specify if the command is promoted to the main toolbar. 
    control.isPromoted = IS_PROMOTED


# Executed when add-in is stopped.
def stop():
    # Get the various UI elements for this command
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    command_control = panel.controls.itemById(CMD_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    # Delete the button command control
    if command_control:
        command_control.deleteMe()

    # Delete the command definition
    if command_definition:
        command_definition.deleteMe()


# Function that is called when a user clicks the corresponding button in the UI.
# This defines the contents of the command dialog and connects to the command related events.
def command_created(args: adsk.core.CommandCreatedEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Created Event')

    # https://help.autodesk.com/view/fusion360/ENU/?contextId=CommandInputs
    inputs = args.command.commandInputs

    # Center point selection tool
    selectionInput = inputs.addSelectionInput('center_point_input', 'Center', 'The front center of the connector')
    selectionInput.setSelectionLimits(1, 1)
    selectionInput.addSelectionFilter('SketchPoints')
    selectionInput.addSelectionFilter('ConstructionPoints')
    selectionInput.addSelectionFilter('Vertices')

    # Create a value input field for the width
    defaultLengthUnits = app.activeProduct.unitsManager.defaultLengthUnits
    default_value = adsk.core.ValueInput.createByString('40')
    inputs.addValueInput('width_value_input', 'Back Width', defaultLengthUnits, default_value)

    # Create a value input field for the height
    defaultLengthUnits = app.activeProduct.unitsManager.defaultLengthUnits
    default_value = adsk.core.ValueInput.createByString('30')
    inputs.addValueInput('height_value_input', 'Back Height', defaultLengthUnits, default_value)

    # boolean input for whether to create the back and cut
    inputs.addBoolValueInput('tools_only', 'Tools Only', True)

    # TODO Connect to the events that are needed by this command.
    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(args.command.executePreview, command_preview, local_handlers=local_handlers)
    futil.add_handler(args.command.validateInputs, command_validate_input, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)


# This event handler is called when the user clicks the OK button in the command dialog or 
# is immediately called after the created event not command inputs were created for the dialog.
def command_execute(args: adsk.core.CommandEventArgs):
    generate_multiconnect_back(args)

def command_preview(args: adsk.core.CommandEventArgs):

    futil.log(f'{CMD_NAME} Command Preview Event')
    args.isValidResult = generate_multiconnect_back(args)



def generate_multiconnect_back(args: adsk.core.CommandEventArgs):
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        root = design.rootComponent
        features = root.features
        
        # We will create and use some user parameters
        userParams = design.userParameters


        # Create a new user parameter if it doesn't exist
        paramName = "DotRadius"
        paramValue = 1.015  # Default value
        paramUnit = "cm"  # Supports 'mm', 'cm', 'in', etc.

        existingParam = userParams.itemByName(paramName)
        if existingParam is None:
            userParams.add(paramName, adsk.core.ValueInput.createByReal(paramValue), paramUnit, "Radius of the connector dot")

        dotDiameter = userParams.itemByName(paramName)

        # Get a reference to your command's inputs.
        inputs = args.command.commandInputs
        width_value_input: adsk.core.TextBoxCommandInput = inputs.itemById('width_value_input')
        height_value_input: adsk.core.ValueCommandInput = inputs.itemById('height_value_input')
        tool_only_input: adsk.core.BoolValueCommandInput = inputs.itemById('tools_only')
        center_point_input: adsk.core.SelectionCommandInput = inputs.itemById('center_point_input')

        backHeight = max(2.5, height_value_input.value)
        backWidth = max(width_value_input.value, distanceBetweenSlots)
        slotCount = math.floor(backWidth/distanceBetweenSlots)
        backThickness = 0.65

        slot_tool = create_slot(backHeight)
        
        # Move the tool to the middle slot location
        bodies = adsk.core.ObjectCollection.create()
        bodies.add(slot_tool)

        # offset to the edge location, because symmetrical patterns aren't working correctly in the API
        slotXShift = (distanceBetweenSlots * ( 1 - slotCount))/2
    
        # don't forget to add in our selected point
        selectedEntity = center_point_input.selection(0).entity
        targetPoint = selectedEntity.worldGeometry if  selectedEntity.objectType == adsk.fusion.SketchPoint.classType() else selectedEntity.geometry
        futil.log(f'{CMD_NAME} Target Point: ({targetPoint.x},{targetPoint.y},{targetPoint.z})')

        vector = adsk.core.Vector3D.create(slotXShift + targetPoint.x, backThickness - 0.42 + targetPoint.y, backHeight - 1.3 + targetPoint.z)
        transform = adsk.core.Matrix3D.create()
        transform.translation = vector

        moveFeats = features.moveFeatures
        moveFeatureInput = moveFeats.createInput2(bodies)
        moveFeatureInput.defineAsFreeMove(transform)
        moveFeats.add(moveFeatureInput)

        #  Make more slots
        rectangularPatterns = features.rectangularPatternFeatures
        patternInput = rectangularPatterns.createInput(
            bodies, 
            root.xConstructionAxis,
            adsk.core.ValueInput.createByReal(slotCount),
            adsk.core.ValueInput.createByReal(distanceBetweenSlots), 
            adsk.fusion.PatternDistanceType.SpacingPatternDistanceType)

        slotPattern = rectangularPatterns.add(patternInput)
        slotBodies = adsk.core.ObjectCollection.create()
        for body in slotPattern.bodies:
                slotBodies.add(body)


        if not tool_only_input.value:
        # Make the overall shape
            back = create_back_cube(backWidth, backThickness, backHeight, targetPoint)

            # Subtract the slot tool
            combineFeatures = features.combineFeatures

            input: adsk.fusion.CombineFeatureInput = combineFeatures.createInput(back, slotBodies)
            input.isNewComponent = False
            input.isKeepToolBodies = False
            input.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
            combineFeature = combineFeatures.add(input)
    except Exception as err:
        args.executeFailed = True
        stackTrace = traceback.format_exc()
        futil.log(f'{CMD_NAME} Error occurred, {err}, {stackTrace}')
        return False  
    return True


def create_back_cube(w, d, h, backEdgePoint):
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    features = root.features

    dotDiameter = design.userParameters.itemByName('DotRadius')

    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = "Back Profile"

    centerPoint = adsk.core.Point3D.create(0 + backEdgePoint.x,backEdgePoint.y + d/2,0 + backEdgePoint.z)
    sketch.sketchCurves.sketchLines.addCenterPointRectangle(centerPoint, adsk.core.Point3D.create(w/2 + backEdgePoint.x , backEdgePoint.y + d, 0 + backEdgePoint.z))    

    profile = sketch.profiles.item(0)
    distance = adsk.core.ValueInput.createByReal(h)
    cubeExtrude = features.extrudeFeatures.addSimple(profile, distance, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

    backBody = cubeExtrude.bodies.item(0)
    backBody.name = "Back"

    return backBody


def create_slot(backHeight):
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    features = root.features

    dotDiameter = design.userParameters.itemByName('DotRadius')

    slotSketch = root.sketches.add(root.xYConstructionPlane)
    slotSketch.name = "Slot Profile"

    profilePoints = [adsk.core.Point3D.create(x, y, 0) for x, y in [[0,0],[dotDiameter.value,0],[dotDiameter.value,0.12121],[0.765,0.3712],[0.765,0.42],[0,0.42]]]

    drawPolyline(slotSketch, profilePoints)

 
    slotProfile = slotSketch.profiles.item(0)

    lines = slotSketch.sketchCurves.sketchLines
    axisLine = root.yConstructionAxis

    revolveFeats = features.revolveFeatures
    revolveInput = revolveFeats.createInput(slotProfile, axisLine, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

    # Set the rotation angle (90 degrees in radians)
    revolveInput.setAngleExtent(False, adsk.core.ValueInput.createByReal(3.14159265359 * 0.5))

    # Execute the revolve
    revolveFeats.add(revolveInput)

    # Extrude the slot length
    extrudes = features.extrudeFeatures
    distance = adsk.core.ValueInput.createByReal(backHeight * -1)
    extrude1 = extrudes.addSimple(slotProfile, distance, adsk.fusion.FeatureOperations.JoinFeatureOperation)        
    # Get the extrusion body
    body1 = extrude1.bodies.item(0)
    body1.name = "Slot"

    inputEntites = adsk.core.ObjectCollection.create()
    inputEntites.add(body1)
    mirrorFeatures = features.mirrorFeatures
    mirrorInput = mirrorFeatures.createInput(inputEntites, root.yZConstructionPlane)
    mirrorInput.isCombine = True
        
    # Create the mirror feature
    mirrorFeature = mirrorFeatures.add(mirrorInput)

    # TODO add conditional for onramp
    rampFeature = createOnramp()

    rampSpacing = distanceBetweenSlots * onRampEveryXSlots
    rampQuantity = math.floor(backHeight/rampSpacing)
    
    patternCollection = adsk.core.ObjectCollection.create()
    patternCollection.add(rampFeature)
    rectangularPatterns = features.rectangularPatternFeatures
    patternInput = rectangularPatterns.createInput(
        patternCollection, 
        root.zConstructionAxis,
        adsk.core.ValueInput.createByReal(rampQuantity),
        adsk.core.ValueInput.createByReal(rampSpacing * -1), 
        adsk.fusion.PatternDistanceType.SpacingPatternDistanceType)
    rectangularPattern = rectangularPatterns.add(patternInput)

    # TODO add conditional for dimple
    createDimple()

    return body1

def createOnramp():
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    features = root.features

    dotDiameter = design.userParameters.itemByName('DotRadius')


    # Create the sketch for the cylinder
    rampSketch = root.sketches.add(root.xZConstructionPlane)
    rampSketch.name = "Ramp Sketch"

    circles = rampSketch.sketchCurves.sketchCircles
    circle1 = circles.addByCenterRadius(adsk.core.Point3D.create(0,2, 0), dotDiameter.value*2)
    circleDim = rampSketch.sketchDimensions.addDiameterDimension(circle1, adsk.core.Point3D.create(1.2, 1.2, 0)) 
    # get ModelParameter
    modelPrm: adsk.fusion.ModelParameter = circleDim.parameter
    # Set user parameter name in ModelParameter
    modelPrm.expression = dotDiameter.name + "*2"

    # extrude into cylinder
    extrudes = features.extrudeFeatures
    distance = adsk.core.ValueInput.createByReal(0.5)
    rampExtrude = extrudes.addSimple(rampSketch.profiles.item(0), distance, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    return rampExtrude

def createDimple():
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    features = root.features

    dotDiameter = design.userParameters.itemByName('DotRadius')

    dimpleSketch = root.sketches.add(root.yZConstructionPlane)
    dimpleSketch.name = "Dimple sketch"

    profilePoints = [adsk.core.Point3D.create(x, y, 0) for x, y in [[0,0],[0,0.15],[0.15,0]]]
    drawPolyline(dimpleSketch, profilePoints)

    profile = dimpleSketch.profiles.item(0)
    axisLine = root.yConstructionAxis

    revolveFeats = features.revolveFeatures

    revolveInput = revolveFeats.createInput(profile, axisLine, adsk.fusion.FeatureOperations.CutFeatureOperation)
    # Revolve the dimple
    revolveInput.setAngleExtent(False, adsk.core.ValueInput.createByReal(3.14159265359 * 2))

    # Execute the revolve
    revolveFeats.add(revolveInput)


def drawPolyline(
    skt :adsk.fusion.Sketch,
    pnts :list):

    count = len(pnts)
    pnts.append(pnts[0])

    lines = skt.sketchCurves.sketchLines

    skt.isComputeDeferred = True
    for i in range(count):
        newline = lines.addByTwoPoints(pnts[i], pnts[i + 1])
        skt.sketchDimensions.addDistanceDimension(newline.startSketchPoint, newline.endSketchPoint, adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation, adsk.core.Point3D.create(5.5, -1, 0))

    skt.isComputeDeferred = False

# This event handler is called when the user changes anything in the command dialog
# allowing you to modify values of other inputs based on that change.
def command_input_changed(args: adsk.core.InputChangedEventArgs):
    changed_input = args.input
    inputs = args.inputs

    # General logging for debug.
    futil.log(f'{CMD_NAME} Input Changed Event fired from a change to {changed_input.id}')


# This event handler is called when the user interacts with any of the inputs in the dialog
# which allows you to verify that all of the inputs are valid and enables the OK button.
def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Validate Input Event')

    inputs = args.inputs
    
    # Verify the validity of the input values. This controls if the OK button is enabled or not.
    valueInput = inputs.itemById('width_value_input')
    if valueInput.value >= 0:
        args.areInputsValid = True
    else:
        args.areInputsValid = False
        
       
    valueInput = inputs.itemById('height_value_input')
    if valueInput.value >= 0:
        args.areInputsValid = True
    else:
        args.areInputsValid = False
        

# This event handler is called when the command terminates.
def command_destroy(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Destroy Event')

    global local_handlers
    local_handlers = []
