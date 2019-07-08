import logging


from starmarinesclient.CodeBattlePythonLibrary import GameClient, ClientCommand, GalaxySnapshot, ClientAction, DisasterType, PlanetType, Disaster
from collections import defaultdict

logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s',
                    level=logging.DEBUG)


def turn(cl: GameClient):
    """
    Задача игрока: реализовать логику формирования команд на отправку дронов в этом методе.
    Для отправки дронов с планеты на планету используется метод :func:`starmarinesclient.GameClient.send_drones`

    Получить снапшот галактики можно используя метол :func:`starmarinesclient.GameClient.get_galaxy`

    Получение всех аннексированных твоими дронами планет можно методом :func:`starmarinesclient.GameClient.get_my_planets`

    Получение всех соседей планеты по её илентификатору: :func:`starmarinesclient.GameClient.get_neighbours`

    Получение описания планеты по её идентификатору: :func:`starmarinesclient.GameClient.get_planet_by_id`

    :param cl: Вспомогательный объект клиента
    :return метод ничего не возвращает
    """
    errors = cl.get_galaxy().errors
    planets = cl.get_galaxy().planets
    disasters = cl.get_galaxy().disasters
    d_list = [] # Метеоры
    hole_list = [] # Дырки
    portals = cl.get_galaxy().portals # Порталы
    portal_list = [] # Список порталов вида [[1, 2], [4, 8]]
    available_to_send_from = 0 # Доступно для отправки с планеты, для max эксплуатации регена планеты
    annexed_type = 0 # Тип своей планеты
    massive_attack_targets = defaultdict(list) #TODO собирать граф общих соседей моих планет для коллективного раша

    for disaster in disasters:  #Берем все планетИД, ноне = не метеор, остальное = метеор
        d_list.append(disaster.planetId)

    for disaster in disasters:  #Список черных дырок
        if disaster.type == DisasterType.BLACK_HOLE:
            a = [disaster.sourcePlanetId, disaster.targetPlanetId]
            hole_list.append(a)
    for portal in portals:  # Формируем список порталов
        b = [portal.source, portal.target]
        portal_list.append(b)

    if errors:
        print("Error occurred", errors)     # выводим информацию об ошибках, если таковые есть (например, с клиента
                                            # отправлено невалидное действие)
    annexed_planets = cl.get_my_planets()   # получаем список своих планет

    for annexed in annexed_planets:  # идем по своим планетам, смотрим тип и число
        if annexed.id in d_list:
            available_to_send_from = annexed.droids
        elif annexed.type == PlanetType.TYPE_D and annexed.droids < 770:
            available_to_send_from = 0
            annexed_type = 4
        elif annexed.type == PlanetType.TYPE_D and annexed.droids >= 770:
            available_to_send_from = annexed.droids - 770
            annexed_type = 4
        elif annexed.type == PlanetType.TYPE_C and annexed.droids < 400:
            available_to_send_from = 0
            annexed_type = 3
        elif annexed.type == PlanetType.TYPE_C and annexed.droids >= 400:
            available_to_send_from = annexed.droids - 400
            annexed_type = 3
        elif annexed.type == PlanetType.TYPE_B and annexed.droids < 180:
            available_to_send_from = 0
            annexed_type = 2
        elif annexed.type == PlanetType.TYPE_B and annexed.droids >= 180:
            available_to_send_from = annexed.droids
            annexed_type = 2
        elif annexed.type == PlanetType.TYPE_A:
            available_to_send_from = annexed.droids
            annexed_type = 1

        neighbours = cl.get_neighbours(annexed.id)  # для каждой аннексированной планеты получаем её соседей

        for i in range(len(portal_list)):                 # Добавляем порталы как соседей для планеты
            if portal_list[i][0] == annexed.id:
                neighbours.extend(cl.get_planet_by_id(portal_list[i][1]))
            elif portal_list[i][1] == annexed.id:
                neighbours.extend(cl.get_planet_by_id(portal_list[i][0]))
            else:
                continue


        for neighbour in neighbours:  # идем по соседям, ставим приоритет для сортировки
            if neighbour.type == PlanetType.TYPE_A:
                setattr(neighbour, 'priority', 1)
            elif neighbour.type == PlanetType.TYPE_B:
                setattr(neighbour, 'priority', 2)
            elif neighbour.type == PlanetType.TYPE_C:
                setattr(neighbour, 'priority', 3)
            elif neighbour.type == PlanetType.TYPE_D:
                setattr(neighbour, 'priority', 4)

        neighbours_sorted = sorted(neighbours, key=lambda x: x.priority, reverse=True)  # сортируем соседей по типу

        #for qwe in annexed_planets:                 #TODO собирать граф общих соседей моих планет для коллективного раша
        #    for ewq in neighbours_sorted:
        #        if qwe in cl.get_neighbours(ewq.id):
        #            if qwe.id not in massive_attack_targets[ewq.id]:
        #                massive_attack_targets[ewq.id].append(qwe.id)

        for neighbour_sort in neighbours_sorted:
            if neighbour_sort.id in d_list:                                         # Метеор
                to_send = 0
                cl.send_drones(annexed.id, neighbour_sort.id, int(to_send))
            elif [neighbour_sort.id, annexed.id] in hole_list or [annexed.id, neighbour_sort.id] in hole_list:  #Дырка
                to_send = 0
                cl.send_drones(annexed.id, neighbour_sort.id, int(to_send))
            elif neighbour_sort.owner is None and neighbour_sort.priority > annexed_type:  # Свободная крутая
                to_send = available_to_send_from
                cl.send_drones(annexed.id, neighbour_sort.id, int(to_send))
            elif neighbour_sort.owner == "NeuroLarion" and neighbour_sort.priority == 4 and neighbour_sort.droids < 700:
                to_send = available_to_send_from
                cl.send_drones(annexed.id, neighbour_sort.id, int(to_send))
            elif (neighbour_sort.priority == 4) and (neighbour_sort.owner is not None) and (neighbour_sort.owner != "NeuroLarion") and (neighbour_sort.droids * 1.5 < annexed.droids):
                to_send = available_to_send_from
                available_to_send_from -= to_send
                cl.send_drones(annexed.id, neighbour_sort.id, int(to_send))
            elif neighbour_sort.owner == "NeuroLarion":                             # Если планета уже моя
                if neighbour_sort.priority == 4 and neighbour_sort.droids > 750:  #не отправлять на крутую полную
                    to_send = 0
                    cl.send_drones(annexed.id, neighbour_sort.id, int(to_send))
                elif neighbour_sort.priority == annexed_type and neighbour_sort.droids < 400:  #отправлять всех если там меньше
                    to_send = available_to_send_from
                    cl.send_drones(annexed.id, neighbour_sort.id, int(to_send))
                    available_to_send_from -= to_send
                elif neighbour_sort.priority < annexed_type and neighbour_sort.droids < 100:
                    to_send = available_to_send_from  #int(available_to_send_from / len(neighbours_sorted))
                    available_to_send_from -= to_send
                    cl.send_drones(annexed.id, neighbour_sort.id, int(to_send))
            elif (neighbour_sort.priority > annexed_type) and (neighbour_sort.droids < available_to_send_from):  # Крутая доступная = олл-ин
                to_send = int(annexed.droids)
                cl.send_drones(annexed.id, neighbour_sort.id, int(to_send))
                available_to_send_from -= to_send
            elif (neighbour_sort.priority == 3) and (neighbour_sort.droids < 400):  #Ходим по третьему типу Условие на 400 добавлено после первых 3 карт
                to_send = available_to_send_from
                cl.send_drones(annexed.id, neighbour_sort.id, int(to_send))
                available_to_send_from -= to_send
            elif (neighbour_sort.priority == 2) and (neighbour_sort.droids < 170): # ВТорой
                to_send = available_to_send_from
                available_to_send_from -= to_send
                cl.send_drones(annexed.id, neighbour_sort.id, int(to_send))
            elif (neighbour_sort.priority == 1) and (neighbour_sort.droids < 50):  # Первый тип
                to_send = available_to_send_from
                available_to_send_from -= to_send
                cl.send_drones(annexed.id, neighbour_sort.id, int(to_send))
            elif neighbour_sort.priority < annexed_type and (neighbour_sort.droids < available_to_send_from):  #Хуже, доступна для захвата
                to_send = available_to_send_from
                cl.send_drones(annexed.id, neighbour_sort.id, int(to_send))
                available_to_send_from -= to_send
            else:
                if available_to_send_from > 500:
                    to_send = available_to_send_from / 2
                    available_to_send_from -= to_send
                    cl.send_drones(annexed.id, neighbour_sort.id, int(to_send))


def main():
    """
    Указываем адрес сервера, токен и логин игрока
    """
    client = GameClient("server", "token", "nickname")
    client.run(turn)


if __name__ == '__main__':
    main()
