# ba_meta require api 8

from bascenev1lib.actor.spazfactory import SpazFactory
from bascenev1lib.actor.spaz import Spaz
import bascenev1 as bs
import babase

from open_actor import safe_inject_task

from typing import Any, Sequence
import random


def hit_handler(self: Spaz, msg: Any) -> bool:
    if isinstance(msg, bs.HitMessage):
        if not self.node:
            return False
        if self.node.invincible:
            SpazFactory.get().block_sound.play(
                1.0,
                position=self.node.position,
            )
            return True

        # If we were recently hit, don't count this as another.
        # (so punch flurries and bomb pileups essentially count as 1 hit)
        local_time = int(bs.time() * 1000.0)
        assert isinstance(local_time, int)
        if self._last_hit_time is None or local_time - self._last_hit_time > 1000:
            self._num_times_hit += 1
            self._last_hit_time = local_time

        mag = msg.magnitude * self.impact_scale
        velocity_mag = msg.velocity_magnitude * self.impact_scale
        damage_scale = 0.22

        # If they've got a shield, deliver it to that instead.
        if self.shield:
            if msg.flat_damage:
                damage = msg.flat_damage * self.impact_scale
            else:
                # Hit our spaz with an impulse but tell it to only return
                # theoretical damage; not apply the impulse.
                assert msg.force_direction is not None
                self.node.handlemessage(
                    "impulse",
                    msg.pos[0],
                    msg.pos[1],
                    msg.pos[2],
                    msg.velocity[0],
                    msg.velocity[1],
                    msg.velocity[2],
                    mag,
                    velocity_mag,
                    msg.radius,
                    1,
                    msg.force_direction[0],
                    msg.force_direction[1],
                    msg.force_direction[2],
                )
                damage = damage_scale * self.node.damage

            assert self.shield_hitpoints is not None
            self.shield_hitpoints -= int(damage)
            self.shield.hurt = (
                1.0 - float(self.shield_hitpoints) / self.shield_hitpoints_max
            )

            # Its a cleaner event if a hit just kills the shield
            # without damaging the player.
            # However, massive damage events should still be able to
            # damage the player. This hopefully gives us a happy medium.
            max_spillover = SpazFactory.get().max_shield_spillover_damage
            if self.shield_hitpoints <= 0:
                # FIXME: Transition out perhaps?
                self.shield.delete()
                self.shield = None
                SpazFactory.get().shield_down_sound.play(
                    1.0,
                    position=self.node.position,
                )

                # Emit some cool looking sparks when the shield dies.
                npos = self.node.position
                bs.emitfx(
                    position=(npos[0], npos[1] + 0.9, npos[2]),
                    velocity=self.node.velocity,
                    count=random.randrange(20, 30),
                    scale=1.0,
                    spread=0.6,
                    chunk_type="spark",
                )

            else:
                SpazFactory.get().shield_hit_sound.play(
                    0.5,
                    position=self.node.position,
                )

            # Emit some cool looking sparks on shield hit.
            assert msg.force_direction is not None
            bs.emitfx(
                position=msg.pos,
                velocity=(
                    msg.force_direction[0] * 1.0,
                    msg.force_direction[1] * 1.0,
                    msg.force_direction[2] * 1.0,
                ),
                count=min(30, 5 + int(damage * 0.005)),
                scale=0.5,
                spread=0.3,
                chunk_type="spark",
            )

            # If they passed our spillover threshold,
            # pass damage along to spaz.
            if self.shield_hitpoints <= -max_spillover:
                leftover_damage = -max_spillover - self.shield_hitpoints
                shield_leftover_ratio = leftover_damage / damage

                # Scale down the magnitudes applied to spaz accordingly.
                mag *= shield_leftover_ratio
                velocity_mag *= shield_leftover_ratio
            else:
                return True  # Good job shield!
        else:
            shield_leftover_ratio = 1.0

        if msg.flat_damage:
            damage = int(msg.flat_damage * self.impact_scale * shield_leftover_ratio)
        else:
            # Hit it with an impulse and get the resulting damage.
            assert msg.force_direction is not None
            self.node.handlemessage(
                "impulse",
                msg.pos[0],
                msg.pos[1],
                msg.pos[2],
                msg.velocity[0],
                msg.velocity[1],
                msg.velocity[2],
                mag,
                velocity_mag,
                msg.radius,
                0,
                msg.force_direction[0],
                msg.force_direction[1],
                msg.force_direction[2],
            )

            damage = int(damage_scale * self.node.damage)
        self.node.handlemessage("hurt_sound")

        # Play punch impact sound based on damage if it was a punch.
        if msg.hit_type == "punch":
            self.on_punched(damage)

            source = msg.get_source_player(bs.Player)

            if source is not None and source.exists():
                self.activity.stats.player_scored(
                    source,
                    damage // 100,
                    display=damage >= 500,
                    screenmessage=False
                )

            # If damage was significant, lets show it.
            if damage >= 350:
                assert msg.force_direction is not None
                show_damage_count(
                    "-" + str(int(damage / 10)) + "%",
                    msg.pos,
                    msg.force_direction,
                    self.node.color
                )

            # Let's always add in a super-punch sound with boxing
            # gloves just to differentiate them.
            if msg.hit_subtype == "super_punch":
                SpazFactory.get().punch_sound_stronger.play(
                    1.0,
                    position=self.node.position,
                )
            if damage >= 500:
                sounds = SpazFactory.get().punch_sound_strong
                sound = sounds[random.randrange(len(sounds))]
            elif damage >= 100:
                sound = SpazFactory.get().punch_sound
            else:
                sound = SpazFactory.get().punch_sound_weak
            sound.play(1.0, position=self.node.position)

            # Throw up some chunks.
            assert msg.force_direction is not None
            bs.emitfx(
                position=msg.pos,
                velocity=(
                    msg.force_direction[0] * 0.5,
                    msg.force_direction[1] * 0.5,
                    msg.force_direction[2] * 0.5,
                ),
                count=min(10, 1 + int(damage * 0.0025)),
                scale=0.3,
                spread=0.03,
            )

            bs.emitfx(
                position=msg.pos,
                chunk_type="sweat",
                velocity=(
                    msg.force_direction[0] * 1.3,
                    msg.force_direction[1] * 1.3 + 5.0,
                    msg.force_direction[2] * 1.3,
                ),
                count=min(30, 1 + int(damage * 0.04)),
                scale=0.9,
                spread=0.28,
            )

            # Momentary flash.
            hurtiness = damage * 0.003
            punchpos = (
                msg.pos[0] + msg.force_direction[0] * 0.02,
                msg.pos[1] + msg.force_direction[1] * 0.02,
                msg.pos[2] + msg.force_direction[2] * 0.02,
            )
            flash_color = (1.0, 0.8, 0.4)
            light = bs.newnode(
                "light",
                attrs={
                    "position": punchpos,
                    "radius": 0.12 + hurtiness * 0.12,
                    "intensity": 0.3 * (1.0 + 1.0 * hurtiness),
                    "height_attenuated": False,
                    "color": flash_color,
                },
            )
            bs.timer(0.06, light.delete)

            flash = bs.newnode(
                "flash",
                attrs={
                    "position": punchpos,
                    "size": 0.17 + 0.17 * hurtiness,
                    "color": flash_color,
                },
            )
            bs.timer(0.06, flash.delete)

        if msg.hit_type == "impact":
            assert msg.force_direction is not None
            bs.emitfx(
                position=msg.pos,
                velocity=(
                    msg.force_direction[0] * 2.0,
                    msg.force_direction[1] * 2.0,
                    msg.force_direction[2] * 2.0,
                ),
                count=min(10, 1 + int(damage * 0.01)),
                scale=0.4,
                spread=0.1,
            )
        if self.hitpoints > 0:
            # It's kinda crappy to die from impacts, so lets reduce
            # impact damage by a reasonable amount *if* it'll keep us alive
            if msg.hit_type == "impact" and damage > self.hitpoints:
                # Drop damage to whatever puts us at 10 hit points,
                # or 200 less than it used to be whichever is greater
                # (so it *can* still kill us if its high enough)
                newdamage = max(damage - 200, self.hitpoints - 10)
                damage = newdamage
            self.node.handlemessage("flash")

            # If we're holding something, drop it.
            if damage > 0.0 and self.node.hold_node:
                self.node.hold_node = None
            self.hitpoints -= damage
            self.node.hurt = 1.0 - float(self.hitpoints) / self.hitpoints_max

            # If we're cursed, *any* damage blows us up.
            if self._cursed and damage > 0:
                bs.timer(
                    0.05,
                    bs.WeakCall(self.curse_explode, msg.get_source_player(bs.Player)),
                )

            # If we're frozen, shatter.. otherwise die if we hit zero
            if self.frozen and (damage > 200 or self.hitpoints <= 0):
                self.shatter()
            elif self.hitpoints <= 0:
                self.node.handlemessage(bs.DieMessage(how=bs.DeathType.IMPACT))

        # If we're dead, take a look at the smoothed damage value
        # (which gives us a smoothed average of recent damage) and shatter
        # us if its grown high enough.
        if self.hitpoints <= 0:
            damage_avg = self.node.damage_smoothed * damage_scale
            if damage_avg >= 1000:
                self.shatter()
        return True
    else:
        return False


