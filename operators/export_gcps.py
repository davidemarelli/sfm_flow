
import csv
import logging
import os
from math import degrees

import bpy
from bpy_extras.object_utils import world_to_camera_view
from sfm_flow.prefs import AddonPreferences
from sfm_flow.utils.animation import get_last_keyframe
from sfm_flow.utils.blender_version import BlenderVersion
from sfm_flow.utils.object import get_gcp_collection
from sfm_flow.utils.path import get_render_image_filename

logger = logging.getLogger(__name__)


class SFMFLOW_OT_export_gcps(bpy.types.Operator):
    """Export the Ground Control Points data files."""
    bl_idname = "sfmflow.export_gcps"
    bl_label = "Export GCPs ground truth"
    bl_options = {'REGISTER'}

    # CSV field names in header for gcps
    GCPS_CSV_FIELDNAMES = ("gcp_name", "x_east", "y_north", "z_altitude", "yaw", "pitch", "roll")
    GCPS_IMAGES_CSV_FIELDNAMES = ("image_name", "gcp_name", "image_x", "image_y")

    # format of floats in gcp files
    DIGITS = 6
    NUM_FORMAT = f"{{:.{DIGITS}f}}"

    ################################################################################################
    # Properties
    #

    # ==============================================================================================
    file_format: bpy.props.EnumProperty(
        name="File format",
        description="GCPs export file format",
        items=(
            ("file_format.csv", "CSV", ".csv file format"),
            ("file_format.tsv", "TSV", ".tsv file format"),
        ),
        default="file_format.csv"
    )

    # ==============================================================================================
    export_rotation: bpy.props.BoolProperty(
        name="Export GCPs rotation",
        description="Include GCPs rotation (Yaw, Pitch, Roll) in the file",
        default=True,
        options={'SKIP_SAVE'}
    )

    ################################################################################################
    # Layout
    #

    def draw(self, context: bpy.types.Context):   # pylint: disable=unused-argument
        """Operator panel layout"""
        layout = self.layout
        row = layout.split(factor=0.33, align=True)
        row.label(text="File format")
        row.row().prop(self, "file_format", expand=True)
        layout.prop(self, "export_rotation")

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
        return context.scene.sfmflow.has_render_camera() and gcp_collection and gcp_collection.objects

    # ==============================================================================================
    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set:  # pylint: disable=unused-argument
        """Init operator when invoked.

        Arguments:
            context {bpy.types.Context} -- invoke context
            event {bpy.types.Event} -- invoke event

        Returns:
            set -- enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        # use user selected file format, ensures correct image filenames in exported files
        scene = context.scene
        scene.render.image_settings.file_format = scene.sfmflow.render_file_format
        #
        if bpy.data.is_saved:
            if bpy.data.is_dirty:
                # unsaved changes are present
                self.report({'WARNING'}, "Unsaved changes found, check and UNDO or SAVE changes before export")
                return {'CANCELLED'}

            return context.window_manager.invoke_props_dialog(self)
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
        cameras = scene.sfmflow.get_render_cameras()
        if not cameras:
            msg = "No render camera available!"
            logger.error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}
        #
        user_preferences = bpy.context.preferences
        addon_user_preferences_name = (__name__)[:__name__.index('.')]
        addon_prefs = user_preferences.addons[addon_user_preferences_name].preferences  # type: AddonPreferences
        #
        # get cameras animation end
        cameras_end_keyframes = []
        for camera in cameras:
            cameras_end_keyframes.append(get_last_keyframe(camera, True))
        #
        gcp_collection = get_gcp_collection(create=False)
        if not gcp_collection or not gcp_collection.objects:
            msg = "No GCPs found in the current scene!"
            logger.error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}
        #
        gcps = sorted(gcp_collection.objects, key=lambda obj: obj.name)
        unit_scale = scene.unit_settings.scale_length
        #
        if self.file_format == "file_format.csv":
            gcp_list_filename = "gcp_list.csv"
            gcp_images_list_filename = "gcp_images_list.csv"
            delimiter = ','
        else:   # TSV
            gcp_list_filename = "gcp_list.tsv"
            gcp_images_list_filename = "gcp_images_list.tsv"
            delimiter = '\t'
        #
        # --- export gcp list
        export_folder = bpy.path.abspath(context.scene.sfmflow.output_path)
        os.makedirs(export_folder, exist_ok=True)
        csv_file_path = os.path.join(export_folder, gcp_list_filename)
        with open(csv_file_path, 'w', encoding='utf-8', newline='') as csvfile:
            csv_writer = csv.writer(csvfile, delimiter=delimiter, lineterminator='\r\n')
            fieldnames = SFMFLOW_OT_export_gcps.GCPS_CSV_FIELDNAMES
            if not self.export_rotation:   # remove rotation fields from header
                fieldnames = fieldnames[:-3]
            csv_writer.writerow(fieldnames)
            for gcp in gcps:
                gcp_location = gcp.location * unit_scale
                row = [gcp.name,
                       SFMFLOW_OT_export_gcps.NUM_FORMAT.format(gcp_location.x),
                       SFMFLOW_OT_export_gcps.NUM_FORMAT.format(gcp_location.y),
                       SFMFLOW_OT_export_gcps.NUM_FORMAT.format(gcp_location.z)]
                if self.export_rotation:   # add gcp rotation info
                    row += [
                        SFMFLOW_OT_export_gcps.NUM_FORMAT.format((360 - degrees(gcp.rotation_euler[2])) % 360),   # yaw
                        SFMFLOW_OT_export_gcps.NUM_FORMAT.format(degrees(gcp.rotation_euler[0]) % 360),   # pitch
                        SFMFLOW_OT_export_gcps.NUM_FORMAT.format(degrees(gcp.rotation_euler[1]) % 360)]   # roll
                csv_writer.writerow(row)
        #
        # --- export gcp list in images
        frame_start = scene.frame_start
        frame_end = scene.frame_end
        render_scale = scene.render.resolution_percentage / 100
        render_size = (int(scene.render.resolution_x * render_scale), int(scene.render.resolution_y * render_scale))
        #
        frame_backup = scene.frame_current
        camera_backup = scene.camera
        #
        csv_file_path = os.path.join(export_folder, gcp_images_list_filename)
        with open(csv_file_path, 'w', encoding='utf-8', newline='') as csvfile:
            csv_writer = csv.writer(csvfile, delimiter=delimiter, lineterminator='\r\n')
            csv_writer.writerow(SFMFLOW_OT_export_gcps.GCPS_IMAGES_CSV_FIELDNAMES)
            #
            for frame in range(frame_start, frame_end+1):
                scene.frame_set(frame)
                #
                view_layer = context.view_layer
                if bpy.app.version >= BlenderVersion.V2_91:
                    view_layer = context.view_layer.depsgraph
                #
                for camera, last_keyframe in zip(cameras, cameras_end_keyframes):
                    if addon_prefs.limit_to_last_camera_keyframe and frame > last_keyframe:
                        break   # skip since camera animation ends before scene's end_frame
                    #
                    view_layer.update()
                    scene.camera = camera   # set render camera
                    image_filename, _ = get_render_image_filename(camera, scene, frame)
                    #
                    clip_start = camera.data.clip_start
                    clip_end = camera.data.clip_end
                    camera_pos = camera.matrix_world.to_translation()
                    #
                    for gcp in gcps:
                        gcp_pos = gcp.matrix_world.to_translation()
                        ray_direction = (gcp_pos - camera_pos)
                        ray_direction.normalize()
                        #
                        result, _, _, _, obj, _ = scene.ray_cast(view_layer, camera_pos, ray_direction)
                        if result and obj is gcp:   # gcp is not occluded
                            v_ndc = world_to_camera_view(scene, camera, gcp_pos)
                            if (0.0 < v_ndc.x < 1.0 and 0.0 < v_ndc.y < 1.0 and clip_start < v_ndc.z < clip_end):
                                # gcp is in the view frustum
                                gcp_px = (v_ndc.x * render_size[0], render_size[1] - v_ndc.y * render_size[1])
                                csv_writer.writerow((image_filename, gcp.name,
                                                     SFMFLOW_OT_export_gcps.NUM_FORMAT.format(gcp_px[0]),
                                                     SFMFLOW_OT_export_gcps.NUM_FORMAT.format(gcp_px[1])))
        #
        scene.frame_set(frame_backup)
        scene.camera = camera_backup
        #
        logger.info("GCPs exported.")
        return {'FINISHED'}
