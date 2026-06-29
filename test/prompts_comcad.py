system_prompt = """You are an expert CAD engineer and Python programmer specialized in COM interface automation. 
Your goal is to write executable Python codes that call the COM APIs (`win32com.client`) to programmatically drive CAD software (AutoCAD, Inventor, Solidworks) and complete the given CAD task.

Rules:
- Think before coding. Generate deterministic, non-interactive codes.
- Always output the complete, fully executable Python script. Do NOT provide partial snippets.
- Use only win32com.client, pythoncom, and Python standard libraries. Use only real, official COM APIs of target CAD software. 

For each step, you receive:
1) Task instruction.
2) Terminal output from the last run.
3) Current screenshot after the last run.

Outputs:
1) Brief reasoning inside <thinking>...</thinking>.
2) A high-level decision for this step. Choose one:
- DONE: The task has been completed.
- FAIL: The task cannot be completed.
- CODE: Output Python code for this step. The system will execute the code.
Wrap the decision as:
```decision
CODE (or DONE/FAIL)```
3) If and only if the decision is CODE, output a single ```python``` block containing full executable codes. For example:
```python
# Full codes```
"""


sldworks_3d_model_example = """
Example: 3D Modeling in Solidworks
- Task Instruction: Model this part in Solidworks: To construct the first part of the cylinder, start by creating a new coordinate system. Define the Euler angles as negative ninety degrees for the x-axis, zero degrees for the y-axis, and negative ninety degrees for the z-axis. Set the translation vector to [0.1286, 0.0, 0.0]. Next, draw a two-dimensional sketch on the first face. In the first loop, draw a circle with its center at [0.375, 0.375] and a radius of 0.375. Transform the two-dimensional sketch into three dimensions by rotating it using the Euler angles and translating it using the defined translation vector. Finally, extrude the sketch 0.0643 units in the direction of the normal and 0.0643 units in the opposite direction of the normal to create a solid body. The final dimensions of this part are 0.7500000000000007 units in length, 0.7500000000000007 units in width, and 0.12857142857142867 units in height. This completes the construction of the first part, which forms the base of the final cylinder. After creating the solid body, export the model as an STL file to: C:/Users/Docker/Downloads/00888524.stl and as a STEP file to: C:/Users/Docker/Downloads/00888524.step.
- Output:
<thinking> Create a new part, select the Right Plane (XY -> YZ under Euler -90,0,-90), sketch a circle at the transformed center (u,v) with radius 0.375, extrude it 0.0643 in both towards and opposite the normal directions to form the cylinder body, apply the translation (0.1286,0,0), then export STL and STEP to the specified paths using silent save.</thinking>

```decision
CODE
```

```python
import win32com.client
import pythoncom
import math
from win32com.client import gencache

# Load SOLIDWORKS 2025 Type Library for early binding
swModule = gencache.EnsureModule('{83A33D31-27C5-11CE-BFD4-00400513BB57}', 0, 33, 0)

def super_cast(obj, interface_name):
    # Cast the COM object to a specific SOLIDWORKS interface
    try:
        interface_class = getattr(swModule, interface_name)
        obj_query = obj._oleobj_.QueryInterface(interface_class.CLSID, pythoncom.IID_IDispatch)
        return interface_class(obj_query)
    except Exception:
        return obj

def get_plane_and_coords_euler_transform(rx_deg, ry_deg, rz_deg, x, y):
    # Determines plane and coordinate mapping based on Euler angles.
    # Euler Angles: [0,0,0], Plane: Front (U=+x, V=+y), Coords: (x,y,z)->(x,y,z)
    # Euler Angles: [-90,0,-90], Plane: Right (U=-z, V=+y), Coords: (x,y,z)->(z,-x,-y)
    # Euler Angles: [0,0,-90], Plane: Front (U=+x, V=+y), Coords: (x,y,z)->(y,-x,z)
    if rx_deg == 0 and ry_deg == 0 and rz_deg == 0:
        return {
            "plane_name": "Front Plane",
            "plane_name_cn": "前视基准面",
            "rot_x": x,
            "rot_y": y
        }
    elif rx_deg == -90 and ry_deg == 0 and rz_deg == -90:
        return {
            "plane_name": "Right Plane",
            "plane_name_cn": "右视基准面",
            "rot_x": y,  # Maps to World -Z
            "rot_y": -x  # Maps to World Y
        }
    elif rx_deg == 0 and ry_deg == 0 and rz_deg == -90:
        return {
            "plane_name": "Front Plane",
            "plane_name_cn": "前视基准面",
            "rot_x": y, # Maps to World X
            "rot_y": -x # Maps to World Y
        }

def main():
    # 1. Initialize SOLIDWORKS Application Session
    try:
        swApp = win32com.client.Dispatch("SldWorks.Application")
        swApp.Visible = True
        swApp.CloseAllDocuments(True)
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    # 2. Document and Manager Initialization
    # swDefaultTemplatePart = 8
    part_template = swApp.GetUserPreferenceStringValue(8)
    model = super_cast(swApp.NewDocument(part_template, 0, 0, 0), "IModelDoc2")
    ext = super_cast(model.Extension, "IModelDocExtension")
    sketch_mgr = super_cast(model.SketchManager, "ISketchManager")
    feat_mgr = super_cast(model.FeatureManager, "IFeatureManager")

    # 3. Define Modeling Parameters
    rx_deg, ry_deg, rz_deg = -90.0, 0.0, -90.0
    tx, ty, tz = 0.1286, 0.0, 0.0
    center_x, center_y, radius = 0.375, 0.375, 0.375
    ext_depth_towards_normal = 0.0643
    ext_depth_opposite_normal = 0.0643

    # 4. Coordinate Transformation and Plane Selection based on Euler Angles
    euler_transform_res = get_plane_and_coords_euler_transform(rx_deg, ry_deg, rz_deg, center_x, center_y)

    # Select target plane for sketching
    static = ext.SelectByID2(
        euler_transform_res['plane_name'],  # Name: Plane to select
        "PLANE",  # Type: Object type
        0,  # X: X selection location or 0
        0,  # Y: Y selection location or 0
        0,  # Z: Z selection location or 0
        False,  # Append: Add to selection list
        0,  # Mark: Value that you want to use as a mark
        None,  # Callout: Pointer to the associated callout
        0  # SelectOption: Selection options
    )
    if not static:
        ext.SelectByID2(euler_transform_res['plane_name_cn'], "PLANE", 0, 0, 0, False, 0, None, 0)

    # 5. Create 2D Sketch Geometry
    sketch_mgr.InsertSketch(True)
    sketch_mgr.CreateCircleByRadius(
        euler_transform_res['rot_x'],  # XC: Local U coordinate of the circle center point in meters
        euler_transform_res['rot_y'],  # YC: Local V coordinate of the circle center point in meters
        0,  # Zc: Normal offset (W) of the circle center point in meters
        radius  # Radius: Radius of the circle center point in meters
    )
    sketch_mgr.InsertSketch(True)

    # 6. Create 3D Extrusion Feature
    # Select Sketch1 for processing
    ext.SelectByID2("Sketch1", "SKETCH", 0, 0, 0, False, 0, None, 0)

    # Extrusion
    feat_mgr.FeatureExtrusion3(
        False,  # Sd: True for single ended, false for double ended
        False,  # Flip: True to flip the side to cut
        False,  # Dir: True to flip the direction of extrusion
        0,  # T1: Termination type for first end of the extrusion
        0,  # T2: Termination type for second end of the extrusion
        ext_depth_towards_normal,  # D1: Depth of extrusion for first end in meters
        ext_depth_opposite_normal,  # D2: Depth of extrusion for second end in meters
        False,  # Dchk1: True to allow drafting in the first direction, false to not
        False,  # Dchk2: True to allow drafting in the second direction, false to not
        False,  # Ddir1: True for first draft angle to be inward, false to be outward; valid only if Dchk1 is true
        False,  # Ddir2: True for second draft angle to be inward, false to be outward; valid only if Dchk2 is true
        0.0,  # Dang1: Draft angle for first end; valid only if Dchk1 is true
        0.0,  # Dang2: Draft angle for second end; valid only if Dchk2 is true
        False,  # OffsetReverse1: True to offset the first end from another face or plane in a direction away from the sketch, false to offset in a direction toward the sketch
        False,  # OffsetReverse2: True to offset the second end from another face or plane in a direction away from the sketch, false to offset in a direction toward the sketch
        True,  # TranslateSurface1: True if the first end of the extrusion is a translation of the reference surface, false if it has a true offset
        True,  # TranslateSurface2: True if the second end of the extrusion is a translation of the reference surface, false if it has a true offset
        True,  # Merge: True to merge the results in a multibody part, false to not
        True,  # UseFeatScope: True if the feature only affects selected bodies, false if the feature affects all bodies
        True,  # UseAutoSelect: True to automatically select all bodies and have the feature affect those bodies, false to select the bodies that the feature affects
        0,  # T0: Start condition
        0,  # StartOffset: Distance from the sketch plane to start the extrude
        False  # FlipStartOffset: True to flip the direction of the start offset, false to not
    )

    # 7. Apply Global Translation
    part = super_cast(model, "IPartDoc")
    bodies = part.GetBodies2(0, False)  # swAllBodies = 0

    if bodies:
        sw_body = super_cast(bodies[0], "IBody2")
        model.ClearSelection2(True)
        # Select body with Mark 1 as required by InsertMoveCopyBody2
        ext.SelectByID2(sw_body.Name, "SOLIDBODY", 0, 0, 0, False, 1, None, 0)

        feat_mgr.InsertMoveCopyBody2(
            float(tx),  # transX: Translation X
            float(ty),  # transY: Translation Y
            float(tz),  # transZ: Translation Z
            0.0,  # transDist: Translation distance
            0.0,  # rotPointX: Rotation center X
            0.0,  # rotPointY: Rotation center Y
            0.0,  # rotPointZ: Rotation center Z
            0.0,  # rotAngleX: Rotation angle X
            0.0,  # rotAngleY: Rotation angle Y
            0.0,  # rotAngleZ: Rotation angle Z
            False,  # bCopy: Copy body or move
            1  # numCopies: Number of copies
        )

    # 8. Rebuild and Export Model
    model.EditRebuild3()
    save_name = 'C:/Users/Docker/Downloads/00888524'

    # Export to STL
    ext.SaveAs3(
        f"{save_name}.stl",  # Name: Full path of the document to save
        0,  # Version: swSaveAsCurrentVersion
        1,  # Options: swSaveAsOptions_Silent
        None,  # ExportData: Export data object
        None,   # AdvancedSaveAsOptions: IAdvancedSaveAsOptions
        0,  # Errors: Output error code
        0  # Warnings: Output warning code
    )

    # Export to STEP
    ext.SaveAs3(
        f"{save_name}.step",  # Name: Full path of the document to save
        0,  # Version: swSaveAsCurrentVersion
        1,  # Options: swSaveAsOptions_Silent
        None,  # ExportData: Export data object
        None,   # AdvancedSaveAsOptions: IAdvancedSaveAsOptions
        0,  # Errors: Output error code
        0  # Warnings: Output warning code
    )

    print(f"Modeling complete. Files saved at {save_name}")

if __name__ == "__main__":
    main()
```
"""

