from config import BOT_TOKEN
import time
import re
from slackclient import SlackClient
import logging
from meme_handler import (
    download_meme,
    readback_meme
)
from meme_db import MemeDB
from youtube import youtube_first_result

logging.basicConfig()
# BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
MEME_CHANNEL = None
MEME_CHANNEL_NAME = "memez"

# instantiate Slack client
slack_client = SlackClient(BOT_TOKEN)
# starterbot's user ID in Slack: value is assigned after the bot starts up
starterbot_id = None
DATABASE = MemeDB()

# constants
RTM_READ_DELAY = 1  # 1 second delay between reading from RTM
EXAMPLE_COMMAND = "send meme"
COMMAND1 = "do"
COMMAND2 = "send"
COMMAND3 = "send meme"
GET_MEMES = "get memes"
BABY_SHARK = "alexa play baby shark"
GUESS_YOUTUBE = "ok google play"
GET_RANDOM_MEMES = "get random meme"
GET_MEMES_FROM = "<@(|[WU].+?)>"
MEME_COMMAND = "!meme"
UNMEME_COMMAND = "!unmeme"
STATS = "stats"

MENTION_REGEX = "^<@(|[WU].+?)>(.*)"


def parse_bot_commands(slack_events):
    """
        Parses a list of events coming from the Slack RTM API to find bot commands.
        If a bot command is found, this function returns a tuple of command and channel.
        If its not found, then this function returns None, None.
    """
    for event in slack_events:
        print(event)
        if event["type"] == "message" and "subtype" not in event and 'files' not in event:
            if "thread_ts" in event:
                handle_thread_response(event)
            else:
                user_id, message = parse_direct_mention(event["text"])
                if user_id == starterbot_id:
                    return message, event["channel"], event
                elif event['text'].startswith(MEME_COMMAND):
                    label = event['text'].split(MEME_COMMAND, 1)[1].strip()
                    ts = DATABASE.get_meme_by_label(label)
                    upload_file(readback_meme(ts), event['channel'], "<@{}> here's {}".format(event['user'], label))
                elif event["text"].startswith(BABY_SHARK):
                    post_chat_message(event['channel'], 'https://youtu.be/XqZsoesa55w?t=9')
                elif event["text"].startswith(GUESS_YOUTUBE):
                    video_query = event["text"].split(GUESS_YOUTUBE, 1)[1].strip()
                    result = youtube_first_result(video_query)
                    if result is None:
                        result = "Sorry, I couldn't find that video"
                    post_chat_message(event['channel'], result)
        elif event["type"] == "message" and 'files' in event and event['user'] != starterbot_id:
            download_meme(event, BOT_TOKEN)
        elif event['type'] == 'reaction_added' and event['item']['type'] == 'message':
            print("adding reaction")
            DATABASE.add_reaction(event)
        elif event['type'] == 'reaction_removed' and event['item']['type'] == 'message':
            print("removing reaction")
            DATABASE.remove_reaction(event)

    return None, None, None


def handle_thread_response(event):
    if event['text'].startswith(MEME_COMMAND):
        label = event['text'].split(MEME_COMMAND, 1)[1].strip()
        DATABASE.add_label(event['thread_ts'], label)
    elif event['text'].startwith(UNMEME_COMMAND):
        label = event['text'].split(UNMEME_COMMAND, 1)[1].strip()
        DATABASE.remove_label(event['thread_ts'], label)


def parse_direct_mention(message_text):
    """
        Finds a direct mention (a mention that is at the beginning) in message text
        and returns the user ID which was mentioned. If there is no direct mention, returns None
    """
    matches = re.search(MENTION_REGEX, message_text)
    # the first group contains the username, the second group contains the remaining message
    return (matches.group(1), matches.group(2).strip()) if matches else (None, None)


def handle_command(command, channel, event=None):
    """
        Executes bot command if the command is known
    """
    # Default response is help text for the user
    default_response = "Not sure what you mean. Try *{}*.".format(EXAMPLE_COMMAND)

    # Finds and executes the given command, filling in response
    response = None
    # This is where you start to implement more commands!
    if command.startswith(COMMAND1):
        response = "Sure...write some more code then I can do that!"
    elif command.startswith(STATS):
        memes = DATABASE.get_all_memes()
        for meme in memes.keys():
            user = memes[meme]['user']
            labels, reactions = None, None
            if memes[meme]['labels']:
                labels = ','.join(['`{}`'.format(label) for label in memes[meme]['labels']])
            if memes[meme]['reactions']:
                reactions = ','.join([':{}:(x{})'.format(reaction, count) for reaction, count in memes[meme]['reactions'].items()])
            upload_file(
                readback_meme(meme),
                comment='Meme from <@{}>\nWith labels {}\nWith reactions {}'.format(user, labels, reactions),
                thread_ts=event['ts']
            )
        return
    elif command.startswith(COMMAND3):
        post_meme(channel)
        return
    elif command.startswith(COMMAND2):
        response = "Send what exactly? need more code"
    elif command.startswith(GET_RANDOM_MEMES):
        matches = re.search(GET_MEMES_FROM, command)
        if matches:
            user = matches.group(1)
            meme_ts = DATABASE.get_random_meme_from_user(user)
            upload_file(readback_meme(meme_ts), comment='Random meme from: <@{}>'.format(user))
            return
        meme_ts = DATABASE.get_random_meme()
        upload_file(readback_meme(meme_ts), comment='<!here> have a random meme!')
        return
    elif command.startswith(GET_MEMES):
        matches = re.search(GET_MEMES_FROM, command)
        if matches:
            user = matches.group(1)
            meme_ts = DATABASE.get_highest_rated_from_user(user)
            upload_file(readback_meme(meme_ts), comment='Highest rated meme from: <@{}>'.format(user))
            return

# Comment out for now
        # for response in DATABASE.get_memes():
        #     post_chat_message(channel, response)
        # return

    # Sends the response back to the channel
    post_chat_message(channel, response or default_response)


def post_chat_message(channel, message):
    return slack_client.api_call(
        "chat.postMessage",
        channel=channel,
        text=message,
        link_names=True
    )


def upload_file(file, channel=None, comment=None, thread_ts=None):
    return slack_client.api_call(
        "files.upload",
        channels=channel or MEME_CHANNEL,
        file=file,
        initial_comment=comment,
        thread_ts=thread_ts
    )


def post_meme(channel, path=None):
    if path is None:
        path = 'memes/ludicolo.jpg'

    with open(path, 'rb') as file_content:
        upload_file(file_content, channel)


if __name__ == "__main__":
    if slack_client.rtm_connect(with_team_state=False):
        print("MemeBot connected and running!")
        # Read bot's user ID by calling Web API method `auth.test`
        starterbot_id = slack_client.api_call("auth.test")["user_id"]
        channels = slack_client.api_call('channels.list')['channels']
        for channel in channels:
            if channel['name'] == MEME_CHANNEL_NAME:
                MEME_CHANNEL = channel['id']
        while True:
            command, channel, event = parse_bot_commands(slack_client.rtm_read())
            if command is not None:
                print('got command ' + command)
                print('on channel ' + channel)
                if command:
                    handle_command(command, channel, event=event)
            time.sleep(RTM_READ_DELAY)
    else:
        print("Connection failed. Exception traceback printed above.")
