
from os import path
from typing import Optional, Tuple

import bpy
from mathutils import Vector

from .blender_version import BlenderVersion

ASSET_FOLDER = path.join(path.dirname(path.abspath(__file__)), "../assets")


# ==================================================================================================
def get_asset(name: str) -> str:
    """Given a file asset name returns the full path to such asset.
    WARNING: no checks on file existence are done!

    Arguments:
        name {str} -- asset's file name

    Returns:
        str -- full asset path
    """
    return path.join(ASSET_FOLDER, name)


# ==================================================================================================
def add_texture_mapping_node(node_tree: bpy.types.NodeTree, location: Vector = Vector((0, 0, 0)),
                             rotation: Vector = Vector((0, 0, 0)),
                             scale: Vector = Vector((1, 1, 1)),
                             nodes_location: Vector = Vector((0, 0))) -> bpy.types.Node:
    """Add texture mapping nodes to a given shader node tree.

    Arguments:
        node_tree {bpy.types.NodeTree} -- node tree to be modified

    Keyword Arguments:
        location {Vector} -- mapping location (default: {Vector((0, 0, 0))})
        rotation {Vector} -- mapping rotation (default: {Vector((0, 0, 0))})
        scale {Vector} -- mapping scale (default: {Vector((1, 1, 1))})

    Returns:
        bpy.types.Node -- texture mapping node
    """
    tex_coords = node_tree.nodes.new("ShaderNodeTexCoord")
    tex_coords.location = nodes_location
    tex_mapping_node = node_tree.nodes.new("ShaderNodeMapping")
    tex_mapping_node.location = nodes_location + Vector((150, 0))
    node_tree.links.new(tex_coords.outputs['UV'], tex_mapping_node.inputs['Vector'])
    if bpy.app.version >= BlenderVersion.V2_81:   # v2.81+
        tex_mapping_node.inputs['Location'].default_value = location
        tex_mapping_node.inputs['Rotation'].default_value = rotation
        tex_mapping_node.inputs['Scale'].default_value = scale
    else:                                         # v2.80
        tex_mapping_node.translation = location
        tex_mapping_node.rotation = rotation
        tex_mapping_node.scale = scale
    return tex_mapping_node


# ==================================================================================================
def add_img_texture_node(node_tree: bpy.types.NodeTree, tex_image: str,
                         mapping_node: bpy.types.Node = None, non_color_space: bool = False,
                         label: str = None, nodes_location: Vector = Vector((0, 0))) -> bpy.types.Node:
    """Add image texture nodes to a given shader node tree.

    Arguments:
        node_tree {bpy.types.NodeTree} -- node tree to be modified
        tex_image {str} -- image texture file path

    Keyword Arguments:
        mapping_node {bpy.types.Node} -- optional texture mapping node,
                                         if not provided the mapping isn't generated (default: {None})
        non_color_space {bool} -- if true image data is used as non-color data
                                  (e.g. normal vectors) (default: {False})
        label {str} -- node label (default: {None})

    Returns:
        bpy.types.Node -- generated texture node
    """
    tex_image_node = node_tree.nodes.new(type="ShaderNodeTexImage")
    tex_image_node.location = nodes_location
    img = bpy.data.images.load(tex_image)
    img.pack()
    tex_image_node.image = img
    if label:
        tex_image_node.label = label
    if non_color_space:
        tex_image_node.image.colorspace_settings.is_data = non_color_space
    if mapping_node:
        node_tree.links.new(mapping_node.outputs['Vector'], tex_image_node.inputs['Vector'])
    return tex_image_node


# ==================================================================================================
def add_diffusive_texture_node(node_tree: bpy.types.NodeTree, tex_image: str,
                               mapping_node: bpy.types.Node = None,
                               nodes_location: Vector = Vector((0, 0))) -> Optional[bpy.types.Node]:
    """Add diffusive image texture node to a given shader node tree.

    Arguments:
        node_tree {bpy.types.NodeTree} -- node tree to be modified
        tex_image {str} -- diffusive texture file path

    Keyword Arguments:
        mapping_node {bpy.types.Node} -- optional texture mapping node, if not provided the mapping
                                         isn't generated (default: {None})

    Returns:
        Optional[bpy.types.Node] -- generated diffusive texture node, {None} if invalid args
    """
    if node_tree and tex_image:
        return add_img_texture_node(node_tree, tex_image=tex_image, mapping_node=mapping_node,
                                    non_color_space=False, label="Diffusive", nodes_location=nodes_location)
    return None


