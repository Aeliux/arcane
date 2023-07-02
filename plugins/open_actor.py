# ba_meta require api 8

import babase

# ba_meta export babase.Plugin
class OpenActor(babase.Plugin)
    def on_app_running(self) -> None:
        babase.screenmessage("Hello World!")