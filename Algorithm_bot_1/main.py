from dis import dis
from tkinter.messagebox import NO
from codequest22.server.ant import AntTypes
import codequest22.stats as stats
from codequest22.server.events import DepositEvent, DieEvent, ProductionEvent, ZoneActiveEvent
from codequest22.server.requests import GoalRequest, SpawnRequest
from numpy import number


def get_team_name():
    return f"Sample Bot"

bot_index = None
def read_index(player_index, n_players):
    global bot_index, number_of_players
    bot_index = player_index
    number_of_players = n_players

my_energy = stats.general.STARTING_ENERGY
map_data = {}
spawns = [None]*4
food = []
food_energy = {}
hills = []
distance = {}
total_ants = 0
# worker_ants = []
worker_ants = 0
fighter_ants = []
settler_ants = []
food_sites_sorted = []
enemy_food_choke_points = []
worker_dispatch_tick_timer = 0
waiting_worker_ants = []
zone_active_ticks = 0

def read_map(md, energy_info):
    global map_data, spawns, food, distance, food_sites_sorted, enemy_food_choke_points, distance
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
    # Read map is called after read_index
    bot_start_point = spawns[bot_index]
    print(f"{bot_index} : {bot_start_point}")
    enemy_start_points = list(filter(lambda point: (point != None and point != spawns[bot_index]), spawns[0:number_of_players-1]))
    # Dijkstra's Algorithm: Find the shortest path from your spawn to each food zone.
    # Step 1: Generate edges - for this we will just use orthogonally connected cells.
    adj = {}
    h, w = len(map_data), len(map_data[0])
    # A list of all points in the grid
    points = []
    # Mapping every point to a number
    idx = {}
    counter = 0
    for y in range(h):
        for x in range(w):
            adj[(x, y)] = []
            if map_data[y][x] == "W": continue
            points.append((x, y))
            idx[(x, y)] = counter
            counter += 1
    for x, y in points:
        for a, b in [(y+1, x), (y-1, x), (y, x+1), (y, x-1)]:
            if 0 <= a < h and 0 <= b < w and map_data[a][b] != "W":
                adj[(x, y)].append((b, a, 1))
    # Step 2: Run Dijkstra's
    import heapq
    # What nodes have we already looked at?
    expanded = [False] * len(points)
    # What nodes are we currently looking at?
    queue = []
    # What is the distance to the startpoint from every other point?
    heapq.heappush(queue, (0, bot_start_point))
    while queue:
        d, (a, b) = heapq.heappop(queue)
        if expanded[idx[(a, b)]]: continue
        # If we haven't already looked at this point, put it in expanded and update the distance.
        expanded[idx[(a, b)]] = True
        distance[(a, b)] = d
        # Look at all neighbours
        for j, k, d2 in adj[(a, b)]:
            if not expanded[idx[(j, k)]]:
                heapq.heappush(queue, (
                    d + d2,
                    (j, k)
                ))
    # Now I can calculate the closest food site.
    food_sites_sorted = list(sorted(food, key=lambda prod: (distance[prod]/food_energy[prod])))
    
    for point in enemy_start_points:
        # What nodes have we already looked at?
        expanded = [False] * len(points)
        # What nodes are we currently looking at?
        queue = []
        enemy_distance = {}
        # What is the distance to the startpoint from every other point?
        heapq.heappush(queue, (0, point))
        while queue:
            d, (a, b) = heapq.heappop(queue)
            if expanded[idx[(a, b)]]: continue
            # If we haven't already looked at this point, put it in expanded and update the distance.
            expanded[idx[(a, b)]] = True
            enemy_distance[(a, b)] = d
            # Look at all neighbours
            for j, k, d2 in adj[(a, b)]:
                if not expanded[idx[(j, k)]]:
                    heapq.heappush(queue, (
                        d + d2,
                        (j, k)
                    ))
                    
        # Now I can calculate the closest food site.
        enemy_food_choke_points.append(list(sorted(food, key=lambda prod: enemy_distance[prod])))
    
def handle_failed_requests(requests):
    global my_energy
    for req in requests:
        if req.player_index == bot_index:
            print(f"Request {req.__class__.__name__} failed. Reason: {req.reason}.")
            raise ValueError()
    # pass

