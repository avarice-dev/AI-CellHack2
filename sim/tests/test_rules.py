"""Unit tests of the rules engine (engine.py only, no I/O).

What is faked: cell programs are scripted Python policies that return fixed (action, insn_count) per
square; boards are tiny and hand-placed.  Each test cites the rule it checks (Rules page, "Each tick"
list and Fine print; Reference; cellhack.inc).
"""

import unittest

from .helpers import (E, NOP, script, board, energy_at, move, split, eat, feed,
                      UP, RIGHT, DOWN, LEFT, REST)


class RestTest(unittest.TestCase):
    def test_rest_gains_one(self):
        # Rules 3: REST gains 1.
        e = board([script({(1, 1): (REST, 1)})])
        e.add_cell(1, 1, 0, 10)
        e.step()
        self.assertEqual(energy_at(e, 1, 1), 11)

    def test_nop_does_nothing(self):
        e = board([script({(1, 1): NOP})])
        e.add_cell(1, 1, 0, 10)
        e.step()
        self.assertEqual(energy_at(e, 1, 1), 10)


class OrderTest(unittest.TestCase):
    def _contest(self, insn_a, insn_b, seed=0):
        # A at (0,1) and B at (2,1) both move into (1,1).
        pol = script({(0, 1): (move(RIGHT), insn_a), (2, 1): (move(LEFT), insn_b)})
        e = board([pol], seed=seed)
        a = e.add_cell(0, 1, 0)
        b = e.add_cell(2, 1, 0)
        e.step()
        return {a: 'A', b: 'B'}[e.cell_at(1, 1)]

    def test_fewest_instructions_act_first(self):
        # Rules 2: cells take their turns in order of insn count, fewest first.
        self.assertEqual(self._contest(5, 3), 'B')
        self.assertEqual(self._contest(3, 5), 'A')

    def test_order_is_by_insn_not_by_birth_or_position(self):
        self.assertEqual(self._contest(999, 1000), 'A')
        self.assertEqual(self._contest(1000, 999), 'B')

    def test_equal_counts_are_a_seeded_coin_flip(self):
        # Rules: equal instruction counts are ordered at random; randomness only from the match seed.
        winners = [self._contest(4, 4, seed=s) for s in range(40)]
        self.assertIn('A', winners)
        self.assertIn('B', winners)
        self.assertEqual(winners, [self._contest(4, 4, seed=s) for s in range(40)])


class StunTest(unittest.TestCase):
    def _duel(self, insn_eater, insn_target, target_colony=1):
        pols = [script({(1, 1): (eat(RIGHT), insn_eater)}),
                script({(2, 1): (REST, insn_target)})]
        if target_colony == 0:
            pols = [script({(1, 1): (eat(RIGHT), insn_eater), (2, 1): (REST, insn_target)}),
                    script({}, default=NOP)]
        e = board(pols)
        e.add_cell(1, 1, 0, 10)
        e.add_cell(2, 1, target_colony, 10)
        e.add_cell(4, 4, 1, 10)  # keeps colony 1 alive / present
        e.step()
        return e

    def test_bite_before_turn_stuns(self):
        # Rules 4: the bitten cell, if it has not had its turn yet, loses its action this tick.
        e = self._duel(1, 5)
        self.assertEqual(energy_at(e, 1, 1), 12)
        self.assertEqual(energy_at(e, 2, 1), 8)       # 10 - 2, no rest
        self.assertEqual(e.stuns[1], 1)

    def test_bite_after_turn_does_not_stun(self):
        e = self._duel(5, 1)
        self.assertEqual(energy_at(e, 1, 1), 12)
        self.assertEqual(energy_at(e, 2, 1), 9)       # rested to 11, then bitten
        self.assertEqual(e.stuns[1], 0)

    def test_bitten_friend_is_stunned_too(self):
        # "You can eat and feed your own cells"; the bitten cell is stunned whoever bites.
        e = self._duel(1, 5, target_colony=0)
        self.assertEqual(energy_at(e, 2, 1), 8)
        self.assertEqual(e.stuns[0], 1)


