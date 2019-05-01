import sys
import tensorflow as tf
from tensorflow import keras
import leankit
import re

domain = sys.argv[1]
username = sys.argv[2]
password = sys.argv[3]

leankit.api.authenticate(domain, username, password)
AppDevID = leankit.get_boards()[0]["Id"]
AppDevBoard = leankit.Board(AppDevID)

'''
def get_done_lane_cards(lane):
    cards = []
    if len(lane.descendants) > 0:
        for descendant in lane.descendants:
            cards.extend(get_done_lane_cards(descendant))
    cards.extend(lane.cards)
    return cards


training_cards = []

for key, lane in AppDevBoard['Lanes'].items():
    if lane['Title'] == 'Done':
        training_cards = get_done_lane_cards(lane)
'''
training_cards = []
for key, lane in AppDevBoard['Lanes'].items():
    if lane['Title'] == 'Passed QA':
        training_cards = lane.cards

print(training_cards)

# We want to train on every card in the done Passed QA lane.
# Figure out what data best relates to the time it took to move from creation to here.
# Then, we want to make a prediction on how long each card in Active will take to move into Passed QA.
# Plot our results from a test portion of the data.
# The most obvious problem is the amount of data here to test on.  We haven't actually stored any data in a database


# inputs: time since creation, TypeName (Task, Bug, etc), size, assigned user(s), priority
# making sense of title and description? (clean html text first)
# making sense of card comments?,
training_data = []


def clean_html(raw_html):
    clean_r = re.compile('<.*?>')
    clean_text = re.sub(clean_r, '', raw_html)
    return clean_text

