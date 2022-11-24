from time import sleep
from datetime import datetime
import pandas as pd
import blessings
from multiprocessing import Process, Value
from ctypes import c_bool, c_wchar
import getch
import numpy as np
from random import randint

# TODO: Fix bug bullet returning

tps_limit = 60
tps_count = 0
g_map = None
g_term = blessings.Terminal()
running = Value(c_bool, True)
shared_input = Value(c_wchar, '0')
map_x_size = 32
map_y_size = 16
obstacles = [(5, 5), (6, 5), (7, 5),
             (4, 5), (4, 4), (4, 3), (4, 2), (4, 1),
             (8, 5), (8, 4), (8, 2), (8, 1),
             (5, 1), (6, 1), (7, 1)]  # (row, column)
time_start = None
enemy_speed = 3.0  # positions/second
enemy_initial_position = (9, 9)
enemy_last_moviment = ''
enemy_last_moviment_time = ''
code_player = 'O'
code_enemy = 'Z'
player_health = 5
vertical_bullet = '|'
horizontal_bullet = '–'
bullet_type = ''
bullet_direction = 'H'
bullet_direction_inc = 1
bullet_direction_full = 'R'
kills = 0


def loop():
    last_tick_time = datetime.now()

    while running.value:
        try:
            now = datetime.now()
            check_user_input()
            update(now)
            render()
            sleep_size = 1.0 / (tps_limit / 2) - (now - last_tick_time).total_seconds()

            if sleep_size > 0:
                sleep(sleep_size)

            last_tick_time = now
            global tps_count
            tps_count += 1
        except KeyboardInterrupt:
            break


def check_user_input():
    if player_health > 0:
        global bullet_direction
        global bullet_direction_inc
        global bullet_direction_full
        if shared_input.value == "s":
            bullet_direction = 'V'
            bullet_direction_inc = 1
            bullet_direction_full = 'B'
            move(bullet_direction, bullet_direction_inc, code_player)
        elif shared_input.value == "w":
            bullet_direction = 'V'
            bullet_direction_inc = -1
            bullet_direction_full = 'U'
            move(bullet_direction, bullet_direction_inc, code_player)
        elif shared_input.value == "d":
            bullet_direction = 'H'
            bullet_direction_inc = 1
            bullet_direction_full = 'R'
            move(bullet_direction, bullet_direction_inc, code_player)
        elif shared_input.value == "a":
            bullet_direction = 'H'
            bullet_direction_inc = -1
            bullet_direction_full = 'L'
            move(bullet_direction, bullet_direction_inc, code_player)
        elif shared_input.value == " ":
            shoot()

        shared_input.value = '0'


def update(in_now):
    if player_health > 0:
        enemy_follow_player(in_now)
    move_bullet()


def render():
    with g_term.fullscreen():
        with g_term.location(0, 0):
            fps = round(tps_count / (datetime.now() -
                                     time_start).total_seconds())
            print(
                f"WASD = Movement\nq = quit\nFPS: {fps}\tHealth: {player_health}\nKills: {kills}\n{g_map.to_string()}")


def enemy_follow_player(in_now):
    player_x, player_y, _ = get_entity_cords(code_player)
    enemy_x, enemy_y, enemy_found = get_entity_cords(code_enemy)

    global enemy_last_moviment
    global enemy_last_moviment_time

    if enemy_found:
        if (in_now - enemy_last_moviment_time).total_seconds() >= 1 / enemy_speed:
            enemy_last_moviment_time = in_now

            if enemy_x >= player_x and enemy_last_moviment != 'V':
                move('V', -1, code_enemy)
                enemy_last_moviment = 'V'
            else:
                move('V', 1, code_enemy)
                enemy_last_moviment = 'V'

            if (enemy_y >= player_y) and (enemy_last_moviment != 'H'):
                move('H', -1, code_enemy)
                enemy_last_moviment = 'H'
            else:
                move('H', 1, code_enemy)
                enemy_last_moviment = 'H'


def move_bullet():
    if have_bullet():
        move(bullet_direction_old, bullet_direction_inc_old, bullet_type_old)


def have_bullet():
    bullet_pos = get_entity_cords([vertical_bullet, horizontal_bullet])
    return bullet_pos[2]