class EatTest(unittest.TestCase):
    def _eat(self, target_energy, eater_energy=10):
        e = board([script({(1, 1): (eat(RIGHT), 1)}), script({}, default=(REST, 9))])
        e.add_cell(1, 1, 0, eater_energy)
        e.add_cell(2, 1, 1, target_energy)
        e.add_cell(4, 4, 1, 10)
        e.step()
        return e

    def test_takes_two(self):
        e = self._eat(3)
        self.assertEqual(energy_at(e, 1, 1), 12)
        self.assertEqual(energy_at(e, 2, 1), 1)

    def test_eating_two_or_less_kills(self):
        # Worth knowing: eating a cell that has 2 or less kills it.
        for te in (1, 2):
            e = self._eat(te)
            self.assertEqual(energy_at(e, 1, 1), 10 + te)
            self.assertIsNone(e.cell_at(2, 1), 'target with %d should be dead and removed' % te)
            self.assertEqual(e.deaths[1], 1)

    def test_eating_empty_or_wall_does_nothing(self):
        e = board([script({(1, 1): (eat(LEFT), 1), (0, 0): (eat(UP), 1)})])
        e.add_cell(1, 1, 0, 10)
        e.add_cell(0, 0, 0, 10)
        e.step()
        self.assertEqual(energy_at(e, 1, 1), 10)
        self.assertEqual(energy_at(e, 0, 0), 10)

    def test_several_eaters_drain_in_turn_until_none(self):
        # Fine print: a cell eaten by several others loses energy to each in turn until it has none.
        pol = script({(1, 2): (eat(DOWN), 1), (0, 3): (eat(RIGHT), 2), (2, 3): (eat(LEFT), 3)})
        e = board([pol, script({}, default=(REST, 9))])
        e.add_cell(1, 2, 0, 10)
        e.add_cell(0, 3, 0, 10)
        e.add_cell(2, 3, 0, 10)
        e.add_cell(1, 3, 1, 3)
        e.add_cell(4, 0, 1, 10)
        e.step()
        self.assertEqual(energy_at(e, 1, 2), 12)
        self.assertEqual(energy_at(e, 0, 3), 11)      # only 1 left to take
        self.assertEqual(energy_at(e, 2, 3), 10)      # target already dead: nothing
        self.assertIsNone(e.cell_at(1, 3))


class DeathTest(unittest.TestCase):
    def test_killed_cell_takes_no_turn(self):
        # Rules 8: a cell that reaches 0 dies on the spot and takes no turn.
        pols = [script({(1, 1): (eat(RIGHT), 1)}),
                script({(2, 1): (feed(RIGHT), 5), (3, 1): NOP})]
        e = board(pols)
        e.add_cell(1, 1, 0, 10)
        e.add_cell(2, 1, 1, 2)
        e.add_cell(3, 1, 1, 10)
        e.step()
        self.assertEqual(energy_at(e, 3, 1), 10)       # was not fed

    def test_dead_cell_cannot_be_fed(self):
        # Rules 8: nobody can eat or feed it.
        pols = [script({(1, 1): (eat(RIGHT), 1), (3, 1): (feed(LEFT), 2)}), script({}, default=NOP)]
        e = board(pols)
        e.add_cell(1, 1, 0, 10)
        e.add_cell(2, 1, 1, 1)
        e.add_cell(3, 1, 0, 10)
        e.add_cell(4, 4, 1, 10)
        e.step()
        self.assertEqual(energy_at(e, 3, 1), 10)       # feed found a corpse: nothing given

    def test_dead_cell_holds_square_until_end_of_tick(self):
        # Rules 8 + Fine print: a square freed by a death cannot be entered until the next tick.
        pols = [script({(0, 1): (eat(RIGHT), 1), (1, 0): (move(DOWN), 2), (1, 2): (split(UP), 3)},
                       default=NOP),
                script({}, default=NOP)]
        e = board(pols)
        e.add_cell(0, 1, 0, 10)
        e.add_cell(1, 1, 1, 2)       # dies to the first bite
        mover = e.add_cell(1, 0, 0, 10)
        e.add_cell(1, 2, 0, 10)
        e.add_cell(4, 4, 1, 10)
        e.step()
        self.assertEqual(e.pos_of(mover), (1, 0))      # move into the corpse square failed
        self.assertEqual(energy_at(e, 1, 2), 10)       # split into it failed too
        self.assertIsNone(e.cell_at(1, 1))             # removed at Tidy
        e.step()                                       # next tick: same move now succeeds
        self.assertEqual(e.pos_of(mover), (1, 1))

    def test_dead_cell_seen_mid_tick_by_cell_at(self):
        # The corpse is still on the board (holding the square) before Tidy.
        captured = {}

        class Spy(E.Engine):
            def _act(self, t, acts):
                E.Engine._act(self, t, acts)
                i = self.cell_at(1, 1)
                captured['id'] = i
                captured['alive'] = None if i is None else self.c_alive[i]

        pols = [script({(0, 1): (eat(RIGHT), 1)}), script({}, default=NOP)]
        e = Spy(pols, width=5, height=5, place_start=False)
        e.add_cell(0, 1, 0, 10)
        e.add_cell(1, 1, 1, 2)
        e.add_cell(4, 4, 1, 10)
        e.step()
        self.assertIsNotNone(captured['id'])
        self.assertFalse(captured['alive'])


