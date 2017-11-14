#!venv/bin/python
import logging
import logging.config
from pathlib import Path
from uuid import uuid4
from core import Oeo, Stats, Element, Move, Item
from battlesim import Battle, Action

logger = logging.getLogger(__name__)
logging.config.fileConfig("logging_terminal.conf", disable_existing_loggers=False)
logger.debug(f"Started logging in {__file__}")

# spark_id, buzz_id = uuid4().hex[8:-8], uuid4().hex[8:-8]
spark_id, buzz_id = None, None


def main():
    print("oeo Terminal Battle Arena!")
    global spark_id, buzz_id

    # path = Path("./saves/David/oeo/player")

    # evs = Stats(74, 195, 86, 48, 84, 23)
    # ivs = Stats(hp=24, attack=12, defence=30, sp_attack=16, sp_defence=23, speed=5)

    # gla = Oeo(gla_id, "Icicle", "gla", 78, 78, None, ivs, evs, ["Freeze Bite"], None, None)
    # # gla = Oeo.load(path / "409a43ec9b5fd540.json")
    # gla._oeo_id = gla_id
    # logger.debug(f"{gla}")

    spark = Oeo.create("Chikaphu", "Spark", 5, 5)
    spark_id = spark.oeo_id
    logger.debug(f"{spark!r}")

    buzz = Oeo.create("Chikaphu", "Buzz", 5, 5)
    buzz_id = buzz.oeo_id
    logger.debug(f"{buzz!r}")

    oeos = {spark.oeo_id: spark, buzz.oeo_id: buzz}
    logger.debug(f"OEO AT START:\n{oeos}")
    t1 = {spark.oeo_id}
    t2 = {buzz.oeo_id}

    logger.debug("Initialise battle...")
    b = Battle(oeos, "X", t1, 2, "Y", t2, 2)
    b.sim_output_message = print_msg_from_sim
    b.event_choose_deployments += choose_oeo_to_deploy
    b.event_choose_actions += choose_actions

    logger.debug("Run the battle...")
    victor = b.run()
    print(f"The battle is won by: {victor}!")

    logger.debug(f"OEO AT END:\n{oeos}")
    logger.debug(f"{spark}")
    logger.debug(f"{buzz}")


def print_msg_from_sim(msg):
    print(msg)


def choose_oeo_to_deploy(team_id, non_fielded_team, empty_positions):
    if team_id == "X":
        return {0: spark_id}
    elif team_id == "Y":
        return {0: buzz_id}
    else:
        raise Exception("Invalid team_id")

    print(f"{team_id} can deploy {non_fielded_team} to empty positions {empty_positions}")
    print("Deploy>> oeo id>position, oeo id>position, ...")
    i = input("Deploy>> ")
    i = i.replace(" ", "")
    deployments = i.split(",")
    d = {}
    for deployment in deployments:
        oeo_id, _, slot_num = deployment.partition(">")
        d[int(slot_num)] = oeo_id
    return d


def choose_actions(team_id, eligible_actors):
    if team_id == "X":
        return {spark_id: Action.use_move("Maul", buzz_id)}
    elif team_id == "Y":
        return {buzz_id: Action.use_move("Maul", spark_id)}
    else:
        raise Exception("Invalid team_id")

    print(f"{team_id}'s team need orders for the turn")
    d = {}
    for actor in eligible_actors:
        print(f"What action should {actor} perform? move|item")
        action = input("Action>> ")
        if action == "move":
            move = input("Move>> ")
            move_name, _, target = move.partition(">")
            move_name = move_name.strip()
            target = target.strip()
            d[actor] = Action.use_move(move_name, target)
        elif action == "item":
            raise NotImplementedError()
        else:
            raise Exception(f"Specified action '{action}' does not exist")
    return d


if __name__ == "__main__":
    main()