inventor_3d_model_example = """
Example: 3D Modeling in Inventor
- Task Instruction: Model this part in Inventor: Create a new coordinate system by setting the Euler angles to zero, zero, and negative ninety degrees, and the translation vector to zero, zero point three nine two six, and zero. Next, draw a two-dimensional sketch on the first face. In the first loop, draw a single circle centered at coordinates zero point zero two five two, zero point zero two five two, with a radius of zero point zero two five two. Transform the two-dimensional sketch into three dimensions by rotating it using the Euler angles of zero, zero, and negative ninety degrees, and translating it using the vector zero, zero point three nine two six, and zero. Extrude the two-dimensional sketch along the normal direction by zero point three nine two six units, ensuring no extrusion occurs in the opposite direction. Perform a boolean operation to create a new solid body from the extruded sketch. The resulting cylindrical object will have a length of zero point zero five zero three eight nine zero five eight eight two three five two nine four one units, a width of zero point zero five zero three eight nine zero five eight eight two three five two nine four one units, and a height of zero point three nine two six four seven zero five eight eight two three five two nine three five units. After creating the solid body, export the model as an STL file to: C:/Users/Docker/Downloads/00776997.stl and as a STEP file to: C:/Users/Docker/Downloads/00776997.step.
- Output: 
<thinking>Create a new part with a UCS defined by Euler angles (0, 0, -90) and translation [0, 0.3926, 0]. Sketch a 0.0252 radius circle on the UCS XY plane, extrude it 0.3926 units in the positive direction to create a new solid body, and export as STL/STEP to the specified path.</thinking>

```decision
CODE
```

```python
import win32com.client
import math
import os

def main():
    # --- Initialize Inventor ---
    # Connect to a running instance of Inventor or start a new one
    try:
        inv_app = win32com.client.GetActiveObject(Class = "Inventor.Application")
    except:
        try:
            inv_app = win32com.client.Dispatch(dispatch = "Inventor.Application")
            inv_app.Visible = True
        except Exception as e:
            print("Failed to connect to Inventor:", e)
            return

    # --- Initialize Document and Managers ---
    # Create a new Part Document using the default template (12290 = kPartDocumentObject)
    doc = inv_app.Documents.Add(
        DocumentType = 12290,
        TemplateFileName = inv_app.FileManager.GetTemplateFile(DocumentType = 12290), 
        CreateVisible = True
    )
    
    # Access the ComponentDefinition to manage features and geometry
    part_def = doc.ComponentDefinition
    
    # Access TransientGeometry for creating points, vectors, and matrices
    tg = inv_app.TransientGeometry

    # --- User Coordinate System (UCS) Setup ---
    # 1. Define rotation and translation for UCS (Euler: [0, 0, -90], Translation: [0, 0.3926, 0])
    rad = math.pi / 180
    matrix = tg.CreateMatrix()
    
    # Create rotation matrices for X, Y, and Z axes
    mX = tg.CreateMatrix()
    mX.SetToRotation(
        Angle = 0 * rad, 
        Axis = tg.CreateVector(XCoord = 1., YCoord = 0., ZCoord = 0.), 
        Center = tg.CreatePoint(XCoord = 0., YCoord = 0., ZCoord = 0.)
    )
    mY = tg.CreateMatrix()
    mY.SetToRotation(
        Angle = 0 * rad, 
        Axis = tg.CreateVector(XCoord = 0., YCoord = 1., ZCoord = 0.), 
        Center = tg.CreatePoint(XCoord = 0., YCoord = 0., ZCoord = 0.)
    )
    mZ = tg.CreateMatrix()
    mZ.SetToRotation(
        Angle = -90 * rad, 
        Axis = tg.CreateVector(XCoord = 0., YCoord = 0., ZCoord = 1.), 
        Center = tg.CreatePoint(XCoord = 0., YCoord = 0., ZCoord = 0.)
    )
    
    # Combine rotations and set translation
    matrix.PreMultiplyBy(Matrix = mX)
    matrix.PreMultiplyBy(Matrix = mY)
    matrix.PreMultiplyBy(Matrix = mZ)

    # Translation vector: [0, 0.3926, 0]
    matrix.SetTranslation(Translation = tg.CreateVector(XCoord = 0., YCoord = 0.3926, ZCoord = 0.0))

    # 2. Create UCS Definition and add it to the component definition
    ucs_def = part_def.UserCoordinateSystems.CreateDefinition()
    ucs_def.Transformation = matrix
    ucs = part_def.UserCoordinateSystems.Add(Definition = ucs_def)

    # --- Modeling Process ---
    # 1. Sketching
    # Add a new sketch on the XY plane of the UCS
    sketch = part_def.Sketches.Add(PlanarEntity = ucs.XYPlane)
    
    # Draw a circle: center point [0.0252, 0.0252], radius 0.0252
    sketch.SketchCircles.AddByCenterRadius(
        CenterPoint = tg.CreatePoint2d(XCoord = 0.0252, YCoord = 0.0252), 
        Radius = 0.0252
    )

    # 2. Extrusion
    # Create a profile from the sketch for the solid feature
    profile = sketch.Profiles.AddForSolid()
    ext_feats = part_def.Features.ExtrudeFeatures
    
    # Create an extrusion definition (20481 = kJoinOperation)
    ext_def = ext_feats.CreateExtrudeDefinition(Profile = profile, Operation = 20481)
    
    # Extrude along the normal direction by 0.3926 units, 0 in opposite direction
    # 20993 = kPositiveExtentDirection
    ext_def.SetDistanceExtent(Distance = 0.3926, ExtentDirection = 20993)
    
    # Submit the definition to create the actual feature
    ext_feats.Add(Definition = ext_def)

    # --- Export ---
    # Save the model as STL and STEP files
    doc.SaveAs(FileName ='C:/Users/Docker/Downloads/00776997.stl', SaveCopyAs = True)
    doc.SaveAs(FileName = 'C:/Users/Docker/Downloads/00776997.step', SaveCopyAs = True)

if __name__ == "__main__":
    main()
```
"""

