import bpy
import bmesh


def get_vertex_indices():
    target_vertices = []
    # Get the current mode
    current_mode = bpy.context.object.mode
    print("Current mode:", current_mode)

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

    # Switch back to Object Mode
    bpy.ops.object.mode_set(mode=current_mode)
    return target_vertices


def copy_weights_from_vtx(obj, vtx_index):
    weights_col = bpy.context.scene.sw_copypaster.clipboard
    weights_col.clear()
    weights = []
    vertex_groups = obj.vertex_groups
    for group in vertex_groups:
        try:
            weight = group.weight(vtx_index)
            weights.append((group.index, weight))
            item = weights_col.add()
            item.vertex_index = group.index  # Replace with the vertex index
            item.group_name = group.name  # Replace with the vertex group name
            item.weight = group.weight(vtx_index)
        except RuntimeError:
            # Vertex is not in this group
            pass
    return weights


def paste_copied_weights(obj, weights_col, target_indices):
    # Paste weights to the target vertex
    settings = bpy.context.scene.sw_copypaster.settings
    vertex_groups = obj.vertex_groups
    current_mode = bpy.context.object.mode
    bpy.ops.object.mode_set(mode='OBJECT')
    for i in target_indices:
        if settings.clear_vertex_groups:
            for group in vertex_groups:
                group.remove([i])
        for wi in weights_col:
            print(wi.group_name)
            vertex_groups[wi.group_name].add([i], wi.weight, 'REPLACE')
    bpy.ops.object.mode_set(mode=current_mode)
    print("Weights copied and pasted successfully!")