class MoveTest(unittest.TestCase):
    def test_vacated_square_can_be_entered_later_same_tick(self):
        # Fine print: a square vacated earlier in the tick can be entered later in the same tick.
        pol = script({(1, 1): (move(RIGHT), 1), (0, 1): (move(RIGHT), 2)})
        e = board([pol])
        a = e.add_cell(1, 1, 0)
        b = e.add_cell(0, 1, 0)
        e.step()
        self.assertEqual(e.pos_of(a), (2, 1))
        self.assertEqual(e.pos_of(b), (1, 1))

    def test_follower_first_is_blocked(self):
        pol = script({(1, 1): (move(RIGHT), 2), (0, 1): (move(RIGHT), 1)})
        e = board([pol])
        a = e.add_cell(1, 1, 0)
        b = e.add_cell(0, 1, 0)
        e.step()
        self.assertEqual(e.pos_of(a), (2, 1))
        self.assertEqual(e.pos_of(b), (0, 1))

    def test_two_cells_cannot_swap(self):
        pol = script({(1, 1): (move(RIGHT), 1), (2, 1): (move(LEFT), 2)})
        e = board([pol])
        a = e.add_cell(1, 1, 0)
        b = e.add_cell(2, 1, 0)
        e.step()
        self.assertEqual(e.pos_of(a), (1, 1))
        self.assertEqual(e.pos_of(b), (2, 1))

    def test_move_into_wall_or_occupied_does_nothing(self):
        pol = script({(0, 0): (move(UP), 1), (0, 1): (move(UP), 2)})
        e = board([pol])
        a = e.add_cell(0, 0, 0)
        b = e.add_cell(0, 1, 0)
        e.step()
        self.assertEqual(e.pos_of(a), (0, 0))
        self.assertEqual(e.pos_of(b), (0, 1))

    def test_bite_at_a_cell_that_stepped_away_finds_nothing(self):
        # Fine print: targets are whatever is in the square when your turn comes.
        pols = [script({(1, 1): (eat(RIGHT), 5)}), script({(2, 1): (move(RIGHT), 1)}, default=NOP)]
        e = board(pols)
        e.add_cell(1, 1, 0, 10)
        e.add_cell(2, 1, 1, 10)
        e.step()
        self.assertEqual(energy_at(e, 1, 1), 10)
        self.assertEqual(energy_at(e, 3, 1), 10)

    def test_bite_at_a_square_someone_stepped_into_hits_newcomer(self):
        pols = [script({(1, 1): (eat(RIGHT), 5)}), script({(2, 0): (move(DOWN), 1)}, default=NOP)]
        e = board(pols)
        e.add_cell(1, 1, 0, 10)
        e.add_cell(2, 0, 1, 10)
        e.step()
        self.assertEqual(energy_at(e, 1, 1), 12)
        self.assertEqual(energy_at(e, 2, 1), 8)


