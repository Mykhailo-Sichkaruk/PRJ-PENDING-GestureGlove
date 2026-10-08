"""Editable placement PoC; executed inside FreeCAD through MCP.

All lengths are millimetres. The hand, sensor modules, wiring and small parts
are simplified envelopes, not manufacturing models or an electrical schematic.
Set project_root before executing this file (scripts/check_mcp.py does this).
"""
from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui
import Part


def build_glove(project_root):
    # Refuse to overwrite an open document and discard someone's manual edits.
    output = Path(project_root) / "examples/poc/cad" / "glove-poc.FCStd"
    if any(
        document.Name == "GlovePoC"
        or (document.FileName and Path(document.FileName).resolve() == output.resolve())
        for document in App.listDocuments().values()
    ):
        raise RuntimeError("Close the glove PoC before rebuilding; save any manual edits first.")

    doc = App.newDocument("GlovePoC")
    doc.Label = "Gesture glove | placement PoC"
    doc.addObject("App::DocumentObjectGroup", "Glove").Label = "01 | Glove envelope"
    doc.addObject("App::DocumentObjectGroup", "Electronics").Label = "02 | Existing modules"
    doc.addObject("App::DocumentObjectGroup", "FlexSensors").Label = "03 | Five DIY flex sensors"
    doc.addObject("App::DocumentObjectGroup", "Contacts").Label = "04 | Five fingertip contacts + palm"
    doc.addObject("App::DocumentObjectGroup", "Passives").Label = "05 | Resistors and capacitors"
    doc.addObject("App::DocumentObjectGroup", "Wiring").Label = "06 | Illustrative wire routes"

    fabric = (0.24, 0.31, 0.38)
    flex_colour = (0.91, 0.63, 0.19)
    contact_colour = (0.78, 0.42, 0.23)

    def finish(obj, group, label, colour):
        doc.getObject(group).addObject(obj)
        obj.Label = label
        obj.ViewObject.ShapeColor = colour
        obj.ViewObject.LineColor = (0.12, 0.15, 0.18)
        return obj

    def box(name, label, size, position, colour, group="Electronics", angle=0):
        obj = doc.addObject("Part::Box", name)
        obj.Length, obj.Width, obj.Height = size
        obj.Placement = App.Placement(App.Vector(*position), App.Rotation(App.Vector(0, 0, 1), angle))
        return finish(obj, group, label, colour)

    def shape(name, label, geometry, colour, group):
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = geometry
        return finish(obj, group, label, colour)

    def route(name, points, colour, label):
        # Line geometry represents a route, not an electrical net or cable diameter.
        obj = shape(name, label, Part.makePolygon([App.Vector(*p) for p in points]), colour, "Wiring")
        obj.ViewObject.LineColor = colour
        obj.ViewObject.LineWidth = 3.0
        return obj

    def note(obj, name, value):
        obj.addProperty("App::PropertyString", name, "PoC notes")
        setattr(obj, name, value)

    box("Palm", "Glove palm / back of hand", (76, 85, 12), (-38, 0, 0), fabric, "Glove")
    box("Cuff", "Wrist cuff", (60, 42, 12), (-30, -42, 0), fabric, "Glove")

    # name, base x/y, width, length, rotation around Z
    fingers = [
        ("Thumb", -35, 17, 19, 56, 45),
        ("Index", -34, 78, 15, 73, 0),
        ("Middle", -15, 82, 16, 83, 0),
        ("Ring", 5, 80, 15, 76, 0),
        ("Little", 24, 70, 13, 61, 0),
    ]
    for index, (name, x, y, width, length, angle) in enumerate(fingers):
        placement = App.Placement(App.Vector(x, y, 0), App.Rotation(App.Vector(0, 0, 1), angle))
        solid = Part.makeBox(width, length - width / 2, 12)
        tip = Part.makeCylinder(width / 2, 12, App.Vector(width / 2, length - width / 2, 0))
        finger = shape(name, name + " glove envelope", solid.fuse(tip).removeSplitter(), fabric, "Glove")
        finger.Placement = placement

        sensor_pos = placement.multVec(App.Vector((width - 6) / 2, 7, 12.5))
        box(name + "Flex", name + " | DIY flex strip", (6, length - 17, 0.6),
            tuple(sensor_pos), flex_colour, "FlexSensors", angle)
        pad_pos = placement.multVec(App.Vector((width - 10) / 2, length - 14, -0.7))
        box(name + "Contact", name + " | contact pad on palm side", (10, 10, 0.7),
            tuple(pad_pos), contact_colour, "Contacts", angle)
        flex_start = placement.multVec(App.Vector(width / 2, 7, 13.2))
        route(name + "FlexRoute", [(-21 + index * 5, -9, 16),
              (-25 + index * 12, 45, 13.5), tuple(flex_start)], flex_colour,
              name + " flex cable route (illustrative)")
        pad_end = placement.multVec(App.Vector(width / 2, length - 9, -1))
        route(name + "ContactRoute", [(-20 + index * 8, -10, -1),
              (-24 + index * 12, 50, -1), tuple(pad_end)], contact_colour,
              name + " contact cable route (palm side)")

    box("PalmContact", "Common palm contact fabric | topology TBD", (32, 20, 0.6),
        (-16, 22, -0.6), contact_colour, "Contacts")

    board = box("ESP32Board", "Adafruit ESP32-S3 Feather 5323 | PCB envelope", (50.8, 22.86, 1.6),
                (-25.4, -35, 14), (0.13, 0.18, 0.24))
    note(board, "SourceURL", "https://www.adafruit.com/product/5323")
    note(board, "Status", "Provisional board. Charging and 3.3 V regulation are onboard. Details simplified.")
    box("ESP32Module", "ESP32-S3 module | simplified", (20, 15, 2.5), (-1, -31, 15.6), (0.69, 0.72, 0.75))
    box("USBC", "USB-C | charging and programming", (7, 9, 3.2), (-27, -28, 15.6), (0.78, 0.80, 0.83))
    box("BatteryConnector", "JST-PH battery connector | simplified", (7, 6, 4), (-18, -17, 15.6), (0.92, 0.90, 0.82))
    for row_y in [-34, -14]:
        for index in range(12):
            pin = Part.makeCylinder(0.75, 0.15, App.Vector(-17 + index * 2.54, row_y, 15.65))
            shape("Pad", "Illustrative header pad (not a pin assignment)", pin, (0.84, 0.65, 0.21), "Electronics")

    battery = box("Battery", "LiPo 3.7 V 500 mAh | Adafruit 1578", (36, 29, 4.75),
                  (-19, 5, 14), (0.71, 0.74, 0.77))
    note(battery, "SourceURL", "https://www.adafruit.com/product/1578")
    note(battery, "Status", "Nominal product dimensions; allow pouch, lead and mounting clearance later.")
    box("BatteryTape", "Battery end tape | illustrative", (36, 4, 4.9), (-19, 5, 14), (0.93, 0.73, 0.19))
    route("BatteryPositive", [(-13, 7, 19), (-20, 0, 19), (-17, -14, 19)], (0.85, 0.16, 0.14), "Battery positive lead")
    route("BatteryNegative", [(-10, 7, 19), (-17, 0, 19), (-14, -14, 19)], (0.12, 0.12, 0.13), "Battery negative lead")

    imu = box("IMU", "GY-521 / MPU6050 | provisional envelope", (20, 16, 1.6),
              (-10, 54, 14), (0.12, 0.42, 0.65))
    note(imu, "Status", "Generic module envelope; confirm dimensions for the purchased board.")
    box("IMUChip", "MPU6050 chip | simplified", (4, 4, 1), (-2, 60, 15.6), (0.12, 0.13, 0.14))
    route("IMUCable", [(4, -12, 16), (21, 38, 15), (8, 55, 16)], (0.20, 0.73, 0.73), "IMU power / I2C bundle route")
    box("PowerSwitch", "Slide switch | proposed EN-to-GND control", (8, 4, 4), (28, 4, 14), (0.18, 0.19, 0.20))
    box("SwitchLever", "Switch lever", (3, 2, 2), (31, 5, 18), (0.72, 0.73, 0.75))

    for index in range(5):
        y = 16 + index * 5
        box("FlexResistor", f"Flex {index + 1} | 10 kohm resistor envelope", (6, 2, 2),
            (24, y, 14), (0.72, 0.64, 0.48), "Passives")
        box("FilterCapacitor", f"Flex {index + 1} | 100 nF capacitor envelope", (2, 2, 2),
            (32, y, 14), (0.60, 0.35, 0.15), "Passives")

    doc.recompute()
    invalid = [o.Name for o in doc.Objects if hasattr(o, "Shape") and not o.Shape.isValid()]
    if invalid:
        raise RuntimeError(f"Invalid geometry: {invalid}")
    Gui.activeDocument().activeView().viewAxonometric()
    Gui.activeDocument().activeView().fitAll()
    doc.recompute()
    doc.saveAs(str(output))
    print(f"Saved {output}; {len(doc.Objects)} objects; five flex sensors and five contact pads.")
    return doc


build_glove(project_root)
