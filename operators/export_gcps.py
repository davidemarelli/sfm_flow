
import csv
import logging
import os

import bpy
from bpy_extras.object_utils import world_to_camera_view

from ..utils.blender_version import BlenderVersion
from ..utils.camera import get_camera_lookat
from ..utils.object import get_gcp_collection

logger = logging.getLogger(__name__)


class SFMFLOW_OT_export_gcps(bpy.types.Operator):
    """Export the Ground Control Points data file"""
    bl_idname = "sfmflow.export_gcps"
    bl_label = "Export GCPs"
    bl_options = {'REGISTER'}

    # CSV field names in header for gcps
    GCPS_CSV_FIELDNAMES = ("image_number", "x", "y", "z", "image_x", "image_y")

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Operator's enabling condition.
        The operator is enabled only if a render camera is configured and GCPs are used in the scene.

        Arguments:
            context {bpy.types.Context} -- poll context

        Returns:
            bool -- True to enable, False to disable
        """
        gcp_collection = get_gcp_collection(create=False)
        return context.scene.camera and gcp_collection and gcp_collection.objects

    # ==============================================================================================
    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set:  # pylint: disable=unused-argument
        """Init operator when invoked.

        Arguments:
            context {bpy.types.Context} -- invoke context
            event {bpy.types.Event} -- invoke event

        Returns:
            set -- enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        if bpy.data.is_saved:
            if bpy.data.is_dirty:
                # unsaved changes are present
                self.report({'WARNING'}, "Unsaved changes found, check and UNDO or SAVE changes before export")
                return {'CANCELLED'}

            return self.execute(context)
        else:
            self.report({'WARNING'}, "Save project before export")
            return {'CANCELLED'}

    # ==============================================================================================
    def execute(self, context: bpy.types.Context) -> set:
        """Export the GCPs.

        Returns:
            set -- {'FINISHED'}
        """
        logger.info("Exporting GCPs...")

        scene = context.scene
        camera = scene.camera
        if not camera:
            msg = "No render camera selected!"
            logger.error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}
        #
        gcp_collection = get_gcp_collection(create=False)
        if not gcp_collection or not gcp_collection.objects:
            msg = "No GCPs found in the current scene!"
            logger.error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}
        #
        frame_start = scene.frame_start
        frame_end = scene.frame_end
        clip_start = camera.data.clip_start
        clip_end = camera.data.clip_end
        gcps = gcp_collection.objects
        render_scale = scene.render.resolution_percentage / 100
        render_size = (int(scene.render.resolution_x * render_scale), int(scene.render.resolution_y * render_scale))
        #
        frame_backup = scene.frame_current
        #
        export_folder = bpy.path.abspath(context.scene.render.filepath)
        os.makedirs(export_folder, exist_ok=True)
        csv_file_path = os.path.join(export_folder, "gcps.csv")
        with open(csv_file_path, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile, delimiter=',')
            csv_writer.writerow(SFMFLOW_OT_export_gcps.GCPS_CSV_FIELDNAMES)
            #
            for frame in range(frame_start, frame_end+1):
                scene.frame_set(frame)
                #
                camera_lookat = get_camera_lookat(camera)
                view_layer = context.view_layer
                if bpy.app.version >= BlenderVersion.V2_91:
                    view_layer = context.view_layer.depsgraph
                #
                for gcp in gcps:
                    v = gcp.location
                    #
                    result, _, _, _, obj, _ = scene.ray_cast(view_layer, camera.location, camera_lookat)
                    if result and obj is gcp:   # gcp is not occluded
                        v_ndc = world_to_camera_view(scene, camera, gcp.matrix_world @ v)
                        if (0.0 < v_ndc.x < 1.0 and 0.0 < v_ndc.y < 1.0 and clip_start < v_ndc.z < clip_end):
                            # gcp is in the view frustum
                            gcp_px = (round(v_ndc.x * render_size[0]), round(v_ndc.y * render_size[1]))
                            csv_writer.writerow((frame, gcp.location.x, gcp.location.y,
                                                 gcp.location.z, gcp_px[0], gcp_px[1]))
        #
        scene.frame_set(frame_backup)
        #
        logger.info("GCPs exported.")
        return {'FINISHED'}