autocad_2d_sketch_example = """
Example: 2D Sketch in AutoCAD
- Task Instruction: Draft this sketch in AutoCAD: Initialize a planar sketch on the XY datum comprising the following geometric primitives: Entity 1: Add an arc centered at (0.0, 0.01603863574564457) with radius 0.0031750000000000003, spanning an angular range from -3.141592653589793 radians to 0.0 radians. Entity 5: Draw a line passing through the reference point (0.0031750000000000003, 0.024024507496505972) along the direction vector (0.0, 1.0), defined by a start parameter of -0.007985871750861403 and an end parameter of 0.022977942135185125. Entity 8: Draw a line passing through the reference point (-0.0031750000000000003, 0.024320040363818407) along the direction vector (0.0, 1.0), defined by a start parameter of -0.008281404618173838 and an end parameter of 0.02268240926787269. Entity 11: Draw a line passing through the reference point (7.703719777548943e-34, 0.0470024496316911) along the direction vector (-1.0, -1.2246467991473532e-16), defined by a start parameter of -0.0031750000000000003 and an end parameter of 0.0031750000000000003. Entity 14: Place a point at the coordinate (-0.0031750000000000003, 0.03637154400348663). After drafting the entities, export the DXF file to: C:\\Users\\Docker\\Downloads\\0a0a7cea184b5c6bac97df6c_4_2_gen.dxf. Note: All given coordinates and dimensions are in meters and must be converted to millimeters in AutoCAD.
- Output:
<thinking>Initialize AutoCAD, create a new document. Sketch the arc, the three lines and the point based on their reference points and start/end parameters. Multiply all coordinates and dimensions by 1000 before passing to the AutoCAD API. Finally, export the document as a DXF file to the specified path.</thinking>

```decision
CODE
```

```python
import win32com.client
import pythoncom

M_to_MM = 1000

def get_line_points(pnt_x, pnt_y, dir_x, dir_y, start_param, end_param):
    start_x = pnt_x + dir_x * start_param
    start_y = pnt_y + dir_y * start_param

    end_x = pnt_x + dir_x * end_param
    end_y = pnt_y + dir_y * end_param

    return {
        "start_x": start_x,
        "start_y": start_y,
        "end_x": end_x,
        "end_y": end_y
    }

def main():
    # --- Initialize AutoCAD ---
    try:
        acad = win32com.client.GetActiveObject("AutoCAD.Application")
    except:
        try:
            acad = win32com.client.Dispatch("AutoCAD.Application")
        except Exception as e:
            print("Failed to initialize AutoCAD:", e)
            return
    acad.Visible = True
    doc = acad.Documents.Add()
    model_space = doc.ModelSpace
    const_layer = doc.Layers.Add("Construction")

    # --- Sketch ---
    
    # Entity 1
    arc_1_center = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, (
        0.0*M_to_MM, 
        0.01603863574564457*M_to_MM, 
        0.0
    ))
    arc_1_radius = 0.0031750000000000003*M_to_MM
    arc_1_obj = model_space.AddArc(arc_1_center, arc_1_radius, -3.141592653589793, 0.0)

    # Entity 5
    line_5_points = get_line_points(
        pnt_x = 0.0031750000000000003,
        pnt_y = 0.024024507496505972,
        dir_x = 0.0,
        dir_y = 1.0,
        start_param = -0.007985871750861403,
        end_param = 0.022977942135185125
    )
    line_5_start_pnt = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, (
        line_5_points['start_x']*M_to_MM, 
        line_5_points['start_y']*M_to_MM, 
        0.0
    ))
    line_5_end_pnt = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, (
        line_5_points['end_x']*M_to_MM, 
        line_5_points['end_y']*M_to_MM, 
        0.0
    ))
    line_5_obj = model_space.AddLine(line_5_start_pnt, line_5_end_pnt)

    # Entity 8
    line_8_points = get_line_points(
        pnt_x = -0.0031750000000000003,
        pnt_y = 0.024320040363818407,
        dir_x = 0.0,
        dir_y = 1.0,
        start_param = -0.008281404618173838,
        end_param = 0.02268240926787269
    )
    line_8_start_pnt = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, (
        line_8_points['start_x']*M_to_MM, 
        line_8_points['start_y']*M_to_MM, 
        0.0
    ))
    line_8_end_pnt = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, (
        line_8_points['end_x']*M_to_MM, 
        line_8_points['end_y']*M_to_MM, 
        0.0
    ))
    line_8_obj = model_space.AddLine(line_8_start_pnt, line_8_end_pnt)

    # Entity 11
    line_11_points = get_line_points(
        pnt_x = 7.703719777548943e-34,
        pnt_y = 0.0470024496316911,
        dir_x = -1.0,
        dir_y = -1.2246467991473532e-16,
        start_param = -0.0031750000000000003,
        end_param = 0.0031750000000000003
    )
    line_11_start_pnt = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, (
        line_11_points['start_x']*M_to_MM, 
        line_11_points['start_y']*M_to_MM, 
        0.0
    ))
    line_11_end_pnt = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, (
        line_11_points['end_x']*M_to_MM, 
        line_11_points['end_y']*M_to_MM, 
        0.0
    ))
    line_11_obj = model_space.AddLine(line_11_start_pnt, line_11_end_pnt)

    # Entity 14
    point_14 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, (
        -0.0031750000000000003 * M_to_MM, 
        0.03637154400348663 * M_to_MM, 
        0.0
    ))
    point_14_obj = model_space.AddPoint(point_14)

    acad.ZoomExtents()

    # --- Save ---
    doc.SaveAs(r"C:\\Users\\Docker\\Downloads\\0a0a7cea184b5c6bac97df6c_4_2_gen.dxf", 61)


if __name__ == "__main__":
    main()
```
"""

