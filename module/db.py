from __future__ import annotations
import sqlite3
from typing import TYPE_CHECKING
from mjgame import MJGameNya
if TYPE_CHECKING:
    from typing import Union
    from io import TextIOBase

def _args(*a):
    return dict(zip([f"a{i}" for i in range(len(a))], a))

class GameRecordNya:
    """
    A record representing one game. The users and final_scores members are always sorted from high scores to low scores.
    """
    game_id: str
    date: str
    users: list[str]
    final_scores: list[int]
    _timestamp: int

    def __init__(self, game_id: str, date: str, users: list[str], final_scores: list[int]):
        if len(users) != len(set(users)):
            raise ValueError("Duplicate users found")
        zipped = list(zip(users, final_scores))
        zipped.sort(key=lambda x: x[1], reverse=True)

        if date.startswith("unix:"):
            self._timestamp = int(date.removeprefix("unix:"))
        else:
            raise ValueError("Unrecognized timestamp format")

        users, final_scores = zip(*zipped)
        self.game_id = game_id
        self.date = date
        self.users = list(users)
        self.final_scores = list(final_scores)
    
    def __eq__(self, __value: object) -> bool:
        if isinstance(__value, GameRecordNya):
            return __value.game_id == self.game_id and \
                __value._timestamp == self._timestamp and \
                __value.users == self.users and \
                __value.final_scores == self.final_scores
        return False
    
    def __lt__(self, __value: object) -> bool:
        if isinstance(__value, GameRecordNya):
            return self.game_id < __value.game_id
        return False
    
    def get_timestamp(self):
        return self._timestamp

    def from_mjgame(mjgame: MJGameNya) -> GameRecordNya:
        users, scores = [list(i) for i in zip(*mjgame.get_raw_scores().items())]
        return GameRecordNya(mjgame.get_gameid(), f"unix:{mjgame.get_date()}", users, scores)

    def into_mjgame(self) -> MJGameNya:
        return MJGameNya(self._timestamp, self.game_id, dict(zip(self.users, self.final_scores)))


class UserScoreRecordNya:
    """
    A record representing a user's participation in a game.
    """
    user_id: str
    game_id: str
    date: str
    # 1-indexed rank
    rank: int
    final_score: int
    _timestamp: int

    def __init__(self, user_id: str, game_id: str, date: str, rank: int, final_score: int):
        if date.startswith("unix:"):
            self._timestamp = int(date.removeprefix("unix:"))
        else:
            raise ValueError("Unrecognized timestamp format")

        self.user_id = user_id
        self.game_id = game_id
        self.date = date
        self.rank = rank
        self.final_score = final_score

    def __eq__(self, __value: object) -> bool:
        if isinstance(__value, UserScoreRecordNya):
            return __value.user_id == self.user_id and \
                __value.game_id == self.game_id and \
                __value._timestamp == self._timestamp and \
                __value.rank == self.rank and \
                __value.final_score == self.final_score
        return False
    
    def __lt__(self, __value: object) -> bool:
        if isinstance(__value, UserScoreRecordNya):
            return self.game_id < __value.game_id
        return False

    def __repr__(self):
        return str(self.user_id) + " " + str(self.game_id) + " " + str(self.date) + " " + str(self.rank) + " " + str(self.final_score)
    
    def get_timestamp(self):
        return self._timestamp

class UserStatsRecordNya:
    """
    A record representing a user's global statistics
    """

    user_id: str
    games_played: int
    games_won: int
    sum_ranks: int

    def __init__(self, user_id: str, games_played: int, games_won: int, sum_ranks: int):
        self.user_id = user_id
        self.games_played = games_played
        self.games_won = games_won
        self.sum_ranks = sum_ranks
    
    def __eq__(self, __value: object) -> bool:
        if isinstance(__value, UserStatsRecordNya):
            return __value.user_id == self.user_id and \
                __value.games_played == self.games_played and \
                __value.games_won == self.games_won and \
                __value.sum_ranks == self.sum_ranks
        return False
    
    def __lt__(self, __value: object) -> bool:
        if isinstance(__value, UserStatsRecordNya):
            return self.user_id < __value.user_id
        return False
    
    def __repr__(self) -> str:
        return self.user_id + " " + str(self.games_played) + " " + str(self.games_won) + " " + str(self.sum_ranks)


