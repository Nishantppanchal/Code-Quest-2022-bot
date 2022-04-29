from dis import dis
from tkinter.messagebox import NO
from urllib import request
from codequest22.server.ant import AntTypes
import codequest22.stats as stats
from codequest22.server.events import DepositEvent, DieEvent, ProductionEvent, ZoneActiveEvent, ZoneDeactivateEvent, TeamDefeatedEvent, QueenAttackEvent, AttackEvent, MoveEvent
from codequest22.server.requests import GoalRequest, SpawnRequest
from numpy import isin
from dijkstrasAlgorithm import dijkstrasAlgorithm

def get_team_name():
    return f"Nishant's Bot 2"

bot_index = None
number_of_players = None
def read_index(player_index, n_players):
    global bot_index, number_of_players
    bot_index = player_index
    number_of_players = n_players

my_energy = stats.general.STARTING_ENERGY
id = 0
map_data = {}
spawns = [None]*4
food = []
food_energy = {}
hills = []
distance = {}
total_ants = 0
food_sorted = []
weakest_enemy = 0
strongest_enemy = 0
worker_ants = {}
teams_defeated = []
waiting_worker_ants = []
worker_dispatch_timer = 0
phase = None
zone_active = False
zone_active_points = []
zone_active_ticks = 0
defence = 0
ticks = 0
attack_bot = 0
current_goal = 0
saved = 0

def read_map(md, energy_info):
    global map_data, spawns, food, food_sorted, distance, enemy_start_point, all_energy, enemy_choke_points, enemy_distance
    
    all_energy = [stats.general.STARTING_ENERGY]*(number_of_players)
    
    map_data = md
    for y in range(len(map_data)):
        for x in range(len(map_data[0])):
            if map_data[y][x] == "F":
                food.append((x, y))
                food_energy[(x, y)] = energy_info[(x, y)]
            elif map_data[y][x] in "RBYG":
                spawns["RBYG".index(map_data[y][x])] = (x, y)
            elif map_data[y][x] == "Z":
                hills.append((x, y))

    bot_start_point = spawns[bot_index]
    enemy_start_points = list(filter(lambda point: (point != None and point != spawns[bot_index]), spawns))
    
    distance = dijkstrasAlgorithm(map_data=map_data, start_point=bot_start_point)
    
    food_sorted = list(sorted(food, key=lambda prod: (distance[prod]*2)/food_energy[prod]))
    
    enemy_choke_points = []
    enemy_distance = []
    print(enemy_start_points)
    for i in range(len(enemy_start_points)):
        enemy_distance.append(dijkstrasAlgorithm(map_data=map_data, start_point=enemy_start_points[i]))
        
        enemy_choke_points.append(list(sorted(food, key=lambda prod: enemy_distance[i][prod])))
    
def handle_failed_requests(requests):
    # # Debugging
    # global my_energy
    # for req in requests:
    #     if req.player_index == bot_index:
    #         print(f"{bot_index} : Request {req.__class__.__name__} failed. Reason: {req.reason}.")
    #         raise ValueError()
    pass

