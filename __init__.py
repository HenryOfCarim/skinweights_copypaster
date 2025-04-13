import bpy
from .op_copypaste_weights import CopySkinWeights, PasteSkinWeights

bl_info = {
    "name": "Skin Weights CopyPaster",
    "version": (0, 0, 2),
    "blender": (2, 80, 0),
    "location": "View 3D > Sidebar > Item Tab > Skin Weights CopyPaster",
    "description": "Copies and paste weights from selected vertices",
    "category": "Rigging",
}


class SWCopyPaster_PT(bpy.types.Panel):
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
    SWCVertexGroupData,
    SWCPropreties,
    SWCopyPaster,
    SWCopyPaster_PT,
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
