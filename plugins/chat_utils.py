# This mod is wip and now it's npt wprking due to a codebase bug
# ba_meta require api 8

import babase as ba
import bascenev1 as bs
import bauiv1 as bui

from bauiv1lib import party
import bascenev1._hooks


def msg_receiver(msg: str, clientID: int):
    bs.screenmessage("message received")
    return 'yea boy'


def msg_receiver2(msg: str):
    bs.screenmessage("kiiir")


# ba_meta export plugin
class ChatUtils(ba.Plugin):
    def on_app_running(self):
        bascenev1._hooks.filter_chat_message = msg_receiver
        bascenev1._hooks.local_chat_message = msg_receiver2