inventor_assembly_example = """
Example: Assembling in Inventor
- Task Instruction: Build this assembly in Inventor: Commence the assembly by grounding component 53066_50d8135d_0020_1 (located at "C:\\Users\\Docker\\Documents\\AssemblyJoint\\steps\\53066_50d8135d_0020_1.step") as the Fixed Base Component and 53066_50d8135d_0001_1 (located at "C:\\Users\\Docker\\Documents\\AssemblyJoint\\steps\\53066_50d8135d_0001_1.step") as the Moving Component. Designate the planar B-Rep face on the base component (reference entity point: {'x': 0.09000000000000001, 'y': 2.500000037252903, 'z': 5.000000074505806}) and the planar B-Rep face on the moving component (reference entity point: {'x': 0.09000000000000001, 'y': 2.500000037252903, 'z': 5.000000074505806}) as the mating entities. Establish a zero-degree-of-freedom Rigid Joint by aligning the Center of the planar B-Rep face on the base component and the Center of the planar B-Rep face on the moving component to ensure the two components are immovably fixed. The constraint is configured in an Anti-Aligned (Flipped) orientation to ensure opposing primary vectors. Set the offset to zero to achieve coincidence between the mating entities. This configuration Fully Constrains the moving component, eliminating all 6 degrees of freedom (DOF) and ensuring that both components behave as a single kinematic body. After fully constraining the assembly, export the model as an STL file to: C:\\Users\\Docker\\Downloads\\09422_gen.stl and as a STEP file to: C:\\Users\\Docker\\Downloads\\09422_gen.step.
- Output:
<thinking>Create a new assembly and import the base and moving component, grounding the base. Locate the mating faces on both components and apply a rigid joint between the centers with a flipped orientation and zero offset. Finally, export the assembly as STL/STEP to the specified paths.</thinking>

```decision
CODE
```

```python
import os
import win32com.client

def find_face_by_point(inv_app, occ, surface_type, pt):
    for face in occ.SurfaceBodies.Item(1).Faces:
        if face.SurfaceType == surface_type:
            dist = inv_app.MeasureTools.GetMinimumDistance(pt, face)[0]
            if dist < 0.001:    # cm
                return face
    return None

def find_edge_by_point(inv_app, occ, curve_type, pt):
    for edge in occ.SurfaceBodies.Item(1).Edges:
        if edge.GeometryType == curve_type:
            dist = inv_app.MeasureTools.GetMinimumDistance(pt, edge)[0]
            if dist < 0.001:
                return edge
    return None


def main():
    # --- Initialize Inventor ---
    try:
        inv_app = win32com.client.GetActiveObject("Inventor.Application")
    except:
        try:
            inv_app = win32com.client.Dispatch("Inventor.Application")
            inv_app.Visible = True
        except Exception as e:
            print(f"Failed to connect to Inventor: {e}")
            return
    
    # --- Create a New Assembly Document ---
    # kAssemblyDocumentObject = 12291
    asm_doc = inv_app.Documents.Add(12291, inv_app.FileManager.GetTemplateFile(12291), True)
    asm_def = asm_doc.ComponentDefinition
    
    # --- Import Components ---
    FILE_DIR = r"C:\\Users\\Docker\\Documents\\AssemblyJoint\\steps"
    path_base = os.path.join(FILE_DIR, '53066_50d8135d_0020_1'+'.step')  # fixed base component
    path_moving = os.path.join(FILE_DIR, '53066_50d8135d_0001_1'+'.step')  # moving component

    # 1. Add Part Occurrences to the Assembly
    tg = inv_app.TransientGeometry
    matrix = tg.CreateMatrix()

    occ_base = asm_def.Occurrences.Add(path_base, matrix)
    occ_moving = asm_def.Occurrences.Add(path_moving, matrix)

    # 2. Fix the fixed base component
    occ_base.Grounded = True

    # --- Locate the mating entities ---
    target_pt_base = tg.CreatePoint(0.09000000000000001, 2.500000037252903, 5.000000074505806)
    target_pt_moving = tg.CreatePoint(0.09000000000000001, 2.500000037252903, 5.000000074505806)

    # kPlaneSurface = 5890
    entity_base = find_face_by_point(inv_app, occ_base, 5890, target_pt_base)
    entity_moving = find_face_by_point(inv_app, occ_moving, 5890, target_pt_moving)

    if not entity_base or not entity_moving:
        print("Error: Unable to locate mating entities by coordinates")
        return

    # --- Create a Rigid Joint ---
    # 1. Create JointGeometry References
    # kPlanarFaceCenterPointIntent = 57868
    intent_base = asm_def.CreateGeometryIntent(entity_base, 57868)
    intent_moving = asm_def.CreateGeometryIntent(entity_moving, 57868)

    # 2. Create Joint Definition
    # kRigidJointType = 102401
    joint_def = asm_def.Joints.CreateAssemblyJointDefinition(102401, intent_moving, intent_base)
    
    # Set Flipping
    joint_def.FlipOriginDirection = True
    

    # --- Execute Assembly ---
    new_joint = asm_def.Joints.Add(joint_def)

    # --- Export to STL and STEP Files ---
    asm_doc.SaveAs(r'C:\\Users\\Docker\\Downloads\\09422_gen.stl', True)
    asm_doc.SaveAs(r'C:\\Users\\Docker\\Downloads\\09422_gen.step', True)

if __name__ == "__main__":
    main()
```
"""


