from dataclasses import dataclass
from typing import Protocol
from _workflow import Workflow
from napari import Viewer
from _workflow import _layer_name_or_value

class Action(Protocol):
    def execute() -> None:
        ...
    
    def undo() -> None:
        ...

    def redo() -> None:
        ...


@dataclass
class Undo_redo_controller:
    undo_stack: list = []
    redo_stack: list = []

    def execute(self,action: Action) -> None:
        action.execute()
        self.redo_stack.clear()
        self.undo_stack.append(action)

    def undo(self) -> None:
        if not self.undo_stack:
            return
        action = self.undo_stack.pop()
        action.undo()
        self.redo_stack.append(action)

    def redo(self) -> None:
        if not self.redo_stack:
            return
        action = self.redo_stack.pop()
        action.redo()
        self.undo_stack.append(action)


class Update_workflow_step:
    def __init__(self,workflow: Workflow, viewer: Viewer, target_layer, function: function, *args, **kwargs) -> None:
        self.workflow = workflow
        self.viewer = viewer
        self.target_layer = target_layer
        self.function = function
        self.args = args
        self.kwargs = kwargs

        try:
            self.old_task = workflow._tasks[target_layer.name]
        except KeyError:
            self.old_task = None

    def execute(self):
        # basically what the update function was before
        args = list(self.args)
        for i in range(len(args)):
            args[i] = _layer_name_or_value(args[i], self.viewer)
        if isinstance(args[-1], Viewer):
            args = args[:-1]
        args = tuple(args)
        self.workflow.set(self.target_layer.name, function, *args, **self.kwargs)

        # plus the remove zombies function
        layer_names = [layer.name for layer in self.viewer.layers]
        self.removed_layers = {k:v for k,v in self.workflow._tasks.items() if k not in layer_names}
        self.workflow.remove_all_except(layer_names)

    def undo(self):
        # set the workflow step to what it was before
        # delete the new wf step if one was created
        if not self.old_task:
            self.workflow.remove(self.target_layer.name)

            # remove zombies undone
            for k, v in self.removed_layers.items():
                self.workflow._tasks[k] = v

        # change the values to the old ones otherwise
        else:
            self.workflow[self.target_layer.name] = self.old_task

    def redo(self):
        #for now just the copied execute
        args = list(self.args)
        for i in range(len(args)):
            args[i] = _layer_name_or_value(args[i], self.viewer)
        if isinstance(args[-1], Viewer):
            args = args[:-1]
        args = tuple(args)
        self.workflow.set(self.target_layer.name, function, *args, **self.kwargs)

        # remove zombies
        layer_names = [layer.name for layer in self.viewer.layers]
        self.removed_layers = {k:v for k,v in self.workflow._tasks.items() if k not in layer_names}
        self.workflow.remove_all_except(layer_names)


class Layer_removed:
    def __init__(self, workflow: Workflow, name: str) -> None:
        self.workflow = workflow
        self.name = name
        try:
            self.old_task = workflow._tasks[name]
        except KeyError:
            self.old_task = None

    def execute(self) -> None:
        self.workflow.remove(self.name)
    
    def undo(self):
        if not self.old_task:
            return
        self.workflow._tasks[self.name] = self.old_task

    def redo(self):
        self.workflow.remove(self.name)
