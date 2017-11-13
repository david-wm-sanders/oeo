from enum import Enum, unique


@unique
class Element(Enum):
    Normal = 1
    Fight = 2
    Flying = 3
    Poison = 4
    Ground = 5
    Rock = 6
    Bug = 7
    Ghost = 8
    Steel = 9
    Fire = 10
    Water = 11
    Grass = 12
    Electric = 13
    Psychic = 14
    Ice = 15
    Dragon = 16
    Dark = 17

    def __repr__(self):
        return "Element.%s" % self.name