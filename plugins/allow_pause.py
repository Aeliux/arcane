# ba_meta require api 8

import babase as ba
import bascenev1 as bs


def new_pause(*args) -> None:
    activity: bs.Activity | None = bs.get_foreground_host_activity()
    if (
        activity is not None
        and activity.allow_pausing
    ):
        from babase import Lstr
        from bascenev1 import NodeActor

        with activity.context:
            globs = activity.globalsnode
            if not globs.paused:
                bs.getsound("refWhistle").play()
                globs.paused = True

            activity.paused_text = NodeActor(
                bs.newnode(
                    "text",
                    attrs={
                        "text": Lstr(resource="pausedByHostText"),
                        "client_only": True,
                        "flatness": 1.0,
                        "h_align": "center",
                    },
                )
            )


# ba_meta export plugin
class AllowPause(ba.Plugin):
    def on_app_running(self):
        ba.app.classic.pause = new_pause
