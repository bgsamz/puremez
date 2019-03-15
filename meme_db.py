import sqlite3
import json
import random

MEME_DB_PATH = "memes.db"


class MemeDB:
    def __init__(self):
        self.connection = sqlite3.connect(MEME_DB_PATH, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS meme_info (
                ts TEXT,
                file_name TEXT,
                file_type TEXT,
                user TEXT,
                reactions TEXT,
                reaction_count INTEGER
            );
        """)

    def add_reaction(self, reaction_event):
        self.cursor.execute('SELECT reactions, reaction_count FROM meme_info WHERE ts=?',
                            (reaction_event['item']['ts'],))
        row = self.cursor.fetchone()
        if row:
            reactions = json.loads(row['reactions'])
            if reaction_event['reaction'] in reactions:
                reactions[reaction_event['reaction']] += 1
            else:
                reactions[reaction_event['reaction']] = 1
            new_reactions = json.dumps(reactions)
            self.cursor.execute('UPDATE meme_info SET reactions=?, reaction_count=? WHERE ts=?',
                                (new_reactions, row['reaction_count']+1, reaction_event['item']['ts']))

    def remove_reaction(self, reaction_event):
        self.cursor.execute('SELECT reactions, reaction_count FROM meme_info WHERE ts=?',
                            (reaction_event['item']['ts'],))
        row = self.cursor.fetchone()
        if row:
            reactions = json.loads(row['reactions'])
            if reaction_event['reaction'] in reactions:
                if reactions[reaction_event['reaction']] > 1:
                    reactions[reaction_event['reaction']] -= 1
                else:
                    del reactions[reaction_event['reaction']]
            else:
                return
            new_reactions = json.dumps(reactions)
            self.cursor.execute('UPDATE meme_info SET reactions=?, reaction_count=? WHERE ts=?',
                                (new_reactions, row['reaction_count']-1, reaction_event['item']['ts']))

    def insert_meme(self, message_event):
        self.cursor.execute('INSERT INTO meme_info (ts, file_name, file_type, user, reactions, reaction_count) '
                            'VALUES (?,?,?,?,?,?)',
                            (message_event['ts'], message_event['files'][0]['name'],
                             message_event['files'][0]['filetype'], message_event['user'], '{}', 0))

    def delete_meme(self, delete_event):
        self.cursor.execute('DELETE FROM meme_info WHERE ts=?', (delete_event['ts'],))

    def get_memes(self):
        self.cursor.execute('SELECT * FROM meme_info')
        rows = self.cursor.fetchall()
        messages = []
        for row in rows:
            reactions = json.loads(row['reactions'])
            key_list = []
            for key in reactions.keys():
                key_list.append(':{}:(x{})'.format(key, reactions[key]))
            formatted_reactions = ','.join(key_list)
            messages.append('Meme {} added by <@{}> with {} reactions: {}'
                            .format(row['file_name'], row['user'], row['reaction_count'], formatted_reactions))
        return messages

    def get_highest_rated_from_user(self, user):
        self.cursor.execute('SELECT * FROM meme_info WHERE user=? ORDER BY reaction_count DESC', (user,))
        rows = self.cursor.fetchone()
        return rows['ts']

    def get_random_meme_from_user(self, user):
        self.cursor.execute('SELECT * FROM meme_info WHERE user=?', (user,))
        rows = self.cursor.fetchall()
        return rows[random.randint(0, len(rows)-1)]['ts']

    def get_random_meme(self):
        self.cursor.execute('SELECT * FROM meme_info')
        rows = self.cursor.fetchall()
        return rows[random.randint(0, len(rows)-1)]['ts']
