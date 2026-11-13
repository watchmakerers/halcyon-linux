"""Hearts: the rules and the computer players. No Qt here.

Cards are (rank, suit) with rank 2..14 (Ace high) and suit in "CDSH".
Seats: 0 = you (bottom), 1 = left (West), 2 = across (North), 3 = right (East).
Play goes clockwise: 0 -> 1 -> 2 -> 3.

    python3 -m halcyon_arcade.hearts_engine --selftest
"""
import random
import sys

SUITS = "CDSH"
QUEEN = (12, "S")
TWO_CLUBS = (2, "C")
PASSES = ["left", "right", "across", "none"]       # the cycle, one per hand
GAME_OVER = 100


def points(card):
    return 13 if card == QUEEN else 1 if card[1] == "H" else 0


def sort_hand(cards):
    order = {"C": 0, "D": 1, "S": 2, "H": 3}
    return sorted(cards, key=lambda c: (order[c[1]], c[0]))


def deal(rng):
    deck = [(r, s) for s in SUITS for r in range(2, 15)]
    rng.shuffle(deck)
    return [sort_hand(deck[i::4]) for i in range(4)]


def pass_target(seat, direction):
    return {"left": (seat + 1) % 4, "right": (seat + 3) % 4, "across": (seat + 2) % 4}.get(direction, seat)


def trick_winner(trick):
    """trick: [(seat, card)] in play order -> winning seat (highest card of the suit led)."""
    lead = trick[0][1][1]
    return max((c[0], seat) for seat, c in trick if c[1] == lead)[1]


class Hand:
    """One deal: passing, thirteen tricks, the points each player took."""
    def __init__(self, hands, direction):
        self.hands = [list(h) for h in hands]
        self.direction = direction
        self.passing = direction != "none"
        self.passed = [None] * 4               # the 3 cards each seat chose
        self.received = [[] for _ in range(4)]
        self.trick = []                        # [(seat, card)]
        self.tricks_played = 0
        self.taken = [[] for _ in range(4)]    # point cards each seat took
        self.hearts_broken = False
        self.played = set()                    # every card played so far (for the AI)
        self.voids = [set() for _ in range(4)] # suits each seat has shown it's out of
        self.turn = None if self.passing else self._two_of_clubs()
        self.last_trick = None                 # (winner, trick) of the trick just completed

    def _two_of_clubs(self):
        return next(i for i, h in enumerate(self.hands) if TWO_CLUBS in h)

    # -- passing
    def choose_pass(self, seat, cards):
        assert self.passing and len(cards) == 3 and all(c in self.hands[seat] for c in cards)
        self.passed[seat] = list(cards)
        if all(p is not None for p in self.passed):
            for s in range(4):
                for c in self.passed[s]:
                    self.hands[s].remove(c)
            for s in range(4):
                t = pass_target(s, self.direction)
                self.hands[t] += self.passed[s]
                self.received[t] = list(self.passed[s])
            self.hands = [sort_hand(h) for h in self.hands]
            self.passing = False
            self.turn = self._two_of_clubs()

    # -- play
    @property
    def first_trick(self):
        return self.tricks_played == 0

    def legal(self, seat):
        hand = self.hands[seat]
        if self.passing or seat != self.turn or not hand:
            return []
        if not self.trick:                                  # leading
            if self.first_trick:
                return [TWO_CLUBS]
            if self.hearts_broken:
                return list(hand)
            non_hearts = [c for c in hand if c[1] != "H"]
            return non_hearts or list(hand)                 # only hearts left: may lead them
        lead = self.trick[0][1][1]
        follow = [c for c in hand if c[1] == lead]
        if follow:
            return follow
        if self.first_trick:                                # no points on the first trick, unless that's all there is
            safe = [c for c in hand if points(c) == 0]
            if safe:
                return safe
            no_queen = [c for c in hand if c != QUEEN]
            return no_queen or list(hand)
        return list(hand)

    def play(self, seat, card):
        """Play a card. Returns the winner if this completed a trick, else None."""
        assert card in self.legal(seat), (seat, card, self.legal(seat))
        if self.trick and card[1] != self.trick[0][1][1]:
            self.voids[seat].add(self.trick[0][1][1])
        self.hands[seat].remove(card)
        self.trick.append((seat, card))
        self.played.add(card)
        if card[1] == "H":
            self.hearts_broken = True
        if len(self.trick) < 4:
            self.turn = (seat + 1) % 4
            return None
        win = trick_winner(self.trick)
        self.taken[win] += [c for _, c in self.trick if points(c)]
        self.last_trick = (win, list(self.trick))
        self.trick = []
        self.tricks_played += 1
        self.turn = win if self.tricks_played < 13 else None
        return win

    @property
    def done(self):
        return self.tricks_played == 13

    def points_taken(self):
        return [sum(points(c) for c in t) for t in self.taken]

    def moon(self):
        """The seat that shot the moon (took all 26), or None."""
        pts = self.points_taken()
        return next((i for i, p in enumerate(pts) if p == 26), None)

    def scores(self):
        """Points added to each player's total: a moon gives everyone else 26."""
        m = self.moon()
        if m is not None:
            return [0 if i == m else 26 for i in range(4)]
        return self.points_taken()