# ==================================================================================================
def add_roughness_texture_node(node_tree: bpy.types.NodeTree, tex_image: str,
                               mapping_node: bpy.types.Node = None,
                               nodes_location: Vector = Vector((0, 0))) -> Optional[bpy.types.Node]:
    """Add roughness image texture node to a given shader node tree.

    Arguments:
        node_tree {bpy.types.NodeTree} -- node tree to be modified
        tex_image {str} -- roughness texture file path

    Keyword Arguments:
        mapping_node {bpy.types.Node} -- optional texture mapping node,
                                         if not provided the mapping isn't generated (default: {None})

    Returns:
        Optional[bpy.types.Node] -- generated roughness texture node, {None} if invalid args
    """
    if node_tree and tex_image:
        return add_img_texture_node(node_tree, tex_image=tex_image, mapping_node=mapping_node,
                                    non_color_space=True, label="Roughness", nodes_location=nodes_location)
    return None


# ==================================================================================================
def add_normal_map_node(node_tree: bpy.types.NodeTree, tex_image: str,
                        mapping_node: bpy.types.Node = None,
                        nodes_location: Vector = Vector((0, 0))) -> Optional[bpy.types.Node]:
    """Add normal image texture and normal map nodes to a given shader node tree.

    Arguments:
        node_tree {bpy.types.NodeTree} -- node tree to be modified
        tex_image {str} -- normal texture file path

    Keyword Arguments:
        mapping_node {bpy.types.Node} -- optional texture mapping node, if not provided the mapping
                                         isn't generated (default: {None})

    Returns:
        Optional[bpy.types.Node] -- generated normal map node, {None} if invalid args
    """
    if node_tree and tex_image:
        tex_normal_node = add_img_texture_node(node_tree, tex_image=tex_image,
                                               non_color_space=True, mapping_node=mapping_node,
                                               label="Normal", nodes_location=nodes_location)
        map_normal_node = node_tree.nodes.new("ShaderNodeNormalMap")
        map_normal_node.location = nodes_location + Vector((250, 0))
        node_tree.links.new(tex_normal_node.outputs['Color'], map_normal_node.inputs['Color'])
        return map_normal_node
    return None


# ==================================================================================================
def add_displacement_map_node(node_tree: bpy.types.NodeTree, tex_image: str,
                              mapping_node: bpy.types.Node = None,
                              nodes_location: Vector = Vector((0, 0))) -> Optional[bpy.types.Node]:
    """Add displacement image texture and displacement map nodes to a given shader node tree.

    Arguments:
        node_tree {bpy.types.NodeTree} -- node tree to be modified
        tex_image {str} -- displacement texture file path

    Keyword Arguments:
        mapping_node {bpy.types.Node} -- optional texture mapping node, if not provided the mapping
                                         isn't generated (default: {None})

    Returns:
        Optional[bpy.types.Node] -- generated displacement node, {None} if invalid args
    """
    if node_tree and tex_image:
        tex_normal_node = add_img_texture_node(node_tree, tex_image=tex_image, non_color_space=True,
                                               mapping_node=mapping_node,
                                               label="Displacement", nodes_location=nodes_location)
        displacement_node = node_tree.nodes.new("ShaderNodeDisplacement")
        displacement_node.location = nodes_location + Vector((250, 0))
        node_tree.links.new(tex_normal_node.outputs['Color'], displacement_node.inputs['Height'])
        return displacement_node
    return None


# ==================================================================================================
def add_principled_bsdf_material_nodes(node_tree: bpy.types.NodeTree,
                                       tex_mapping_node: bpy.types.Node,
                                       tex_diffusive: str,
                                       tex_roughness: str = None,
                                       tex_normal: str = None, tex_displacement: str = None,
                                       nodes_location: Vector = Vector((0, 0))) -> Tuple[bpy.types.Node,
                                                                                         Optional[bpy.types.Node]]:
    """Add principled BSDF nodes to a given node tree.

    Arguments:
        node_tree {bpy.types.NodeTree} -- node tree to be modified
        tex_mapping_node {bpy.types.Node} -- textures mapping node
        tex_diffusive {str} -- diffusive texture file path

    Keyword Arguments:
        tex_roughness {str} -- roughness map file path (default: {None})
        tex_normal {str} -- normal map file path (default: {None})
        tex_displacement {str} -- displacement map file path (default: {None})

    Returns:
        Tuple[bpy.types.Node, Optional[bpy.types.Node]] -- BSDF node, displacement node
    """
    nodes = node_tree.nodes
    links = node_tree.links

    # --- textures
    diffusive_node = add_diffusive_texture_node(node_tree, tex_image=tex_diffusive, mapping_node=tex_mapping_node,
                                                nodes_location=(nodes_location+Vector((0, 0))))
    roughness_node = add_roughness_texture_node(node_tree, tex_image=tex_roughness, mapping_node=tex_mapping_node,
                                                nodes_location=(nodes_location+Vector((0, -270))))
    normal_node = add_normal_map_node(node_tree, tex_image=tex_normal, mapping_node=tex_mapping_node,
                                      nodes_location=(nodes_location+Vector((0, -530))))
    displacement_node = add_displacement_map_node(node_tree, tex_image=tex_displacement, mapping_node=tex_mapping_node,
                                                  nodes_location=(nodes_location+Vector((0, -800))))

    # --- principled BSDF
    bsdf_node = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf_node.location = nodes_location + Vector((410, -100))
    links.new(diffusive_node.outputs['Color'], bsdf_node.inputs[0])
    if roughness_node:
        links.new(roughness_node.outputs['Color'], bsdf_node.inputs['Roughness'])
    if normal_node:
        links.new(normal_node.outputs['Normal'], bsdf_node.inputs['Normal'])

    return bsdf_node, displacement_node


