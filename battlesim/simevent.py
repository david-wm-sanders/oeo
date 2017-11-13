from enum import Enum, unique


@unique
class SimEventType(Enum):
    BeginTurn = 1
    UseMove = 2
    UseItem = 3
    Switch = 4
    Run = 5


class SimEvent(object):
    """
    Events and actions that occur during the course of a battle
    """
    def __init__(self, event_type, **kwargs):
        assert isinstance(event_type, SimEventType), "event_type is not a SimEventType"
        self._event_type = event_type
        self._event_data = kwargs

    @property
    def event_type(self):
        return self._event_type

    @property
    def data(self):
        return self._event_data

    def __repr__(self):
        return "SimEvent(%s%s)" % (self._event_type.name, (", %s" % self._event_data) if self._event_data else "")


class Action(object):
    @staticmethod
    def use_move(move_id, target_id):
        return SimEvent(SimEventType.UseMove, move_id=move_id, target_id=target_id)
