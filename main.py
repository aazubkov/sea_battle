from random import randint
from random import choice
import time
import os

# declare Exceptions
class BoardException(Exception):
    pass


class BoardOutException(BoardException):
    def __str__(self):
        time.sleep(1)
        return f"\t {g.x.trans['mimo_doski'][g.x.lang]}"


class BoardUsedException(BoardException):
    def __str__(self):
        time.sleep(1)
        return f"\t {g.x.trans['used_cell'][g.x.lang]}"


class BoardWrongShipException(BoardException):
    pass


# declare Language to translate printing text on both Russian and English
# both versions are set in 'translation.txt' file and get reached by tags
class Language:
    def __init__(self, lng):
        self.lang = lng
        self.f = open('translation.txt', 'r', encoding='utf8')
        self.tags = ['lang', 'greet', 'user_board', 'comp_board', 'user_turn', 'board_size',
                     'comp_turn', 'user_win', 'comp_win', 'mimo_doski', 'used_cell', 'comp_shoot',
                     'user_shoot', 'enter_coord', 'enter_digs', 'ship_dead', 'ship_hit', 'shot_miss',
                     'print_score', 'print_bit', 'failed_manual_ship', 'thanx_for_play', 'wanna_play',
                     'wrong_ship_pos', 'place_ships', 'manual_rules', 'mnl_board_again']
        self.trans = {}
        self.read_translation()

    def find_tag(self, tag):                                    # finds tag in file and read the text
        self.f.seek(0, 0)
        for i, line in enumerate(self.f):
            if line == tag + '\n':
                rus = self.read_phrase()
                eng = self.read_phrase()
                self.trans.update({tag: {'R': rus, 'E': eng}})

    def read_phrase(self):                                      # read the phrase up to \n
        par = ""
        line = self.f.readline()
        while len(line) != 1:
            par += line
            line = self.f.readline()
        par = par.strip()
        return par

    def read_translation(self):                                 # set phrases for all tags
        for t in self.tags:
            self.find_tag(t)
        self.f.close()

    def prnt(self, tag):                                        # prints phrase
        print(f"\t {self.trans[tag][self.lang]}")
        time.sleep(1)

    def prnt_in_text(self, tag):                                # returns phrase as string
        return f"\t {self.trans[tag][self.lang]}"


# declare Dot class
class Dot:
    def __init__(self, x, y):                                   # coordinates
        self.x = x
        self.y = y

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __repr__(self):
        return f"({self.x}, {self.y})"

    def dist(self, a):                                          # calculate so called 'distance' between 2 Dots
        return ((self.x - a.x) ** 2 + (self.y - a.y) ** 2) ** 0.5

# declare Dot class
class Ship:
    def __init__(self, bow, l, o):                              # bow as Dot, length, orientation
        self.bow = bow
        self.l = l
        self.o = o
        self.lives = l

    @property
    def dots(self):                                             # list of Dots belonging to Ship
        ship_dots = []
        for i in range(self.l):
            cur_x = self.bow.x
            cur_y = self.bow.y

            if self.o == 0:
                cur_x += i

            elif self.o == 1:
                cur_y += i

            ship_dots.append(Dot(cur_x, cur_y))

        return ship_dots

    def shooten(self, shot):
        return shot in self.dots

# declare special class for Ship which is under AI's fire at the current turn
# idea is to focus AI only on killing this special Ship
# high-priority Dots around the Ship are genetrated
class ShipUnderFire:
    def __init__(self):
        self.dots = []                          # known Ship Dots
        self.orient = ''                        # Ship orientation  (h - hor, v - vert or hv if 1 Dot)
        self.prior = []                         # high priority Dots around the Ship

    def update_dots(self, d):                   # updating Ship Dots
        self.dots.append(d)
        self.orient = self.define_orient()      # define orientation
        self.prior = self.updt_prior()          # recalculating priority Dots

    def clear_dots(self):                       # clear Dots after Ship is killed
        self.dots = []
        self.prior = []

    def define_orient(self):                     # define orientation: either dx or dy between 2 Dots is 0
        if len(self.dots) == 1:
            res = 'hv'
        else:
            res = 'h' if self.dots[0].x == self.dots[1].x else 'v'
        return res

    def updt_prior(self):                       # recalculates priority Dots after the shot
        dxy = {'hv': [[-1, 0], [1, 0], [0, -1], [0, 1]],
               'v': [[-1, 0], [1, 0]],
               'h': [[0, -1], [0, 1]]}
        res = []
        for sd in self.dots:
            for dx, dy in dxy[self.orient]:
                cur = Dot(sd.x + dx, sd.y + dy)
                if cur not in self.dots:
                    res.append(cur)
        return res