class SplitTest(unittest.TestCase):
    def _split(self, energy, **kw):
        e = board([script({(1, 1): (split(RIGHT), 1)})], **kw)
        e.add_cell(1, 1, 0, energy)
        e.step()
        return energy_at(e, 1, 1), energy_at(e, 2, 1)

    def test_split_needs_five(self):
        # Rules 6 / Fine print: nothing happens when you split with less than 5.
        self.assertEqual(self._split(4), (4, None))
        self.assertEqual(self._split(5), (3, 2))

    def test_split_default_rounding_child_gets_floor(self):
        # ASSUMPTION (parameter): child gets floor(e/2), parent keeps the rest.
        self.assertEqual(self._split(7), (4, 3))
        self.assertEqual(self._split(10), (5, 5))

    def test_split_ceil_rounding_parameter(self):
        self.assertEqual(self._split(7, split_child_rounding='ceil'), (3, 4))
        self.assertEqual(self._split(5, split_child_rounding='ceil'), (2, 3))

    def test_split_into_wall_or_occupied_does_nothing(self):
        pol = script({(0, 0): (split(LEFT), 1), (0, 1): (split(UP), 2)})
        e = board([pol])
        e.add_cell(0, 0, 0, 10)
        e.add_cell(0, 1, 0, 10)
        e.step()
        self.assertEqual(len(e.cells()), 2)
        self.assertEqual(energy_at(e, 0, 0), 10)
        self.assertEqual(energy_at(e, 0, 1), 10)

    def test_split_into_square_vacated_this_tick(self):
        pol = script({(2, 1): (move(RIGHT), 1), (1, 1): (split(RIGHT), 2)})
        e = board([pol])
        e.add_cell(2, 1, 0, 10)
        e.add_cell(1, 1, 0, 10)
        e.step()
        self.assertEqual(energy_at(e, 2, 1), 5)
        self.assertEqual(energy_at(e, 3, 1), 10)


class FeedTest(unittest.TestCase):
    def _feed(self, feeder_energy, target=True, target_colony=0):
        pols = [script({(1, 1): (feed(RIGHT), 1), (2, 1): NOP}), script({}, default=NOP)]
        e = board(pols)
        e.add_cell(1, 1, 0, feeder_energy)
        if target:
            e.add_cell(2, 1, target_colony, 10)
        e.add_cell(4, 4, 1, 10)
        e.step()
        return e

    def test_feed_gives_two(self):
        e = self._feed(10)
        self.assertEqual(energy_at(e, 1, 1), 8)
        self.assertEqual(energy_at(e, 2, 1), 12)

    def test_feed_enemy_allowed(self):
        e = self._feed(10, target_colony=1)
        self.assertEqual(energy_at(e, 2, 1), 12)

    def test_feeder_with_one_gives_all_and_dies(self):
        # Fine print: a feeder with less than 2 gives all it has, and dies if that was all of it.
        e = self._feed(1)
        self.assertIsNone(e.cell_at(1, 1))
        self.assertEqual(energy_at(e, 2, 1), 11)

    def test_feeder_with_exactly_two_dies(self):
        # Rules 5 + 8: gives 2, reaches 0, dies on the spot.
        e = self._feed(2)
        self.assertIsNone(e.cell_at(1, 1))
        self.assertEqual(energy_at(e, 2, 1), 12)

    def test_feeding_empty_square_does_nothing(self):
        e = self._feed(10, target=False)
        self.assertEqual(energy_at(e, 1, 1), 10)

    def test_feed_does_not_stun(self):
        pols = [script({(1, 1): (feed(RIGHT), 1), (2, 1): (REST, 5)})]
        e = board(pols)
        e.add_cell(1, 1, 0, 10)
        e.add_cell(2, 1, 0, 10)
        e.step()
        self.assertEqual(energy_at(e, 2, 1), 13)