def shoot():
    player_x, player_y, _ = get_entity_cords(code_player)
    if not have_bullet():
        global bullet_type
        if bullet_direction_full == 'R':
            bullet_type = horizontal_bullet
            bullet_x = player_x
            bullet_y = player_y + 1
        elif bullet_direction_full == 'L':
            bullet_type = horizontal_bullet
            bullet_x = player_x
            bullet_y = player_y - 1
        elif bullet_direction_full == 'U':
            bullet_type = vertical_bullet
            bullet_x = player_x - 1
            bullet_y = player_y
        elif bullet_direction_full == 'B':
            bullet_type = vertical_bullet
            bullet_x = player_x + 1
            bullet_y = player_y
        else:
            return None

        if 0 <= bullet_x < map_y_size and 0 <= bullet_y < map_x_size:
            if g_map.iloc[bullet_x, bullet_y] == '.':
                g_map.iloc[bullet_x, bullet_y] = bullet_type

                global bullet_direction_old
                global bullet_direction_inc_old
                global bullet_direction_full_old
                global bullet_type_old
                bullet_direction_old = bullet_direction
                bullet_direction_inc_old = bullet_direction_inc
                bullet_direction_full_old = bullet_direction_full
                bullet_type_old = bullet_type


def setup_map():
    global g_map
    g_map = pd.DataFrame('.', index=range(map_y_size),
                         columns=range(map_x_size))
    for obstacle in obstacles:
        g_map.iloc[obstacle] = "X"


def user_input_loop(in_running, in_shared_key):
    while in_running.value:
        user_input = getch.getch()
        if user_input == "q":
            in_running.value = False
        else:
            in_shared_key.value = user_input


def set_initial_position():
    g_map.iloc[0, 0] = code_player


def get_entity_cords(in_entity_value):
    if isinstance(in_entity_value, list):
        x, y = np.where((g_map == in_entity_value[0]) | (
                g_map == in_entity_value[1]))
    else:
        x, y = np.where(g_map == in_entity_value)

    if len(x) > 0:
        ret = x[0], y[0], True
    else:
        ret = x, y, False
    return ret


def move(in_direction, in_increment, in_entity):
    x, y, _ = get_entity_cords(in_entity)
    if in_direction == 'V':
        x_new = x + in_increment
        y_new = y
        limit = g_map.shape[0]
        limit_ref = x_new
    else:
        x_new = x
        y_new = y + in_increment
        limit = g_map.shape[1]
        limit_ref = y_new

    if limit > limit_ref >= 0:
        if g_map.iloc[x_new, y_new] == '.':
            g_map.iloc[x, y] = '.'
            g_map.iloc[x_new, y_new] = in_entity
        elif g_map.iloc[x_new, y_new] == code_player and in_entity == code_enemy:
            global player_health
            if player_health == 1:
                player_health -= 1
                kill_player()
            else:
                player_health -= 1
        elif g_map.iloc[x_new, y_new] == code_enemy and in_entity == bullet_type:
            g_map.iloc[x_new, y_new] = '.'
            global kills
            kills += 1
            spawn_new_enemy()
        elif g_map.iloc[x_new, y_new] == "X" and in_entity == bullet_type:
            g_map.iloc[x, y] = '.'
    elif in_entity == bullet_type:
        g_map.iloc[x, y] = '.'


def spawn_new_enemy():
    # edge of row or column
    is_column_edge = randint(0, 1) == 0

    if is_column_edge:
        x = randint(0, map_x_size - 1)
        y = 0
    else:
        x = 0
        y = randint(0, map_y_size - 1)
    global enemy_speed
    enemy_speed += 0.5
    g_map.iloc[y, x] = 'Z'


def kill_player():
    cords = get_entity_cords(code_player)
    g_map.iloc[cords] = 'D'


def setup_enemy():
    global enemy_last_moviment_time
    g_map.iloc[enemy_initial_position] = "Z"
    enemy_last_moviment_time = datetime.now()


def setup_user_input():
    proc = Process(target=user_input_loop, args=(running, shared_input))
    proc.start()


if __name__ == '__main__':
    time_start = datetime.now()
    setup_map()
    setup_enemy()
    setup_user_input()
    set_initial_position()
    loop()
    time_end = datetime.now()
    time_duration = time_end - time_start
    print("duration:", str(time_duration.total_seconds()))
    print("average FPS:", tps_count / time_duration.total_seconds())
    print("ended")