# declare Board class
class Board:
    def __init__(self, hid=False, size=6):
        self.size = size
        self.hid = hid

        self.count = 0

        self.field = [["O"] * size for _ in range(size)]                    # creating of Field

        self.busy = []                                                      # used Dots
        self.ships = []                                                     # list of Ships

        self.avdot = [Dot(i, j) for j in range(size) for i in range(size)]  # creating Available List of  Dots to shoot
        self.suf = ShipUnderFire()                                          # creating empty Ship Under Fire (suf)
        self.prior = []                                                     # prioritized dots around wounded ship

    def updt_prior(self):                                   # recalculates Prior Dots of the Board
        self.prior = []
        for cur in self.suf.prior:
            if not (self.out(cur)) and cur in self.avdot:
                self.prior.append(cur)                      # obviously this list is <= than SUF Prior Dots

    def erase_av_dot(self, d):                              # deletes Dot from Available List
        if d in self.avdot:
            self.avdot.pop(self.avdot.index(d))

    def add_ship(self, ship):                               # adds Ship to Board
        for d in ship.dots:
            if self.out(d) or d in self.busy:
                raise BoardWrongShipException()
        for d in ship.dots:
            self.field[d.x][d.y] = "■"
            self.busy.append(d)

        self.ships.append(ship)
        self.contour(ship)

    def contour(self, ship, verb=False):                    # sets contour of Ship
        near = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1), (0, 0), (0, 1),
            (1, -1), (1, 0), (1, 1)
        ]
        for d in ship.dots:
            for dx, dy in near:
                cur = Dot(d.x + dx, d.y + dy)
                if not (self.out(cur)) and cur not in self.busy:
                    if verb:
                        self.field[cur.x][cur.y] = "."
                        self.erase_av_dot(cur)              # erasing cur from available dots
                    self.busy.append(cur)

    def __str__(self):                                      # prints Board
        res = "  |"
        for i in range(1, self.size + 1):
            res += f' {i} |'
        res += ' y→'
        for i, row in enumerate(self.field):
            res += f"\n{i + 1} | " + " | ".join(row) + " |"
        res += '\nx↓'

        if self.hid:
            res = res.replace("■", "O")
        return res

    def out(self, d):                                       # checks if Dot is outside the Board
        return not ((0 <= d.x < self.size) and (0 <= d.y < self.size))

    def shot(self, d):                                      # shots the Dot
        if self.out(d):
            raise BoardOutException()

        if d in self.busy:
            raise BoardUsedException()

        self.busy.append(d)
        self.erase_av_dot(d)                                # erasing Dot from Available List of Dots

        for ship in self.ships:                             # cycling on all Ships on the Board
            if d in ship.dots:                              # checking if hit the Ship
                ship.lives -= 1
                self.field[d.x][d.y] = "X"
                self.suf.update_dots(d)                     # adds Dot to SUF Dots and update SUF Prior Dots
                self.updt_prior()                           # update Prior Dots of the Board
                if ship.lives == 0:
                    self.count += 1
                    self.contour(ship, verb=True)           # if Ship killed, makes visible its contour
                    g.x.prnt('ship_dead')
                    self.prior = []                                           # clears Prior Dots of Board
                    self.suf.clear_dots()                                     # clears SUF Dots and SUF Prior Dots
                    return True                             # if ship is destroyed - another turn
                else:
                    g.x.prnt('ship_hit')
                    return True

        self.field[d.x][d.y] = "."
        g.x.prnt('shot_miss')
        return False

    def begin(self):
        self.busy = []


# declaring Player class and 2 players - AI and User
class Player:
    def __init__(self, board, enemy):                       # creates boards
        self.board = board
        self.enemy = enemy

    def ask(self):                                          # will be updated for each player
        raise NotImplementedError()

    def move(self):                                         # makes Player's move
        while True:
            try:
                target = self.ask()
                repeat = self.enemy.shot(target)
                return repeat
            except BoardException as e:
                print(e)

    def print_score(self):                                  # prints 'score' as a maximum turns for the Player to win
        print(f'{g.x.prnt_in_text("print_score")}: AI - {len(g.us.board.avdot)}, User - {len(g.ai.board.avdot)}')

class AI(Player):
    def ask(self):
        self.enemy.updt_prior()                             # recaluclating Prior Dots, if any
        self.print_score()                                  # prints 'score' based on unknown Dots on the Board
        if len(self.enemy.prior) > 0:                       # if any Prior Dots - random choice from their list
            d = choice(self.enemy.prior)
        else:
            d = choice(self.enemy.avdot)                    # if no Prior Dots - random choice from Available Dots List
        print(f"\t {g.x.trans['comp_shoot'][g.x.lang]}: {d.x + 1} {d.y + 1}")
        return d


class User(Player):
    def ask(self):                                          # manual input of User's shot
        self.print_score()
        while True:
            cords = input(f"\t {g.x.trans['user_shoot'][g.x.lang]} ").split()
            if len(cords) != 2:
                g.x.prnt('enter_coord')
                continue
            x, y = cords
            if not (x.isdigit()) or not (y.isdigit()):
                g.x.prnt('enter_digs')
                continue
            x, y = int(x), int(y)

            return Dot(x - 1, y - 1)