def handle_events(events):
    global my_energy, total_ants, worker_ants, worker_dispatch_tick_timer, waiting_worker_ants, distance, zone_active_ticks
    requests = []
    spawned_this_tick = 0

    for ev in events:
        if isinstance(ev, DepositEvent):
            if ev.player_index == bot_index:
                waiting_worker_ants.append(ev.ant_id)
                # Additionally, let's update how much energy I've got.
                my_energy = ev.cur_energy + 30
                print(f"{bot_index} : {(ev.cur_energy + 30)} set")
        elif isinstance(ev, ProductionEvent):
            if ev.player_index == bot_index:
                # One of my worker ants just made it to the food site! Let's send them back to the Queen.
                requests.append(GoalRequest(ev.ant_id, spawns[bot_index]))
        elif isinstance(ev, DieEvent):
            if ev.player_index == bot_index:
                # One of my workers just died :(
                total_ants -= 1
                
                if ev.ant_id in waiting_worker_ants:
                    waiting_worker_ants.remove(ev.ant_id)
        elif isinstance(ev, ZoneActiveEvent): 
            sorted_points_hill = list(sorted(ev.points, key=lambda prod: (distance[prod])))
            closest_hill_tile = sorted_points_hill[0]
            zone_active_ticks = ev.num_ticks - distance[closest_hill_tile]/stats.ants.Settler.SPEED
            
            if (zone_active_ticks > 0):    
                while (
                    total_ants < stats.general.MAX_ANTS_PER_PLAYER and 
                    spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
                    my_energy >= stats.ants.Worker.COST - stats.ants.Settler.COST
                ):
                    requests.append(SpawnRequest(AntTypes.SETTLER, id=None, color=None, goal=closest_hill_tile))
                    spawned_this_tick += 1
                    total_ants += 1
                    my_energy -= stats.ants.Settler.COST
                zone_active_ticks -= 1
            
    print(f"{bot_index} : {my_energy} before")
    
    if (
        total_ants < stats.general.MAX_ANTS_PER_PLAYER and 
        spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
        my_energy >= stats.ants.Worker.COST and
        len(waiting_worker_ants) == 0 and
        worker_dispatch_tick_timer == 0
    ):
        spawned_this_tick += 1
        total_ants += 1
        requests.append(SpawnRequest(AntTypes.WORKER, id=None, color=None, goal=food_sites_sorted[0]))
        worker_dispatch_tick_timer += 1
        my_energy -= stats.ants.Worker.COST
    elif (
        total_ants < stats.general.MAX_ANTS_PER_PLAYER and 
        spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
        my_energy >= stats.ants.Worker.COST and
        len(waiting_worker_ants) != 0 and
        worker_dispatch_tick_timer == 0
    ):
        ant_id = waiting_worker_ants.pop(0)
        requests.append(GoalRequest(ant_id, food_sites_sorted[0]))
        worker_dispatch_tick_timer += 1
    elif (
        total_ants < stats.general.MAX_ANTS_PER_PLAYER and 
        spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
        my_energy >= stats.ants.Worker.COST and
        worker_dispatch_tick_timer == 1
    ): 
        worker_dispatch_tick_timer += 1
    elif (
        total_ants < stats.general.MAX_ANTS_PER_PLAYER and 
        spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
        my_energy >= stats.ants.Worker.COST and
        worker_dispatch_tick_timer == 2
    ):
        worker_dispatch_tick_timer = 0
    
    if (
        total_ants < stats.general.MAX_ANTS_PER_PLAYER and 
        spawned_this_tick < stats.general.MAX_SPAWNS_PER_TICK and
        my_energy >= (stats.ants.Fighter.COST*number_of_players + stats.ants.Worker.COST)
    ): 
        for point in enemy_food_choke_points:
            # for point in enemy_food_choke_points:
            spawned_this_tick += 1
            total_ants += 1
            requests.append(SpawnRequest(AntTypes.FIGHTER, id=None, color=None, goal=point[0]))
            my_energy -= stats.ants.Fighter.COST
        
    print(f"{bot_index} : {my_energy} after")
    
    return requests