sldworks_modify_example = """
Example: Modify in Solidworks
- Task Instruction: Below is the baseline Python script that models a design consisting of a cylinder with a rectangular section at the top, where the cylinder stands 0.75 units tall and has a square base that measures 0.0375 units on each side.
```python
import win32com.client
import pythoncom
import math
from win32com.client import gencache

# Load SOLIDWORKS 2025 Type Library for early binding
swModule = gencache.EnsureModule('{83A33D31-27C5-11CE-BFD4-00400513BB57}', 0, 33, 0)

def super_cast(obj, interface_name):
    try:
        interface_class = getattr(swModule, interface_name)
        obj_query = obj._oleobj_.QueryInterface(interface_class.CLSID, pythoncom.IID_IDispatch)
        return interface_class(obj_query)
    except Exception:
        return obj

def get_plane_and_coords_euler_transform(rx_deg, ry_deg, rz_deg, x, y):
    # Determines plane and coordinate mapping based on Euler angles.
    if rx_deg == 0 and ry_deg == 0 and rz_deg == 0:
        return {"plane_name": "Front Plane", "plane_name_cn": "前视基准面", "rot_x": x, "rot_y": y}
    elif rx_deg == -90 and ry_deg == 0 and rz_deg == -90:
        return {"plane_name": "Right Plane", "plane_name_cn": "前视基准面", "rot_x": y, "rot_y": -x}
    elif rx_deg == 0 and ry_deg == 0 and rz_deg == -90:
        return {"plane_name": "Front Plane", "plane_name_cn": "前视基准面", "rot_x": y, "rot_y": -x}
    return {"plane_name": "Front Plane", "plane_name_cn": "前视基准面", "rot_x": x, "rot_y": y}

def main():
    # --- Initialize SOLIDWORKS Application Session ---
    try:
        swApp = win32com.client.Dispatch("SldWorks.Application")
        swApp.Visible = True
        swApp.CloseAllDocuments(True)
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    # --- Document and Manager Initialization ---
    part_template = swApp.GetUserPreferenceStringValue(8)
    model = super_cast(swApp.NewDocument(part_template, 0, 0, 0), "IModelDoc2")
    ext = super_cast(model.Extension, "IModelDocExtension")
    sketch_mgr = super_cast(model.SketchManager, "ISketchManager")
    feat_mgr = super_cast(model.FeatureManager, "IFeatureManager")

    # --- Modeling ---
    # --- part_1 ---
    part_1_rx, part_1_ry, part_1_rz = 0.0, 0.0, 0.0
    # Select sketching plane based on Euler Angles
    part_1_euler_res = get_plane_and_coords_euler_transform(part_1_rx, part_1_ry, part_1_rz, 0.0, 0.0)
    model.ClearSelection2(True)

    # Select target plane for sketching
    static = ext.SelectByID2(part_1_euler_res['plane_name'], 'PLANE', 0, 0, 0, False, 0, None, 0)
    if not static:
        ext.SelectByID2(part_1_euler_res['plane_name_cn'], 'PLANE', 0, 0, 0, False, 0, None, 0)

    # Sketching
    sketch_mgr.InsertSketch(True)

    # Circle
    pt = get_plane_and_coords_euler_transform(part_1_rx, part_1_ry, part_1_rz, 0.0188, 0.0188)
    sketch_mgr.CreateCircleByRadius(pt['rot_x'], pt['rot_y'], 0, 0.0188)

    sketch_mgr.InsertSketch(True) # Close Sketch

    # Extrusion
    ext.SelectByID2('Sketch1', 'SKETCH', 0, 0, 0, False, 0, None, 0)
    feat_mgr.FeatureExtrusion3(
        True, # True for single ended
        False, # Flip
        False, # Dir
        0, 0,
        0.75, # D1: Depth of extrusion for first end in meters
        0.0, # D2: Depth of extrusion for second end in meters
        False, False, False, False, 0.0, 0.0, False, False, False, False, False, True, True, 0, 0, False)


    # --- Rebuild and Export Model ---
    model.EditRebuild3()
    ext.SaveAs3("C:/Users/Docker/Downloads/00085757.stl", 0, 1, None, None, 0, 0)
    ext.SaveAs3("C:/Users/Docker/Downloads/00085757.step", 0, 1, None, None, 0, 0)
    print("Modeling complete.")

if __name__ == "__main__":
    main()
```

Modify this script to: Decrease the cylinder radius from 0.0188 to 0.0109 and shorten its height from 0.75 to 0.5668, keeping the center location unchanged.
Export the modified model as an STL file to C:/Users/Docker/Downloads/00085757_level_1_0.stl.
- Output:
<thinking>The user requested to change the cylindrical feature size while preserving its placement. So I only need to update the circle radius to 0.0109,  decrease the extrude evalue from 0.75 to 0.5668, and export the STL to the modified path. No other changes are needed.</thinking>

```decision
CODE
```

```python
import win32com.client
import pythoncom
import math
from win32com.client import gencache

# Load SOLIDWORKS 2025 Type Library for early binding
swModule = gencache.EnsureModule('{83A33D31-27C5-11CE-BFD4-00400513BB57}', 0, 33, 0)

def super_cast(obj, interface_name):
    try:
        interface_class = getattr(swModule, interface_name)
        obj_query = obj._oleobj_.QueryInterface(interface_class.CLSID, pythoncom.IID_IDispatch)
        return interface_class(obj_query)
    except Exception:
        return obj

def get_plane_and_coords_euler_transform(rx_deg, ry_deg, rz_deg, x, y):
    # Determines plane and coordinate mapping based on Euler angles.
    if rx_deg == 0 and ry_deg == 0 and rz_deg == 0:
        return {"plane_name": "Front Plane", "plane_name_cn": "前视基准面", "rot_x": x, "rot_y": y}
    elif rx_deg == -90 and ry_deg == 0 and rz_deg == -90:
        return {"plane_name": "Right Plane", "plane_name_cn": "前视基准面", "rot_x": y, "rot_y": -x}
    elif rx_deg == 0 and ry_deg == 0 and rz_deg == -90:
        return {"plane_name": "Front Plane", "plane_name_cn": "前视基准面", "rot_x": y, "rot_y": -x}
    return {"plane_name": "Front Plane", "plane_name_cn": "前视基准面", "rot_x": x, "rot_y": y}

def main():
    # --- Initialize SOLIDWORKS Application Session ---
    try:
        swApp = win32com.client.Dispatch("SldWorks.Application")
        swApp.Visible = True
        swApp.CloseAllDocuments(True)
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    # --- Document and Manager Initialization ---
    part_template = swApp.GetUserPreferenceStringValue(8)
    model = super_cast(swApp.NewDocument(part_template, 0, 0, 0), "IModelDoc2")
    ext = super_cast(model.Extension, "IModelDocExtension")
    sketch_mgr = super_cast(model.SketchManager, "ISketchManager")
    feat_mgr = super_cast(model.FeatureManager, "IFeatureManager")

    # --- Modeling ---
    # --- part_1 ---
    part_1_rx, part_1_ry, part_1_rz = 0.0, 0.0, 0.0
    # Select sketching plane based on Euler Angles
    part_1_euler_res = get_plane_and_coords_euler_transform(part_1_rx, part_1_ry, part_1_rz, 0.0, 0.0)
    model.ClearSelection2(True)

    # Select target plane for sketching
    static = ext.SelectByID2(part_1_euler_res['plane_name'], 'PLANE', 0, 0, 0, False, 0, None, 0)
    if not static:
        ext.SelectByID2(part_1_euler_res['plane_name_cn'], 'PLANE', 0, 0, 0, False, 0, None, 0)

    # Sketching
    sketch_mgr.InsertSketch(True)

    # Circle
    pt = get_plane_and_coords_euler_transform(part_1_rx, part_1_ry, part_1_rz, 0.0188, 0.0188)
    sketch_mgr.CreateCircleByRadius(pt['rot_x'], pt['rot_y'], 0, 0.0109)    # Modify the radius

    sketch_mgr.InsertSketch(True) # Close Sketch

    # Extrusion
    ext.SelectByID2('Sketch1', 'SKETCH', 0, 0, 0, False, 0, None, 0)
    feat_mgr.FeatureExtrusion3(
        True, # True for single ended
        False, # Flip 
        False, # Dir
        0, 0, 
        0.5668, # D1: Depth of extrusion for first end in meters  # Modify the height
        0.0, # D2: Depth of extrusion for second end in meters
        False, False, False, False, 0.0, 0.0, False, False, False, False, False, True, True, 0, 0, False)


    # --- Rebuild and Export Model ---
    model.EditRebuild3()
    ext.SaveAs3("C:/Users/Docker/Downloads/00085757_level_1_0.stl", 0, 1, None, None, 0, 0)

if __name__ == "__main__":
    main()
```
"""


