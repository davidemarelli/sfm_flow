
import logging
import os
from csv import DictWriter

import bpy
from sfm_flow.reconstruction import ReconstructionsManager
from sfm_flow.utils import is_active_object_reconstruction

logger = logging.getLogger(__name__)


class SFMFLOW_OT_evaluate_reconstruction(bpy.types.Operator):
    """Evaluate a 3D reconstruction."""
    bl_idname = "sfmflow.evaluate_reconstruction"
    bl_label = "Evaluate selected reconstruction"

    FILENAME = "sfmflow_evaluation.txt"

    LENGTH_UNIT = {
        'ADAPTIVE': "",
        'METERS': "m",
        'KILOMETERS': "km",
        'CENTIMETERS': "cm",
        'MILLIMETERS': "mm",
        'MICROMETERS': "μm",
        'MILES': "mi",
        'FEET': "ft",
        'INCHES': "in",
        'THOU': "mil"
    }

    ################################################################################################
    # Properties
    #

    # ==============================================================================================
    use_filtered_cloud: bpy.props.BoolProperty(
        name="Use filtered point cloud",
        description="If checked the filtered point cloud is used to run the evaluation,"
                    " otherwise the full point cloud is used",
        default=True,
        options={'SKIP_SAVE'}
    )

    # ==============================================================================================
    evaluation_filepath: bpy.props.StringProperty(
        name="Path to evaluation output file",
        default="//reconstructions/sfmflow_evaluation.txt",
        description="Path to the SfM Flow evaluation file for export",
        subtype='FILE_PATH',
        options={'HIDDEN', 'SKIP_SAVE'}
    )

    # ==============================================================================================
    overwrite_evaluation_file: bpy.props.BoolProperty(
        name="Overwrite evaluation file",
        description="If checked the evaluation file will be overwritten, otherwise new data will be appended"
        " to the existing one (if any)",
        default=False,
        options={'SKIP_SAVE'}
    )

    ################################################################################################
    # Layout
    #

    def draw(self, context: bpy.types.Context):   # pylint: disable=unused-argument
        """Operator panel layout"""
        layout = self.layout
        layout.prop(self, "use_filtered_cloud", expand=True)
        layout.separator()
        row = layout.row(align=True)
        row.label(text="Evaluation output files:")
        col = layout.column(align=True)
        col.alignment = 'RIGHT'
        col.label(text=self.evaluation_filepath)
        col.label(text=(self.evaluation_filepath[:-3] + "csv"))
        layout.prop(self, "overwrite_evaluation_file")

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Operator's enabling condition.
        The operator is enabled only if a 3D reconstruction is selected.

        Arguments:
            context {bpy.types.Context} -- poll context

        Returns:
            bool -- True to enable, False to disable
        """
        return is_active_object_reconstruction(context)

    # ==============================================================================================
    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set:  # pylint: disable=unused-argument
        """Init operator when invoked.

        Arguments:
            context {bpy.types.Context} -- invoke context
            event {bpy.types.Event} -- invoke event

        Returns:
            set -- enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        path1 = os.path.normpath(os.path.join(
            bpy.path.abspath(context.scene.sfmflow.reconstruction_path),
            SFMFLOW_OT_evaluate_reconstruction.FILENAME))
        path2 = bpy.path.relpath(path1)
        self.evaluation_filepath = path1 if len(path1) < len(path2) else path2
        #
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    # ==============================================================================================
    def execute(self, context: bpy.types.Context) -> set:
        """Evaluates the reconstructed point cloud and camera poses.

        Returns:
            set -- in {'FINISHED', 'CANCELLED'}
        """
        obj = context.view_layer.objects.active
        model = ReconstructionsManager.get_model_by_uuid(obj['sfmflow_model_uuid'])
        result = model.evaluate(context.scene, ReconstructionsManager.gt_kdtree, self.use_filtered_cloud)
        #
        # build full evaluation result dictionary
        out_data = {
            "unit_system": context.scene.unit_settings.system,
            "length_unit": context.scene.unit_settings.length_unit,
            "name": obj.name,
            "name_internal": model.name,
            "project_name": bpy.path.basename(bpy.data.filepath),
        }
        out_data.update({f'pc_{k}': ("{:.6f}".format(v) if isinstance(v, float) else v) for k, v in result[0].items()})
        out_data.update({f'cam_{k}': ("{:.6f}".format(v) if isinstance(v, float) else v) for k, v in result[1].items()})
        #
        len_scale = context.scene.unit_settings.scale_length
        len_unit = SFMFLOW_OT_evaluate_reconstruction.LENGTH_UNIT[context.scene.unit_settings.length_unit]
        flags = 'w' if self.overwrite_evaluation_file else 'a'
        try:
            # write .txt file
            filepath = bpy.path.abspath(self.evaluation_filepath)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, mode=flags) as f:
                f.write("Project: {}\n".format(out_data["project_name"]))
                f.write("Evaluation of Reconstruction model '{}' (internal name '{}')\n".format(
                    out_data["name"], out_data["name_internal"]))
                f.write("Scene measurement system: {}\n".format(out_data["unit_system"]))
                f.write("Scene length unit: {}\n".format(out_data["length_unit"]))
                #
                f.write("Point cloud evaluation:\n")
                out_pc = result[0]
                f.write("   used filtered point cloud: {}\n".format(out_pc['used_filtered_cloud']))
                f.write("   filter threshold: {:.3f}\n".format(out_pc['filter_threshold']))
                f.write("   full cloud size: {}\n".format(out_pc['full_cloud_size']))
                f.write("   evaluated cloud size: {} ({:.1f}%)\n".format(
                    out_pc['used_cloud_size'], out_pc['used_cloud_size_percent']*100))
                f.write("   discarded points count: {}\n".format(out_pc['discarded_points']))
                f.write("   distance mean: {:.3f}{}\n".format(out_pc['dist_mean']*len_scale, len_unit))
                f.write("   distance standard deviation: {:.3f}{}\n".format(out_pc['dist_std']*len_scale, len_unit))
                f.write("   distance min: {:.3f}{}\n".format(out_pc['dist_min']*len_scale, len_unit))
                f.write("   distance max: {:.3f}{}\n".format(out_pc['dist_max']*len_scale, len_unit))
                #
                f.write("Camera poses evaluation:\n")
                out_cam = result[1]
                f.write("   cameras count: {}\n".format(out_cam['camera_count']))
                f.write("   reconstructed camera count: {} ({:.1f}%)\n".format(
                    out_cam['reconstructed_camera_count'], out_cam['reconstructed_camera_percent']*100))
                f.write("   distance mean: {:.3f}{}\n".format(out_cam['pos_mean']*len_scale, len_unit))
                f.write("   distance standard deviation: {:.3f}{}\n".format(out_cam['pos_std']*len_scale, len_unit))
                f.write("   distance min: {:.3f}{}\n".format(out_cam['pos_min']*len_scale, len_unit))
                f.write("   distance max: {:.3f}{}\n".format(out_cam['pos_max']*len_scale, len_unit))
                f.write("   rotation difference mean: {:.3f}°\n".format(out_cam['rot_mean']))
                f.write("   rotation difference standard deviation: {:.3f}°\n".format(out_cam['rot_std']))
                f.write("   rotation difference min: {:.3f}°\n".format(out_cam['rot_min']))
                f.write("   rotation difference max: {:.3f}°\n".format(out_cam['rot_max']))
                f.write("   look-at direction difference mean: {:.3f}°\n".format(out_cam['lookat_mean']))
                f.write("   look-at direction difference standard deviation: {:.3f}°\n".format(out_cam['lookat_std']))
                f.write("   look-at direction difference min: {:.3f}°\n".format(out_cam['lookat_min']))
                f.write("   look-at direction difference max: {:.3f}°\n".format(out_cam['lookat_max']))
                #
                f.write("\n\n")
            #
            # write .csv file
            csv_filepath = bpy.path.abspath(self.evaluation_filepath)[:-3] + "csv"
            with open(csv_filepath, flags, newline='') as csv_f:
                writer = DictWriter(csv_f, fieldnames=out_data.keys())
                if csv_f.tell() == 0:
                    writer.writeheader()
                writer.writerow(out_data)
            #
            msg = "Evaluation written to file: {}|.csv".format(self.evaluation_filepath)
            logger.info(msg)
            self.report({'INFO'}, msg)
            return {'FINISHED'}
        #
        except OSError as e:
            msg = str(e)
            logger.error(e)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}
