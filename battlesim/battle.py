import logging
import itertools
from operator import itemgetter
from axel import Event
from pqdict import PQDict
from core import Oeo, Move
from .simevent import SimEvent, SimEventType
from .field import Field
from .damage import get_damage_function

logger = logging.getLogger(__name__)


class Battle(object):
    """
    Fight a battle between two teams of oeo
    """
    _turn_stage_map = {8: '02', 7: '03', 6: '04', 5: '05', 4: '06', 3: '07', 2: '08', 1: '09', 0: '10',
                       -1: '11', -2: '12', -3: '13', -4: '14', -5: '15', -6: '16', -7: '17'}

    _turn_spi_map = {0: '01', 1: '02', 2: '03', 3: '04', 4: '05', 5: '06',
                     6: '07', 7: '08', 8: '09', 9: '10', 10: '11', 11: '12'}

    def __init__(self, oeos, a_id, a, a_max_fielded, b_id, b, b_max_fielded):
        assert all(isinstance(oeo, Oeo) for oeo in oeos.values()), "oeos is not a dict of oeo_id:oeo"
        assert isinstance(a_id, str), "'a_id' is not a string"
        assert isinstance(a, set), "'a' is not a set of oeo_id"
        assert isinstance(a_max_fielded, int), "'a_max_fielded' is not an int"
        assert isinstance(b_id, str), "'b_id' is not a string"
        assert isinstance(b, set), "'b' is not a set of oeo_id"
        assert isinstance(b_max_fielded, int), "'b_max_fielded' is not an int"
        # Throw error if each oeo_id is not unique between teams
        if a & b:
            raise ValueError(f"{a & b} oeo_id(s) not unique between teams")

        self._oeo = oeos
        self._a_id = a_id
        self._a = a
        self._b_id = b_id
        self._b = b

        self._turn_number = 0
        self._field = Field(a_id, a_max_fielded, b_id, b_max_fielded)
        self._pending_sim_events = PQDict()
        self._processed_sim_events = []

        move_set = set()
        for o in itertools.chain(self._oeo.values()):
            for move in o.moves:
                move_set.add(move)
        moves = Move.load_moves(move_set)
        self._moves = moves

        # self._speed_priority_list = None
        self._setup_axel_events()

    @property
    def teams(self):
        return {self._a_id: self._a, self._b_id: self._b}

    @property
    def field(self):
        return self._field

    def _setup_axel_events(self):
        """
        Initialise axel events
        """
        # sim_output_message(msg)
        self.sim_output_message = Event()

        # event_choose_deployments(team_id, non_fielded_team, empty_positions)
        # non_fielded_team: oeo from the team who are not on the field but are conscious
        # empty_positions: empty positions on the field into which an oeo could be deployed
        self.event_choose_deployments = Event()

        # event_choose_actions(team_id, oeo_requiring_actions)
        # oeo_requiring_actions: oeo that are on the field and need to select an action for the current turn
        self.event_choose_actions = Event()

    def run(self):
        """
        Run the battle

        :return: id of the victor
        :rtype: str
        """
        logger.info(f"{self._a_id} vs {self._b_id}...")
        ta = {oeo_id: self._oeo[oeo_id] for oeo_id in self._a}
        tb = {oeo_id: self._oeo[oeo_id] for oeo_id in self._b}
        logger.debug(f"{self._a_id}'s team:\n{ta}")
        logger.debug(f"{self._b_id}'s team:\n{tb}")

        # Add the BEGIN_TURN SimEvent for turn 1
        self._pending_sim_events.additem(SimEvent(SimEventType.BeginTurn), 1)

        victor = None

        # While there are pending sim events, loop until we break when a battle end condition is met
        while self._pending_sim_events:
            # Remove any oeo with 0 HP from the field
            self._remove_unconscious_oeo()

            # Check teams: if all oeo in the battle are unconscious, then end battle as a draw
            #              if all oeo in team A are unconscious, then end battle as win for team B
            #              if all oeo in team B are unconscious, then end battle as win for team A
            if not any(oeo.conscious for oeo in self._oeo.values()):
                logger.info("All oeo on both sides of the battle are unconscious, the battle is a draw")
                victor = "DRAW"
                break
            elif not any(self._oeo[oeo_id].conscious for oeo_id in self._a):
                logger.info(f"{self._a_id}'s team are unconscious, {self._b_id} wins the battle")
                victor = self._b_id
                break
            elif not any(self._oeo[oeo_id].conscious for oeo_id in self._b):
                logger.info(f"{self._b_id}'s team are unconscious, {self._a_id} wins the battle")
                victor = self._a_id
                break

            # Let both sides choose oeo to deploy
            self._choose_deployments()
            logger.debug(f"{self._a_id}'s side: {self._field[self._a_id]}")
            logger.debug(f"{self._b_id}'s side: {self._field[self._b_id]}")

            # Check both sides of the field: if team A side is empty, then end as win for team B
            #                                if team B side is empty, then end as win for team A
            if self._field[self._a_id].is_empty():
                logger.info(f"{self._a_id} yields, {self._b_id} wins the battle")
                victor = self._b_id
                break
            elif self._field[self._b_id].is_empty():
                logger.info(f"{self._b_id} yields, {self._a_id} wins the battle")
                victor = self._a_id
                break

            # Pop the next event to be processed, add it to the processed events list, and process it
            event, event_priority = self._pending_sim_events.popitem()
            event_complete = 0
            event_type = event.event_type
            if event_type is SimEventType.BeginTurn:
                event_complete = self._process_begin_turn()
            elif event_type is SimEventType.UseMove:
                event_complete = self._process_use_move(**event.data)
            elif event_type is SimEventType.UseItem:
                # event_complete = self._process_use_item
                pass
            elif event_type is SimEventType.Switch:
                # event_complete = self._process_switch_oeo
                pass
            elif event_type is SimEventType.Run:
                # event_complete = self._process_run
                pass
            else:
                raise ValueError(f"Invalid event_type: {event}")

            self._processed_sim_events.append((event_priority, event, event_complete))

        logger.debug(f"Pending events: {self._pending_sim_events}")
        logger.info(f"Processed events: {self._processed_sim_events}")
        return victor

    def _process_begin_turn(self):
        # Increment the turn number and add the BeginTurn SimEvent for the next turn
        self._turn_number += 1
        logger.debug(f"Processing BeginTurn({self._turn_number}) SimEvent")
        self._pending_sim_events.additem(SimEvent(SimEventType.BeginTurn), self._turn_number + 1)

        # todo: Update status conditions - burn, poison, landing from flight, then remove unconscious oeo from field

        # Choose the actions for the oeo on the field this turn, calculate the order in which the actions should occur,
        # and add them to the pending sim events priority queue
        self._choose_actions()
        return 1

    def _process_use_move(self, user_id, move_id, target_id):
        logger.debug("Processing UseMove SimEvent")
        user, move, target = self._oeo[user_id], self._moves[move_id], self._oeo[target_id]
        user_is_fielded = self._is_fielded(user_id)
        target_is_fielded = self._is_fielded(target_id)
        if user_is_fielded and target_is_fielded:
            logger.info(f"{user_id} attacks {target_id} using {move_id}")
            df_id = getattr(move, "df_id", "Standard")
            damage_function = get_damage_function(df_id)
            damage = damage_function(user, move, target)
            hp = target.current_hp
            target.current_hp -= damage
            logger.info(f"{target_id}'s HP = {hp}-{damage} = {target.current_hp}")
            return 1
        else:
            logger.debug(f"User on field = {user_is_fielded}, Target on field = {target_is_fielded}")
            return -1

    def _process_use_item(self, item, target):
        logger.debug("Processing UseItem SimEvent")
        return 0

    def _process_switch(self, user, target):
        logger.debug("Processing Switch SimEvent")
        return 0

    def _process_run(self, user, run_type):
        logger.debug("Processing Run SimEvent")
        return 0

    def _calculate_event_priority(self, turn, priority, speed_priority):
        """
        :param turn: the turn in which the event is to be actioned
        :param priority: the stage of the turn in which the event is to be actioned
        :param speed_priority: the speed_priority of the oeo undertaking the event
        :return: the priority of the event to be actioned
        """
        return float(f"{turn}.{self._turn_stage_map[priority]}{self._turn_spi_map[speed_priority]}")

    def _remove_unconscious_oeo(self):
        """
        Withdraw unconscious oeo from the field
        """
        for team_id in [self._a_id, self._b_id]:
            oeo_to_remove = [oeo_id for oeo_id in self._field[team_id].fielded if self._oeo[oeo_id].conscious is False]
            for oeo_id in oeo_to_remove:
                self._field.withdraw(team_id, oeo_id)

    def _is_fielded(self, oeo_id):
        """
        :param oeo_id:
        :return: True if oeo_id is on the field else False
        """
        if (oeo_id in self._field[self._a_id]) or (oeo_id in self._field[self._b_id]):
            return True
        else:
            return False

    def _choose_deployments(self):
        """
        Choose and make deployments to the field
        """
        for team_id in [self._a_id, self._b_id]:
            empty_positions = self._field[team_id].empty_positions
            logger.debug(f"Empty positions on {team_id}'s side: {empty_positions}")
            if empty_positions:
                fielded = self._field[team_id].fielded
                benched = [oeo_id for oeo_id in self.teams[team_id] if oeo_id not in fielded and
                           self._oeo[oeo_id].conscious]
                logger.debug(f"Benched on {team_id}'s side: {benched}")
                if benched:
                    deployments = self._poll_deployments(team_id, benched, empty_positions)
                    logger.debug(f"{team_id}'s oeo to deploy: {deployments}")
                    for position, oeo_id in deployments.items():
                        self._field.deploy(team_id, oeo_id, position)

    def _poll_deployments(self, team_id, non_fielded_team, empty_positions):
        """
        Polls for deployments for team_id
        :return: dict of position:oeo_id
        """
        logger.debug(f"Polling for deployments from {team_id}")
        results = self.event_choose_deployments(team_id, list(non_fielded_team), empty_positions)
        flag, result, handler = results[0]
        if flag:
            for position, oeo_id in result.items():
                # Ensure that each oeo is only deployed to one field position at most
                if list(result.values()).count(oeo_id) > 1:
                    raise Exception(f"{oeo_id} can not be deployed to more than one field position")
                # Ensure 0 >= position < len(self._field[team_id])
                if position < 0 or position >= len(self._field[team_id]):
                    raise Exception(f"Field position {position} is out of bounds (0-{len(self._field[team_id]) - 1})")
                # Ensure oeo_id is in self.team[team_id]
                if oeo_id not in self.teams[team_id]:
                    raise Exception(f"{oeo_id} is not in {team_id}'s team")
            return result
        else:
            raise Exception("Exception in choose_deployments handler") from result

    def _choose_actions(self):
        """
        Choose and schedule actions for oeo on the field
        """
        # Create the speed_priority_list for this turn
        oeo_against_speed = [(oeo_id, oeo.speed) for oeo_id, oeo in self._oeo.items()]
        oeo_against_speed.sort(key=itemgetter(1), reverse=True)
        logger.debug(f"Speed Priority List: {oeo_against_speed}")
        speed_priority_list = [t[0] for t in oeo_against_speed]

        a_fielded = self._field[self._a_id].fielded
        b_fielded = self._field[self._b_id].fielded

        # Create action_map dictionary of oeo_id to action:None for fielded oeo and update it from future_action
        # dictionary
        action_map = {oeo_id: None for oeo_id in itertools.chain(a_fielded, b_fielded)}
        # todo: Update action_map from future_actions dictionary
        logger.debug(f"Initial action map for turn {self._turn_number}: {action_map}")

        # Call event_choose_actions for each team for oeo that do not have an action to perform (action is None)
        a_oeo_requiring_actions = [oeo_id for oeo_id, action in action_map.items() if (oeo_id in a_fielded) and
                                   (action is None)]
        a_oeo_requiring_actions.sort(key=lambda x: self._oeo[x].speed, reverse=True)
        b_oeo_requiring_actions = [oeo_id for oeo_id, action in action_map.items() if (oeo_id in b_fielded) and
                                   (action is None)]
        b_oeo_requiring_actions.sort(key=lambda x: self._oeo[x].speed, reverse=True)
        logger.debug(f"{self._a_id}'s oeo requiring actions: {a_oeo_requiring_actions}")
        logger.debug(f"{self._b_id}'s oeo requiring actions: {b_oeo_requiring_actions}")
        a_actions = self._poll_actions(self._a_id, a_oeo_requiring_actions)
        b_actions = self._poll_actions(self._b_id, b_oeo_requiring_actions)
        logger.info(f"{self._a_id}'s actions chosen: {a_actions}")
        logger.info(f"{self._b_id}'s actions chosen: {b_actions}")

        # For each {oeo_id: action} in dictionary returned by the event handlers, add it to the action map if
        # the oeo does not already have an action for this turn in the action map
        for oeo_id, action in itertools.chain(a_actions.items(), b_actions.items()):
            if action_map[oeo_id] is not None:
                raise Exception(f"{oeo_id} already had an action for this turn")
            action_map[oeo_id] = action
        logger.debug(f"Final action map for turn {self._turn_number}: {action_map}")

        # For each {oeo_id: action} in the action map add the SimEvent for the action to the pending sim events queue
        for oeo_id, action in action_map.items():
            if action:
                if action.event_type == SimEventType.UseMove:
                    target = action.data["target_id"]
                    move_id = action.data["move_id"]
                    move_priority = self._moves[move_id].priority
                    oeo_priority = speed_priority_list.index(oeo_id)
                    self._pending_sim_events.additem(SimEvent(SimEventType.UseMove,
                                                              user_id=oeo_id, target_id=target, move_id=move_id),
                                                     self._calculate_event_priority(self._turn_number, move_priority,
                                                                                    oeo_priority))
                if action.event_type == SimEventType.UseItem:
                    pass

    def _poll_actions(self, team_id, oeo_requiring_actions):
        """
        Polls for actions from team_id
        :return: dict of oeo_id:action
        """
        logger.debug(f"Polling for actions from {team_id}")
        results = self.event_choose_actions(team_id, oeo_requiring_actions)
        flag, result, handler = results[0]
        if flag:
            for oeo_id, action in result.items():
                # Ensure oeo is on the field
                if not self._is_fielded(oeo_id):
                    raise Exception(f"{oeo_id} is not on the field")
                # Ensure oeo is in team_id
                if oeo_id not in self.teams[team_id]:
                    raise Exception(f"{oeo_id} is not on {team_id}'s side")
                # Ensure action is SimEvent
                if not isinstance(action, SimEvent):
                    raise Exception("Action is not a SimEvent")
                # Ensure action.event_type is UseMove, UseItem, Switch or Run
                if action.event_type not in [SimEventType.UseMove, SimEventType.UseItem,
                                             SimEventType.Switch, SimEventType.Run]:
                    raise Exception("Action event type not UseMove, UseItem, Switch or Run")
            return result
        else:
            raise Exception("Exception in choose_actions handler") from result
