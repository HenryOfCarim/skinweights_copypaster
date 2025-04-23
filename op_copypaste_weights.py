import bpy
import bmesh


class CopySkinWeights(bpy.types.Operator):
    """Copy skin weights from a vertex"""
    bl_idname = "object.copy_skin_weights_op"
    bl_label = "Copy skin weights"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        obj = context.active_object
        selected_indices = get_vertex_indices(obj)
        if selected_indices:
            copy_weights_from_vtx(obj, selected_indices[0])
            self.report({'INFO'}, f"Copied form vertex {selected_indices[0]}")
        return {'FINISHED'}


class PasteSkinWeights(bpy.types.Operator):
    """Paste copied skin weights to selected vertices"""
    bl_idname = "object.paste_skin_weights_op"
    bl_label = "Paste skin weights"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        weights = context.scene.sw_copypaster.clipboard
        return context.active_object is not None and weights

    def execute(self, context):
        settings = context.scene.sw_copypaster.settings
        weights = context.scene.sw_copypaster.clipboard
        obj = context.active_object
        selected_indices = get_vertex_indices(obj)
        if selected_indices:
            if settings.clear_vertex_groups:
                for i in selected_indices:
                    clear_vertex_groups(obj, i)
            paste_copied_weights(obj, weights, selected_indices)
            if settings.normalize_weights:
                for i in selected_indices:
                    normalize_weights(obj, i)
        self.report({'INFO'}, "Pasted")
        return {'FINISHED'}


class SelectLoops(bpy.types.Operator):
    bl_idname = "object.select_loops_op"
    bl_label = "Select edge loop"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj.type == 'MESH':
            return True
        else:
            return False

    def execute(self, context):
        select_loops()
        return {'FINISHED'}


class SetWeightOperator(bpy.types.Operator):
    bl_idname = "object.set_weight"
    bl_label = "Set Weight"
    bl_description = "Set weight to selected vertices"
    bl_options = {'REGISTER', 'UNDO'}
    weight: bpy.props.FloatProperty(
        name="Set skin weight",
        min=0.0,
        max=1.0,
        step=0.05,
        precision=3
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj.type == 'MESH' and obj.vertex_groups.active:
            return True
        else:
            return False

    def execute(self, context):
        obj = context.active_object
        vertex_groups = obj.vertex_groups
        active_vg = obj.vertex_groups.active
        selected_indices = get_vertex_indices(obj)
        if selected_indices:
            for vtx_index in selected_indices:
                wgroups = {}
                for group in vertex_groups:
                    try:
                        # if group.weight(vtx_index) == 0:
                        #    continue
                        wgroups[group.name] = group.weight(vtx_index)
                    except RuntimeError:
                        # Vertex is not in this group
                        pass
                updated_wgroups = scale_values(self.weight, active_vg.name, wgroups)
                for name, weight in updated_wgroups.items():
                    vertex_groups[name].add([vtx_index], weight, 'REPLACE')
        return {'FINISHED'}


def get_vertex_indices(obj):
    target_vertices = []
    # Get the current mode
    current_mode = bpy.context.object.mode
    # Ensure you're in Object Mode
    bpy.ops.object.mode_set(mode='OBJECT')
    # Switch to Edit Mode to access vertex selection
    bpy.ops.object.mode_set(mode='EDIT')
    # Access the mesh data in Edit Mode
    bm = bmesh.from_edit_mesh(obj.data)
    # Get the indices of selected vertices
    target_vertices = [v.index for v in bm.verts if v.select]
    # Switch back to the mode that was before editing
    bpy.ops.object.mode_set(mode=current_mode)
    return target_vertices


def copy_weights_from_vtx(obj, vtx_index):
    """This function copies skin weight data from a selected vertex to the clipboard"""
    swc_clipboard = bpy.context.scene.sw_copypaster.clipboard
    # Clear clipboard before coping
    swc_clipboard.clear()
    # Get vertex group from the active object
    vertex_groups = obj.vertex_groups
    for group in vertex_groups:
        try:
            # Form and item for the vertex groups clipboard collection
            if group.weight(vtx_index) == 0:
                continue
            # Form and item for the vertex groups clipboard collection
            item = swc_clipboard.add()
            item.vertex_index = group.index
            item.group_name = group.name
            item.weight = group.weight(vtx_index)
        except RuntimeError:
            # Vertex is not in this group
            pass


def paste_copied_weights(obj, skin_weights_buff, target_indices):
    """This function pastes sking weights from the clipboard to the target vertex"""
    vertex_groups = obj.vertex_groups
    # Switch to Object mode
    current_mode = bpy.context.object.mode
    bpy.ops.object.mode_set(mode='OBJECT')
    for i in target_indices:
        for sw in skin_weights_buff:
            try:
                vertex_groups[sw.group_name].add([i], sw.weight, 'REPLACE')
            except KeyError:
                # print("There is no vertex group", sw.group_name)
                obj.vertex_groups.new(name=sw.group_name)
                vertex_groups[sw.group_name].add([i], sw.weight, 'REPLACE')
    # Switch back to the mode that was before editing
    bpy.ops.object.mode_set(mode=current_mode)
    print("Weights copied and pasted successfully!")


def normalize_weights(obj, vtx_index):
    v = obj.data.vertices[vtx_index]
    total_weight = sum([g.weight for g in v.groups])
    if total_weight > 0:
        for g in v.groups:
            g.weight /= total_weight  # Normalize weight


def clear_vertex_groups(obj, vtx_index):
    vertex_groups = obj.vertex_groups
    for group in vertex_groups:
        try:
            group.remove([vtx_index])
            # print(f"Removed vertex {vtx_index} from group '{group.name}'")
        except RuntimeError:
            pass


def select_loops():
    cur_edit_mode = bpy.context.object.mode
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_mode(type='EDGE')
    bpy.ops.mesh.loop_multi_select(ring=False)
    bpy.ops.object.mode_set(mode=cur_edit_mode)


def scale_values(new_value, active_vg, vertex_groups):
    sum_of_others = sum(vertex_groups.values()) - vertex_groups[active_vg]
    updated_values = {}
    for name, weight in vertex_groups.items():
        if name == active_vg:
            updated_values[name] = new_value
        else:
            scaled_value = weight * (1 - new_value) / sum_of_others
            updated_values[name] = scaled_value
    return updated_values