class CapTest(unittest.TestCase):
    def test_cap_applied_at_tidy(self):
        # Rules 9: energy is capped at 50 (at Tidy).
        pol = script({(1, 1): (REST, 1), (3, 3): (feed(RIGHT), 1)})
        e = board([pol])
        e.add_cell(1, 1, 0, 50)
        e.add_cell(3, 3, 0, 10)
        e.add_cell(4, 3, 0, 49)
        e.step()
        self.assertEqual(energy_at(e, 1, 1), 50)
        self.assertEqual(energy_at(e, 4, 3), 50)

    def _fed_then_split(self, **kw):
        pol = script({(1, 1): (feed(RIGHT), 1), (2, 1): (split(RIGHT), 2)})
        e = board([pol], **kw)
        e.add_cell(1, 1, 0, 10)
        e.add_cell(2, 1, 0, 50)
        e.step()
        return energy_at(e, 2, 1), energy_at(e, 3, 1)

    def test_energy_above_50_spendable_before_tidy_by_default(self):
        # ASSUMPTION (parameter, default from the rules text "Tidy. Energy is capped at 50"):
        # 50 + 2 fed = 52 mid-tick, split -> 26 / 26.
        self.assertEqual(self._fed_then_split(), (26, 26))

    def test_cap_mid_tick_parameter(self):
        self.assertEqual(self._fed_then_split(cap_mid_tick=True), (25, 25))

    def test_overfull_eater_then_bitten(self):
        pols = [script({(1, 1): (eat(RIGHT), 1)}), script({(0, 1): (eat(RIGHT), 2)}, default=NOP)]
        for cap_mid, expected in ((False, 50), (True, 48)):
            e = board(pols, cap_mid_tick=cap_mid)
            e.add_cell(1, 1, 0, 50)
            e.add_cell(2, 1, 1, 10)
            e.add_cell(0, 1, 1, 10)
            e.step()
            self.assertEqual(energy_at(e, 1, 1), expected, 'cap_mid_tick=%s' % cap_mid)


class NewbornTest(unittest.TestCase):
    def test_newborn_acts_next_tick_with_age_zero_and_copied_memory(self):
        # Fine print: newborns act from the next tick, with VIEW_AGE 0 and a copy of the parent's memory.
        log = []

        def pol(view, mem):
            log.append((view.tick, view.x, view.y, view.age, mem[0], mem[1]))
            if view.tick == 0:
                mem[0] = 42                 # written in the splitting call itself
                return split(RIGHT), 1
            if view.x == 2:
                mem[1] = 7                  # the child changes its own copy only
            return NOP
        e = board([pol])
        e.add_cell(1, 1, 0, 10)
        e.step()
        self.assertEqual([r[0] for r in log], [0])        # newborn did not decide on tick 0
        e.step()
        e.step()
        t1 = sorted(r for r in log if r[0] == 1)
        self.assertEqual(t1, [(1, 1, 1, 1, 42, 0), (1, 2, 1, 0, 42, 0)])
        t2 = sorted(r for r in log if r[0] == 2)
        self.assertEqual(t2, [(2, 1, 1, 2, 42, 0), (2, 2, 1, 1, 42, 7)])

    def test_newborn_can_be_eaten_in_its_birth_tick(self):
        # ASSUMPTION: a newborn is on the board at once, so a later bite in the same tick hits it.
        pols = [script({(1, 1): (split(RIGHT), 1)}), script({(3, 1): (eat(LEFT), 2)}, default=NOP)]
        e = board(pols)
        e.add_cell(1, 1, 0, 5)
        e.add_cell(3, 1, 1, 10)
        e.step()
        self.assertIsNone(e.cell_at(2, 1))
        self.assertEqual(energy_at(e, 3, 1), 12)

    def test_memory_persists_between_calls_and_survives_stun(self):
        # ASSUMPTION: memory writes persist even if the cell is stunned (the call already ran).
        def p0(view, mem):
            return eat(RIGHT), 1

        def p1(view, mem):
            mem[5] += 1
            return REST, 5
        e = board([p0, p1])
        e.add_cell(1, 1, 0, 10)
        b = e.add_cell(2, 1, 1, 20)
        e.step()
        e.step()
        self.assertEqual(e.c_mem[b][5], 2)
        self.assertEqual(e.c_en[b], 16)          # stunned twice: no rest

    def test_age_saturates_at_255(self):
        ages = []

        def pol(view, mem):
            ages.append(view.age)
            return NOP
        e = board([pol])
        e.add_cell(1, 1, 0, 10, age=254)
        e.step()
        e.step()
        e.step()
        self.assertEqual(ages, [254, 255, 255])