# ==================================================================================================
def add_floor_material_nodes(node_tree: bpy.types.NodeTree, floor_size: float) -> None:
    """Add floor materials shader nodes to a given node tree.

    Arguments:
        node_tree {bpy.types.NodeTree} -- shader node tree to be modified
        floor_size {float} -- size of the floor
    """
    nodes = node_tree.nodes
    links = node_tree.links

    # clear existing
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = Vector((1500, 0))

    tex_mapping_node = add_texture_mapping_node(node_tree, scale=Vector(
        (floor_size / 2., floor_size / 2., floor_size / 2.)), nodes_location=Vector((0, 0)))
    bsdf_node_1, disp_node_1 = add_principled_bsdf_material_nodes(node_tree,
                                                                  tex_mapping_node,
                                                                  get_asset("Concrete12_col.jpg"),
                                                                  get_asset("Concrete12_rgh.jpg"),
                                                                  get_asset("Concrete12_nrm.jpg"),
                                                                  get_asset("Concrete12_disp.jpg"),
                                                                  nodes_location=Vector((500, 1100)))

    bsdf_node_2, disp_node_2 = add_principled_bsdf_material_nodes(node_tree,
                                                                  tex_mapping_node,
                                                                  get_asset("Concrete05_col.jpg"),
                                                                  get_asset("Concrete05_rgh.jpg"),
                                                                  get_asset("Concrete05_nrm.jpg"),
                                                                  get_asset("Concrete05_disp.jpg"),
                                                                  nodes_location=Vector((500, -350)))

    # --- mix maps
    tex_noise_node = nodes.new("ShaderNodeTexNoise")
    tex_noise_node.location = Vector((550, 0))
    tex_noise_node.inputs['Scale'].default_value = floor_size / 2.
    tex_noise_node.inputs['Detail'].default_value = floor_size / 10.
    tex_noise_node.inputs['Distortion'].default_value = 0.
    color_ramp_node = nodes.new("ShaderNodeValToRGB")
    color_ramp_node.location = Vector((700, 0))
    c = color_ramp_node.color_ramp.elements[0]
    c.position = 0.333
    c.color = Vector((0, 0, 0, 1))
    c = color_ramp_node.color_ramp.elements[1]
    c.position = 0.666
    c.color = Vector((1, 1, 1, 1))
    links.new(tex_noise_node.outputs['Fac'], color_ramp_node.inputs['Fac'])

    # --- mix displacement maps
    if disp_node_1 and disp_node_2:
        disp_out_node = nodes.new("ShaderNodeMixRGB")
        disp_out_node.location = Vector((1200, -75))
        links.new(color_ramp_node.outputs['Color'], disp_out_node.inputs['Fac'])
        links.new(disp_node_1.outputs[0], disp_out_node.inputs['Color1'])
        links.new(disp_node_2.outputs[0], disp_out_node.inputs['Color2'])
    elif disp_node_1:
        disp_out_node = disp_node_1
    elif disp_node_2:
        disp_out_node = disp_node_2
    links.new(disp_out_node.outputs[0], output.inputs['Displacement'])

    # --- mix BSDFs
    bsdf_out_node = nodes.new("ShaderNodeMixShader")
    bsdf_out_node.location = Vector((1200, 75))
    links.new(color_ramp_node.outputs['Color'], bsdf_out_node.inputs[0])
    links.new(bsdf_node_1.outputs[0], bsdf_out_node.inputs[1])
    links.new(bsdf_node_2.outputs[0], bsdf_out_node.inputs[2])
    links.new(bsdf_out_node.outputs[0], output.inputs['Surface'])
