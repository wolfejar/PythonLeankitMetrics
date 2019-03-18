import sys
import leankit
from _datetime import datetime, timezone
from datetime import date
from datetime import timedelta
from dateutil import parser
from dateutil.relativedelta import relativedelta, MO
import pytz
# import plotly.offline as py  # use this for testing, doesn't contribute to plotly data limit
import plotly
import plotly.plotly as py
import plotly.graph_objs as go
import re

# cmd args: domain, username, password

utc = pytz.UTC

domain = sys.argv[1]
username = sys.argv[2]
password = sys.argv[3]

plotly.tools.set_credentials_file(username=sys.argv[4], api_key=sys.argv[5])

leankit.api.authenticate(domain, username, password)

AppDevID = leankit.get_boards()[0]["Id"]


def take_second(elem):
    return elem[1]


def cleanhtml(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext


AppDevBoard = leankit.Board(AppDevID)
card_size_by_user = {}
cards_developed_this_week = {}
size_of_cards_deployed_this_week = 0

weekly_points_per_user = {}

for user in AppDevBoard.users.items():
    weekly_points_per_user[user[1]["FullName"]] = 0

# store Event objects from each card in card_history dictionary
card_history = {}
stuck_cards = []
possible_stuck_lanes = ["Active", "Development", "Other", "Code Review", "Dev Complete",
                        "Available for Testing", "Testing", "Passed QA"]
stuck_parent_lanes = ["Active", "Code Review", "Dev Complete",
                        "Available for Testing", "Testing", "Passed QA"]
app_list = ['admissions', 'sso', 'ctam', 'eis', 'elp', 'expansis', 'gradesubmission', 'grouper', 'eprofile',
            'sanitychecker', 'idmservices', 'idmsupport', 'jenkins', 'jobapp', 'attendance', 'peoplesearch',
            'psengine', 'pdb', 'photoroster', 'scantron', 'sga', 'shibboleth', 'telecom', 'teval']
app_card_color = [
'#FF0000',
'#FFFF00',
'#00EAFF',
'#AA00FF',
'#FF7F00',
'#BFFF00',
'#0095FF',
'#FF00AA',
'#FFD400',
'#6AFF00',
'#0040FF',
'#EDB9B9',
'#B9D7ED',
'#E7E9B9',
'#DCB9ED',
'#B9EDE0',
'#8F2323',
'#23628F',
'#8F6A23',
'#6B238F',
'#4F8F23',
'#000000',
'#737373',
'#CCCCCC',
]

app_dict = {}
for card in AppDevBoard.cards:
    # print(AppDevBoard.cards[card])
    history = []
    for item in AppDevBoard.cards[card].history:
        history.append(item)
    card_history[card] = history
    for app_title in app_list:
        if app_title in re.sub('-', '', AppDevBoard.cards[card]['Title'].lower()):
            if app_title in app_dict.keys():
                app_dict[app_title].append(AppDevBoard.cards[card])
            else:
                app_dict[app_title] = [AppDevBoard.cards[card]]

    # too many cards in archive lane to store history

app_card_id = {}
app_card_days = {}
app_card_size = {}
app_card_structs = {}
app_card_index = {}
app_card_app = {}
index = 0
for key, value in app_dict.items():
    index += 1
    app_card_index[key] = []
    app_card_app[key] = []
    for card in value:
        app_card_app[key].append(key)
        app_card_index[key].append(index)
        for event in card_history[card['Id']]:
            if event['Type'] == 'CardCreationEventDTO':
                if key in app_card_days.keys():
                    app_card_days[key].append((datetime.now() - event['DateTime']).days)
                else:
                    app_card_days[key] = [(datetime.now() - event['DateTime']).days]
                break
        if key in app_card_size.keys():
            size = 1 if card['Size'] == 0 else card['Size']
            app_card_size[key].append(size)
            app_card_id[key].append(card['Title'])
        else:
            size = 1 if card['Size'] == 0 else card['Size']
            app_card_size[key] = [size]
            # if not card['ExternalCardID']:
                # app_card_id[key] =
            app_card_id[key] = [card['Title']]
# add empty arrays for apps with no data
for key in app_list:
    if key not in app_card_id.keys():
        app_card_id[key] = []
        app_card_days[key] = []
        app_card_size[key] = []
        app_card_index[key] = []
        app_card_app[key] = []
traces = []

for i, app in enumerate(app_list):
    traces.append({
        "x": app_card_days[app],
        # y=app_card_size[app],
        "y": app_card_app[app],
        "name": app,
        "mode": "markers",
        "marker": {
            "size": 10,
            "color": app_card_color[i],
            "line": {
                "width": 2
            }
        },
        "text": app_card_id[app],
        "type": "scatter"
    })
app_layout = dict(title='Cards Per Application',
                  yaxis=dict(zeroline=False, title="Application"),
                  xaxis=dict(zeroline=False, title="Days Since Creation"),
                  hovermode="closest"
                  )
fig = dict(data=traces, layout=app_layout)
py.plot(fig, filename='Cards-Per-Application', auto_open=False)

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
    if time_since_move > timedelta(days=3):
        lane_title = AppDevBoard.Lanes[AppDevBoard.cards[card[0]]["LaneId"]]["Title"]
        if lane_title in stuck_parent_lanes:
            stuck_cards.append((AppDevBoard.cards[card[0]], time_since_move))
        elif lane_title in ["Other", "Development"]:
            parent_lane_id = AppDevBoard.Lanes[AppDevBoard.cards[card[0]]["LaneId"]]["ParentLaneId"]
            if AppDevBoard.Lanes[parent_lane_id]["Title"] == "Active":
                stuck_cards.append((AppDevBoard.cards[card[0]], time_since_move))
    all_card_moves[card[0]] = card_move_events
stuck_cards.sort(key=take_second, reverse=True)  # Sort stuck cards in descending order by the time since last move
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
        size = int(AppDevBoard.cards[hist[0]]["Size"])
        if item[0] == "Dev Complete" and dev_complete_limit is False\
                and parser.parse(item[1]) >= utc.localize(datetime.combine(last_monday, datetime.min.time())):
            for user in card_users:
                weekly_points_per_user[user["FullName"]] += size
                if user in cards_developed_this_week.keys():
                    cards_developed_this_week[user["FullName"]] += size
                else:
                    cards_developed_this_week[user["FullName"]] = size
            dev_complete_limit = True
        if item[0] == "Passed QA" and passed_qa_limit is False\
                and parser.parse(item[1]) >= utc.localize(datetime.combine(last_monday, datetime.min.time())):
            for user in card_users:
                weekly_points_per_user[user["FullName"]] += size
            passed_qa_limit = True
        if item[0] == "Testing" and\
                parser.parse(item[1]) >= utc.localize(datetime.combine(last_monday, datetime.min.time())):
            weekly_points_per_user["Cindy Sorrick"] += size

# Remove users who have no points this week
remove_keys = []
for key, value in weekly_points_per_user.items():
    if value == 0:
        remove_keys.append(key)
for key in remove_keys:
    del weekly_points_per_user[key]

weekly_points_per_user_data = [go.Bar(
    x=list(weekly_points_per_user.keys()),
    y=list(weekly_points_per_user.values())
)]

py.plot(weekly_points_per_user_data, filename='Weekly-Points-Per-User', auto_open=False)
print("Weekly Points Per User... Done")
limit_colors = []
total_cards_list = []
wip_limit_list = []
lane_limit_pie_list = []
pie_annotation_list = []
index = 0
for lane in AppDevBoard.top_level_lanes:

    # Calculate size of cards in lane vs lane WIP limit
    size = 0

    # pipe_one.gauge("Leankit.Lanes.Limits."+lane["Title"], lane["CardLimit"])
    for card in lane["Cards"]:
            if card["Size"] == 0:
                card["Size"] = 1
            size += card["Size"]
    for child_lane in lane["ChildLanes"]:
        for card in child_lane["Cards"]:
            if card["Size"] == 0:
                card["Size"] = 1
            size += card["Size"]
    # pipe_one.gauge("Leankit.Lanes.TotalSizes."+lane["Title"], size)
    size_available = int(lane["CardLimit"]) - size
    if lane["Title"] in stuck_parent_lanes:
        total_cards_list.append(size)
        wip_limit_list.append(int(lane["CardLimit"]))
        if size > int(lane["CardLimit"]):
            limit_colors.append('#f7bfbb')
        else:
            limit_colors.append('#bcffcc')

    # Calculate cycle time for each individual card within the lane
    cards = []
    cycle_times = []
    total_lane_cycle_time = 0
    for card in lane["Cards"]:
        card_cycle_time = (datetime.now() - parser.parse(card["LastMove"])).total_seconds() / 86400.0
        total_lane_cycle_time += card_cycle_time
        # Gauge cycle time for card
        for username in card["AssignedUsers"]:
            cards.append("ID-" + str(card["ExternalCardID"]))
            cycle_times.append(card_cycle_time)
    for child_lane in lane["ChildLanes"]:
        for card in child_lane["Cards"]:
            card_cycle_time = (datetime.now() - parser.parse(card["LastMove"])).total_seconds() / 86400.0
            total_lane_cycle_time += card_cycle_time
            # Gauge cycle time for card
            for username in card["AssignedUsers"]:
                cards.append("ID-" + str(card["ExternalCardID"]))
                cycle_times.append(card_cycle_time)

    # Gauge cycle time for lane
    # pipe_one.gauge("Leankit.Lanes.CycleTimes."+lane["Title"], total_lane_cycle_time)
    if lane["Title"] in possible_stuck_lanes:
        cycle_times_in_lane = [go.Bar(
            x=cards,
            y=cycle_times
        )]
        cycle_times_in_lane_layout = go.Layout(
            title=lane["Title"],
            xaxis=dict(
                title='Card ID'
            ),
            yaxis=dict(
                title='Time (Days)'
            )
        )
        fig = go.Figure(data=cycle_times_in_lane, layout=cycle_times_in_lane_layout)
        # py.plot(fig, filename=lane["Title"], auto_open=False)
        print(lane["Title"] + "... Done")
    # Track number of cards moved to "Done" this week
    if lane["Title"] == "Done":
        for card in lane["Cards"]:
            if parser.parse(card["LastMove"]) >= datetime.combine(last_monday, datetime.min.time()):
                size_of_cards_deployed_this_week += card["Size"]
        for child_lane in lane["ChildLanes"]:
            for card in child_lane["Cards"]:
                if parser.parse(card["LastMove"]) >= datetime.combine(last_monday, datetime.min.time()):
                    size_of_cards_deployed_this_week += card["Size"]
            for child_child_lane in child_lane["ChildLanes"]:
                for card in child_child_lane["Cards"]:
                    if parser.parse(card["LastMove"]) >= datetime.combine(last_monday, datetime.min.time()):
                        size_of_cards_deployed_this_week += card["Size"]

limit_trace = go.Table(
    header=dict(
        values=['Lane', 'Total Card Size', 'WIP Limit'],
        fill=dict(color='#60656d'),
        line=dict(color='white'),
        font=dict(color='white', size=14),
        height=40
    ),
    cells=dict(
        values=[stuck_parent_lanes, total_cards_list, wip_limit_list],
        fill=dict(color=[limit_colors]),
        line=dict(color='white'),
        font=dict(color='black', size=14),
        height=40
    )
)

limit_data = [limit_trace]

py.plot(limit_data, filename="Lane-Limits-Table", auto_open=False)

# gauge total size of cards in dev complete this week by user
cards_developed_this_week_data = [go.Bar(
    x=list(cards_developed_this_week.keys()),
    y=list(cards_developed_this_week.values())
)]

py.plot(cards_developed_this_week_data, filename='Cards-Developed-This-Week', auto_open=False)
print("Cards Developed This Week... Done")

stuck_cards_id = []
stuck_cards_time = []
stuck_cards_lane = []
stuck_cards_title = []
stuck_cards_block_reason = []
stuck_cards_comment = []
for card in stuck_cards:
    stuck_cards_id.append("ID-" + str(card[0]["ExternalCardID"]))
    stuck_cards_title.append(card[0]["Title"])
    stuck_cards_time.append(int(int(card[1].total_seconds())/86400.0))
    if AppDevBoard.Lanes[card[0]["LaneId"]]["Title"] in ["Other", "Development"]:
        stuck_cards_lane.append("Active")
    else:
        stuck_cards_lane.append(AppDevBoard.Lanes[card[0]["LaneId"]]["Title"])
    stuck_cards_block_reason.append(str(card[0]['BlockReason']).replace("\n", ""))
    if card[0]['CommentsCount'] > 0 and stuck_cards_lane[-1] == "Active":
        clean_str = cleanhtml(card[0].comments[-1]['Text'])
        if len(clean_str) > 300:
            stuck_cards_comment.append(clean_str[0:301] + " ...")
        else:
            stuck_cards_comment.append(clean_str)
    else:
        stuck_cards_comment.append("")
trace = go.Table(
    header=dict(
        values=['Card', 'Title', 'Days Since Update', 'Lane', 'Block Reason', 'Last Comment (if in Development)'],
        fill=dict(color='red'),
        font=dict(color='white', size=14)
    ),
    cells=dict(
        values=[stuck_cards_id, stuck_cards_title, stuck_cards_time, stuck_cards_lane, stuck_cards_block_reason,
                stuck_cards_comment],
        height=50,
        fill=dict(color='#f7bfbb'),
        font=dict(color='black', size=14)
    )
)
stuck_cards_data = [trace]
stuck_div = py.plot(stuck_cards_data, filename='Stuck-Cards', auto_open=False)