class ViewTest(unittest.TestCase):
    def test_layout_types_energies(self):
        views = {}

        def p0(view, mem):
            views[(view.x, view.y)] = view
            return NOP
        e = board([p0, script({}, default=NOP)], w=6, h=4, seed=3)
        e.add_cell(0, 1, 0, 9)       # viewer, on the left edge
        e.add_cell(0, 0, 0, 4)       # friend above (VIEW_UP 7)
        e.add_cell(1, 1, 1, 6)       # enemy right (VIEW_RIGHT 13)
        e.add_cell(2, 3, 1, 3)       # enemy at dx=+2, dy=+2 (index 24)
        e.step()
        v = views[(0, 1)]
        c, en = v.cells, v.energies
        self.assertEqual(len(c), 25)
        self.assertEqual(c[E.VIEW_UP], E.CELL_FRIEND)
        self.assertEqual(en[E.VIEW_UP], 4)
        self.assertEqual(c[E.VIEW_RIGHT], E.CELL_ENEMY)
        self.assertEqual(en[E.VIEW_RIGHT], 6)
        self.assertEqual(c[E.VIEW_LEFT], E.CELL_WALL)
        self.assertEqual(en[E.VIEW_LEFT], 0)
        self.assertEqual(c[E.VIEW_DOWN], E.CELL_EMPTY)
        self.assertEqual(c[24], E.CELL_ENEMY)
        self.assertEqual(en[24], 3)
        self.assertEqual(c[2], E.CELL_WALL)            # (dx 0, dy -2): above the board
        self.assertEqual(c[E.VIEW_CENTER], E.CELL_FRIEND)   # ASSUMPTION: self reads as FRIEND
        self.assertEqual(en[E.VIEW_CENTER], 9)
        self.assertEqual((v.tick, v.energy, v.x, v.y, v.w, v.h, v.colony), (0, 9, 0, 1, 6, 4, 0))
        self.assertEqual((v.pop_self, v.pop_enemy), (2, 2))
        self.assertTrue(0 <= v.rand <= 255)

    def test_self_type_parameter(self):
        seen = []

        def pol(view, mem):
            seen.append(view.cells[12])
            return NOP
        e = board([pol], self_type=E.CELL_EMPTY)
        e.add_cell(1, 1, 0, 10)
        e.step()
        self.assertEqual(seen, [E.CELL_EMPTY])

    def test_view_is_start_of_tick_snapshot(self):
        # Rules 1: decide sees a snapshot; a faster cell's move does not change a slower cell's view.
        views = {}

        def pol(view, mem):
            views[(view.x, view.y)] = view
            return (move(DOWN), 1) if (view.x, view.y) == (2, 1) else (NOP)
        e = board([pol])
        e.add_cell(1, 1, 0, 10)
        e.add_cell(2, 1, 0, 10)
        e.step()
        self.assertEqual(views[(1, 1)].cells[E.VIEW_RIGHT], E.CELL_FRIEND)   # read after the move

    def test_to_bytes_offsets(self):
        got = {}

        def pol(view, mem):
            got['b'] = view.to_bytes()
            return NOP
        e = board([pol], w=7, h=6)
        e.add_cell(3, 2, 0, 17)
        e.step()
        b = got['b']
        self.assertEqual(len(b), 128)
        self.assertEqual(b[4], 17)                      # VIEW_ENERGY
        self.assertEqual(int.from_bytes(b[8:10], 'little'), 3)
        self.assertEqual(int.from_bytes(b[10:12], 'little'), 2)
        self.assertEqual(int.from_bytes(b[12:14], 'little'), 7)
        self.assertEqual(int.from_bytes(b[14:16], 'little'), 6)
        self.assertEqual(int.from_bytes(b[16:18], 'little'), 1)
        self.assertEqual(b[32 + 12], E.CELL_FRIEND)
        self.assertEqual(b[64 + 12], 17)

    def test_rand_is_seeded(self):
        def collect(seed):
            out = []

            def pol(view, mem):
                out.append(view.rand)
                return NOP
            e = board([pol], seed=seed)
            e.add_cell(1, 1, 0)
            e.add_cell(3, 3, 0)
            for _ in range(10):
                e.step()
            return out
        self.assertEqual(collect(5), collect(5))
        self.assertNotEqual(collect(5), collect(6))


