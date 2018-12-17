import sys
import leankit
import statsd
from _datetime import datetime, timezone
from datetime import date
from dateutil import parser
from dateutil.relativedelta import relativedelta, MO
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# cmd args: domain (ksu), username, password

domain = sys.argv[1]
username = sys.argv[2]
password = sys.argv[3]

mailserver = smtplib.SMTP('smtp.office365.com', 587)
mailserver.ehlo()
mailserver.starttls()
mailserver.login('wolfejar@ksu.edu', 'dsgacTddR7')

client = statsd.StatsClient('localhost', 8125)

leankit.api.authenticate(domain, username, password)

AppDevID = leankit.get_boards()[0]["Id"]

AppDevBoard = leankit.Board(AppDevID)

card_size_by_user = {}
cards_developed_this_week = {}
size_of_cards_deployed_this_week = 0

for lane in AppDevBoard.top_level_lanes:

    # Calculate size of cards in lane vs lane WIP limit
    size = 0
    client.gauge("Leankit.Lanes.Limits."+lane["Title"], lane["CardLimit"])
    for card in lane["Cards"]:
            if card["Size"] == 0:
                card["Size"] = 1
            size += card["Size"]
    for child_lane in lane["ChildLanes"]:
        for card in child_lane["Cards"]:
            if card["Size"] == 0:
                card["Size"] = 1
            size += card["Size"]
    client.gauge("Leankit.Lanes.TotalSizes."+lane["Title"], size)

    # Calculate cycle time for each lane and each individual card within the lane
    total_lane_cycle_time = 0
    for card in lane["Cards"]:
        card_cycle_time = (datetime.now() - parser.parse(card["LastMove"])).total_seconds()
        total_lane_cycle_time += card_cycle_time
        # Gauge cycle time for card
        client.gauge("Leankit.Lanes.CycleTimes."+lane["Title"]+".ID-"+card["ExternalCardID"], card_cycle_time)
    for child_lane in lane["ChildLanes"]:
        for card in child_lane["Cards"]:
            card_cycle_time = (datetime.now() - parser.parse(card["LastMove"])).total_seconds()
            total_lane_cycle_time += card_cycle_time
            # Gauge cycle time for card
            client.gauge("Leankit.Lanes.CycleTimes." + lane["Title"] + ".ID-" + card["ExternalCardID"],
                         card_cycle_time)
    # Gauge cycle time for lane
    client.gauge("Leankit.Lanes.CycleTimes."+lane["Title"], total_lane_cycle_time)

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

    # Calculate lead time for cards in "Done" lane
    if lane["Title"] == "Done":
        for card in lane["Cards"]:
            creation_date = datetime.combine(AppDevBoard.get_card(card["Id"])["CreateDate"], datetime.min.time())
            lead_time = (parser.parse(card["LastMove"]) - creation_date).total_seconds()
            client.gauge("Leankit.Cards.Types."+card["TypeName"]+".ID-"+card["ExternalCardID"], lead_time)
            client.gauge("Leankit.Cards.Sizes."+card["Size"]+".ID-"+card["ExternalCardID"], lead_time)
            # record weekly deployment stats
            last_monday = date.today() + relativedelta(weekday=MO(-1))
            if parser.parse(card["LastMove"]) >= datetime.combine(last_monday, datetime.min.time()):
                size_of_cards_deployed_this_week += card["Size"]
        for child_lane in lane["ChildLanes"]:
            for card in child_lane["Cards"]:
                creation_date = datetime.combine(AppDevBoard.get_card(card["Id"])["CreateDate"], datetime.min.time())
                lead_time = (parser.parse(card["LastMove"]) - creation_date).total_seconds()
                client.gauge("Leankit.Cards.Types." + card["TypeName"] + ".ID-" + card["ExternalCardID"],
                             lead_time)
                client.gauge("Leankit.Cards.Sizes." + str(card["Size"]) + ".ID-" + card["ExternalCardID"], lead_time)
                # record weekly deployment stats
                last_monday = date.today() + relativedelta(weekday=MO(-1))
                if parser.parse(card["LastMove"]) >= datetime.combine(last_monday, datetime.min.time()):
                    size_of_cards_deployed_this_week += card["Size"]

    # record card points dev complete per user this week
    if lane["Title"] == "Dev Complete":
        for card in lane["Cards"]:
            last_monday = date.today() + relativedelta(weekday=MO(-1))
            if parser.parse(card["LastMove"]) >= datetime.combine(last_monday, datetime.min.time()):
                for username in card["AssignedUsers"]:
                    username = username["FullName"]
                    if username in cards_developed_this_week.keys():
                        cards_developed_this_week[username] += card["Size"]
                    else:
                        cards_developed_this_week[username] = card["Size"]

# store Event objects from each card in card_history dictionary
card_history = {}
for card in AppDevBoard.cards:
    # print(AppDevBoard.cards[card])
    history = []
    for item in AppDevBoard.cards[card].history:
        history.append(item)
    card_history[card] = history


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
    all_card_moves[card[0]] = card_move_events

card_times = {}
card_times_per_user = {}
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

# gauge time per lane for each card
for item in card_times.items():
    for lane_time_pair in item[1].items():
        client.gauge("Leankit.Cards.CycleTimes.ID-" + str(item[0]) + "." + lane_time_pair[0], lane_time_pair[1])
for user in card_times_per_user.items():
    for item in user[1].items():
        for lane_time_pair in item[1].items():
            client.gauge("Leankit.Users.CycleTimes."+user[0]+".ID-" + str(item[0]) + "." + lane_time_pair[0],
                         lane_time_pair[1])
# gauge total work load (size) per user, reset stats for dev_complete per user
for user in card_size_by_user.keys():
    client.gauge("Leankit.Users.TotalSize." + user, card_size_by_user[user])
    client.gauge("Leankit.Users.WeeklyDevelopment." + user, 0)
# gauge total size of cards in dev complete this week by user
for user in cards_developed_this_week.keys():
    client.gauge("Leankit.Users.WeeklyDevelopment." + user, cards_developed_this_week[user])
# gauge total size of cards deployed this week
client.gauge("Leankit.WeeklyDeployments", size_of_cards_deployed_this_week)


lane_time_limits = ""
message = MIMEMultipart()
message['FROM'] = 'wolfejar@ksu.edu'

message['TO'] = 'wolfejar@ksu.edu'
message['Subject'] = 'User Card Update'

"""body = MIMEText(lane_time_limits, 'plain')
message.attach(body)
mailserver.sendmail('wolfejar@ksu.edu', 'wolfejar@ksu.edu', message.as_string())
mailserver.quit()"""
