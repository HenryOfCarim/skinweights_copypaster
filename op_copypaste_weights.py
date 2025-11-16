import bpy
import bmesh


class CopySkinWeights(bpy.types.Operator):
    """Copy skin weights from active vertex group"""
    bl_idname = "object.copy_skin_weights_op"
    bl_label = "Copy skin weights"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and obj.vertex_groups.active is not None

    def execute(self, context):
        obj = context.active_object
        active_vg = obj.vertex_groups.active
        if active_vg:
            vertex_indices = get_vertex_group_indices(obj, active_vg)
            if vertex_indices:
                copy_weights_from_vertex_group(obj, vertex_indices)
                self.report({'INFO'}, f"Copied weights from vertex group '{active_vg.name}' ({len(vertex_indices)} vertices)")
            else:
                self.report({'WARNING'}, f"No vertices found in vertex group '{active_vg.name}'")
        return {'FINISHED'}


class PasteSkinWeights(bpy.types.Operator):
    """Paste copied skin weights to active vertex group"""
    bl_idname = "object.paste_skin_weights_op"
    bl_label = "Paste skin weights"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        per_vertex_weights = context.scene.sw_copypaster.per_vertex_clipboard
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and obj.vertex_groups.active is not None and per_vertex_weights

    def execute(self, context):
        settings = context.scene.sw_copypaster.settings
        per_vertex_weights = context.scene.sw_copypaster.per_vertex_clipboard
        obj = context.active_object
        active_vg = obj.vertex_groups.active
        if active_vg:
            vertex_indices = get_vertex_group_indices(obj, active_vg)
            current_mode = context.object.mode
            
            if vertex_indices:
                # Ensure we're in OBJECT mode for weight operations
                bpy.ops.object.mode_set(mode='OBJECT')
                
                if settings.clear_vertex_groups:
                    for i in vertex_indices:
                        clear_vertex_groups(obj, i)
                
                # Use per-vertex paste to preserve individual vertex weights
                paste_count = paste_per_vertex_weights(obj, per_vertex_weights, vertex_indices)
                
                if settings.normalize_weights:
                    # Only normalize vertices that received weights
                    for i in range(min(paste_count, len(vertex_indices))):
                        normalize_weights(obj, vertex_indices[i])
                
                # Return to original mode
                bpy.ops.object.mode_set(mode=current_mode)
                
                if paste_count < len(vertex_indices):
                    self.report({'WARNING'}, f"Pasted weights to {paste_count} of {len(vertex_indices)} vertices in '{active_vg.name}' (source had {len(per_vertex_weights)} vertices)")
                else:
                    self.report({'INFO'}, f"Pasted weights to vertex group '{active_vg.name}' ({paste_count} vertices)")
            else:
                self.report({'WARNING'}, f"No vertices found in vertex group '{active_vg.name}'")
        return {'FINISHED'}


class SelectLoops(bpy.types.Operator):
    """
    Select an edge loop if 2 or more vertices from it were selected
    """
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


class SelectVGVertices(bpy.types.Operator):
    """
    Select all vertices from the active vertex group
    """
    bl_idname = "object.select_vg_vertices"
    bl_label = "Select vertices from vertex group"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj.type == 'MESH' and obj.vertex_groups.active:
            return True
        else:
            return False

    def execute(self, context):
        obj = context.active_object
        current_mode = context.object.mode
        cunrent_vg = obj.vertex_groups.active
        bpy.ops.object.mode_set(mode='OBJECT')
        # Deselect all vertices before selecting
        for v in obj.data.vertices:
            v.select = False
        for v in obj.data.vertices:
            for g in v.groups:
                if g.group == cunrent_vg.index:
                    v.select = True
        bpy.ops.object.mode_set(mode=current_mode)
        return {'FINISHED'}


