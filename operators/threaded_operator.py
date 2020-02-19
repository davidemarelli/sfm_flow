
import logging
import threading
from abc import abstractmethod
from typing import List, Tuple, Union

import bpy

logger = logging.getLogger(__name__)


class ThreadedOperator(bpy.types.Operator):
    """Template for operators that need to execute heavy computations.
    Base class, can be extended by operators that execute heavy tasks or
    require long-term background running.

    The sub-classes can define arguments for the execution using `heavy_load_args` and
    `heavy_load_kwargs`, those can be in the `invoke` method.

    See sfm_flow.operators.SFMFLOW_OT_align_reconstruction or
    sfm_flow.operators.SFMFLOW_OT_run_pipelines for sub-classing examples.
    """

    ################################################################################################
    # Constructor
    #

    # ==============================================================================================
    def __init__(self):

        # arguments to be passed to the thread when starting execution
        self.heavy_load_args = []     # type: Union[List, Tuple]

        # named arguments to be passed to the thread when starting execution
        self.heavy_load_kwargs = {}   # type: Dict

        # progress message to show in the status bar
        self.progress_string = None   # type: str

        # thread exit code, MUST be set before the end of `heavy_load()`. 0=execution ok, otherwise errors
        self.exit_code = None         # type: int

        # internal timer to push updates to the status bar
        self._timer = None            # type: bpy.types.Timer

        # internal counter to delay status bar message clear
        self._progress_delay_counter = 0   # type: int

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    def modal(self, context: bpy.types.Context, event: str) -> set:
        """Callback, used to update the status text in the status bar to show progress.

        Arguments:
            context {bpy.types.Context} -- current context
            event {str} -- event, currently reacts only on 'TIMER' events

        Returns:
            set -- {'PASS_THROUGH'}
        """
        if event.type == 'TIMER':
            if self.progress_string:
                context.workspace.status_text_set(self.progress_string)
            #
            if self.exit_code is not None:           # process terminated
                if self._progress_delay_counter > 10:
                    self.progress_string = None
                    self.exit_code = None
                    self._progress_delay_counter = 0
                    context.window_manager.event_timer_remove(self._timer)
                    context.workspace.status_text_set("")
                elif self._progress_delay_counter == 0 and self.exit_code != 0:
                    self.report({'ERROR'}, "Execution ended with error, see console.")
                self._progress_delay_counter += 1
        return {'PASS_THROUGH'}

    # ==============================================================================================
    def execute(self, context: bpy.types.Context) -> set:
        """Execute the heavy load in a separate thread.
        MUST be called by the sub-class as last operation: return super().execute(context)

        Arguments:
            context {bpy.types.Context} -- current context

        Returns:
            set -- {'RUNNING_MODAL'}
        """
        # setup timer to update the status bar
        self._timer = context.window_manager.event_timer_add(0.5, window=context.window)
        context.window_manager.modal_handler_add(self)
        #
        # start execution
        processThread = threading.Thread(target=self.heavy_load,
                                         args=self.heavy_load_args,
                                         kwargs=self.heavy_load_kwargs)
        processThread.start()
        return {'RUNNING_MODAL'}

    ################################################################################################
    # Heavy load method
    #

    # ==============================================================================================
    @abstractmethod
    def heavy_load(self, *args, **kwargs) -> None:
        """This method is executed in a separated thread and MUST be implemented by the sub-classes.

        Raises:
            NotImplementedError: if method is not implemented in the sub-classes
        """
        raise NotImplementedError("Abstract method, missing override!")
