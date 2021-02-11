
import logging

import bpy
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from mathutils import Vector

from ..utils import get_gcp_collection, nodes

logger = logging.getLogger(__name__)


class SFMFLOW_OT_add_gcp():
    """Helper class with common methods to multiple Ground Control Point operators."""

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Operator's enabling condition.
        The operator is enabled only if a scene is present.

        Arguments:
            context {bpy.types.Context} -- poll context

        Returns:
            bool -- True to enable, False to disable
        """
        return context.scene is not None

    ################################################################################################
    # Methods
    #

    # ==============================================================================================
    def add_gcp_geometry(self, context: bpy.types.Context, gcp_name: str = "gcp") -> bpy.types.Object:
        """Add the geometry of a GCP.
        All GCP's are created in a dedicated collection 'SFMFLOW_GCPs'.

        Arguments:
            context {bpy.types.Context} -- execution context

        Keyword Arguments:
            gcp_name {str} -- GCP's name, blender UI use only (default: {"gcp"})

        Returns:
            bpy.types.Object -- GCP object
        """
        logger.debug("Add GCP geometry")

        scale_x = 0.5
        scale_y = 0.5

        verts = [
            Vector((-1 * scale_x, 1 * scale_y, 0)),
            Vector((1 * scale_x, 1 * scale_y, 0)),
            Vector((1 * scale_x, -1 * scale_y, 0)),
            Vector((-1 * scale_x, -1 * scale_y, 0)),
        ]
        edges = []
        faces = [[0, 1, 2, 3]]

        mesh = bpy.data.meshes.new(name=gcp_name)
        mesh.from_pydata(verts, edges, faces)
        gcp = object_data_add(context, mesh, operator=self)

        gcp_collection = get_gcp_collection()
        bpy.context.collection.objects.unlink(gcp)
        gcp_collection.objects.link(gcp)

        # TODO switch to uv-unwrap instead of using generated in node setup
        # context.view_layer.objects.active = gcp
        # bpy.ops.object.mode_set(mode='EDIT')
        # bm = bmesh.from_edit_mesh(mesh)
        # uv_layer = bm.loops.layers.uv.verify()
        # bmesh.update_edit_mesh(mesh)
        # bpy.ops.object.mode_set(mode='OBJECT')

        logger.debug("Added GCP geometry")

        return gcp

    # ==============================================================================================
    def add_gcp_texture(self, gcp: bpy.types.Object, gcp_type: str) -> None:
        """Add material with texture to the GCP.
        All GCP materials are created with a name in format 'SFMFLOW_GCP_*' where * is the type of GCP.
        If a material with the same name already exists it will be used, otherwise a new one is created.

        Arguments:
            gcp {bpy.types.Object} -- the GCP object
            gcp_type {str} -- type of GCP, used to name the material and recover the texture asset
        """
        logger.debug("Add GCP material")

        material_name = "SFMFLOW_GCP_" + gcp_type
        #
        if material_name in bpy.data.materials:   # re-use material if possible
            material = bpy.data.materials[material_name]
        else:                                     # create new material
            material = bpy.data.materials.new(material_name)
            material.use_nodes = True

            node_tree = material.node_tree
            links = node_tree.links

            node_tree.nodes.clear()
            output = node_tree.nodes.new("ShaderNodeOutputMaterial")
            output.location = Vector((1300, 0))

            # old diffusive only material
            # bsdf_node = node_tree.nodes.new("ShaderNodeBsdfPrincipled")
            # tex_node = nodes.add_diffusive_texture_node(node_tree, nodes.get_asset("GCP_{}.png".format(gcp_type)))
            # tex_coords = node_tree.nodes.new("ShaderNodeTexCoord")
            # links.new(tex_coords.outputs['Generated'], tex_node.inputs['Vector'])
            # links.new(tex_node.outputs['Color'], bsdf_node.inputs[0])

            tex_mapping_node = nodes.add_texture_mapping_node(node_tree, scale=Vector((1., 1., 1.)),
                                                              nodes_location=Vector((0, 0)), use_generated_uv=True)
            bsdf_node, disp_node = nodes.add_principled_bsdf_material_nodes(
                node_tree, tex_mapping_node,
                nodes.get_asset("GCP_{}.png".format(gcp_type)),
                nodes.get_asset("GCP_Roughness.jpg"),
                nodes.get_asset("GCP_Normal.jpg"),
                nodes.get_asset("GCP_Displacement.jpg"),
                nodes_location=Vector((500, 500)))

            links.new(bsdf_node.outputs[0], output.inputs['Surface'])
            links.new(disp_node.outputs[0], output.inputs['Displacement'])

        gcp.active_material = material

        logger.debug("Created GCP material: %s", material_name)

#
#
#


class SFMFLOW_OT_add_gcp_cross1(bpy.types.Operator, AddObjectHelper, SFMFLOW_OT_add_gcp):
    """Add a ground control point in the scene"""
    bl_idname = "sfmflow.add_gcp_cross1"
    bl_label = "Add GCP Cross 1"
    bl_options = {'REGISTER', 'UNDO'}

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    def execute(self, context: bpy.types.Context) -> set:   # pylint: disable=unused-argument
        """Add a ground control point.

        Returns:
            set -- {'FINISHED'}
        """
        gcp = self.add_gcp_geometry(context)
        self.add_gcp_texture(gcp, 'Cross1')
        return {'FINISHED'}

#
#
#


class SFMFLOW_OT_add_gcp_cross2(bpy.types.Operator, AddObjectHelper, SFMFLOW_OT_add_gcp):
    """Add a ground control point in the scene"""
    bl_idname = "sfmflow.add_gcp_cross2"
    bl_label = "Add GCP Cross 2"
    bl_options = {'REGISTER', 'UNDO'}

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    def execute(self, context: bpy.types.Context) -> set:   # pylint: disable=unused-argument
        """Add a ground control point.

        Returns:
            set -- {'FINISHED'}
        """
        gcp = self.add_gcp_geometry(context)
        self.add_gcp_texture(gcp, 'Cross2')
        return {'FINISHED'}

#
#
#


class SFMFLOW_OT_add_gcp_hourglass(bpy.types.Operator, AddObjectHelper, SFMFLOW_OT_add_gcp):
    """Add a ground control point in the scene"""
    bl_idname = "sfmflow.add_gcp_hourglass"
    bl_label = "Add GCP Hourglass"
    bl_options = {'REGISTER', 'UNDO'}

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    def execute(self, context: bpy.types.Context) -> set:   # pylint: disable=unused-argument
        """Add a ground control point.

        Returns:
            set -- {'FINISHED'}
        """
        gcp = self.add_gcp_geometry(context)
        self.add_gcp_texture(gcp, 'Hourglass')
        return {'FINISHED'}

#
#
#


# class SFMFLOW_OT_add_gcp_l(bpy.types.Operator, AddObjectHelper, SFMFLOW_OT_add_gcp):
#     """Add a ground control point in the scene"""
#     bl_idname = "sfmflow.add_gcp_l"
#     bl_label = "Add GCP L"
#     bl_options = {'REGISTER', 'UNDO'}

#     ################################################################################################
#     # Behavior
#     #

#     # ==============================================================================================
#     def execute(self, context: bpy.types.Context) -> set:   # pylint: disable=unused-argument
#         """Add a ground control point.

