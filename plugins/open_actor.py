# ba_meta require api 8

import babase as ba
import bascenev1 as bs
from bascenev1lib.actor import bomb, powerupbox, spaz
from bascenev1lib.actor.spaz import Spaz, SpazFactory, POWERUP_WEAR_OFF_TIME

from bascenev1lib.actor.powerupbox import (
    PowerupBox,
    PowerupBoxFactory,
    DEFAULT_POWERUP_INTERVAL,
)

from typing import Callable, Sequence, Any
import random

early_tasks: dict[str, list[Callable]] = {}
late_tasks: dict[str, list[Callable]] = {}

hooks_loaded = False
registered_ids: list[str] = []


def inject_task(scope: str, function: Callable, taskType: str = "early"):
    register_scope(scope)

    if taskType == "early":
        early_tasks[scope].append(function)
    elif taskType == "late":
        late_tasks[scope].append(function)
    else:
        raise ValueError("Task scope must be early or late.")


def safe_inject_task(id: str, scope: str, function: Callable, taskType: str = "early"):
    if id not in registered_ids:
        inject_task(scope, function, taskType)
        registered_ids.append(id)


def register_scope(scope: str, ignore_check=False):
    print_msg = False
    if early_tasks.get(scope) is None:
        print_msg = True
        early_tasks[scope] = []

    if late_tasks.get(scope) is None:
        print_msg = True
        late_tasks[scope] = []

    if print_msg and not ignore_check and False:
        print(f"scope {scope} not found, creating new scope!")


class PowerupType:
    name: str
    texture_name: str
    mesh_name: str | None
    interval: float
    scale: float
    rarity: int
    frequency: int

    def __init__(
        self,
        name: str,
        texturename: str,
        meshname: str | None = None,
        interval: float = DEFAULT_POWERUP_INTERVAL,
        scale: float = 1.0,
        rarity: int = 1,
        frequency: int = 1,
    ) -> None:
        self.name = name
        self.texture_name = texturename
        self.mesh_name = meshname
        self.interval = interval
        self.scale = scale
        self.rarity = rarity
        self.frequency = frequency

    def _register_factory(self, factory: Any) -> None:
        if not hasattr(factory, "open_powerup"):
            factory.open_powerup = {}

    def get_texture(self) -> bs.Texture:
        factory: Any = PowerupBoxFactory.get()  # suppress errors
        self._register_factory(factory)
        tex = factory.open_powerup.get(f"tex_{self.texture_name}", None)
        if tex is None:
            tex = factory.open_powerup[f"tex_{self.texture_name}"] = bs.gettexture(
                self.texture_name
            )
        return tex

    def get_mesh(self) -> bs.Mesh:
        factory: Any = PowerupBoxFactory.get()  # suppress errors
        self._register_factory(factory)
        if self.mesh_name is None:
            return factory.mesh
        mesh = factory.open_powerup.get(f"mesh_{self.mesh_name}", None)
        if mesh is None:
            mesh = factory.open_powerup[f"mesh_{self.mesh_name}"] = bs.getmesh(
                self.mesh_name
            )
        return mesh

    def on_apply(self, spaz: Spaz):
        """
        Called when the powerup is consumed by a spaz
        """
        pass

    def on_init(
        self,
        object: PowerupBox,
        position: Sequence[float] = (0.0, 1.0, 0.0),
        poweruptype: str = "triple_bombs",
        expire: bool = True,
    ):
        """
        Called before creating the powerup node
        """
        pass

    def on_create(self, object: PowerupBox):
        """
        Called right after creating the powerup box node
        The node is accessible in object.node
        """
        pass