def handle_events(events):
    global bot_index, my_energy, total_ants, worker_ants, id, all_energy, weakest_enemy, teams_defeated, figther_protection_group, worker_dispatch_timer, waiting_worker_ants
    global phase, enemy_choke_points, zone_active, zone_active_points, distance, zone_active_ticks, defence, ticks, strongest_enemy, attack_bot, food_sorted, current_goal
    global enemy_spawns, saved
    requests = []
    spawned_this_tick = 0
    
    for ev in events:
        if isinstance(ev, DieEvent):
            if ev.player_index == bot_index:
                total_ants -= 1

                if ev.ant_id in worker_ants:
                    del worker_ants[str(ev.ant_id)]
        elif isinstance(ev, DepositEvent):
            if ev.player_index == bot_index:
                requests.append(GoalRequest(ev.ant_id, food_sorted[worker_ants[ev.ant_id]]))
                my_energy = ev.total_energy
            else:
                all_energy[ev.player_index] = ev.cur_energy
                other_energy_indexes = []
                other_energy = []
                for i in range(0, number_of_players):
                    if i not in teams_defeated and i != bot_index:
                        other_energy_indexes.append(i)
                        other_energy.append(all_energy[i])
                weakest_enemy = other_energy_indexes[other_energy.index(min(other_energy))]
                strongest_enemy = other_energy_indexes[other_energy.index(max(other_energy))]
        elif isinstance(ev, ProductionEvent):
            if ev.player_index == bot_index:
                requests.append(GoalRequest(ev.ant_id, spawns[bot_index]))
        elif isinstance(ev, TeamDefeatedEvent):
            if ev.defeated_index != bot_index:
                teams_defeated.append(ev.defeated_index)
        elif isinstance(ev, ZoneActiveEvent):
            zone_active = True
            zone_active_points = list(sorted(ev.points, key=lambda prod: distance[prod]))
            zone_active_ticks = ev.num_ticks - distance[zone_active_points[0]]/stats.ants.Settler.SPEED
        elif isinstance(ev, ZoneDeactivateEvent):
            zone_active = False
        elif isinstance(ev, QueenAttackEvent):
            # if ev.queen_player_index == bot_index:
            #     phase = 4
            #     defence = 1
            if ev.queen_player_index == bot_index:
                if ticks > 100:
                    phase = "Attack"
                    attack_bot = ev.ant_player_index
        elif isinstance(ev, AttackEvent):
            if ev.defender_id == bot_index:
                print("attack_event")
                phase = "Attack"
                attack_bot = ev.attacker_id
                food_sorted = list(sorted(food, key=lambda prod: (distance[prod])/enemy_distance[attack_bot][prod]))
                print(food_sorted)
    
    if ticks <= 100: 
        phase = 1
    else: 
        phase = 2
        
        
        
    if zone_active == True:
        if (
            total_ants < stats.general.MAX_ANTS_PER_PLAYER and 
            spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
            my_energy > stats.ants.Settler.COST + stats.ants.Worker.COST*2 and 
            zone_active_ticks > 0
        ):
            spawned_this_tick += 1
            total_ants += 1
            
            requests.append(SpawnRequest(AntTypes.SETTLER, id=None, color=None, goal=zone_active_points[0]))
            
            my_energy -= stats.ants.Settler.COST
            
            zone_active_ticks -= 1
        if (
            total_ants < stats.general.MAX_ANTS_PER_PLAYER and 
            spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
            my_energy > stats.ants.Settler.COST + stats.ants.Worker.COST*2 and 
            zone_active_ticks > 0
        ):
            spawned_this_tick += 1
            total_ants += 1
            
            requests.append(SpawnRequest(AntTypes.FIGHTER, id=None, color=None, goal=zone_active_points[0]))
            
            my_energy -= stats.ants.Fighter.COST
            
            zone_active_ticks -= 1
            
    if phase == 1:
        if (
            total_ants < stats.general.MAX_ANTS_PER_PLAYER and 
            spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
            my_energy >= (stats.ants.Fighter.COST + stats.ants.Worker.COST) and
            ticks > 100
        ): 
            enemy_spawns = spawns.copy()
            enemy_spawns.pop(bot_index)
            spawned_this_tick += 1
            total_ants += 1
            try:
                requests.append(SpawnRequest(AntTypes.FIGHTER, id=None, color=None, goal=enemy_spawns[0]))
            except:
                requests.append(SpawnRequest(AntTypes.FIGHTER, id=None, color=None, goal=enemy_spawns))
            my_energy -= stats.ants.Fighter.COST
        while (
            total_ants < stats.general.MAX_ANTS_PER_PLAYER and 
            spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
            my_energy >= stats.ants.Worker.COST
        ):
            print(f"{total_ants < stats.general.MAX_ANTS_PER_PLAYER} and {spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK} and {my_energy >= stats.ants.Worker.COST}")
            spawned_this_tick += 1
            total_ants += 1
            
            requests.append(SpawnRequest(AntTypes.WORKER, id=str(id), color=None, goal=food_sorted[0]))
            worker_ants[str(id)] = current_goal
            if current_goal <= 4:
                current_goal += 1
            else:
                current_goal = 0
            
            id += 1
            
            my_energy -= stats.ants.Worker.COST
            print("worker")
        
        
                
    if phase == 2:
        while (
            total_ants < stats.general.MAX_ANTS_PER_PLAYER*0.75 and 
            spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
            my_energy >= stats.ants.Worker.COST 
        ):
            spawned_this_tick += 1
            total_ants += 1
            
            requests.append(SpawnRequest(AntTypes.WORKER, id=str(id), color=None, goal=food_sorted[0]))
            worker_ants[str(id)] = current_goal
            if current_goal <= 4:
                current_goal += 1
            else:
                current_goal = 0
            
            id += 1
            
            my_energy -= stats.ants.Worker.COST
            saved += stats.ants.Fighter.COST
            
            print("worker")
            
        while (
            total_ants < stats.general.MAX_ANTS_PER_PLAYER and 
            spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
            my_energy >= stats.ants.Fighter.COST 
        ):
            requests.append(SpawnRequest(AntTypes.FIGHTER, id=None, color=None, goal=spawns[weakest_enemy]))
            my_energy -= stats.ants.Fighter.COST
        
    if phase == "Attack":
        if (
            total_ants < stats.general.MAX_ANTS_PER_PLAYER and 
            spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
            my_energy > stats.ants.Worker.COST
        ):
            if worker_dispatch_timer == 0: 
                if len(waiting_worker_ants) == 0:
                    spawned_this_tick += 1
                    total_ants += 1
                    
                    requests.append(SpawnRequest(AntTypes.WORKER, id=str(id), color=None, goal=food_sorted[0]))
                    worker_ants[str(id)] = current_goal
                    if current_goal <= 4:
                        current_goal += 1
                    else:
                        current_goal = 0
                    
                    id += 1
                    
                    my_energy -= stats.ants.Worker.COST
                    worker_dispatch_timer += 1
                elif len(waiting_worker_ants) != 0:
                    ant_id = waiting_worker_ants.pop(0)
                    requests.append(GoalRequest(ant_id, food_sorted[worker_ants[ant_id]]))
            
            elif worker_dispatch_timer == 1:
                worker_dispatch_timer += 1
            
            elif worker_dispatch_timer == 2:
                worker_dispatch_timer = 0

        while (
            total_ants < stats.general.MAX_ANTS_PER_PLAYER and 
            spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
            my_energy > stats.ants.Fighter.COST
        ): 
            requests.append(SpawnRequest(AntTypes.FIGHTER, id=None, color=None, goal=spawns[attack_bot]))
            my_energy -= stats.ants.Fighter.COST
            print("attack")
            
    ticks += 1
    return requests