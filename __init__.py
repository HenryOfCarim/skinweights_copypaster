import bpy
from .op_copypaste_weights import (CopySkinWeights, PasteSkinWeights, SelectLoops, SelectVGVertices,
                                   SetWeightOperator)

bl_info = {
    "name": "Skin Weights CopyPaster",
    "version": (0, 3, 0),
    "blender": (2, 80, 0),
    "location": "View 3D > Sidebar > Item Tab > Skin Weights CopyPaster",
    "description": "Copies and paste weights from selected vertices",
    "category": "Rigging",
}


class SW_PT_CopyPaster(bpy.types.Panel):
    bl_label = "Skin Weights Copypaster"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Item"

    @classmethod
    def poll(cls, context):
        return context.active_object and context.mode in {'EDIT_MESH', 'PAINT_WEIGHT'}

    def draw(self, context):
        scn = context.scene
        swp_settings = scn.sw_copypaster.settings
        layout = self.layout
        row = layout.row(align=True)
        row.operator("object.copy_skin_weights_op", text="Copy Weights")
        row.operator("object.paste_skin_weights_op", text="Paste Weights")
        layout.prop(swp_settings, "clear_vertex_groups", text="Clear existing weights")
        layout.prop(swp_settings, "normalize_weights", text="Normalize weights")
        layout.label(text="Select")
        row = layout.row(align=True)
        row.operator("object.select_loops_op", text="Select Loops")
        row.operator("object.select_vg_vertices", text="Select Vertex Group")
        layout.label(text="Set skin weights value")
        row = layout.row(align=True)
        for weight in [0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]:
            row.operator("object.set_weight", text=str(weight)).weight = weight


class SWCVertexGroupData(bpy.types.PropertyGroup):
    vertex_index: bpy.props.IntProperty(name="Vertex Group ID")
    group_name: bpy.props.StringProperty(name="Group Name")
    weight: bpy.props.FloatProperty(name="Skin Weights")


class SWCPropreties(bpy.types.PropertyGroup):
    clear_vertex_groups: bpy.props.BoolProperty(
        name="Clear vertex groups",
        description="Clear all vertex groups before paste",
        default=False)
    normalize_weights: bpy.props.BoolProperty(
        name="Normalize weights",
        description="Normalize paste weights for the selection",
        default=False)


class SWCopyPaster(bpy.types.PropertyGroup):
    clipboard: bpy.props.CollectionProperty(type=SWCVertexGroupData)
    settings: bpy.props.PointerProperty(type=SWCPropreties)


classes = [
    CopySkinWeights,
    PasteSkinWeights,
    SelectLoops,
    SelectVGVertices,
    SetWeightOperator,
    SWCVertexGroupData,
    SWCPropreties,
    SWCopyPaster,
    SW_PT_CopyPaster,
]


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    bpy.types.Scene.sw_copypaster = bpy.props.PointerProperty(type=SWCopyPaster)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    del bpy.types.Scene.sw_copypaster


if __name__ == "__main__":
    register()