inventor_modify_example = """
Example: Modify in Inventor
- Task Instruction: Below is the baseline Python script that models a design consisting of a cylinder with a rectangular section at the top, where the cylinder stands 0.75 units tall and has a square base that measures 0.0375 units on each side.
```python
import win32com.client
import math
import os

def main():
    # --- Initialize Inventor ---
    try:
        inv_app = win32com.client.GetActiveObject(Class = 'Inventor.Application')
    except:
        try:
            inv_app = win32com.client.Dispatch(dispatch = 'Inventor.Application')
            inv_app.Visible = True
        except Exception as e:
            print(f'Failed to connect to Inventor: {e}')
            return

    # --- Initialize Document and Managers ---
    # Create a new Part Document using the default template (12290 = kPartDocumentObject)
    doc = inv_app.Documents.Add(
        DocumentType = 12290,
        TemplateFileName = inv_app.FileManager.GetTemplateFile(DocumentType = 12290),
        CreateVisible = True
    )
    part_def = doc.ComponentDefinition
    tg = inv_app.TransientGeometry

    rad = math.pi / 180

    # --- part_1 ---
    # 1. Define rotation and translation for UCS (Euler: [0.0, 0.0, 0.0], Translation: [0.0, 0.0, 0.0])
    matrix_1 = tg.CreateMatrix()
    mX_1 = tg.CreateMatrix()
    mX_1.SetToRotation(Angle = 0.0 * rad, Axis = tg.CreateVector(XCoord=1., YCoord=0., ZCoord=0.), Center = tg.CreatePoint(0., 0., 0.))
    mY_1 = tg.CreateMatrix()
    mY_1.SetToRotation(Angle = 0.0 * rad, Axis = tg.CreateVector(XCoord=0., YCoord=1., ZCoord=0.), Center = tg.CreatePoint(0., 0., 0.))
    mZ_1 = tg.CreateMatrix()
    mZ_1.SetToRotation(Angle = 0.0 * rad, Axis = tg.CreateVector(XCoord=0., YCoord=0., ZCoord=1.), Center = tg.CreatePoint(0., 0., 0.))
    matrix_1.PreMultiplyBy(Matrix = mX_1)
    matrix_1.PreMultiplyBy(Matrix = mY_1)
    matrix_1.PreMultiplyBy(Matrix = mZ_1)
    matrix_1.SetTranslation(Translation = tg.CreateVector(XCoord=0.0, YCoord=0.0, ZCoord=0.0))
    ucs_def_1 = part_def.UserCoordinateSystems.CreateDefinition()
    ucs_def_1.Transformation = matrix_1
    ucs_1 = part_def.UserCoordinateSystems.Add(Definition = ucs_def_1)

    # 2. Sketching
    sketch_1 = part_def.Sketches.Add(PlanarEntity = ucs_1.XYPlane)
    sketch_1.SketchCircles.AddByCenterRadius(CenterPoint = tg.CreatePoint2d(0.0188, 0.0188), Radius = 0.0188)

    # 3. Extrusion
    profile_1 = sketch_1.Profiles.AddForSolid()
    ext_feats_1 = part_def.Features.ExtrudeFeatures
    ext_def_1 = ext_feats_1.CreateExtrudeDefinition(Profile = profile_1, Operation = 20485)

    # Extrude along the normal direction by 0.75 units
    ext_def_1.SetDistanceExtent(Distance = 0.75, ExtentDirection = 20993)
    ext_feats_1.Add(Definition = ext_def_1)

    # --- Export ---
    doc.SaveAs(FileName = 'C:/Users/Docker/Downloads/00085757.stl', SaveCopyAs = True)
    doc.SaveAs(FileName = 'C:/Users/Docker/Downloads/00085757.step', SaveCopyAs = True)
    print(f'Model generated and saved successfully!')

if __name__ == '__main__':
    main()```

Modify this script to: Decrease the cylinder radius from 0.0188 to 0.0109 and shorten its height from 0.75 to 0.5668, keeping the center location unchanged.
Export the modified model as an STL file to C:/Users/Docker/Downloads/00085757_level_1_0.stl.
- Output:
<thinking>The user requested to change the cylindrical feature size while preserving its placement. So I only need to update the circle radius to 0.0109,  decrease the extrude evalue from 0.75 to 0.5668, and export the STL to the modified path. No other changes are needed.</thinking>

```decision
CODE
```

```python
import win32com.client
import math
import os

def main():
    # --- Initialize Inventor ---
    try:
        inv_app = win32com.client.GetActiveObject(Class = 'Inventor.Application')
    except:
        try:
            inv_app = win32com.client.Dispatch(dispatch = 'Inventor.Application')
            inv_app.Visible = True
        except Exception as e:
            print(f'Failed to connect to Inventor: {e}')
            return

    # --- Initialize Document and Managers ---
    # Create a new Part Document using the default template (12290 = kPartDocumentObject)
    doc = inv_app.Documents.Add(
        DocumentType = 12290,
        TemplateFileName = inv_app.FileManager.GetTemplateFile(DocumentType = 12290),
        CreateVisible = True
    )
    part_def = doc.ComponentDefinition
    tg = inv_app.TransientGeometry

    rad = math.pi / 180

    # --- part_1 ---
    # 1. Define rotation and translation for UCS (Euler: [0.0, 0.0, 0.0], Translation: [0.0, 0.0, 0.0])
    matrix_1 = tg.CreateMatrix()
    mX_1 = tg.CreateMatrix()
    mX_1.SetToRotation(Angle = 0.0 * rad, Axis = tg.CreateVector(XCoord=1., YCoord=0., ZCoord=0.), Center = tg.CreatePoint(0., 0., 0.))
    mY_1 = tg.CreateMatrix()
    mY_1.SetToRotation(Angle = 0.0 * rad, Axis = tg.CreateVector(XCoord=0., YCoord=1., ZCoord=0.), Center = tg.CreatePoint(0., 0., 0.))
    mZ_1 = tg.CreateMatrix()
    mZ_1.SetToRotation(Angle = 0.0 * rad, Axis = tg.CreateVector(XCoord=0., YCoord=0., ZCoord=1.), Center = tg.CreatePoint(0., 0., 0.))
    matrix_1.PreMultiplyBy(Matrix = mX_1)
    matrix_1.PreMultiplyBy(Matrix = mY_1)
    matrix_1.PreMultiplyBy(Matrix = mZ_1)
    matrix_1.SetTranslation(Translation = tg.CreateVector(XCoord=0.0, YCoord=0.0, ZCoord=0.0))
    ucs_def_1 = part_def.UserCoordinateSystems.CreateDefinition()
    ucs_def_1.Transformation = matrix_1
    ucs_1 = part_def.UserCoordinateSystems.Add(Definition = ucs_def_1)

    # 2. Sketching
    sketch_1 = part_def.Sketches.Add(PlanarEntity = ucs_1.XYPlane)
    sketch_1.SketchCircles.AddByCenterRadius(CenterPoint = tg.CreatePoint2d(0.0188, 0.0188), Radius = 0.0109)   # Modify the radius

    # 3. Extrusion
    profile_1 = sketch_1.Profiles.AddForSolid()
    ext_feats_1 = part_def.Features.ExtrudeFeatures
    ext_def_1 = ext_feats_1.CreateExtrudeDefinition(Profile = profile_1, Operation = 20485)
    ext_def_1.SetDistanceExtent(Distance = 0.5668, ExtentDirection = 20993)   # Modify the height
    ext_feats_1.Add(Definition = ext_def_1)

    # --- Export ---
    doc.SaveAs(FileName = 'C:/Users/Docker/Downloads/00085757_level_1_0.stl', SaveCopyAs = True)

if __name__ == '__main__':
    main()
```
"""


sldworks_drawing_example = """
Example: Engineering Drawing in SolidWorks
- Task Instruction: Load the part file located at C:\\Users\\Docker\\Documents\\Text2CAD\\step\\00000007.step in SolidWorks. Create a new engineering drawing from this part containing standard 3rd angle views and an isometric view. Automatically apply dimensions to the views, and save the drawing as a PDF to C:\\Users\\Docker\\Downloads\\00000007.pdf.
- Output:
<thinking>To complete the task, I'll connect to Solidworks via COM, import the STEP file and convert it to a SLDPRT part. Then, load the SLDPRT part to initialize a drawing document, lay out the 3rd angle and isometric views, auto-dimension them, and save the result as a PDF to the specified path.</thinking>

```decision
CODE
```

```python
import win32com.client
import pythoncom
from win32com.client import gencache
import os
import sys
import time

swModule = gencache.EnsureModule('{83A33D31-27C5-11CE-BFD4-00400513BB57}', 0, 33, 0)

def super_cast(obj, interface_name):
    try:
        interface_class = getattr(swModule, interface_name)
        obj_query = obj._oleobj_.QueryInterface(interface_class.CLSID, pythoncom.IID_IDispatch)
        return interface_class(obj_query)
    except Exception:
        return obj

def main():
    step_path = r'C:\\Users\\Docker\\Documents\\Text2CAD\\step\\00000007.step'
    path_part = r'C:\\Users\\Docker\\Downloads\\00000007.sldprt'
    path_draw = r'C:\\Users\\Docker\\Downloads\\00000007.slddrw'
    path_pdf = r'C:\\Users\\Docker\\Downloads\\00000007.pdf'

    #----- Convert STEP to SLDPRT -----
    # Connect to SolidWorks
    swApp = win32com.client.Dispatch("SldWorks.Application")
    swApp.Visible = True

    # Load STEP file
    swApp.SetUserPreferenceToggle(196, False) # swMultiCAD_Enable3DInterconnect = False
    import_data = swApp.GetImportFileData(step_path)
    errors = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    model_doc_raw = swApp.LoadFile4(step_path, "r", import_data, errors)

    if model_doc_raw:
        model_doc = super_cast(model_doc_raw, "IModelDoc2")
        model_doc.EditRebuild3()
        save_errors = model_doc.SaveAs3(path_part, 0, 1)
        if save_errors == 0:
            print(f"Save SLDPRT file success!: {path_part}")
        else:
            print(f"Save SLDPRT file Failed!: {save_errors}")
            return
    else:
        print(f"Load step file Failed!: {errors.value}")
        return

    time.sleep(1)

    #----- Create drawing from part -----
    # Connect to SolidWorks
    swApp = win32com.client.Dispatch("SldWorks.Application")
    swApp.Visible = True

    # Open part file
    arg_errors = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    arg_warnings = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    swApp.OpenDoc6(path_part, 1, 1, "", arg_errors, arg_warnings)   # swDocPART=1

    # Create drawing file
    draw_tmpl = swApp.GetUserPreferenceStringValue(10)  # swDefaultTemplateDrawing=10
    draw_raw = swApp.NewDocument(draw_tmpl, 0, 0, 0)
    
    if not draw_raw:
        print("Failed to create drawing file!")
        return
    swDraw = super_cast(draw_raw, "IDrawingDoc")
    draw_doc = super_cast(draw_raw, "IModelDoc2")

    #----- Add views and dimension -----
    # Create 3rd Angle Views
    angle_view = swDraw.Create3rdAngleViews2(path_part)

    # Auto-dimension
    view = swDraw.GetFirstView()
    while view:
        swView = super_cast(view, "IView")
        if swView.Type > 1:
            v_name = swView.Name
            draw_doc.Extension.SelectByID2(v_name, "DRAWINGVIEW", 0, 0, 0, False, 0, None, 0)
            status = swDraw.AutoDimension(1, 0, 0, 0, 1)
            draw_doc.Extension.AlignDimensions(0, 0)    # arrange dimmension from blocking
        view = swView.GetNextView()
    draw_doc.EditRebuild3()
    draw_doc.SaveAs3(path_draw, 0, 1)

    # Add Isometric view
    time.sleep(1)
    arg_errors = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    arg_warnings = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    res = swApp.OpenDoc6(path_draw, 3, 1, "", arg_errors, arg_warnings)  # swDocDRAWING=3
    if isinstance(res, (list, tuple)):
        draw_raw = res[0]
    else:
        draw_raw = res
            
    swDraw = super_cast(draw_raw, "IDrawingDoc")
    draw_doc = super_cast(draw_raw, "IModelDoc2")
    target_view_name = "*Isometric" 
    iso_view_raw = swDraw.CreateDrawViewFromModelView3(path_part, target_view_name, 0.3, 0.22, 0)
    if iso_view_raw:
        swView = super_cast(iso_view_raw, "IView")
        swView.SetDisplayMode3(False, 5, False, True)
        swView.UseSheetScale = True 

    draw_doc.ForceRebuild3(True)
    draw_doc.Save3(1, 0, 0) # swSaveAsOptions_Silent=1

    #----- Export PDF -----
    arg_pdf_errors = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    arg_pdf_warnings = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    draw_doc.Extension.SaveAs3(
        path_pdf, 
        0, # swSaveAsCurrentVersion
        1, # swSaveAsOptions_Silent
        None, None,
        0,0
    )
    print("PDF saved:", path_pdf)

if __name__ == "__main__":
    main()
```"""


