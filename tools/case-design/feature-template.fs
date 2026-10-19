FeatureScript 1890;
import(path : "onshape/std/geometry.fs", version : "1890.0");

// Reconstruction from STL sections. Curved Z surfaces use 0.25 mm bands.
// Paste into a Feature Studio, then add "CLEAVE HHJP case" to a Part Studio.
export enum CleavePart
{
    annotation { "Name" : "Base left" } BASE_LEFT,
    annotation { "Name" : "Base right" } BASE_RIGHT,
    annotation { "Name" : "Cover left" } COVER_LEFT,
    annotation { "Name" : "Cover right" } COVER_RIGHT,
    annotation { "Name" : "Choc plate left" } PLATE_LEFT,
    annotation { "Name" : "Choc plate right" } PLATE_RIGHT,
    annotation { "Name" : "Power switch knob (reference position)" } KNOB
}
const DATA = /*PROFILE_DATA*/;
const FLOOR_BOUNDS = { (millimeter) : [0.8, 2, 5] } as LengthBoundSpec;
const DEPTH_BOUNDS = { (millimeter) : [0, 0, 20] } as LengthBoundSpec;
const MARGIN_BOUNDS = { (millimeter) : [0, 0, 10] } as LengthBoundSpec;
const INSERT_BOUNDS = { (millimeter) : [2, 2.9, 4] } as LengthBoundSpec;
const PLATE_BOUNDS = { (millimeter) : [1, 1.5, 3] } as LengthBoundSpec;
const COVER_BOUNDS = { (millimeter) : [1, 2, 5] } as LengthBoundSpec;

function partKey(part is CleavePart) returns string
{
    if (part == CleavePart.BASE_LEFT) return "base_case_left";
    if (part == CleavePart.BASE_RIGHT) return "base_case_right";
    if (part == CleavePart.COVER_LEFT) return "top_cover_left";
    if (part == CleavePart.COVER_RIGHT) return "top_cover_right";
    if (part == CleavePart.PLATE_LEFT) return "top_plate_choc_left";
    if (part == CleavePart.PLATE_RIGHT) return "top_plate_choc_right";
    return "power_switch_knob";
}
function addLoop(sketch is Sketch, name is string, loop is map, insertDiameter)
{
    if (loop.circle != undefined)
    {
        var c = loop.circle;
        var radius = c[2] * millimeter;
        if (insertDiameter != undefined && abs(c[2] - 1.45) < 0.0003)
            radius = insertDiameter / 2;
        skCircle(sketch, name, { "center" : vector(c[0], c[1]) * millimeter, "radius" : radius });
    }
    else
    {
        var points = [];
        for (var p in loop.points)
            points = append(points, vector(p[0], p[1]) * millimeter);
        skPolyline(sketch, name, { "points" : points });
    }
}
function sectionSolid(context is Context, id is Id, profiles is array, z0, z1, insertDiameter)
{
    var sketchId = id + "sketch";
    var sketch = newSketchOnPlane(context, sketchId, {
        "sketchPlane" : plane(vector(0, 0, z0) * millimeter, vector(0, 0, 1), vector(1, 0, 0))
    });
    for (var i = 0; i < size(profiles); i += 1)
    {
        addLoop(sketch, "outline" ~ i, profiles[i].outer, undefined);
        for (var j = 0; j < size(profiles[i].holes); j += 1)
            addLoop(sketch, "hole" ~ i ~ "_" ~ j, profiles[i].holes[j], insertDiameter);
    }
    skSolve(sketch);
    opExtrude(context, id + "extrude", {
        "entities" : qSketchRegion(sketchId, true),
        "direction" : vector(0, 0, 1), "endBound" : BoundingType.BLIND,
        "endDepth" : (z1 - z0) * millimeter
    });
    opDeleteBodies(context, id + "cleanup", { "entities" : qCreatedBy(sketchId, EntityType.BODY) });
}