#         Returns:
#             set -- {'FINISHED'}
#         """
#         gcp = self.add_gcp_geometry(context)
#         self.add_gcp_texture(gcp, 'L')
#         return {'FINISHED'}

#
#
#


class SFMFLOW_OT_add_gcp_round1(bpy.types.Operator, AddObjectHelper, SFMFLOW_OT_add_gcp):
    """Add a ground control point in the scene"""
    bl_idname = "sfmflow.add_gcp_round1"
    bl_label = "Add GCP Round 1"
    bl_options = {'REGISTER', 'UNDO'}

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    def execute(self, context: bpy.types.Context) -> set:   # pylint: disable=unused-argument
        """Add a ground control point.

        Returns:
            set -- {'FINISHED'}
        """
        gcp = self.add_gcp_geometry(context)
        self.add_gcp_texture(gcp, 'Round1')
        return {'FINISHED'}

#
#
#


class SFMFLOW_OT_add_gcp_round2(bpy.types.Operator, AddObjectHelper, SFMFLOW_OT_add_gcp):
    """Add a ground control point in the scene"""
    bl_idname = "sfmflow.add_gcp_round2"
    bl_label = "Add GCP Round 2"
    bl_options = {'REGISTER', 'UNDO'}

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    def execute(self, context: bpy.types.Context) -> set:   # pylint: disable=unused-argument
        """Add a ground control point.

        Returns:
            set -- {'FINISHED'}
        """
        gcp = self.add_gcp_geometry(context)
        self.add_gcp_texture(gcp, 'Round2')
        return {'FINISHED'}

#
#
#


class SFMFLOW_OT_add_gcp_round3(bpy.types.Operator, AddObjectHelper, SFMFLOW_OT_add_gcp):
    """Add a ground control point in the scene"""
    bl_idname = "sfmflow.add_gcp_round3"
    bl_label = "Add GCP Round 3"
    bl_options = {'REGISTER', 'UNDO'}

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    def execute(self, context: bpy.types.Context) -> set:   # pylint: disable=unused-argument
        """Add a ground control point.

        Returns:
            set -- {'FINISHED'}
        """
        gcp = self.add_gcp_geometry(context)
        self.add_gcp_texture(gcp, 'Round3')
        return {'FINISHED'}

#
#
#


class SFMFLOW_OT_add_gcp_square(bpy.types.Operator, AddObjectHelper, SFMFLOW_OT_add_gcp):
    """Add a ground control point in the scene"""
    bl_idname = "sfmflow.add_gcp_square"
    bl_label = "Add GCP Square"
    bl_options = {'REGISTER', 'UNDO'}

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    def execute(self, context: bpy.types.Context) -> set:   # pylint: disable=unused-argument
        """Add a ground control point.

        Returns:
            set -- {'FINISHED'}
        """
        gcp = self.add_gcp_geometry(context)
        self.add_gcp_texture(gcp, 'Square')
        return {'FINISHED'}