sldworks_mass_property_example = """
Example: Evaluate Mass Properties in Solidworks
- Task Instruction: In Solidworks, load the part from "C:\\Users\\Docker\\Documents\\AssemblyJoint\\steps\\100218_83ec552f_0000_1.step". Assign "Nylon 6/6" (density=1130.0) as the material and evaluate the part's Inertia Tensor at the Centroid and at the Origin. Format the result strictly as a JSON object: {"Inertial_Tensor": {"At_Centroid": <value>, "At_Origin": <value>}}, where <value> is the exact numerical array. Save this JSON file to "C:\\Users\\Docker\\Downloads\\100218_83ec552f_0000_1.json."
- Output:
<thinking>First, connect to Solidworks, load the STEP file, and override the mass using the designated material and density. Then, obtain the inertia tensor at centroid and inertia tensor at origin, and dump the formatted result to the specific path.</thinking>

```decision
CODE
```

```python
import os
import json
import win32com.client
import pythoncom
from win32com.client import gencache

swModule = gencache.EnsureModule('{83A33D31-27C5-11CE-BFD4-00400513BB57}', 0, 33, 0)

def super_cast(obj, interface_name):
    # Cast the COM object to a specific SOLIDWORKS interface.
    try:
        interface_class = getattr(swModule, interface_name)
        obj_query = obj._oleobj_.QueryInterface(interface_class.CLSID, pythoncom.IID_IDispatch)
        return interface_class(obj_query)
    except Exception:
        return obj


def main():
    # -- Initialize Solidworks
    try:
        swApp = win32com.client.Dispatch("SldWorks.Application")
        swApp.Visible = True
        swApp.CloseAllDocuments(True)
    except Exception as e:
        print(f"Failed to connect: {e}")
        return
        
    # --- Loading Loading STEP file ---
    step_path = r"C:\\Users\\Docker\\Documents\\AssemblyJoint\\steps\\100218_83ec552f_0000_1.step"
    if not os.path.exists(step_path):
        print("Can't find step file!", step_path)
        return
    swApp.SetUserPreferenceToggle(196, False) # swMultiCAD_Enable3DInterconnect = False
    import_data = swApp.GetImportFileData(step_path)
    errors = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    model_doc_raw = swApp.LoadFile4(step_path, "r", import_data, errors)
    model = super_cast(model_doc_raw, "IModelDoc2")
    if model is None:
        print("Fail to load step file!")
        return

    ext = super_cast(model.Extension, "IModelDocExtension")

    # --- Create MassProperty2 Object ---
    mp = super_cast(ext.CreateMassProperty2(), "IMassProperty2")
    mp.UseSystemUnits = True
    mp.AccuracyLevel = 6

    # Set Material and Density
    swPart = super_cast(model, "IPartDoc")
    material_name = "Nylon 6/6"
    swPart.SetMaterialPropertyName2("", "solidworks materials.sldmat", material_name)

    target_density = 1130.0
    target_mass = mp.Volume * target_density
  
    # Override mass property
    ov_prop = super_cast(mp.GetOverrideOptions(), "IMassPropertyOverrideOptions")
    ov_prop.OverrideMass = True
    ov_prop.SetOverrideMassValue(target_mass)
    success = mp.SetOverrideOptions(ov_prop, 1, None)
    if not success:
        print("Fail to override mass property!")
        return

    # --- Obtain physical properties ---
    properties_data = {
        "Inertia_Tensor": {
            "At_Centroid": mp.GetMomentOfInertia(0),
            "At_Origin": mp.GetMomentOfInertia(1)
        }
    }

    with open(r'C:\\Users\\Docker\\Downloads\\100218_83ec552f_0000_1.json', 'w') as f:
        f.write(json.dumps(properties_data, indent=4))

if __name__ == "__main__":
    main()
```
"""

inventor_mass_property_example = """
Example: Evaluate Mass Properties in Inventor
- Task Instruction: In Inventor, load the part from "C:\\Users\\Docker\\Documents\\AssemblyJoint\\steps\\100218_83ec552f_0000_1.step". Assign "Water" (density=0.001) as the material and evaluate the part's Center of Mass. Format the result strictly as a JSON object: {"Center_of_Mass": {"x": <value> ,"y": <value> ,"z": <value>}}, where <value> is the exact numerical value. Save this JSON file to "C:\\Users\\Docker\\Downloads\\100218_83ec552f_0000_1.json."
- Output:
<thinking>First, connect to Inventor, open the STEP file, and assign the specific material to the component. Then, override the mass using the target density, obtain the center of mass, and dump the formatted result to the specific path.</thinking>

```decision
CODE
```

```python
import win32com.client
import os
import json

def main():
    # --- Initialize Inventor ---
    try:
        inv_app = win32com.client.GetActiveObject(Class = "Inventor.Application")
    except:
        try:
            inv_app = win32com.client.Dispatch(dispatch = "Inventor.Application")
            inv_app.Visible = True
        except Exception as e:
            print(f"Failed to connect to Inventor: {e}")
            return
    
    step_path = r"C:\\Users\\Docker\\Documents\\AssemblyJoint\\steps\\100218_83ec552f_0000_1.step"
    if not os.path.exists(step_path):
        print("Can't find step file!", step_path)
        return
    doc = inv_app.Documents.Open(step_path, True)

    # --- Obtain Mass Properties Object ---
    comp_def = doc.ComponentDefinition
    mp = comp_def.MassProperties

    # 1. Set Material Property ---
    material_name = "Water"
    new_material = doc.Materials.Item(material_name)
    doc.ComponentDefinition.Material = new_material
    doc.Update()

    # 2. Set Density 
    target_density = 0.001 
    mp.Mass = mp.Volume * target_density

    # --- Obtain physical properties ---
    properties_data = {
        "Center_of_Mass": {
            "x": mp.CenterOfMass.X,
            "y": mp.CenterOfMass.Y,
            "z": mp.CenterOfMass.Z
        }
    }
    
    with open(r'C:\\Users\\Docker\\Downloads\\100218_83ec552f_0000_1.json', 'w') as f:
        f.write(json.dumps(properties_data, indent=4))

if __name__ == "__main__":
    main()
```
"""