class DatabaseNya:
    """
    Holds a simple database used to store user data
    """
    conn: sqlite3.Connection

    def __init__(self, path="db.sqlite"):
        """
        Initializes the database to read from a file argument. Defaults to db.sqlite
        """
        self.conn = sqlite3.connect(path)
        self.conn.execute("""
create table if not exists "user_scores" (
	"game_id"	integer not null,
	"user_id"	text not null,
	"date"	text not null,
	"rank"	integer not null,
	"score"	integer not null
)
""")
        self.conn.execute("""
create table if not exists "user_stats" (
    "user_id"       text not null unique,
    "games_played"  integer not null,
    "games_won"     integer not null,
    "sum_ranks"     integer not null,
    primary key("user_id")
)
""")
        self.conn.isolation_level = None

    def new_game(self, record: GameRecordNya):
        """
        Records a new game in the database
        """
        c = self.conn.cursor()
        if self.get_game(record.game_id) != None:
            raise ValueError("Game already exists")
        c.execute("begin")
        for i in range(len(record.users)):
            c.execute(
                "insert into user_scores (game_id, user_id, date, rank, score) values (:a0, :a1, :a2, :a3, :a4)",
                _args(record.game_id, record.users[i], record.date, i + 1, record.final_scores[i])
            )
            c.execute(
                "insert into user_stats (user_id, games_played, games_won, sum_ranks) values (:a0, 1, :a1, :a2)\n" +
                "on conflict(user_id) do update set games_played = games_played + 1, games_won = games_won + :a1, sum_ranks = sum_ranks + :a2",
                _args(record.users[i], 1 if i == 0 else 0, i + 1)
            )
        c.execute("commit")
        c.close()

    def get_user_games(self, user_id: str) -> list[UserScoreRecordNya]:
        """
        Get all games a user has participated in
        """
        c = self.conn.cursor()
        c.execute("select game_id, date, rank, score from user_scores where user_id = :a0", _args(user_id,))
        scores = [UserScoreRecordNya(user_id, v[0], v[1], v[2], v[3]) for v in c.fetchall()]
        c.close()
        return scores

    def get_game(self, game_id: str) -> Union[GameRecordNya, None]:
        """
        Get the record for one game
        """
        c = self.conn.cursor()
        c.execute("select user_id, date, score from user_scores where game_id = :a0", _args(game_id,))
        value = c.fetchall()
        if len(value) == 0: return None
        if len(value) not in [3, 4]: raise RuntimeError(f"Invalid game detected; DB is corrupted (game_id={game_id})")
        users, dates, scores = zip(*value)
        game = GameRecordNya(game_id, dates[0], users, scores)
        c.close()
        return game

    def get_user_stats(self, user_id: str) -> Union[UserStatsRecordNya, None]:
        """
        Gets a user's stats
        """
        c = self.conn.cursor()
        c.execute("select games_played, games_won, sum_ranks from user_stats where user_id = :a0", _args(user_id,))
        res = c.fetchone()
        c.close()
        if res == None:
            return None
        return UserStatsRecordNya(user_id, res[0], res[1], res[2])

    def delete_game(self, game_id: str):
        """
        Remove a game from the database
        """
        c = self.conn.cursor()
        c.execute("begin")
        game = self.get_game(game_id)
        for i in range(len(game.users)):
            c.execute("update user_stats\n" + 
                      "set games_played = games_played - 1, games_won = games_won - :a1, sum_ranks = sum_ranks - :a2\n" +
                      "where user_id = :a0",
                      _args(game.users[i], 1 if i == 0 else 0, i + 1))
        c.execute("delete from user_scores where game_id = :a0", _args(game_id,))
        c.execute("commit")
        c.close()
    
    def list_user_stats(self, sorting: str, limit: int = -1) -> list[UserStatsRecordNya]:
        """
        List top n users using a specified sorting order.
        Sorting can be one of "games_played", "games_won", or "avg_rank"
        """
        order_by = "!invalid!"
        if sorting == "games_played":
            order_by = "games_played desc, user_id asc"
        elif sorting == "games_won":
            order_by = "games_won desc, user_id asc"
        elif sorting == "avg_rank":
            order_by = "cast(sum_ranks as float) / cast(games_played as float) asc, user_id asc"
        else:
            raise ValueError("sorting has an invalid value")
        sql = f"select user_id, games_played, games_won, sum_ranks from user_stats order by {order_by} limit :a0"
        c = self.conn.cursor()
        c.execute(sql, _args(limit))
        records = [UserStatsRecordNya(v[0], v[1], v[2], v[3]) for v in c.fetchall()]
        c.close()
        return records


    def fix_user_stats(self):
        """
        Regenerates the entire user_stats table from user_games (an expensive operation)
        """
        raise NotImplementedError()


    def export_as_csv(self, user_scores: TextIOBase, user_stats: TextIOBase):
        """
        Exports the database to multiple CSV files
        """
        c = self.conn.cursor()

        # warning: doesn't do escaping! careful of arbitrary strings
        c.execute("select * from user_scores")
        user_scores.write("game_id,user_id,date,rank,score\n")
        for row in c:
            user_scores.write(','.join([str(i) for i in row]) + "\n")
        
        c.execute("select * from user_stats")
        user_stats.write("user_id,games_played,games_won,sum_ranks\n")
        for row in c:
            user_stats.write(','.join([str(i) for i in row]) + "\n")
        
        c.close()