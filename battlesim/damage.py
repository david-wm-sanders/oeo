import logging
import math
import random
import json
from pathlib import Path
from core import Oeo, Element, Move, MoveCategory

logger = logging.getLogger(__name__)


def get_damage_function(df_id):
    if df_id == "Standard":
        return calculate_standard_damage
    else:
        raise Exception("No other damage functions currently implemented")


def calculate_standard_damage(user, move, target):
    """
    Calculates damage using the formula:

    Damage = ( ( 2 x user.lvl + 10 / 250 ) x ( user.att|sp.att / target.def|sp.def ) x move.power + 2 ) x Modifier
    Modifier = SameTypeAttackBonus x ElementEffectiveness x CriticalModifier x Other x (random(0.85, 1.05))
    """
    logger.debug("Calculating damage using standard formula...")
    assert isinstance(user, Oeo), "user is not an Oeo"
    assert isinstance(move, Move), "move is not a Move"
    assert isinstance(target, Oeo), "target is not an Oeo"

    stab = _same_type_attack_bonus(move.element, user.elements)
    user_elements = "/".join([str(e.name) for e in user.elements])
    logger.debug(f"STAB for {user_elements} Oeo using a {move.element.name} Move = {stab}")

    element_effectiveness = _element_effectiveness(move.element, target.elements)
    target_elements = "/".join([str(e.name) for e in target.elements])
    logger.debug(f"Element Effectiveness of a {move.element.name} Move against a {target_elements} Oeo = {element_effectiveness}")

    critical_modifier = _critical_modifier(user, move, target)
    logger.debug(f"Critical Modifier = {critical_modifier}")

    other = _other_modifiers(user, move, target)
    logger.debug(f"Other Modifiers = {other}")

    randomness_factor = _randomness_factor(0.85, 1.0)
    logger.debug(f"Randomness Factor = {randomness_factor}")

    modifier = stab * element_effectiveness * critical_modifier * other * randomness_factor
    logger.debug(f"Damage Modifier = {stab}*{element_effectiveness}*{critical_modifier}*{other}*{randomness_factor} = {modifier}")

    if move.category == MoveCategory.Physical:
        attack = user.attack
        defence = target.defence
    elif move.category == MoveCategory.Special:
        attack = user.sp_attack
        defence = target.sp_defence
    else:
        raise Exception("Move is neither Physical nor Special - why is this function running?")
    raw_damage = ((2 * user.level + 10) / 250) * (attack / defence) * move.power + 2
    logger.debug(f"Raw Damage = (2*{user.level}+10)/250*({attack}/{defence})*{move.power}+2 = {raw_damage}")

    damage = math.floor(raw_damage * modifier)
    logger.debug(f"Damage = floor({raw_damage}*{modifier}) = {damage}")

    return damage


def _same_type_attack_bonus(move_element, user_elements):
    stab = 1.0
    for element in user_elements:
        if element == move_element:
            stab = 1.5
    return stab


def _element_effectiveness(move_element, target_elements):
    effectiveness_adjustments = _element_effectiveness_map[move_element.name]
    effectiveness = 1
    for element in target_elements:
        effectiveness *= effectiveness_adjustments.get(element.name, 1)
    return effectiveness


def _critical_modifier(user, move, target):
    return 1


def _other_modifiers(user, move, target):
    return 1


def _randomness_factor(a, b):
    return random.randint(a * 100, b * 100) / 100


def _load_element_effectiveness_map():
    p = Path("./data/battle/element_effectiveness.json")
    with p.open() as f:
        element_effectiveness_map = json.load(f)
    return element_effectiveness_map


_element_effectiveness_map = _load_element_effectiveness_map()