# declaring the Game class
class Game:
    def __init__(self):
        self.x = self.choose_language()                     # chooses language
        self.x.prnt('greet')                                # prints greeting at the beginning of the game
        self.size = self.choose_size()                      # chooses size of the Board 6 or 9
        self.ships_len_dict = {6: [3, 2, 2, 1, 1, 1, 1],    # corresponding lists of Ships
                               9: [4, 3, 3, 3, 2, 2, 2, 1, 1, 1, 1]}
        # depends on User's choice it can be manual or random generation of the Board:
        pl = self.random_board() if self.choose_board_input_type() == 'R' else self.manual_board()
        co = self.random_board()                            # generates the AI's Board randomly
        co.hid = True
        self.ai = AI(co, pl)                                # creates AI player
        self.us = User(pl, co)                              # creates User player

    def choose_size(self):                                  # defines the size of the Board
        options = [6, 9]
        while True:
            res = input(f' {self.x.prnt_in_text("board_size")} 6 / 9 : --->  ').strip()
            if res.isdigit() and int(res) in options:
                return int(res)

    def choose_language(self):                              # defines the language of the game
        lng = ''
        while lng != 'R' and lng != 'E':
            lng = input('\t Please choose your language (R - русский, E - English): --->  ').upper()
        return Language(lng)

    def choose_board_input_type(self):                      # defines Manual or Random type of generating User's Board
        bit = ''
        while bit != 'M' and bit != 'R':
            bit = input(f'{self.x.prnt_in_text("print_bit")}: ---> ').upper()
        return bit

    def random_board(self):                                 # generates the Board randomly
        board = None
        while board is None:
            board = self.random_place()
        return board

    def manual_board(self):                                 # generates the Board manually
        board = Board(size=self.size)
        lens = self.ships_len_dict[self.size]
        print(board)
        print(f'{self.x.prnt_in_text("place_ships")}: {lens}.')
        orient = {'H': 1, 'V': 0}
        i = 0
        while i != len(lens):
            ln = lens[i]
            otv = input(f' {self.x.prnt_in_text("manual_rules")} [{ln}] --->   ').split()
            if otv[0].upper() == 'XXX':
                print(f"{self.x.prnt_in_text('mnl_board_again')}\n")
                board = Board(size=self.size)
                print(board)
                i = 0
                continue
            if len(otv) != 3 and ln != 1:
                self.x.prnt('failed_manual_ship')
                continue
            if ln == 1:
                hv = 'h'
                x, y = otv
            else:
                x, y, hv = otv
            if not (x.isdigit() and y.isdigit() and hv.upper() in orient.keys()):
                self.x.prnt('failed_manual_ship')
                continue
            x, y = int(x), int(y)
            hv = orient[hv.upper()]
            ship = Ship(Dot(x - 1, y - 1), ln, hv)
            try:
                board.add_ship(ship)
                i += 1
                print(board)
                continue
            except BoardWrongShipException:
                self.x.prnt('wrong_ship_pos')
                pass
        board.begin()
        return board

    def random_place(self):                                 # places Ship on Board randomly
        board = Board(size=self.size)
        lens = self.ships_len_dict[self.size]
        attempts = 0
        for l in lens:
            while True:
                attempts += 1
                if attempts > 2000:
                    return None
                ship = Ship(Dot(randint(0, self.size), randint(0, self.size)), l, randint(0, 1))
                try:
                    board.add_ship(ship)
                    break
                except BoardWrongShipException:
                    pass
        board.begin()
        return board

    def loop(self):                                         # playing loop of the game
        num = 0
        while True:
            print("-" * 20)
            if num % 2 == 0:
                self.x.prnt('comp_board')
                print(self.ai.board)
                print("-" * 20)
                self.x.prnt('user_turn')
                repeat = self.us.move()                     # User's turn
            else:
                self.x.prnt('user_board')
                print(self.us.board)
                print("-" * 20)
                self.x.prnt('comp_turn')
                repeat = self.ai.move()                     # AI's turn
            if repeat:
                num -= 1

            if self.ai.board.count == len(self.ships_len_dict[self.size]):      # if quantity of killed equals
                print("-" * 20)                                                 # quantity of Ships in Starting List
                self.x.prnt('user_win')                                         # all Ships are killed, let's dance!
                break

            if self.us.board.count == len(self.ships_len_dict[self.size]):
                print("-" * 20)
                self.x.prnt('comp_win')
                break
            num += 1

    def start(self):
        self.loop()

# general cycle of the game
while True:
    g = Game()
    g.start()
    otv = ''
    while otv.upper() != 'Y' and otv.upper() != 'N':        # one more game Y or N
        otv = input(f"\n{g.x.prnt_in_text('wanna_play')} --> ")
    if otv.upper() == 'Y':
        print('\n\n\n')
        continue
    else:
        g.x.prnt('thanx_for_play')
        break


# Actually code was given in the presentation, so the game is based on that code
# However, it was updated a bit on my own:
# 1) Uncluded Russian / English languages versions
# 2) Increased AI's IQ: it doesn't shoot on unavailable cells to prevent BoardUsedException on its turns
# 3) Increased AI's IQ: it understands when a User's Ship is under fire and try to kill it hitting on surroundings
# 4) Option for manual placing of Ships on Board added for User
# 5) Board's size 6x6 or 9x9 option added

