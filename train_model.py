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


def clean_html(raw_html):
    clean_r = re.compile('<.*?>')
    clean_text = re.sub(clean_r, '', raw_html)
    return clean_text


training_cards = []
for key, lane in AppDevBoard['Lanes'].items():
    if lane['Title'] == 'Passed QA':
        training_cards = lane.cards

# We want to train on every card in the Passed QA lane.
# Figure out what data best relates to the time it took to move from Active to here.
# Then, we want to make a prediction on how long each card in Active will take to move into Passed QA.
# Plot our results from a test portion of the data.
# The most obvious problem is the amount of data here to test on.  We haven't actually stored any data in a database


# inputs: TypeName (Task, Bug, etc), size, assigned user(s), priority
# making sense of title and description? (clean html text first)
# making sense of card comments?,
training_data = []
for card in training_cards:
    card_data = []
    card_data.append(card['TypeName'])
    card_data.append(card['Size'])
    for user in card['AssignedUsers']:
        if user['FullName'] != 'Cindy Sorrick':
            card_data.append(user['FullName'])
    for comment in card.comments:
        card_data.append(clean_html(comment['Text']))
    training_data.append(card_data)

print('done')

