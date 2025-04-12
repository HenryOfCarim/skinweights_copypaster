import bpy
from .op_copypaste_weights import get_vertex_indices, copy_weights_from_vtx, paste_copied_weights

bl_info = {
    "name": "Skin Weights CopyPaster",
    "version": (0, 0, 1),
    "blender": (2, 8, 0),
    "location": "View 3D > Sidebar > Item Tab > Skin Weights CopyPaster",
    "description": "Copies and paste weights from selected vertices",
    "category": "Object",
}


class SWCopyPaster_PT_main(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Item"
    bl_label = "Skin Weights Copypaster"

    @classmethod
    def poll(cls, context):
        return context.active_object and context.mode in {'EDIT_MESH', 'PAINT_WEIGHT'}

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.operator("object.copy_skin_weights_op", text="Copy Weights")
        row.operator("object.paste_skin_weights_op", text="Paste Weights")


class SWeightsPropertyGroup(bpy.types.PropertyGroup):
    vertex_index: bpy.props.IntProperty(name="Vertex Group ID")
    group_name: bpy.props.StringProperty(name="Group Name")
    weight: bpy.props.FloatProperty(name="Skin Weights")


class SWCopyPasterPropreties(bpy.types.PropertyGroup):
    clear_vertex_groups: bpy.props.BoolProperty(
        name="Clear vertex groups",
        description="Clear all vertex groups before paste",
        default=False)


class CopySkinWeights(bpy.types.Operator):
    """Copy skin weights from a"""
    bl_idname = "object.copy_skin_weights_op"
    bl_label = "Copy skin weights"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        ob = context.active_object
        selected_indices = get_vertex_indices()
        if selected_indices:
            weigths = copy_weights_from_vtx(ob, selected_indices[0])
            print("indices selected", selected_indices[0], weigths)
        return {'FINISHED'}


class PasteSkinWeights(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.paste_skin_weights_op"
    bl_label = "Paste skin weights"

    @classmethod
    def poll(cls, context):
        weights = context.scene.sw_copypaster
        return context.active_object is not None and weights

    def execute(self, context):
        weights = context.scene.sw_copypaster
        ob = context.active_object
        selected_indices = get_vertex_indices()
        if selected_indices:
            print("target indices", selected_indices)
            paste_copied_weights(ob, weights, selected_indices)
        return {'FINISHED'}


classes = [
    SWCopyPaster_PT_main,
    CopySkinWeights,
    PasteSkinWeights,
    SWeightsPropertyGroup,
]


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    bpy.types.Scene.sw_copypaster = bpy.props.CollectionProperty(type=SWeightsPropertyGroup)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    del bpy.types.Scene.sw_copypaster


if __name__ == "__main__":
    register()
