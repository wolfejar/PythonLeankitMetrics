import sys
import leankit
import statsd
from _datetime import datetime, timezone
from datetime import date
from datetime import timedelta
from dateutil import parser
from dateutil.relativedelta import relativedelta, MO
import pytz
import time
# cmd args: domain, username, password
# TODO: Reorganize loops to prioritize which metrics should get sent first.
# TODO: Remove large chunks of data if they are not being used
# Storing cycle time of every card Leankit.Lanes.CycleTimes.LaneName.User.ID-123
# Displaying cycle time for each card in lane = Leankit.Lanes.CycleTimes.LaneName.*.*
# Displaying cycle time for each card per user = Leankit.Lanes.CycleTimes.*.UserName

utc = pytz.UTC

domain = sys.argv[1]
username = sys.argv[2]
password = sys.argv[3]

client = statsd.StatsClient('localhost', 8125)

leankit.api.authenticate(domain, username, password)

AppDevID = leankit.get_boards()[0]["Id"]

AppDevBoard = leankit.Board(AppDevID)
card_size_by_user = {}
cards_developed_this_week = {}
size_of_cards_deployed_this_week = 0

pipe_one = client.pipeline()

weekly_points_per_user = {}

for user in AppDevBoard.users.items():
    weekly_points_per_user[user[1]["FullName"]] = 0

# store Event objects from each card in card_history dictionary
card_history = {}
stuck_cards = []
possible_stuck_lanes = ["Active Development", "Code Review", "Dev Complete",
                        "Available For Testing", "Testing", "Passed QA"]
for card in AppDevBoard.cards:
    # print(AppDevBoard.cards[card])
    history = []
    for item in AppDevBoard.cards[card].history:
        history.append(item)
    card_history[card] = history
    # too many cards in archive lane to store history

all_card_moves = {}
for card in card_history.items():
    card_move_events = []
    for event in card[1]:
        if "FromLaneId" in event:
            if event["FromLaneId"] != event["ToLaneId"]:  # if card wasn't moved to same lane
                # add tuple of last lane and time of move to array
                card_move_events.append((event["ToLaneTitle"], event["EventDateTime"]))
        elif "CardCreationEventDTO" == event["Type"]:
            card_move_events.append((event["ToLaneTitle"], event["EventDateTime"]))
    # record cards stuck in certain lanes for more than 3 days
    time_since_move = datetime.now() - card[1][-1]["DateTime"]
    if time_since_move > timedelta(days=3) and\
            AppDevBoard.Lanes[AppDevBoard.cards[card[0]]["LaneId"]]["Title"] in possible_stuck_lanes:
        stuck_cards.append((AppDevBoard.cards[card[0]], time_since_move))
    all_card_moves[card[0]] = card_move_events
card_times = {}
card_times_per_user = {}
last_monday = date.today() + relativedelta(weekday=MO(-1))
for hist in all_card_moves.items():
    card_id = AppDevBoard.cards[hist[0]]["ExternalCardID"]
    card_users = AppDevBoard.cards[hist[0]]["AssignedUsers"]
    time_in_lanes = {}
    for i, item in enumerate(hist[1]):
        if 0 < i < len(hist[1]):
            # record total time the card was in the previous lane
            if hist[1][i-1][0] in time_in_lanes:
                time_in_lanes[hist[1][i-1][0]] += (parser.parse(item[1])
                                                   - parser.parse(hist[1][i-1][1])).total_seconds()
            else:
                time_in_lanes[hist[1][i-1][0]] = (parser.parse(item[1])
                                                  - parser.parse(hist[1][i-1][1])).total_seconds()
        if i == len(hist[1])-1 and i > 0:
            # record time since last move for time in current lane
            if hist[1][i][0] in time_in_lanes:
                time_in_lanes[hist[1][i][0]] += (datetime.now(timezone.utc) - parser.parse(item[1])).total_seconds()
            else:
                time_in_lanes[hist[1][i][0]] = (datetime.now(timezone.utc) - parser.parse(item[1])).total_seconds()
        if i == 0 and i == len(hist[1])-1:
            # if card hasn't moved since creation, record time since creation
            time_in_lanes[hist[1][i][0]] = (datetime.now(timezone.utc) - parser.parse(item[1])).total_seconds()
    card_times[card_id] = time_in_lanes
    for user in card_users:
        if user["FullName"] in card_times_per_user:
            card_times_per_user[user["FullName"]][card_id] = time_in_lanes
        else:
            card_times_per_user[user["FullName"]] = {}
            card_times_per_user[user["FullName"]][card_id] = time_in_lanes
    dev_complete_limit = False
    passed_qa_limit = False
    for item in hist[1]:
        if item[0] == "Dev Complete" and dev_complete_limit is False\
                and parser.parse(item[1]) >= utc.localize(datetime.combine(last_monday, datetime.min.time())):
            for user in card_users:
                weekly_points_per_user[user["FullName"]] += int(AppDevBoard.cards[hist[0]]["Size"])
            dev_complete_limit = True
        if item[0] == "Passed QA" and passed_qa_limit is False\
                and parser.parse(item[1]) >= utc.localize(datetime.combine(last_monday, datetime.min.time())):
            for user in card_users:
                weekly_points_per_user[user["FullName"]] += int(AppDevBoard.cards[hist[0]]["Size"])
            passed_qa_limit = True
        if item[0] == "Testing" and\
                parser.parse(item[1]) >= utc.localize(datetime.combine(last_monday, datetime.min.time())):
            weekly_points_per_user["Cindy Sorrick"] += int(AppDevBoard.cards[hist[0]]["Size"])

