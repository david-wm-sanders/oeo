import logging
import json
from pathlib import Path
from enum import Enum, unique
from .element import Element

logger = logging.getLogger(__name__)


@unique
class MoveCategory(Enum):
    Physical = 1
    Special = 2
    Status = 3

    def __repr__(self):
        return "MoveCategory.%s" % self.name


class Move(object):
    data_root = Path("./data/moves")

    def __init__(self, name, element, category, power, accuracy, makes_contact, priority, stages):
        self._name = name
        try:
            self._element = Element[element]
        except KeyError:
            logger.error(f"{element} is not a valid Element")
            raise Exception(f"{element} is not a valid Element")
        try:
            self._category = MoveCategory[category]
        except KeyError:
            logger.error(f"{category} is not a valid MoveCategory")
            raise Exception(f"{category} is not a valid MoveCategory")
        self._power = power
        self._accuracy = accuracy
        self._makes_contact = makes_contact
        self._priority = priority
        self._stages = stages

    @property
    def name(self):
        return self._name

    @property
    def element(self):
        return self._element

    @property
    def category(self):
        return self._category

    @property
    def power(self):
        return self._power

    @property
    def accuracy(self):
        return self._accuracy

    @property
    def makes_contact(self):
        return self._makes_contact

    @property
    def priority(self):
        return self._priority

    @property
    def stages(self):
        return self._stages

    def __repr__(self):
        return "Move(%r, %r, %r, Power:%r, Accuracy:%r, MakesContact:%r, Stages:%r, Priority:%r)" \
               % (self._name, self._element, self._category, self._power, self._accuracy,
                  self._makes_contact, self._stages, self._priority)

    @classmethod
    def from_json_dict(cls, move_data):
        try:
            move_name = move_data["name"]
            element = move_data["element"]
            category = move_data["category"]
            power = move_data["power"]
            accuracy = move_data["accuracy"]
            makes_contact = move_data["makes_contact"]
            priority = move_data.get("priority", 0)
            stages = move_data.get("stages", [])
        except KeyError as e:
            logger.error(f"Move data for '{move_name}' is missing a value for {e}")
            raise Exception(f"Move data for '{move_name}' is missing a value for {e}") from e
        else:
            return cls(move_name, element, category, power, accuracy, makes_contact, priority, stages)

    @staticmethod
    def load_moves(list_moves):
        moves = {}
        for move_name in list_moves:
            m = Move.data_root / f"{move_name}.json"
            if m.exists():
                with m.open() as f:
                    move = json.load(f, object_hook=Move.from_json_dict)
                    if move:
                        moves[move_name] = move
            else:
                raise Exception(f"{m} does not exist")
        return moves