sldworks_interference_example = """
Example: Interference Detection in SolidWorks
- Task Instruction: In SolidWorks, load the assembly file located at "C:/Users/Docker/Documents/AssemblyJoint/steps/joint_set_00000.step". Perform a full automated interference analysis across all components. Count the total number of components (bottom-level parts) in the assembly and extract their names, along with the total interference count and combined interference volume. Do not perform any unit conversions on the extracted values. Format the result strictly as a JSON object: {"components": {"count": <component_count>, "names": ["<name1>", "<name2>",...]}, "interference": {"count": <interference_count>, "total_volume": <volume_value>}}. Save this JSON file to "C:/Users/Docker/Downloads/joint_set_00000.json"
- Output:
<thinking>First, connect to Solidworks, load the STEP file as an assembly, and extract all leaf component names. Then, run interference detection, count interferences and sum their volumes. Finally, output the JSON exactly as specified to the target path.</thinking>

```decision
CODE
```

```python
import os
import win32com.client
import pythoncom
import json
from win32com.client import gencache

# Load SOLIDWORKS 2025 Type Library for early binding
swModule = gencache.EnsureModule('{83A33D31-27C5-11CE-BFD4-00400513BB57}', 0, 33, 0)

def super_cast(obj, interface_name):
    # Cast the COM object to a specific SOLIDWORKS interface.
    try:
        interface_class = getattr(swModule, interface_name)
        obj_query = obj._oleobj_.QueryInterface(interface_class.CLSID, pythoncom.IID_IDispatch)
        return interface_class(obj_query)
    except Exception:
        return obj

def main():
    # --- Initialize SOLIDWORKS ---
    try:
        swApp = win32com.client.Dispatch("SldWorks.Application")
        swApp.Visible = True
        swApp.CloseAllDocuments(True)
    except Exception as e:
        print(f"Failed to connect: {e}")
        return
    
    # --- Load STEP and Cast to Assembly ---
    step_path = "C:/Users/Docker/Documents/AssemblyJoint/steps/joint_set_00000.step"
    swApp.SetUserPreferenceToggle(196, False)  # swMultiCAD_Enable3DInterconnect = False
    import_data = swApp.GetImportFileData(step_path)
    errors = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    model_doc_raw = swApp.LoadFile4(step_path, "r", import_data, errors)
    model = super_cast(model_doc_raw, "IModelDoc2")
    if model is None:
        print(f"Failed to load file: {step_path}")
        return

    swAssy = super_cast(model, "IAssemblyDoc")
    if swAssy is None:
        print("Error! File is not an assembly.")
        return
    
    # --- Hard Interference Detection ---
    # Retrieve all components
    vComps = swAssy.GetComponents(False)
    component_names = []
    if vComps:
        for comp_obj in vComps:
            c = super_cast(comp_obj, "IComponent2")
            if not c.GetChildren():
                component_names.append(c.Name2)
    
    # Initialize interference detection manager
    intMgr = super_cast(swAssy.InterferenceDetectionManager, "IInterferenceDetectionMgr")
    intMgr.SetComponentsAndTransforms(vComps, None)
    intMgr.TreatCoincidenceAsInterference = False # Ignore surface-to-surface touching
    intMgr.IncludeMultibodyPartInterferences = True # Check internal part bodies

    vInterferences = intMgr.GetInterferences()
    hard_interference_count = intMgr.GetInterferenceCount()
    total_vol = 0.0
    if hard_interference_count > 0:
        for i in range(hard_interference_count):
            interf = super_cast(vInterferences[i], "IInterference")
            total_vol += interf.Volume
    
    intMgr.Done()

    # --- Save JSON result ---
    result = {
        "components": {
            "count": len(component_names),
            "names": component_names
        },
        "hard_interference": {
            "count": hard_interference_count,
            "total_volume": total_vol
        }
    }
    with open('C:/Users/Docker/Downloads/joint_set_00000.json', 'w', encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    main()
```
"""

inventor_interference_example = """
Example: Interference Detection in Inventor
- Task Instruction: In Inventor, load the assembly file located at "C:/Users/Docker/Documents/AssemblyJoint/steps/joint_set_00000.step". Perform a full automated interference analysis across all components. Count the total number of components (bottom-level parts) in the assembly and extract their names, along with the total interference count and combined interference volume. Do not perform any unit conversions on the extracted values. Format the result strictly as a JSON object: {"components": {"count": <component_count>, "names": ["<name1>", "<name2>",...]}, "interference": {"count": <interference_count>, "total_volume": <volume_value>}}. Save this JSON file to "C:/Users/Docker/Downloads/joint_set_00000.json".
- Output:
<thinking>First, connect to Inventor, open the STEP assembly file, and collect all component names from occurrences. Then, run interference analysis, count interferences and sum their volumes. Finally, output the JSON exactly as specified to the target path.</thinking>

```decision
CODE
```

```python
import os
import json
import win32com.client

def main():
    # --- Initialize Autodesk Inventor ---
    try:
        # Connect to an active session or start a new one
        invApp = win32com.client.Dispatch("Inventor.Application")
        invApp.Visible = True
        
        # Suppress dialog boxes during file import/open
        invApp.SilentOperation = True 
    except Exception as e:
        print(f"Failed to connect to Inventor: {e}")
        return

    # --- Load STEP File ---
    step_path = "C:/Users/Docker/Documents/AssemblyJoint/steps/joint_set_00000.step"
    if not os.path.exists(step_path):
        print(f"File not found: {step_path}")
        return
    try:
        doc = invApp.Documents.Open(step_path)
    except Exception as e:
        print(f"Failed to open file: {e}")
        invApp.SilentOperation = False
        return

    # Check if the document is an Assembly (DocumentTypeEnum.kAssemblyDocumentObject = 12291)
    if doc.DocumentType != 12291:
        print("Error: Document is not an assembly.")
        doc.Close(True)
        invApp.SilentOperation = False
        return

    assemDef = doc.ComponentDefinition
    
    # --- Interference Detection ---
    # Collect components
    component_names = []
    transientObjs = invApp.TransientObjects
    checkSet = transientObjs.CreateObjectCollection()
    for occ in assemDef.Occurrences:
        checkSet.Add(occ)
        component_names.append(occ.Name)

    # Calculate interferences
    try:
        emptySet = transientObjs.CreateObjectCollection()
        results = assemDef.AnalyzeInterference(checkSet, emptySet)
    except Exception as e:
        print(f"Interference analysis failed: {e}")
        doc.Close(True)
        invApp.SilentOperation = False
        return

    interference_count = results.Count
    total_vol = 0.0
    if interference_count > 0:
        # COM collections are typically 1-indexed
        for i in range(1, interference_count + 1):
            res = results.Item(i)
            total_vol += res.Volume

    # --- Save JSON result ---
    output_data = {
        "components": {
            "count": len(component_names),
            "names": component_names
        },
        "interference": {
            "count": interference_count,
            "total_volume": total_vol
        }
    }
    with open('C:/Users/Docker/Downloads/joint_set_00000.json', 'w', encoding="utf-8") as f:
        json.dump(output_data, f, indent=4)
    print("Interference detection completed successfully.")

if __name__ == "__main__":
    main()
```
"""



def build_user_message(terminal_output):
    msg = f"""
- Current Screenshot: <image>
- Previous Terminal output: {terminal_output}
"""
    return msg

def build_user_message_with_rag(terminal_output, api_list):
    msg = f"""
- Current Screenshot: <image>
- Previous Terminal output: {terminal_output}

Here are some COM APIs that might be useful for completing this task.
{api_list}
"""
    return msg