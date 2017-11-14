import logging

logger = logging.getLogger(__name__)


class Field(object):
    """
    Handles the field of battle
    """
    def __init__(self, a_id, a_max_fielded, b_id, b_max_fielded):
        self._field = {a_id: Side(a_max_fielded),
                       b_id: Side(b_max_fielded)}

    def __getitem__(self, item):
        try:
            return self._field[item]
        except KeyError as e:
            logger.error(f"Team id:{item} not on field")
            raise Exception(f"Team id:{item} not on field") from e

    def deploy(self, team_id, oeo_id, position):
        try:
            self._field[team_id].deploy(oeo_id, position)
            logger.info(f"{team_id} deployed {oeo_id} to position {position}")
        except KeyError as e:
            logger.error(f"Team id:{team_id} not on field")
            raise Exception(f"Team id:{team_id} not on field") from e

    def withdraw(self, team_id, oeo_id):
        try:
            position = self._field[team_id].index(oeo_id)
            self._field[team_id].withdraw(oeo_id)
            logger.info(f"{team_id} withdrew {oeo_id} from position {position}")
        except KeyError as e:
            logger.error(f"Team id:{team_id} not on field")
            raise Exception(f"Team id:{team_id} not on field") from e


class Side(object):
    """
    Handles a side on the field of battle
    """
    def __init__(self, max_fielded):
        self._max_fielded = max_fielded
        self._side = [None for _ in range(max_fielded)]

    def __len__(self):
        return self._max_fielded

    def __iter__(self):
        return iter(self._side)

    def index(self, oeo_id):
        return self._side.index(oeo_id)

    @property
    def side(self):
        return self._side

    @property
    def fielded(self):
        return [oeo_id for oeo_id in self._side if oeo_id is not None]

    @property
    def empty_positions(self):
        return [index for index, oeo_id in enumerate(self._side) if oeo_id is None]

    def is_empty(self):
        if all((True if oeo_id is None else False) for oeo_id in self._side):
            return True
        else:
            return False

    def deploy(self, oeo_id, position):
        self._side[position] = oeo_id

    def withdraw(self, oeo_id):
        position = self._side.index(oeo_id)
        self._side[position] = None

    def __str__(self):
        return "%s" % self._side
