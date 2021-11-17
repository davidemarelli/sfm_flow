
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
        out_data.update({f'pc_{k}': (f"{v:.6f}" if isinstance(v, float) else v) for k, v in result[0].items()})
        out_data.update({f'cam_{k}': (f"{v:.6f}" if isinstance(v, float) else v) for k, v in result[1].items()})
        #
        len_scale = context.scene.unit_settings.scale_length
        len_unit = SFMFLOW_OT_evaluate_reconstruction.LENGTH_UNIT[context.scene.unit_settings.length_unit]
        flags = 'w' if self.overwrite_evaluation_file else 'a'
        try:
            # write .txt file
            filepath = bpy.path.abspath(self.evaluation_filepath)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, mode=flags, encoding='utf-8', newline='\n') as f:
                f.write(f"Project: {out_data['project_name']}\n")
                f.write(f"Evaluation of Reconstruction model '{out_data['name']}'"
                        f" (internal name '{out_data['name_internal']}')\n")
                f.write(f"Scene measurement system: {out_data['unit_system']}\n")
                f.write(f"Scene length unit: {out_data['length_unit']}\n")
                #
                f.write("Point cloud evaluation:\n")
                out_pc = result[0]
                f.write(f"   used filtered point cloud: {out_pc['used_filtered_cloud']}\n")
                f.write(f"   filter threshold: {out_pc['filter_threshold']:.3f}\n")
                f.write(f"   full cloud size: {out_pc['full_cloud_size']}\n")
                f.write(f"   evaluated cloud size: {out_pc['used_cloud_size']}"
                        f" ({(out_pc['used_cloud_size_percent']*100):.1f}%)\n")
                f.write(f"   discarded points count: {out_pc['discarded_points']}\n")
                f.write(f"   distance mean: {(out_pc['dist_mean']*len_scale):.3f}{len_unit}\n")
                f.write(f"   distance standard deviation: {(out_pc['dist_std']*len_scale):.3f}{len_unit}\n")
                f.write(f"   distance min: {(out_pc['dist_min']*len_scale):.3f}{len_unit}\n")
                f.write(f"   distance max: {(out_pc['dist_max']*len_scale):.3f}{len_unit}\n")
                #
                f.write("Camera poses evaluation:\n")
                out_cam = result[1]
                f.write(f"   cameras count: {out_cam['camera_count']}\n")
                f.write(f"   reconstructed camera count: {out_cam['reconstructed_camera_count']}"
                        f" ({(out_cam['reconstructed_camera_percent']*100):.1f}%)\n")
                f.write(f"   distance mean: {(out_cam['pos_mean']*len_scale):.3f}{len_unit}\n")
                f.write(f"   distance standard deviation: {(out_cam['pos_std']*len_scale):.3f}{len_unit}\n")
                f.write(f"   distance min: {(out_cam['pos_min']*len_scale):.3f}{len_unit}\n")
                f.write(f"   distance max: {(out_cam['pos_max']*len_scale):.3f}{len_unit}\n")
                f.write(f"   rotation difference mean: {out_cam['rot_mean']:.3f}°\n")
                f.write(f"   rotation difference standard deviation: {out_cam['rot_std']:.3f}°\n")
                f.write(f"   rotation difference min: {out_cam['rot_min']:.3f}°\n".format())
                f.write(f"   rotation difference max: {out_cam['rot_max']:.3f}°\n")
                f.write(f"   look-at direction difference mean: {out_cam['lookat_mean']:.3f}°\n")
                f.write(f"   look-at direction difference standard deviation: {out_cam['lookat_std']:.3f}°\n")
                f.write(f"   look-at direction difference min: {out_cam['lookat_min']:.3f}°\n")
                f.write(f"   look-at direction difference max: {out_cam['lookat_max']:.3f}°\n")
                #
                f.write("\n\n")
            #
            # write .csv file
            csv_filepath = bpy.path.abspath(self.evaluation_filepath)[:-3] + "csv"
            with open(csv_filepath, mode=flags, encoding='utf-8', newline='') as csv_f:
                writer = DictWriter(csv_f, fieldnames=out_data.keys(), lineterminator='\r\n')
                if csv_f.tell() == 0:
                    writer.writeheader()
                writer.writerow(out_data)
            #
            msg = f"Evaluation written to file: {self.evaluation_filepath}|.csv"
            logger.info(msg)
            self.report({'INFO'}, msg)
            return {'FINISHED'}
        #
        except OSError as e:
            msg = str(e)
            logger.error(e)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}