annotation { "Feature Type Name" : "CLEAVE HHJP case" }
export const cleaveCase = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Part", "Default" : CleavePart.BASE_LEFT }
        definition.part is CleavePart;
        if (definition.part == CleavePart.BASE_LEFT || definition.part == CleavePart.BASE_RIGHT)
        {
            annotation { "Name" : "Bottom thickness" }
            isLength(definition.bottomThickness, FLOOR_BOUNDS);
            annotation { "Name" : "Extra cavity depth below PCB" }
            isLength(definition.extraDepth, DEPTH_BOUNDS);
            annotation { "Name" : "Extra lower wall thickness (outward)" }
            isLength(definition.wallExtra, MARGIN_BOUNDS);
            annotation { "Name" : "Additional width per side" }
            isLength(definition.widthExtra, MARGIN_BOUNDS);
            annotation { "Name" : "Additional length per side" }
            isLength(definition.lengthExtra, MARGIN_BOUNDS);
            annotation { "Name" : "Insert bore diameter" }
            isLength(definition.insertDiameter, INSERT_BOUNDS);
        }
        if (definition.part == CleavePart.PLATE_LEFT || definition.part == CleavePart.PLATE_RIGHT)
        {
            annotation { "Name" : "Main plate thickness (Choc clips: keep 1.5 mm)" }
            isLength(definition.plateThickness, PLATE_BOUNDS);
        }
        if (definition.part == CleavePart.COVER_LEFT || definition.part == CleavePart.COVER_RIGHT)
        {
            annotation { "Name" : "Upper cover thickness" }
            isLength(definition.coverThickness, COVER_BOUNDS);
        }
    }
    {
        var key = partKey(definition.part);
        var model = DATA[key];
        var isBase = definition.part == CleavePart.BASE_LEFT || definition.part == CleavePart.BASE_RIGHT;
        var isPlate = definition.part == CleavePart.PLATE_LEFT || definition.part == CleavePart.PLATE_RIGHT;
        var isCover = definition.part == CleavePart.COVER_LEFT || definition.part == CleavePart.COVER_RIGHT;
        var bottom = 0;
        var insertDiameter = undefined;
        if (isBase)
        {
            bottom = 2 - (definition.extraDepth + definition.bottomThickness) / millimeter;
            insertDiameter = definition.insertDiameter;
        }
        for (var i = 0; i < size(model.layers); i += 1)
        {
            var layer = model.layers[i];
            var z0 = layer.z0;
            var z1 = layer.z1;
            if (isBase && z0 < 2)
            {
                z0 = bottom;
                z1 = 2 - definition.extraDepth / millimeter;
            }
            if (isPlate && z0 >= 8.8)
            {
                z0 = 8.8 + (z0 - 8.8) * definition.plateThickness / (1.5 * millimeter);
                z1 = 8.8 + (z1 - 8.8) * definition.plateThickness / (1.5 * millimeter);
            }
            if (isCover && z0 >= 13.5)
            {
                z0 = 13.5 + (z0 - 13.5) * definition.coverThickness / (2 * millimeter);
                z1 = 13.5 + (z1 - 13.5) * definition.coverThickness / (2 * millimeter);
            }
            sectionSolid(context, id + ("layer" ~ i), layer.profiles, z0, z1, insertDiameter);
        }
        if (isBase && definition.extraDepth > 0 * millimeter)
        {
            // Extend the lower cavity, leaving PCB/plate/cover interface datums fixed.
            var rim = [];
            for (var layer in model.layers)
                if (layer.z0 <= 5.5 && layer.z1 >= 5.5) rim = layer.profiles;
            sectionSolid(context, id + "depthExtension", rim, 2 - definition.extraDepth / millimeter, 2, undefined);
        }
        if (isBase)
        {
            var dx = (definition.wallExtra + definition.widthExtra) / millimeter;
            var dy = (definition.wallExtra + definition.lengthExtra) / millimeter;
            if (dx > 0 || dy > 0)
            {
                var original = model.layers[0].profiles[0].outer;
                var cx = (model.bounds[0][0] + model.bounds[1][0]) / 2;
                var cy = (model.bounds[0][1] + model.bounds[1][1]) / 2;
                var expanded = [];
                for (var p in original.points)
                    expanded = append(expanded, [p[0] + (p[0] < cx ? -dx : dx), p[1] + (p[1] < cy ? -dy : dy)]);
                sectionSolid(context, id + "outerExtension", [{ "outer" : { "points" : expanded }, "holes" : [original] }], bottom, 6.5, undefined);
            }
        }
        var bodies = qBodyType(qCreatedBy(id, EntityType.BODY), BodyType.SOLID);
        if (size(evaluateQuery(context, bodies)) > 1)
            opBoolean(context, id + "union", { "tools" : bodies, "operationType" : BooleanOperationType.UNION });
        setProperty(context, { "entities" : qBodyType(qCreatedBy(id, EntityType.BODY), BodyType.SOLID),
            "propertyType" : PropertyType.NAME, "value" : key ~ "_editable" });
    });
