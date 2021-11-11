
import logging
from typing import Dict

import bpy
from mathutils import Matrix
from sfm_flow.reconstruction import ReconstructionsManager

from .threaded_operator import ThreadedOperator

logger = logging.getLogger(__name__)


class SFMFLOW_OT_align_reconstruction(ThreadedOperator):
    """Align a 3D SfM reconstruction to the ground truth geometry"""
    bl_idname = "sfmflow.align_reconstruction"
    bl_label = "Align selected reconstruction"
    bl_options = {'REGISTER', 'UNDO'}

    ################################################################################################
    # Properties
    #

    # ==============================================================================================
    use_filtered_cloud: bpy.props.BoolProperty(
        name="Use filtered point cloud",
        description="If checked the filtered point cloud is used to run the alignment,"
                    " otherwise the full point cloud is used",
        default=True,
        options={'SKIP_SAVE'}
    )

    # ==============================================================================================
    use_custom_params: bpy.props.BoolProperty(
        name="Custom setup",
        description="Use custom ICP parameters",
        default=False,
        options={'SKIP_SAVE'}
    )

    # ==============================================================================================
    max_iterations: bpy.props.IntProperty(
        name="Max iterations",
        description="Maximum allowed iterations for best alignment search",
        min=1,
        soft_max=1000,
        default=100,
        subtype='FACTOR',
        options={'SKIP_SAVE'}
    )

    # ==============================================================================================
    samples_percentage: bpy.props.IntProperty(
        name="Point cloud sampling",
        description="Percentage of reconstructed points to be used for alignment",
        min=1,
        max=100,
        default=75,
        subtype='PERCENTAGE',
        options={'SKIP_SAVE'}
    )

    # ==============================================================================================
    alignment_mode: bpy.props.EnumProperty(
        name="Alignment mode",
        description="Reconstruction alignment mode",
        items=[
            ("cloud_align.auto", "Auto", "Compute the alignment using the Iterative Closest Point algorithm"),
            ("cloud_align.matrix", "Matrix", "Set the alignment using a custom matrix"),
        ],
        default="cloud_align.auto",
    )

    # ==============================================================================================
    # alignment_matrix: bpy.props.FloatVectorProperty(
    # FIXME this is the correct solution but does not render in blender 2.80. bug ??
    #     name="Alignment matrix",
    #     description="Manually set the reconstruction to ground truth alignment matrix",
    #     size=16,
    #     subtype="MATRIX",
    #     default=(
    #         1., 0., 0., 0.,
    #         0., 1., 0., 0.,
    #         0., 0., 1., 0.,
    #         0., 0., 0., 1.
    #     ),
    #     precision=4,
    #     unit='NONE',
    #     options={'SKIP_SAVE'}
    # )

    alignment_matrix_row1: bpy.props.FloatVectorProperty(
        size=4,
        default=(1., 0., 0., 0.),
        precision=4,
        options={'SKIP_SAVE'}
    )
    alignment_matrix_row2: bpy.props.FloatVectorProperty(
        size=4,
        default=(0., 1., 0., 0.),
        precision=4,
        options={'SKIP_SAVE'}
    )
    alignment_matrix_row3: bpy.props.FloatVectorProperty(
        size=4,
        default=(0., 0., 1., 0.),
        precision=4,
        options={'SKIP_SAVE'}
    )
    alignment_matrix_row4: bpy.props.FloatVectorProperty(
        size=4,
        default=(0., 0., 0., 1.),
        precision=4,
        options={'SKIP_SAVE'}
    )

    ################################################################################################
    # Layout
    #

    def draw(self, context: bpy.types.Context):   # pylint: disable=unused-argument
        """Operator layout"""
        layout = self.layout
        layout.prop(self, "alignment_mode", expand=True)
        box = layout.box()
        if self.alignment_mode == "cloud_align.matrix":
            #box.prop(self, "alignment_matrix")
            r = box.row(align=True)
            r.label(text="Alignment matrix")
            col = box.column(align=True)
            r = col.row(align=True)
            r.prop(self, "alignment_matrix_row1", text="")
            r = col.row(align=True)
            r.prop(self, "alignment_matrix_row2", text="")
            r = col.row(align=True)
            r.prop(self, "alignment_matrix_row3", text="")
            r = col.row(align=True)
            r.prop(self, "alignment_matrix_row4", text="")
        else:
            col = box.column(align=True)
            col.label(text="Iterative Closest Point (ICP) parameters")
            col.prop(self, "use_filtered_cloud")
            col.prop(self, "use_custom_params")
            if self.use_custom_params:
                col = box.column()
                col.prop(self, "max_iterations")
                col.prop(self, "samples_percentage")

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Panel's enabling condition.
        The operator is enabled only if a reconstruction is selected.

        Arguments:
            context {bpy.types.Context} -- poll context

        Returns:
            bool -- True to enable, False to disable
        """
        obj = context.view_layer.objects.active
        return (obj is not None) and ('sfmflow_model_uuid' in obj) and obj.select_get()

    # ==============================================================================================
    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set:  # pylint: disable=unused-argument
        """Init operator data when invoked.

        Arguments:
            context {bpy.types.Context} -- invoke context
            event {bpy.types.Event} -- invoke event

        Returns:
            set -- enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        # set arguments for thread
        uuid = context.view_layer.objects.active['sfmflow_model_uuid']
        self.heavy_load_args = (str(uuid), )
        #
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    # ==============================================================================================
    def heavy_load(self, model_uuid: str, **kwargs: Dict) -> None:   # pylint: disable=arguments-differ
        """Align 3D reconstruction to the ground truth geometry.
        This workload is executed in a dedicated thread.

        Returns:
            set -- {'FINISHED', ‘CANCELLED’}
        """
        model = ReconstructionsManager.get_model_by_uuid(model_uuid)
        logger.info("Starting reconstructed model registration...")
        #
        if self.alignment_mode == "cloud_align.matrix":   # use user's matrix to align
            self.progress_string = "Aligning model using matrix"
            align_matrix = Matrix((self.alignment_matrix_row1, self.alignment_matrix_row2,
                                   self.alignment_matrix_row3, self.alignment_matrix_row4))
            model.apply_registration_matrix(align_matrix)
            msg = f"Applied registration matrix to model `{model.name}`."
        elif self.alignment_mode == "cloud_align.auto":   # use ICP alignment
            self.progress_string = "Aligning model using ICP"
            if not self.use_custom_params:
                error = model.register_model(ReconstructionsManager.gt_points, ReconstructionsManager.gt_kdtree)
            else:
                error = model.register_model(ReconstructionsManager.gt_points, ReconstructionsManager.gt_kdtree,
                                             max_iterations=self.max_iterations, samples=self.samples_percentage,
                                             use_filtered_cloud=self.use_filtered_cloud)
            msg = f"Reconstructed model `{model.name}` registered to ground truth (mean error: {error:.3f})."
        else:
            msg = f"Unknown alignment mode: {self.alignment_mode}"
            self.progress_string = msg
            self.exit_code = -1
            logger.error(msg)
            return
        #
        self.progress_string = msg
        self.exit_code = 0
        logger.info(msg)
