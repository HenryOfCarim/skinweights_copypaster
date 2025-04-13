import bpy
import bmesh


class CopySkinWeights(bpy.types.Operator):
    """Copy skin weights from a vertex"""
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
    """Paste copied skin weights to selected vertices"""
    bl_idname = "object.paste_skin_weights_op"
    bl_label = "Paste skin weights"

    @classmethod
    def poll(cls, context):
        weights = context.scene.sw_copypaster.clipboard
        return context.active_object is not None and weights

    def execute(self, context):
        weights = context.scene.sw_copypaster.clipboard
        ob = context.active_object
        selected_indices = get_vertex_indices()
        if selected_indices:
            print("target indices", selected_indices)
            paste_copied_weights(ob, weights, selected_indices)
        return {'FINISHED'}


def get_vertex_indices():
    target_vertices = []
    # Get the current mode
    current_mode = bpy.context.object.mode
    # Ensure you're in Object Mode
    bpy.ops.object.mode_set(mode='OBJECT')
    # Get the active object
    ob = bpy.context.active_object
    # Switch to Edit Mode to access vertex selection
    bpy.ops.object.mode_set(mode='EDIT')
    # Access the mesh data in Edit Mode
    bm = bmesh.from_edit_mesh(ob.data)
    # Get the indices of selected vertices
    target_vertices = [v.index for v in bm.verts if v.select]
    # Switch back to the mode that was before editing
    bpy.ops.object.mode_set(mode=current_mode)
    return target_vertices


def copy_weights_from_vtx(obj, vtx_index):
    """This function copies skin weight data from a selected vertex to the clipboard"""
    # Get the custom vertex groups clipboard collection
    weights_col = bpy.context.scene.sw_copypaster.clipboard
    # Clear it before coping
    weights_col.clear()
    # Get vertex group from the active object
    vertex_groups = obj.vertex_groups
    for group in vertex_groups:
        try:
            # Form and item for the vertex groups clipboard collection
            item = weights_col.add()
            item.vertex_index = group.index
            item.group_name = group.name
            item.weight = group.weight(vtx_index)
        except RuntimeError:
            # Vertex is not in this group
            pass


def paste_copied_weights(obj, skin_weights_buff, target_indices):
    """This function pastes sking weights from the clipboard to the target vertex"""
    settings = bpy.context.scene.sw_copypaster.settings
    vertex_groups = obj.vertex_groups
    # Switch to Object mode
    current_mode = bpy.context.object.mode
    bpy.ops.object.mode_set(mode='OBJECT')
    for i in target_indices:
        # If Clear weights enabled
        if settings.clear_vertex_groups:
            for group in vertex_groups:
                group.remove([i])
        for sw in skin_weights_buff:
            try:
                vertex_groups[sw.group_name].add([i], sw.weight, 'REPLACE')
            except KeyError:
                obj.vertex_groups.new(name=sw.group_name)
                vertex_groups[sw.group_name].add([i], sw.weight, 'REPLACE')
        if settings.normalize_weights:
            normalize_weights(obj, i)
    # Switch back to the mode that was before editing
    bpy.ops.object.mode_set(mode=current_mode)
    print("Weights copied and pasted successfully!")


def normalize_weights(obj, vtx_index):
    v = obj.data.vertices[vtx_index]
    total_weight = sum([g.weight for g in v.groups])
    if total_weight > 0:
        for g in v.groups:
            g.weight /= total_weight  # Normalize weight