class FaultTest(unittest.TestCase):
    def _one(self, result):
        def pol(view, mem):
            if isinstance(result, Exception):
                raise result
            return result
        e = board([pol])
        e.add_cell(1, 1, 0, 10)
        e.step()
        return e

    def test_none_is_a_fault(self):
        e = self._one(None)
        self.assertEqual(e.faults[0], {E.FAULT_CRASH: 1})
        self.assertEqual(energy_at(e, 1, 1), 10)

    def test_exception_is_a_fault(self):
        e = self._one(RuntimeError('boom'))
        self.assertEqual(e.faults[0], {E.FAULT_CRASH: 1})

    def test_invalid_action_bytes(self):
        # Reference: any value other than the listed actions is a bad_action fault.
        for a in (0x02, 0x05, 0x0F, 0x14, 0x24, 0x34, 0x44, 0x50, 0xFF):
            e = self._one((a, 3))
            self.assertEqual(e.faults[0], {E.FAULT_BAD_ACTION: 1}, hex(a))

    def test_all_valid_actions_accepted(self):
        for a in sorted(E.VALID_ACTIONS):
            e = self._one((a, 3))
            self.assertEqual(e.faults[0], {}, hex(a))

    def test_only_al_is_read(self):
        # Reference: only al is read as the action; the rest of rax is ignored.
        e = self._one((0x101, 3))
        self.assertEqual(e.faults[0], {})
        self.assertEqual(energy_at(e, 1, 1), 11)

    def test_budget(self):
        # More than 1000 instructions is a fault; exactly 1000 is fine.
        e = self._one((REST, 1001))
        self.assertEqual(e.faults[0], {E.FAULT_BUDGET: 1})
        self.assertEqual(energy_at(e, 1, 1), 10)
        e = self._one((REST, 1000))
        self.assertEqual(e.faults[0], {})
        self.assertEqual(energy_at(e, 1, 1), 11)
        self.assertEqual(e.insn_max[0], 1000)

    def test_faults_counted_per_colony(self):
        pols = [script({}, default=None), script({}, default=(0x77, 2))]
        e = board(pols)
        e.add_cell(0, 0, 0)
        e.add_cell(1, 0, 0)
        e.add_cell(4, 4, 1)
        e.step()
        self.assertEqual(e.faults[0], {E.FAULT_CRASH: 2})
        self.assertEqual(e.faults[1], {E.FAULT_BAD_ACTION: 1})
        self.assertEqual(len(e.fault_log[0]), 2)


