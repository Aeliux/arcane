# ba_meta require api 8

import babase
from bascenev1lib.actor import bomb, powerupbox, spaz

from typing import Callable

early_tasks: dict[str, list[Callable]] = {}
late_tasks: dict[str, list[Callable]] = {}


def inject_task(scope: str, function: Callable, taskType: str = "early"):
    register_scope(scope)

    if taskType == "early":
        early_tasks[scope].append(function)
    elif taskType == "late":
        late_tasks[scope].append(function)
    else:
        raise ValueError("Task scope must be early or late.")


def register_scope(scope: str):
    if early_tasks.get(scope) is None:
        early_tasks[scope] = []

    if late_tasks.get(scope) is None:
        late_tasks[scope] = []


# ba_meta export babase.Plugin
class OpenActor(babase.Plugin):
    @staticmethod
    def replace(scope: str, function: Callable):
        register_scope(scope)

        def wrapper(*args, **kwargs):
            refuse_run = False

            for t in early_tasks[scope]:
                if t(*args, **kwargs):
                    refuse_run = True

            if not refuse_run:
                function(*args, **kwargs)

            for t in late_tasks[scope]:
                t(*args, **kwargs)

        return wrapper

    def on_app_running(self) -> None:
        bomb.Bomb.__init__ = self.replace(
            "bomb", bomb.Bomb.__init__
        )
        bomb.Bomb.handlemessage = self.replace(
            "bomb_handler", bomb.Bomb.handlemessage
        )

        powerupbox.PowerupBox.__init__ = self.replace(
            "powerupbox", powerupbox.PowerupBox.__init__
        )
        powerupbox.PowerupBox.handlemessage = self.replace(
            "powerupbox_handler", powerupbox.PowerupBox.handlemessage
        )

        spaz.Spaz.__init__ = self.replace(
            "spaz", spaz.Spaz.__init__
        )
        spaz.Spaz.handlemessage = self.replace(
            "spaz_handler", spaz.Spaz.handlemessage
        )