def show_damage_count(
    damage: str, position: Sequence[float], direction: Sequence[float], color: Sequence[float]
) -> None:
    """Pop up a damage count at a position in space.

    Category: **Gameplay Functions**
    """
    lifespan = 1.0
    app = babase.app

    # FIXME: Should never vary game elements based on local config.
    #  (connected clients may have differing configs so they won't
    #  get the intended results).
    assert app.classic is not None
    do_big = app.ui_v1.uiscale is babase.UIScale.SMALL or app.vr_mode
    scale = 0.015 if do_big else 0.01
    damage_value = int(damage[1:-1])
    txtnode = bs.newnode(
        'text',
        attrs={
            'text': damage,
            'in_world': True,
            'h_align': 'center',
            'flatness': 1.0,
            'shadow': 1.0 if do_big else 0.7,
            'color': color,
            'scale': scale * (damage_value / 35),
        },
    )
    # Translate upward.
    tcombine = bs.newnode('combine', owner=txtnode, attrs={'size': 3})
    tcombine.connectattr('output', txtnode, 'position')
    v_vals = []
    pval = 0.0
    vval = 0.07
    count = 6
    for i in range(count):
        v_vals.append((float(i) / count, pval))
        pval += vval
        vval *= 0.5
    p_start = position[0]
    p_dir = direction[0]
    bs.animate(
        tcombine,
        'input0',
        {i[0] * lifespan: p_start + p_dir * i[1] for i in v_vals},
    )
    p_start = position[1]
    p_dir = direction[1]
    bs.animate(
        tcombine,
        'input1',
        {i[0] * lifespan: p_start + p_dir * i[1] for i in v_vals},
    )
    p_start = position[2]
    p_dir = direction[2]
    bs.animate(
        tcombine,
        'input2',
        {i[0] * lifespan: p_start + p_dir * i[1] for i in v_vals},
    )
    bs.animate(txtnode, 'opacity', {0.7 * lifespan: 1.0, lifespan: 0.0})
    bs.timer(lifespan, txtnode.delete)


# ba_meta export babase.Plugin
class BetterFight(babase.Plugin):
    def on_app_running(self) -> None:
        safe_inject_task("punch_handler", "spaz_handler", hit_handler, "early")