# gauge total work load (size) per user
for user in card_size_by_user.keys():
    pipe_one.gauge("Leankit.Users.TotalSize." + user, card_size_by_user[user])

# gauge total size of cards deployed this week
pipe_one.gauge("Leankit.WeeklyDeployments", size_of_cards_deployed_this_week)
# gauge points for game among users
for user in weekly_points_per_user:
    if weekly_points_per_user[user] > 0:
        pipe_one.gauge("Leankit.Game." + user, weekly_points_per_user[user])
# Send all stuck cards
for card in stuck_cards:
    print("ID-" + card[0]["ExternalCardID"] + ", stuck " + str(card[1].total_seconds()) + " seconds")
    pipe_one.gauge("Leankit.Cards.Stuck.ID-" + card[0]["ExternalCardID"], int(card[1].total_seconds()))
pipe_one.send()
print("Data sent...")
'''
# gauge cycle time for each card per lane
for item in card_times.items():
    for lane_time_pair in item[1].items():
        pipe_one.gauge("Leankit.Cards.CycleTimes.ID-" + str(item[0]) + "." + lane_time_pair[0], lane_time_pair[1])
pipe_one.send()
print("Pipe one sent...")
print("Waiting...")
time.sleep(15)'''
'''# gauge cycle time for each card per user
for user in card_times_per_user.items():
    for item in user[1].items():
        for lane_time_pair in item[1].items():
            pipe_one.gauge("Leankit.Users.CycleTimes."+user[0]+".ID-" + str(item[0]) + "." + lane_time_pair[0],
                           lane_time_pair[1])
pipe_one.send()
print("Pipe one sent...")
print("Waiting...")
time.sleep(15)'''
for lane in AppDevBoard.top_level_lanes:

    # Calculate size of cards in lane vs lane WIP limit
    size = 0
    pipe_one.gauge("Leankit.Lanes.Limits."+lane["Title"], lane["CardLimit"])
    for card in lane["Cards"]:
            if card["Size"] == 0:
                card["Size"] = 1
            size += card["Size"]
    for child_lane in lane["ChildLanes"]:
        for card in child_lane["Cards"]:
            if card["Size"] == 0:
                card["Size"] = 1
            size += card["Size"]
    pipe_one.gauge("Leankit.Lanes.TotalSizes."+lane["Title"], size)

    # Calculate cycle time for each individual card within the lane
    total_lane_cycle_time = 0
    for card in lane["Cards"]:
        card_cycle_time = (datetime.now() - parser.parse(card["LastMove"])).total_seconds()
        total_lane_cycle_time += card_cycle_time
        # Gauge cycle time for card
        for username in card["AssignedUsers"]:
            pipe_one.gauge("Leankit.Lanes.CycleTimes."+lane["Title"] + ".ID-" + card["ExternalCardID"]
                           + "." + username["FullName"] + ".CycleTime", card_cycle_time)
            pipe_one.gauge("Leankit.Lanes.CycleTimes." + lane["Title"] + ".ID-" + card["ExternalCardID"]
                           + "." + username["FullName"] + ".Size", card["Size"])
    for child_lane in lane["ChildLanes"]:
        for card in child_lane["Cards"]:
            card_cycle_time = (datetime.now() - parser.parse(card["LastMove"])).total_seconds()
            total_lane_cycle_time += card_cycle_time
            # Gauge cycle time for card
            for username in card["AssignedUsers"]:
                pipe_one.gauge("Leankit.Lanes.CycleTimes." + lane["Title"]+".ID-" + card["ExternalCardID"]
                               + "." + username["FullName"] + ".CycleTime", card_cycle_time)
                pipe_one.gauge("Leankit.Lanes.CycleTimes." + lane["Title"] + ".ID-" + card["ExternalCardID"]
                               + "." + username["FullName"] + ".Size", card["Size"])
    # Gauge cycle time for lane
    pipe_one.gauge("Leankit.Lanes.CycleTimes."+lane["Title"], total_lane_cycle_time)
    '''
    # record card sizes per user
    for card in lane["Cards"]:
        for username in card["AssignedUsers"]:
            username = username["FullName"]
            if username in card_size_by_user.keys():
                card_size_by_user[username] += card["Size"]
            else:
                card_size_by_user[username] = card["Size"]
    for child_lane in lane["ChildLanes"]:
        for card in child_lane["Cards"]:
            for username in card["AssignedUsers"]:
                username = username["FullName"]
                if username in card_size_by_user.keys():
                    card_size_by_user[username] += card["Size"]
                else:
                    card_size_by_user[username] = card["Size"]
    '''
    '''
    # Calculate lead time for cards in "Done" lane
    if lane["Title"] == "Done":
        for card in lane["Cards"]:
            creation_date = datetime.combine(AppDevBoard.get_card(card["Id"])["CreateDate"], datetime.min.time())
            lead_time = (parser.parse(card["LastMove"]) - creation_date).total_seconds()
            pipe_one.gauge("Leankit.Cards.Types."+card["TypeName"]+".ID-"+card["ExternalCardID"], lead_time)
            pipe_one.gauge("Leankit.Cards.Sizes."+card["Size"]+".ID-"+card["ExternalCardID"], lead_time)
            # record weekly deployment stats
            last_monday = date.today() + relativedelta(weekday=MO(-1))
            if parser.parse(card["LastMove"]) >= datetime.combine(last_monday, datetime.min.time()):
                size_of_cards_deployed_this_week += card["Size"]
        for child_lane in lane["ChildLanes"]:
            for card in child_lane["Cards"]:
                creation_date = datetime.combine(AppDevBoard.get_card(card["Id"])["CreateDate"], datetime.min.time())
                lead_time = (parser.parse(card["LastMove"]) - creation_date).total_seconds()
                pipe_one.gauge("Leankit.Cards.Types." + card["TypeName"] + ".ID-" + card["ExternalCardID"],
                               lead_time)
                pipe_one.gauge("Leankit.Cards.Sizes." + str(card["Size"]) + ".ID-" + card["ExternalCardID"], lead_time)
                # record weekly deployment stats
                last_monday = date.today() + relativedelta(weekday=MO(-1))
                if parser.parse(card["LastMove"]) >= datetime.combine(last_monday, datetime.min.time()):
                    size_of_cards_deployed_this_week += card["Size"]
            for child_child_lane in child_lane["ChildLanes"]:
                for card in child_child_lane["Cards"]:
                    creation_date = datetime.combine(AppDevBoard.get_card(card["Id"])["CreateDate"],
                                                     datetime.min.time())
                    lead_time = (parser.parse(card["LastMove"]) - creation_date).total_seconds()
                    pipe_one.gauge("Leankit.Cards.Types." + card["TypeName"] + ".ID-" + card["ExternalCardID"],
                                   lead_time)
                    pipe_one.gauge("Leankit.Cards.Sizes." + str(card["Size"]) + ".ID-" + card["ExternalCardID"],
                                   lead_time)
                    # record weekly deployment stats
                    last_monday = date.today() + relativedelta(weekday=MO(-1))
                    if parser.parse(card["LastMove"]) >= datetime.combine(last_monday, datetime.min.time()):
                        size_of_cards_deployed_this_week += card["Size"]
    '''
    # record card points dev complete per user this week
    if lane["Title"] == "Dev Complete":
        for card in lane["Cards"]:
            last_monday = date.today() + relativedelta(weekday=MO(-1))
            if parser.parse(card["LastMove"]) >= datetime.combine(last_monday, datetime.min.time()):
                for username in card["AssignedUsers"]:
                    username = username["FullName"]
                    if username in cards_developed_this_week.keys():
                        cards_developed_this_week[username] += int(card["Size"])
                    else:
                        cards_developed_this_week[username] = int(card["Size"])
    # gauge total size of cards in dev complete this week by user
    for user in cards_developed_this_week.keys():
        pipe_one.gauge("Leankit.Users.WeeklyDevelopment." + user, cards_developed_this_week[user])
    pipe_one.send()
    print("Data sent...")

