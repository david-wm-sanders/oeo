import json
import logging
import math
import uuid
from pathlib import Path
from .element import Element
from .item import Item
from .stats import Stats

logger = logging.getLogger(__name__)


class Oeo(object):
    """
    Defines an oeo
    """
    data_root = Path("./data/oeo")

    def __init__(self, oeo_id, name, species, level, xp, current_hp,
                 ivs, evs, moves, status_conditions, held_item):
        assert isinstance(oeo_id, str), "oeo_id is not a string"
        assert isinstance(name, str), "name is not a string"
        assert isinstance(species, str), "species is not a string"
        assert isinstance(level, int), "level is not an int"
        assert isinstance(xp, int), "xp is not an int"
        assert isinstance(current_hp, (int, type(None))), "current_hp is not an int"
        assert isinstance(ivs, Stats), "ivs is not a Stats namedlist"
        assert isinstance(evs, Stats), "evs is not a Stats namedlist"
        assert isinstance(moves, list), "moves is not a list of moves"
        assert all(isinstance(m, str) for m in moves), "moves list contains items that are not strings"
        assert isinstance(status_conditions, (list, type(None))), "status_conditions is not a list of status conditions"
        assert isinstance(held_item, (Item, type(None))), "held_item is not an Item or None"

        self._oeo_id = oeo_id
        self._name = name
        self._species = species

        self._level = level
        self._xp = xp

        self._elements, self._base_stats = Oeo._load_oeo_base(self._species)

        self._ivs = ivs
        self._evs = evs

        if current_hp is None:
            self._current_hp = self.full_hp
        else:
            self.current_hp = current_hp

        self._moves = moves

        if status_conditions is None:
            self._status_conditions = []
        else:
            self._status_conditions = status_conditions

        self._held_item = held_item

    @property
    def oeo_id(self):
        return self._oeo_id

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def species(self):
        return self._species

    @property
    def elements(self):
        return self._elements

    @property
    def level(self):
        return self._level

    @property
    def xp(self):
        return self._xp

    @property
    def conscious(self):
        if self._current_hp > 0:
            return True
        else:
            return False

    @property
    def current_hp(self):
        return self._current_hp

    @current_hp.setter
    def current_hp(self, value):
        if value <= 0:
            self._current_hp = 0
        elif value > self.full_hp:
            self._current_hp = self.full_hp
        else:
            self._current_hp = value

    @property
    def full_hp(self):
        return self._calculate_hp_stat()

    @property
    def attack(self):
        return self._calculate_stat("attack")

    @property
    def defence(self):
        return self._calculate_stat("defence")

    @property
    def sp_attack(self):
        return self._calculate_stat("sp_attack")

    @property
    def sp_defence(self):
        return self._calculate_stat("sp_defence")

    @property
    def speed(self):
        return self._calculate_stat("speed")

    @property
    def moves(self):
        return self._moves

    @moves.setter
    def moves(self, value):
        self._moves = value

    @property
    def status_conditions(self):
        return self._status_conditions

    def add_status_condition(self, status_condition):
        self._status_conditions.append(status_condition)

    def remove_status_condition(self, status_condition):
        self._status_conditions.remove(status_condition)

    @property
    def held_item(self):
        return self._held_item

    @held_item.setter
    def held_item(self, value):
        self._held_item = value

    @property
    def ivs(self):
        return self._ivs

    @ivs.setter
    def ivs(self, value):
        self._ivs = value

    @property
    def evs(self):
        return self._evs

    @evs.setter
    def evs(self, value):
        self._evs = value

    def __repr__(self):
        return "Oeo(ID:%r, Name:%r, Species:%r, Element(s):%r, Lvl:%r, XP:%r, HP:%r/%r, BaseStats:%r, IVs:%r, EVs:%r, "\
               "Moves:%r, Conditions:%r, HeldItem:%r)" % (self._oeo_id, self._name, self._species, self._elements,
                                                          self._level, self._xp, self._current_hp, self.full_hp,
                                                          self._base_stats, self._ivs, self._evs,
                                                          self._moves, self._status_conditions, self._held_item)

    def __str__(self):
        return "{0} the {1} <Lvl:{2}, XP:{3}, HP:{4}/{5}, Attack:{6}, Defence:{7}, Sp.Attack:{8}, " \
               "Sp.Defence:{9}, Speed:{10}>".format(self._name if self._name else self._oeo_id,
                                                    self._species, self._level, self._xp, self._current_hp,
                                                    self.full_hp, self.attack, self.defence, self.sp_attack,
                                                    self.sp_defence, self.speed)

    def _calculate_hp_stat(self):
        """
        Calculate full hp stat as ((IV[hp] + 2(BASE[hp]) + EV[hp]/4 + 100) x LEVEL)/100 + 10
        :return: full hp of this oeo
        """
        full_hp = math.floor(((self._ivs.hp + 2*self._base_stats.hp + self._evs.hp/4 + 100) * self._level)/100 + 10)
        return full_hp

    def _calculate_stat(self, stat):
        """
        Calculate stat as (((IV[stat] + 2(BASE[stat]) + EV[stat]/4) x LEVEL)/100 + 5) x NATURE
        :return:
        """
        base_stat = getattr(self._base_stats, stat)
        iv = getattr(self._ivs, stat)
        ev = getattr(self._evs, stat)
        lvl = self._level
        stat = math.floor(((iv + 2*base_stat + ev/4) * lvl)/100 + 5)
        return stat

    def heal(self):
        self.current_hp = self.full_hp

    @classmethod
    def create(cls, species, name, level, xp):
        oeo_id = uuid.uuid4().hex[8:-8]
        name = name if name else ""
        current_hp = None
        ivs = Stats.rand_ivs()
        evs = Stats()
        moves = ["Maul"]
        status_conditions = None
        held_item = None

        return cls(oeo_id, name, species, level, xp, current_hp, ivs, evs, moves, status_conditions, held_item)

    @classmethod
    def load(cls, path):
        with path.open(mode="r", encoding="utf-8") as f:
            j = json.load(f)

        oeo_id = j["oeo_id"]
        name = j["name"]
        species = j["species"]
        level = j["level"]
        xp = j["xp"]
        current_hp = j["current_hp"]
        ivs = Stats.from_dict(j["ivs"])
        evs = Stats.from_dict(j["evs"])
        moves = j["moves"]
        # status_conditions = j["status_conditions"]
        status_conditions = None
        held_item = j["held_item"]

        return cls(oeo_id, name, species, level, xp, current_hp, ivs, evs, moves, status_conditions, held_item)

    def save(self, dir_path):
        path = dir_path / "{0}.json".format(self._oeo_id)
        o = {"oeo_id": self._oeo_id, "name": self._name, "species": self._species, "level": self._level, "xp": self._xp,
             "current_hp": self._current_hp, "ivs": self._ivs.to_dict(), "evs": self._evs.to_dict(),
             "moves": self._moves, "held_item": self._held_item}
        # todo: Remember to implement status conditions eventually xd
        # o["status_conditions"] = ...
        with path.open(mode="w", encoding="utf-8") as f:
            json.dump(o, f, sort_keys=True, indent=2, ensure_ascii=False)

    @staticmethod
    def _load_oeo_base(species):
        o = Oeo.data_root / "{0}.json".format(species)
        if o.exists():
            with o.open(encoding="utf-8") as f:
                oeo_data = json.load(f)
        else:
            raise Exception("{0} does not exist".format(o))
        try:
            elements = []
            elem = oeo_data["elements"]
            for element in elem:
                elements.append(Element[element])
            base_stats = Stats.from_dict(oeo_data["base_stats"])
        except KeyError as e:
            logger.error("Oeo data for '{0}' is missing a value for {1}".format(species, e))
            raise Exception("Oeo data for '{0}' is missing a value for {1}".format(species, e)) from e
        else:
            return elements, base_stats