class Match:
    """Hands until someone reaches 100; the lowest total wins."""
    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.totals = [0, 0, 0, 0]
        self.history = []                      # per hand: [points added]
        self.number = 0
        self.hand = None
        self.new_hand()

    def new_hand(self):
        self.hand = Hand(deal(self.rng), PASSES[self.number % 4])
        self.number += 1
        return self.hand

    def finish_hand(self):
        add = self.hand.scores()
        self.history.append(add)
        self.totals = [t + a for t, a in zip(self.totals, add)]
        return add

    @property
    def over(self):
        return max(self.totals) >= GAME_OVER

    def winners(self):
        low = min(self.totals)
        return [i for i, t in enumerate(self.totals) if t == low]


# ------------------------------------------------------------ computer play ---
class Player:
    """A sensible computer player: builds voids when passing, ducks tricks,
    unloads the Queen and high hearts, shoots the moon only with a strong hand
    and blocks others who try."""
    def __init__(self, seat):
        self.seat = seat
        self.moon = False

    # -- passing
    def choose_pass(self, hand):
        hand = list(hand)
        out = []

        def take(c):
            if c in hand and c not in out and len(out) < 3:
                out.append(c)

        spades = [c for c in hand if c[1] == "S"]
        low_spades = [c for c in spades if c[0] < 12]
        # The Queen is only safe with plenty of low spades to hide behind.
        if QUEEN in hand and len(low_spades) < 4:
            take(QUEEN)
        if QUEEN not in hand or len(low_spades) < 4:
            for r in (14, 13):                              # A/K of spades catch the Queen
                if (r, "S") in hand and len(low_spades) < 4:
                    take((r, "S"))
        # Empty a short club or diamond suit: one less suit to follow means chances to unload.
        for suit in sorted("CD", key=lambda s: sum(1 for c in hand if c[1] == s)):
            cards = sorted([c for c in hand if c[1] == suit], reverse=True)
            if 0 < len(cards) <= 3 - len(out):
                for c in cards:
                    if not (c == TWO_CLUBS and len(cards) > 1):
                        take(c)
        # Then the highest hearts, then the highest cards overall.
        for c in sorted([c for c in hand if c[1] == "H"], reverse=True):
            if c[0] >= 11:
                take(c)
        for c in sorted(hand, key=lambda c: (-c[0], c[1] == "H")):
            take(c)
        return out[:3]

    def plan_moon(self, hand):
        """Try for the moon with lots of high hearts and control of the other suits."""
        hearts = sorted(c[0] for c in hand if c[1] == "H")
        high = sum(1 for c in hand if c[0] >= 12)
        self.moon = (len(hearts) >= 6 and hearts[-3:] == [12, 13, 14] and high >= 7
                     and (QUEEN in hand or (14, "S") in hand))
        return self.moon

    # -- play
    def choose(self, h):
        legal = h.legal(self.seat)
        if len(legal) == 1:
            return legal[0]
        taken = h.points_taken()
        if self.moon and any(p for i, p in enumerate(taken) if i != self.seat):
            self.moon = False                               # someone else took a point: give up
        if self.moon:
            return self._moon_play(h, legal)
        shooter = self._shooter(h)
        if not h.trick:
            return self._lead(h, legal, shooter)
        lead = h.trick[0][1][1]
        if legal[0][1] == lead:
            return self._follow(h, legal, shooter)
        return self._discard(h, legal, shooter)

    def _shooter(self, h):
        """Someone else who has every point so far (and a fair number of them): they may be shooting."""
        taken = h.points_taken()
        total = sum(taken)
        for i, p in enumerate(taken):
            if i != self.seat and p == total and p >= 14 and h.tricks_played >= 6:
                return i
        return None

    def _danger(self, h, suit):
        """How risky leading this suit is: low when others still hold higher cards."""
        unseen = [r for r in range(2, 15) if (r, suit) not in h.played and (r, suit) not in h.hands[self.seat]]
        return unseen

    def _lead(self, h, legal, shooter):
        queen_out = QUEEN not in h.played and QUEEN not in h.hands[self.seat]
        best, best_key = None, None
        for c in legal:
            r, s = c
            unseen = self._danger(h, s)
            under = sum(1 for u in unseen if u > r)          # cards that would beat this one
            key = under * 2 - r * 0.1
            if s == "S":
                if c == QUEEN or (r > 12 and queen_out):
                    key -= 40                                # never lead into the Queen
                elif queen_out and r < 12:
                    key += 3                                 # flush the Queen out with low spades
            if s == "H":
                key -= 2
            if shooter is not None and s == "H" and r >= 10:
                key += 20                                    # take a heart back from a shooter
            if not unseen:
                key -= 6                                     # nobody can follow: we'd take it
            if best_key is None or key > best_key:
                best, best_key = c, key
        return best

    def _follow(self, h, legal, shooter):
        lead = h.trick[0][1][1]
        high = max(c[0] for _, c in h.trick if c[1] == lead)
        pts = sum(points(c) for _, c in h.trick)
        last = len(h.trick) == 3
        under = [c for c in legal if c[0] < high]
        over = [c for c in legal if c[0] > high]
        if shooter is not None and pts and over and trick_winner(h.trick) == shooter:
            return min(over)                                 # stop the moon: take this one
        if lead == "S":
            if QUEEN in legal and any(c[0] > 12 for _, c in h.trick if c[1] == "S"):
                return QUEEN                                 # someone else's A/K wins: give them the Queen
            if under:
                safe = [c for c in under if c != QUEEN]
                return max(safe) if safe else QUEEN if not over else min(over)
            if last and pts == 0 and QUEEN not in [c for _, c in h.trick]:
                no_q = [c for c in legal if c != QUEEN]
                return max(no_q) if no_q else QUEEN
            no_q = [c for c in over if c != QUEEN]
            return min(no_q) if no_q else min(over)
        if under:
            return max(under)                                # the highest card that still loses
        if last and pts == 0:
            return max(legal)                                # winning anyway, and it's clean: use the big one
        if h.first_trick and lead == "C":
            return max(legal)                                # first trick can't carry points
        return min(legal)

    def _discard(self, h, legal, shooter):
        winner = trick_winner(h.trick)
        if shooter is not None and winner == shooter:
            safe = [c for c in legal if not points(c)]       # don't feed a shooter
            if safe:
                return max(safe)
        if QUEEN in legal:
            return QUEEN
        queen_out = QUEEN not in h.played
        for r in (14, 13):
            if (r, "S") in legal and queen_out:
                return (r, "S")
        hearts = [c for c in legal if c[1] == "H"]
        if hearts:
            return max(hearts)
        # otherwise the highest card from the shortest suit, to make a new void
        counts = {s: sum(1 for c in h.hands[self.seat] if c[1] == s) for s in SUITS}
        return max(legal, key=lambda c: (-counts[c[1]], c[0]))

    def _moon_play(self, h, legal):
        if not h.trick:
            return max(legal, key=lambda c: (c[1] == "H", c[0]))
        lead = h.trick[0][1][1]
        high = max(c[0] for _, c in h.trick if c[1] == lead)
        if legal[0][1] == lead:
            over = [c for c in legal if c[0] > high]
            return max(over) if over else min(legal)
        return min(legal, key=lambda c: (points(c) > 0, c[0]))   # keep point cards for ourselves


