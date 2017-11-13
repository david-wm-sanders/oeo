from random import randint
from namedlist import namedlist


class Stats(namedlist("Stat", "hp attack defence sp_attack sp_defence speed", default=0)):
    def to_dict(self):
        d = {"hp": self.hp, "attack": self.attack, "defence": self.defence,
             "sp_attack": self.sp_attack, "sp_defence": self.sp_defence, "speed": self.speed}
        return d

    @classmethod
    def from_dict(cls, d):
        hp = d["hp"]
        attack = d["attack"]
        defence = d["defence"]
        sp_attack = d["sp_attack"]
        sp_defence = d["sp_defence"]
        speed = d["speed"]
        return cls(hp, attack, defence, sp_attack, sp_defence, speed)

    @classmethod
    def rand_ivs(cls):
        hp = randint(0, 31)
        attack, defence = randint(0, 31), randint(0, 31)
        sp_attack, sp_defence = randint(0, 31), randint(0, 31)
        speed = randint(0, 31)
        return cls(hp, attack, defence, sp_attack, sp_defence, speed)
