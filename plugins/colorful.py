# ba_meta require api 8

import babase as ba
import bascenev1 as bs

from bascenev1lib.actor.bomb import Blast
from open_actor import safe_inject_task

import random


def colored_blast(self: Blast, **kwargs):
    scorchRadius = self.radius
    s = bs.newnode('scorch', attrs={'position': self.node.position,
                   'size': scorchRadius*0.5, 'big': (self.blast_type == 'tnt')})
    s2 = bs.newnode('scorch', attrs={'position': self.node.position,
                    'size': scorchRadius*0.5, 'big': (self.blast_type == 'tnt')})
    s3 = bs.newnode('scorch', attrs={'position': self.node.position,
                    'size': scorchRadius*0.5, 'big': (self.blast_type == 'tnt')})
    if self.blast_type == 'ice':
        s.color = s2.color = s3.color = (1, 1, 1.5)
    else:
        s.color = s2.color = s3.color = (random.random(), random.random(), random.random())

    bs.animate(s, "presence", {3: 1, 13: 0})
    bs.animate(s2, "presence", {3: 1, 13: 0})
    bs.apptimer(13, s.delete)
    bs.apptimer(13, s2.delete)


# ba_meta export plugin
class Colorful(ba.Plugin):
    def on_app_running(self):
        safe_inject_task("colorful_blast", "blast", colored_blast, "late")