class OpenPowerupBox:
    powerups: dict[str, PowerupType] = {}
    default_powerup: Callable

    @staticmethod
    def powerup_task(
        self: PowerupBox,  # type: ignore
        position: Sequence[float] = (0.0, 1.0, 0.0),
        poweruptype: str = "triple_bombs",
        expire: bool = True,
    ):
        # call Actor.__init__
        super(PowerupBox, self).__init__()

        shared = powerupbox.SharedObjects.get()
        factory = PowerupBoxFactory.get()
        self.poweruptype = poweruptype
        self._powersgiven = False

        mesh = factory.mesh
        interval = DEFAULT_POWERUP_INTERVAL
        scale = 1.0

        if poweruptype == "triple_bombs":
            tex = factory.tex_bomb
        elif poweruptype == "punch":
            tex = factory.tex_punch
        elif poweruptype == "ice_bombs":
            tex = factory.tex_ice_bombs
        elif poweruptype == "impact_bombs":
            tex = factory.tex_impact_bombs
        elif poweruptype == "land_mines":
            tex = factory.tex_land_mines
        elif poweruptype == "sticky_bombs":
            tex = factory.tex_sticky_bombs
        elif poweruptype == "shield":
            tex = factory.tex_shield
        elif poweruptype == "health":
            tex = factory.tex_health
        elif poweruptype == "curse":
            tex = factory.tex_curse
        elif poweruptype in OpenPowerupBox.powerups:
            _obj = OpenPowerupBox.powerups[poweruptype]
            tex = _obj.get_texture()
            mesh = _obj.get_mesh()
            interval = _obj.interval
            scale = _obj.scale
            # call on_init
            _obj.on_init(self, position, poweruptype, expire)
        else:
            raise ValueError("invalid poweruptype: " + str(poweruptype))

        if len(position) != 3:
            raise ValueError("expected 3 floats for position")

        self.node = bs.newnode(
            "prop",
            delegate=self,
            attrs={
                "body": "box",
                "position": position,
                "mesh": mesh,
                "light_mesh": factory.mesh_simple,
                "shadow_size": 0.5,
                "color_texture": tex,
                "reflection": "powerup",
                "reflection_scale": [1.0],
                "materials": (factory.powerup_material, shared.object_material),
            },
        )

        # call on_create
        if poweruptype in OpenPowerupBox.powerups:
            OpenPowerupBox.powerups[poweruptype].on_create(self)

        # Animate in.
        curve = bs.animate(self.node, "mesh_scale", {0: 0, 0.14: 1.6, 0.2: scale})
        bs.timer(0.2, curve.delete)

        if expire:
            bs.timer(
                interval - 2.5,
                bs.WeakCall(self._start_flashing),
            )
            bs.timer(
                interval - 1.0,
                bs.WeakCall(self.handlemessage, bs.DieMessage()),
            )

    @staticmethod
    def powerup_handle(self: Spaz, msg: bs.PowerupMessage) -> bool:
        if isinstance(msg, bs.PowerupMessage):
            if self._dead or not self.node:
                return True
            if self.pick_up_powerup_callback is not None:
                self.pick_up_powerup_callback(self)
            if msg.poweruptype == "triple_bombs":
                tex = PowerupBoxFactory.get().tex_bomb
                self._flash_billboard(tex)
                self.set_bomb_count(3)
                if self.powerups_expire:
                    self.node.mini_billboard_1_texture = tex
                    t_ms = int(bs.time() * 1000.0)
                    assert isinstance(t_ms, int)
                    self.node.mini_billboard_1_start_time = t_ms
                    self.node.mini_billboard_1_end_time = t_ms + POWERUP_WEAR_OFF_TIME
                    self._multi_bomb_wear_off_flash_timer = bs.Timer(
                        (POWERUP_WEAR_OFF_TIME - 2000) / 1000.0,
                        bs.WeakCall(self._multi_bomb_wear_off_flash),
                    )
                    self._multi_bomb_wear_off_timer = bs.Timer(
                        POWERUP_WEAR_OFF_TIME / 1000.0,
                        bs.WeakCall(self._multi_bomb_wear_off),
                    )
            elif msg.poweruptype == "land_mines":
                self.set_land_mine_count(min(self.land_mine_count + 3, 3))
            elif msg.poweruptype == "impact_bombs":
                self.bomb_type = "impact"
                tex = self._get_bomb_type_tex()
                self._flash_billboard(tex)
                if self.powerups_expire:
                    self.node.mini_billboard_2_texture = tex
                    t_ms = int(bs.time() * 1000.0)
                    assert isinstance(t_ms, int)
                    self.node.mini_billboard_2_start_time = t_ms
                    self.node.mini_billboard_2_end_time = t_ms + POWERUP_WEAR_OFF_TIME
                    self._bomb_wear_off_flash_timer = bs.Timer(
                        (POWERUP_WEAR_OFF_TIME - 2000) / 1000.0,
                        bs.WeakCall(self._bomb_wear_off_flash),
                    )
                    self._bomb_wear_off_timer = bs.Timer(
                        POWERUP_WEAR_OFF_TIME / 1000.0,
                        bs.WeakCall(self._bomb_wear_off),
                    )
            elif msg.poweruptype == "sticky_bombs":
                self.bomb_type = "sticky"
                tex = self._get_bomb_type_tex()
                self._flash_billboard(tex)
                if self.powerups_expire:
                    self.node.mini_billboard_2_texture = tex
                    t_ms = int(bs.time() * 1000.0)
                    assert isinstance(t_ms, int)
                    self.node.mini_billboard_2_start_time = t_ms
                    self.node.mini_billboard_2_end_time = t_ms + POWERUP_WEAR_OFF_TIME
                    self._bomb_wear_off_flash_timer = bs.Timer(
                        (POWERUP_WEAR_OFF_TIME - 2000) / 1000.0,
                        bs.WeakCall(self._bomb_wear_off_flash),
                    )
                    self._bomb_wear_off_timer = bs.Timer(
                        POWERUP_WEAR_OFF_TIME / 1000.0,
                        bs.WeakCall(self._bomb_wear_off),
                    )
            elif msg.poweruptype == "punch":
                tex = PowerupBoxFactory.get().tex_punch
                self._flash_billboard(tex)
                self.equip_boxing_gloves()
                if self.powerups_expire and not self.default_boxing_gloves:
                    self.node.boxing_gloves_flashing = False
                    self.node.mini_billboard_3_texture = tex
                    t_ms = int(bs.time() * 1000.0)
                    assert isinstance(t_ms, int)
                    self.node.mini_billboard_3_start_time = t_ms
                    self.node.mini_billboard_3_end_time = t_ms + POWERUP_WEAR_OFF_TIME
                    self._boxing_gloves_wear_off_flash_timer = bs.Timer(
                        (POWERUP_WEAR_OFF_TIME - 2000) / 1000.0,
                        bs.WeakCall(self._gloves_wear_off_flash),
                    )
                    self._boxing_gloves_wear_off_timer = bs.Timer(
                        POWERUP_WEAR_OFF_TIME / 1000.0,
                        bs.WeakCall(self._gloves_wear_off),
                    )
            elif msg.poweruptype == "shield":
                factory = SpazFactory.get()

                # Let's allow powerup-equipped shields to lose hp over time.
                self.equip_shields(decay=factory.shield_decay_rate > 0)
            elif msg.poweruptype == "curse":
                self.curse()
            elif msg.poweruptype == "ice_bombs":
                self.bomb_type = "ice"
                tex = self._get_bomb_type_tex()
                self._flash_billboard(tex)
                if self.powerups_expire:
                    self.node.mini_billboard_2_texture = tex
                    t_ms = int(bs.time() * 1000.0)
                    assert isinstance(t_ms, int)
                    self.node.mini_billboard_2_start_time = t_ms
                    self.node.mini_billboard_2_end_time = t_ms + POWERUP_WEAR_OFF_TIME
                    self._bomb_wear_off_flash_timer = bs.Timer(
                        (POWERUP_WEAR_OFF_TIME - 2000) / 1000.0,
                        bs.WeakCall(self._bomb_wear_off_flash),
                    )
                    self._bomb_wear_off_timer = bs.Timer(
                        POWERUP_WEAR_OFF_TIME / 1000.0,
                        bs.WeakCall(self._bomb_wear_off),
                    )
            elif msg.poweruptype == "health":
                if self._cursed:
                    self._cursed = False

                    # Remove cursed material.
                    factory = SpazFactory.get()
                    for attr in ["materials", "roller_materials"]:
                        materials = getattr(self.node, attr)
                        if factory.curse_material in materials:
                            setattr(
                                self.node,
                                attr,
                                tuple(
                                    m for m in materials if m != factory.curse_material
                                ),
                            )
                    self.node.curse_death_time = 0
                self.hitpoints = self.hitpoints_max
                self._flash_billboard(PowerupBoxFactory.get().tex_health)
                self.node.hurt = 0
                self._last_hit_time = None
                self._num_times_hit = 0
            elif msg.poweruptype in OpenPowerupBox.powerups:
                OpenPowerupBox.powerups[msg.poweruptype].on_apply(self)

            self.node.handlemessage("flash")
            if msg.sourcenode:
                msg.sourcenode.handlemessage(bs.PowerupAcceptMessage())
            return True
        else:
            return False

    @classmethod
    def get_powerups(cls) -> Sequence[tuple[str, int]]:
        dlist = cls.default_powerup()
        extra: list[tuple[str, int]] = []

        for p in cls.powerups.values():
            if p.rarity == 1:
                extra.append(
                    (p.name, p.frequency),
                )
            elif p.rarity > 1:
                if random.randint(1, p.rarity) == p.rarity:
                    extra.append(
                        (p.name, p.frequency),
                    )

        return dlist + tuple(extra)

    @classmethod
    def register_powerup(cls, powerup: PowerupType):
        if powerup.name not in cls.powerups:
            cls.powerups[powerup.name] = powerup