class SetWeightOperator(bpy.types.Operator):
    bl_idname = "object.set_weight"
    bl_label = "Set Weight"
    bl_description = "Set weight to selected vertices"
    bl_options = {'REGISTER', 'UNDO'}
    weight: bpy.props.FloatProperty(
        name="Set Weight",
        min=0.0,
        max=1.0,
        step=0.05,
        precision=3
    )
    blend_mode: bpy.props.EnumProperty(
        name="Set Blend Mode",
        description="Algorithm for setting new weights.",
        items=[('REPLACE', "Replace", "Set selected skin weights value", 0),
               ('ADD', "Add", "Adds selected skin weights value to existing one", 1),
               ('SUBTRACT', "Subtract","Subtruct selected skin weights value from existing one", 2),
               ],
        default='REPLACE'
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
        current_mode = context.object.mode
        bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
        vertex_groups = obj.vertex_groups
        active_vg = obj.vertex_groups.active
        selected_indices = get_vertex_indices(obj)
        if selected_indices:
            for vtx_index in selected_indices:
                wgroups = {}
                for group in vertex_groups:
                    try:
                        wgroups[group.name] = group.weight(vtx_index)
                    except RuntimeError:
                        pass
                # Fix for issue that happens in scale weights if the active vg doesn't exsist yet
                if active_vg.name not in wgroups.keys():
                    wgroups[active_vg.name] = 0
                updated_wgroups = scale_values(self.weight, active_vg.name, wgroups, self.blend_mode)
                for name, weight in updated_wgroups.items():
                    vertex_groups[name].add([vtx_index], weight, 'REPLACE')
        bpy.ops.object.mode_set(mode=current_mode)
        return {'FINISHED'}


def get_vertex_indices(obj):
    target_vertices = []
    # Get the current mode
    current_mode = bpy.context.object.mode if bpy.context.object else 'OBJECT'
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


def get_vertex_group_indices(obj, vertex_group):
    """
    Get all vertex indices that belong to the specified vertex group
    """
    vertex_indices = []
    current_mode = bpy.context.object.mode
    bpy.ops.object.mode_set(mode='OBJECT')
    
    for v in obj.data.vertices:
        for g in v.groups:
            if g.group == vertex_group.index:
                vertex_indices.append(v.index)
                break
    
    bpy.ops.object.mode_set(mode=current_mode)
    return vertex_indices


def copy_weights_from_vtx(obj, vtx_index):
    """
    This function copies skin weight data from a selected vertex to the clipboard
    """
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


def copy_weights_from_vertex_group(obj, vertex_indices):
    """
    This function copies per-vertex skin weight data from all vertices in a vertex group to the clipboard.
    For each vertex in the source group, this copies ALL of its vertex group weights (all bones).
    """
    swc_per_vertex_clipboard = bpy.context.scene.sw_copypaster.per_vertex_clipboard
    # Clear per-vertex clipboard before copying
    swc_per_vertex_clipboard.clear()
    
    if not vertex_indices:
        return
    
    # Must be in OBJECT mode to read weights accurately
    current_mode = bpy.context.object.mode
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Get vertex group from the active object
    vertex_groups = obj.vertex_groups
    
    # Store weights for each vertex separately
    for vtx_index in vertex_indices:
        # Create a new entry for this vertex
        vertex_entry = swc_per_vertex_clipboard.add()
        
        # Store all weights for this vertex (all bone/group assignments)
        for group in vertex_groups:
            try:
                weight = group.weight(vtx_index)
                if weight > 0:
                    item = vertex_entry.vertex_data.add()
                    item.vertex_index = group.index
                    item.group_name = group.name
                    item.weight = weight
            except RuntimeError:
                # Vertex is not in this group, skip
                pass
    
    # Restore the original mode
    bpy.ops.object.mode_set(mode=current_mode)


def paste_copied_weights(obj, skin_weights_buff, target_indices):
    """
    This function pastes skin weights from the clipboard to the target vertex
    """
    vertex_groups = obj.vertex_groups
    current_mode = bpy.context.object.mode
    # Switch to Object mode
    bpy.ops.object.mode_set(mode='OBJECT')
    for i in target_indices:
        for sw in skin_weights_buff:
            try:
                vertex_groups[sw.group_name].add([i], sw.weight, 'REPLACE')
            except KeyError:
                obj.vertex_groups.new(name=sw.group_name)
                vertex_groups[sw.group_name].add([i], sw.weight, 'REPLACE')
    # Switch back to the mode that was before editing
    bpy.ops.object.mode_set(mode=current_mode)


def paste_per_vertex_weights(obj, per_vertex_weights_buff, target_indices):
    """
    This function pastes per-vertex skin weights from the clipboard to target vertices.
    Matches source vertices to target vertices in order (1st to 1st, 2nd to 2nd, etc.)
    NOTE: Assumes caller has already switched to OBJECT mode.
    """
    vertex_groups = obj.vertex_groups
    
    # Determine how many vertices we can paste based on what we have
    num_source_vertices = len(per_vertex_weights_buff)
    num_target_vertices = len(target_indices)
    
    # Paste to as many target vertices as we have source data for
    paste_count = min(num_source_vertices, num_target_vertices)
    
    for i in range(paste_count):
        target_vtx_index = target_indices[i]
        source_vertex_data = per_vertex_weights_buff[i].vertex_data
        
        # Apply all weights from this source vertex to the target vertex
        for sw in source_vertex_data:
            try:
                vertex_groups[sw.group_name].add([target_vtx_index], sw.weight, 'REPLACE')
            except KeyError:
                # Create the vertex group if it doesn't exist
                obj.vertex_groups.new(name=sw.group_name)
                vertex_groups[sw.group_name].add([target_vtx_index], sw.weight, 'REPLACE')
    
    return paste_count


def normalize_weights(obj, vtx_index):
    """
    Normalize weights for a vertex so they sum to 1.0
    Uses proper Blender API to modify weights
    """
    v = obj.data.vertices[vtx_index]
    vertex_groups = obj.vertex_groups
    
    # Get current weights
    weights = {}
    for g in v.groups:
        try:
            group = vertex_groups[g.group]
            weights[group.name] = g.weight
        except (IndexError, KeyError):
            pass
    
    # Calculate total weight
    total_weight = sum(weights.values())
    
    if total_weight > 0:
        # Normalize and apply weights
        for group_name, weight in weights.items():
            normalized_weight = weight / total_weight
            vertex_groups[group_name].add([vtx_index], normalized_weight, 'REPLACE')


def clear_vertex_groups(obj, vtx_index):
    vertex_groups = obj.vertex_groups
    for group in vertex_groups:
        try:
            group.remove([vtx_index])
        except RuntimeError:
            pass


def select_loops():
    cur_edit_mode = bpy.context.object.mode
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_mode(type='EDGE')
    bpy.ops.mesh.loop_multi_select(ring=False)
    bpy.ops.object.mode_set(mode=cur_edit_mode)


def clamp(n, min, max):
    if n < min:
        return min
    elif n > max:
        return max
    else:
        return n


def scale_values(new_weight, active_vg, vertex_groups, blend_mode):
    """
    This function sets new_weight value for an active vertex group and rescalse other groups
    to keep sum of weights equal 1.0
    """
    sum_of_others = sum(vertex_groups.values()) - vertex_groups[active_vg]
    updated_values = {}
    # Need to finalize and set weights to the selected vertex group before scaling
    for name, weight in vertex_groups.items():
        if name == active_vg:
            if blend_mode == 'ADD':
                new_weight = clamp((weight + new_weight), 0, 1)
            elif blend_mode == 'SUBTRACT':
                new_weight = clamp((weight - new_weight), 0, 1)
            updated_values[name] = new_weight
            break
    # The second loop scales weights
    for name, weight in vertex_groups.items():
        if name != active_vg:
            scaled_value = weight * (1 - new_weight) / sum_of_others
            updated_values[name] = scaled_value
    return updated_values