def hint(h, seat):
    """What the computer would do in your place: a card to play, or three to pass."""
    p = Player(seat)
    if h.passing:
        return p.choose_pass(h.hands[seat])
    return [p.choose(h)]


# ---------------------------------------------------------------- selftest ---
def _selftest(hands_to_play=400):
    rng = random.Random(7)
    assert trick_winner([(0, (5, "C")), (1, (14, "D")), (2, (9, "C")), (3, (2, "C"))]) == 2
    assert [pass_target(0, d) for d in ("left", "right", "across", "none")] == [1, 3, 2, 0]

    # first trick: 2 of clubs leads; no points unless that's all you have
    h = Hand([[(2, "C")] + [(r, "D") for r in range(3, 15)], [(12, "S")] + [(r, "H") for r in range(2, 14)],
              [(r, "S") for r in range(2, 12)] + [(13, "S"), (14, "S"), (14, "H")],
              [(r, "C") for r in range(3, 15)] + [(2, "S")]], "none")
    assert h.turn == 0 and h.legal(0) == [TWO_CLUBS]
    h.play(0, TWO_CLUBS)
    assert QUEEN not in h.legal(1) and all(c[1] == "H" for c in h.legal(1))      # only points: hearts, not the Queen
    h.play(1, (2, "H"))
    assert h.legal(2) == [c for c in h.hands[2] if c[1] == "S" and c != QUEEN] or QUEEN not in h.legal(2)
    assert h.legal(3) == [] and h.turn == 2                                      # not seat 3's turn yet

    totals_ok = moons = 0
    for n in range(hands_to_play):
        m = Match(seed=rng.randrange(10 ** 9))
        m.number = n % 4
        h = m.new_hand()
        players = [Player(i) for i in range(4)]
        if h.passing:
            for i in range(4):
                c = players[i].choose_pass(h.hands[i])
                assert len(set(c)) == 3 and all(x in h.hands[i] for x in c), (c, h.hands[i])
                h.choose_pass(i, c)
            assert all(len(x) == 13 for x in h.hands)
        for i in range(4):
            players[i].plan_moon(h.hands[i])
        first = True
        while not h.done:
            seat = h.turn
            legal = h.legal(seat)
            card = players[seat].choose(h)
            assert card in legal, (card, legal)
            if first:
                assert card == TWO_CLUBS
                first = False
            if not h.trick and card[1] == "H" and not h.hearts_broken:
                assert all(c[1] == "H" for c in h.hands[seat])      # hearts only led early when nothing else is left
            h.play(seat, card)
        pts = h.points_taken()
        assert sum(pts) == 26, pts
        assert sum(len(x) for x in h.hands) == 0
        sc = h.scores()
        if h.moon() is not None:
            moons += 1
            assert sorted(sc) == [0, 26, 26, 26]
        else:
            assert sc == pts
        totals_ok += 1
    # a whole match ends with someone at 100+ and a lowest-score winner
    m = Match(seed=3)
    for _ in range(60):
        h = m.hand
        players = [Player(i) for i in range(4)]
        if h.passing:
            for i in range(4):
                h.choose_pass(i, players[i].choose_pass(h.hands[i]))
        while not h.done:
            h.play(h.turn, players[h.turn].choose(h))
        m.finish_hand()
        if m.over:
            break
        m.new_hand()
    assert m.over and m.winners() and all(m.totals[w] == min(m.totals) for w in m.winners())
    print(f"hearts selftest ok: {totals_ok} hands, {moons} moons, match over after {len(m.history)} hands "
          f"(totals {m.totals})")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