# ba_meta export babase.Plugin
class OpenActor(ba.Plugin):
    @staticmethod
    def replace(scope: str, function: Callable):
        register_scope(scope, True)

        def wrapper(*args, **kwargs):
            refuse_run = False
            res = None

            for t in early_tasks[scope]:
                if t(*args, **kwargs):
                    refuse_run = True

            if not refuse_run:
                res = function(*args, **kwargs)

            for t in late_tasks[scope]:
                t(*args, _result=res, **kwargs)

        return wrapper

    def on_app_running(self) -> None:
        global hooks_loaded

        if not hooks_loaded:
            bomb.Bomb.__init__ = self.replace("bomb", bomb.Bomb.__init__)

            bomb.Blast.__init__ = self.replace("blast", bomb.Blast.__init__)

            powerupbox.PowerupBox.__init__ = OpenPowerupBox.powerup_task
            OpenPowerupBox.default_powerup = bs.get_default_powerup_distribution
            bs.get_default_powerup_distribution = OpenPowerupBox.get_powerups

            spaz.Spaz.__init__ = self.replace("spaz", spaz.Spaz.__init__)
            spaz.Spaz.handlemessage = self.replace(
                "spaz_handler", spaz.Spaz.handlemessage
            )

            hooks_loaded = True

        safe_inject_task("powerup_apply", "spaz_handler", OpenPowerupBox.powerup_handle)