class EndAndRankingTest(unittest.TestCase):
    def test_tick_limit(self):
        e = board([script({}, default=(REST, 1)), script({}, default=(REST, 1))], max_ticks=3)
        e.add_cell(0, 0, 0)
        e.add_cell(4, 4, 1)
        e.run()
        self.assertEqual(e.tick, 3)
        self.assertTrue(e.finished)

    def test_ends_when_one_colony_left(self):
        pols = [script({(1, 1): (eat(RIGHT), 1)}, default=(REST, 1)), script({}, default=(REST, 9))]
        e = board(pols, max_ticks=100)
        e.add_cell(1, 1, 0, 10)
        e.add_cell(2, 1, 1, 2)
        res = e.run()
        self.assertEqual(e.tick, 1)
        self.assertEqual(e.death_tick[1], 0)
        self.assertEqual([r['colony'] for r in res], [0, 1])
        self.assertEqual([r['points'] for r in res], [3, 2])

    def test_ends_when_all_dead(self):
        # Every killing action leaves a living cell (the eater, or the fed target), so "all dead" can
        # only be reached from an empty board; check the end condition itself that way.
        e = board([script({}), script({})], max_ticks=100)
        e.run()
        self.assertTrue(e.finished)
        self.assertEqual(e.tick, 1)
        self.assertEqual(e.death_tick[:2], [0, 0])

    def test_feeding_to_death_leaves_target_alive(self):
        # Supports the comment above: a feeder with 1 dies, but its target survives.
        pols = [script({}, default=(feed(RIGHT), 1)), script({}, default=(feed(LEFT), 2))]
        e = board(pols, max_ticks=100)
        e.add_cell(0, 0, 0, 1)
        e.add_cell(1, 0, 1, 1)
        e.run()
        self.assertEqual(e.pop[:2], [0, 1])
        self.assertEqual(energy_at(e, 1, 0), 2)

    def test_single_colony_runs_to_limit(self):
        # ASSUMPTION: "one colony left" only ends a match that started with more than one colony.
        e = board([script({}, default=(REST, 1))], max_ticks=5)
        e.add_cell(0, 0, 0)
        e.run()
        self.assertEqual(e.tick, 5)

    def _rank(self, pop, energy, insn, death):
        e = board([script({})] * 4)
        e.pop, e.energy, e.insn_total, e.death_tick = list(pop), list(energy), list(insn), list(death)
        e.finished = True
        return [r['colony'] for r in e.ranking()], [r['points'] for r in e.ranking()]

    def test_living_rank_by_population(self):
        order, pts = self._rank([5, 9, 7, 1], [0, 0, 0, 0], [0, 0, 0, 0], [None] * 4)
        self.assertEqual(order, [1, 2, 0, 3])
        self.assertEqual(pts, [3, 2, 1, 0])

    def test_then_total_energy_then_fewer_instructions(self):
        order, _ = self._rank([5, 5, 5, 5], [100, 120, 100, 100], [50, 1, 40, 40], [None] * 4)
        self.assertEqual(order, [1, 2, 3, 0])

    def test_full_tie_goes_to_lower_colony(self):
        order, _ = self._rank([5, 5, 5, 5], [9, 9, 9, 9], [3, 3, 3, 3], [None] * 4)
        self.assertEqual(order, [0, 1, 2, 3])

    def test_dead_below_living_by_how_long_they_lasted(self):
        order, _ = self._rank([0, 1, 0, 0], [0, 1, 0, 0], [0, 0, 0, 0], [10, None, 30, 10])
        self.assertEqual(order, [1, 2, 0, 3])      # 0 and 3 died the same tick: lower number first

    def test_dead_colony_with_more_energy_history_still_below_living(self):
        order, _ = self._rank([0, 0, 1, 0], [0, 0, 1, 0], [0, 0, 999999, 0], [2999, 5, None, 5])
        self.assertEqual(order, [2, 0, 1, 3])


class DeterminismTest(unittest.TestCase):
    def test_same_seed_same_match(self):
        import bots

        def play(seed):
            e = E.Engine([bots.hunter, bots.walker, bots.random_bot, bots.medic],
                         width=12, height=12, seed=seed, max_ticks=150)
            res = e.run()
            return e.cells(), [(r['colony'], r['pop'], r['energy']) for r in res]
        self.assertEqual(play(11), play(11))
        self.assertNotEqual(play(11)[0], play(12)[0])


if __name__ == '__main__':
    unittest.main()
