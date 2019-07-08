import json
import logging
from enum import Enum
from json import JSONEncoder

import websocket

logger = logging.getLogger(__name__)


class PlanetType(Enum):
    TYPE_A = 'TYPE_A',
    TYPE_B = 'TYPE_B',
    TYPE_C = 'TYPE_C',
    TYPE_D = 'TYPE_D'

    def __repr__(self):
        return self.name


class DisasterType(Enum):
    METEOR = 'METEOR',
    BLACK_HOLE = 'BLACK_HOLE'

    def __repr__(self):
        return self.name


class Entity:
    def __str__(self):
        return self.__dict__.__str__()

    def __repr__(self) -> str:
        return self.__str__()


class Disaster(Entity):
    def __init__(self, dict):
        self.type = DisasterType[dict['type']]
        if self.type == DisasterType.METEOR:
            self.planetId = dict['planetId']
        else:
            self.sourcePlanetId = dict['sourcePlanetId']
            self.targetPlanetId = dict['targetPlanetId']
            self.planetId = None        # Костыль, чтобы нормально собирать список дизастеров по типу


class Planet(Entity):
    def __init__(self, dict):
        self.id = dict['id']
        self.droids = dict['droids']
        self.owner = dict['owner']
        self.type = PlanetType[dict['type']]
        self.neighbours = dict['neighbours']
        self.priority = 0       # Добавлен для определения приоритета соседей


class Portal(Entity):
    def __init__(self, dict):
        self.source = dict['source']
        self.target = dict['target']


class GalaxySnapshot(Entity):
    def __init__(self, dict={}):
        self.errors = dict['errors'] if 'errors' in dict else []
        self.planets = list(map(lambda p_dict: Planet(p_dict), dict['planets'])) if 'planets' in dict else []
        self.disasters = list(
            map(lambda d_dict: Disaster(d_dict), dict['disasters'])) if 'disasters' in dict else []
        self.portals = list(map(lambda p_dict: Portal(p_dict), dict['portals'])) if 'portals' in dict else []


class ClientAction(Entity):
    def __init__(self, src, dest, units_count):
        self.src = src
        self.dest = dest
        self.units_count = units_count


class ClientCommandEncoder(JSONEncoder):
    def default(self, action):
        return {'from': action.src, 'to': action.dest, 'unitsCount': action.units_count}


class ClientCommand:
    def __init__(self, actions):
        self.actions = actions


class GameClient:
    """
    Основной объект клиента для взаимодействия с сервером.
    """
    def __init__(self, server, token, player):
        path = "ws://{}/galaxy".format(server)
        self.galaxy = None
        self.actions = []
        self.player = player
        self.socket = websocket.WebSocketApp(path,
                                             header=['token: '.format(token)],
                                             on_message=self.on_message,
                                             on_error=self.on_error,
                                             on_close=self.on_close,
                                             on_open=self.on_open)

    def send_drones(self, src, dest, drones):
        """
        Добавление команды отправки дронов
        :param src: идентификатор аннексированной планеты, с который ты собираешься выслать дронов
        :param dest: идентификатор планеты, на которую ты высылаешь дронов
        :param drones: количество пересылаемых дронов
        """
        self.actions.append(ClientAction(src, dest, drones))

    def get_my_planets(self):
        """
        :return: Аннексированные тобой планеты или **[]**, если таковых не найдено
        """
        return list(filter(lambda p: p.owner == self.player, self.galaxy.planets))

    def get_planet_by_id(self, planet_id):
        """
        :param planet_id: идентификатор планеты
        :return: планета с идентификатором **planet_id** или **None**, если такой планеты не найлено
        """
        planet = list(filter(lambda p: p.id == planet_id, self.galaxy.planets))
        return None if len(planet) == 0 else planet

    def get_neighbours(self, planet_id):
        """
        Получение соседних планет относительно планеты **planet_id**

        :param planet_id: идентификатор планеты для получения её соседей
        :return: список соседних планет
        """
        planet = self.get_planet_by_id(planet_id)
        return [] if not planet else list(filter(lambda p: planet_id in p.neighbours, self.galaxy.planets))

    def get_galaxy(self):
        """
        :return: снапшот галактики
        """
        return self.galaxy

    def run(self, on_turn=None):
        self.on_turn = on_turn
        self.socket.run_forever()

    def on_message(self, message):
        logger.debug("Received command <<< {}".format(message))
        self.galaxy = GalaxySnapshot(json.loads(message))
        self.actions = []
        self.on_turn(self)
        command = ClientCommand(self.actions)
        json_command = json.dumps(command.__dict__, cls=ClientCommandEncoder)
        self.__send(json_command)

    def __send(self, msg):
        logger.debug('Sending command >>> {}'.format(msg))
        if self.socket.sock:
            self.socket.send(msg)

    def on_open(self):
        logger.info('Connection established')

    def on_error(self, error):
        logger.error("Error: {}".format(error))

    def on_close(self):
        logger.info("Disconnected")
