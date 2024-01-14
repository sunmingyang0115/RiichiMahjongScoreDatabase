import functools
from datetime import date
from typing import Union, List, Callable
from richii.module.db import Database, GameRecord


# deprecated
def parse_ping(s: str) -> Union[int, None]:
    if (not s.startswith("<@")) or (not s.endswith(">")):
        return None
    s = s[2:-1]
    if s.startswith("!"):
        s = s[1:]
    try:
        return int(s)
    except:
        return None


def ping_to_userid(s: str) -> str:
    return functools.reduce(lambda a, b: a + b, [i for i in s if i.isnumeric()])


async def command_fetch(frags: List[str], db: Database):
    if len(frags) != 4:
        raise RuntimeError("Not enough/too many arguments!")
    return db.get_user_games(ping_to_userid(frags[3]))


# deprecated
async def command_store(frags: List[str], msg_id: str, db: Database):
    if len(frags) != 11:
        raise RuntimeError("Not enough/too many arguments!")
    players = []
    for i in range(3, 11, 2):
        ping = ping_to_userid(frags[i])
        if ping is None:
            raise RuntimeError(f"{i + 1}th argument is not a ping")
        money = None
        try:
            money = int(frags[i + 1])
        except:
            raise RuntimeError(f"{i + 2}th argument isn't an integer")
        players.append((ping, money))
    record = GameRecord("discord:" + msg_id, str(date.today()), [v[0] for v in players], [v[1] for v in players])
    db.new_game(record)


async def command_store2(frags: List[str], msg_id: str, db: Database):
    players = find_score2(frags)
    if players is None:
        raise RuntimeError("Invalid Data")
    record = GameRecord("discord:" + msg_id, str(date.today()), [v[0] for v in players], [v[1] for v in players])
    db.new_game(record)


def find_score2(frags: List[str]) -> Union[list[tuple[str, int]], None]:
    tot = 0
    score_list = []
    for i in range(3, 11, 2):
        tot += float(frags[i + 1])
    if 90 <= tot <= 100 and abs(round(tot) - tot) < 1e-6:
        for i in range(3, 11, 2):
            usr_id = ping_to_userid(frags[i])
            score = float(frags[i + 1])
            score_list.append((usr_id, 100 * round(10 * score)))
        return score_list
    elif tot % 1000 == 0:
        for i in range(3, 11, 2):
            usr_id = ping_to_userid(frags[i])
            score = int(frags[i + 1])
            score_list.append((usr_id, 100 * round(10 * score)))
        return score_list
    else:
        return None


# deprecated
def findscore(inp: str) -> Union[dict[int, int], None]:
    # replace with input() later
    entries = inp.split("\n")
    score_dict = {}
    tot = 0
    for entry in entries:
        score_pair = entry[2:].split(">")
        tot += float(score_pair[1])

    if 90 <= tot <= 100 and abs(round(tot) - tot) < 1e-6:
        for entry in entries:
            score_pair = entry[2:].split(">")
            score_dict[int(score_pair[0])] = 100 * round(10 * float(score_pair[1]))
        '''
    ret = ""
    for player in scoredict:
        ret += "<@" + str(player) + ">" + " " + str(scoredict[player]) + "\n"
    '''
        return score_dict;
    elif tot % 1000 == 0:
        for entry in entries:
            score_pair = entry[2:].split(">")
            score_dict[int(score_pair[0])] = int(score_pair[1])
        '''
    ret = ""
    for player in scoredict:
        ret += str(player) + " " + str(scoredict[player]) + "\n"
    '''
        return score_dict;
    else:
        return None

# deprecated
def get_response(message: str) -> str:
    p_message = message.lower()

    if p_message[0] == '<':
        print(findscore(p_message))  # outputs the dictionary in console
        return 'scores saved'

    if p_message == '!help':
        return '`this is a help message nya~`'

    return 'I didn\'t understand what u said nya~~'
