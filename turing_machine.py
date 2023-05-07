import json
from enum import Enum
from pathlib import Path
from typing import Set, Dict, Tuple, List

from graphviz import Digraph


class Move(Enum):
    MINUS = -1
    ZERO = 0
    PLUS = +1


State = str
Symbol = str
TransitionFunction = Dict[Tuple[State, Symbol], Tuple[State, Symbol, Move]]

BLANK = '□'
Q_ACC = 'Q_acc'
Q_REJ = 'Q_rej'


class Tape:
    def __init__(self, tape: List[Symbol], head: int):
        if len(tape) == 0:
            tape = [BLANK]
        self.tape = tape
        self.head = head

    def __str__(self):
        out = ''
        for i, symbol in enumerate(self.tape):
            if i == self.head:
                out += '[' + symbol + ']'
            else:
                out += ' ' + symbol + ' '
        return out

    def __repr__(self):
        return f'Tape({self.tape}, {self.head})'

    def __trim(self):
        while len(self.tape) > 0 and self.tape[0] == BLANK and self.head > 0:
            self.tape = self.tape[1:]
            self.head -= 1

        while len(self.tape) > 0 and self.tape[-1] == BLANK and self.head < len(self.tape) - 1:
            self.tape = self.tape[:-1]

    def read(self) -> Symbol:
        return self.tape[self.head]

    def write(self, symbol: Symbol):
        self.tape[self.head] = symbol

    def move(self, move: Move):
        self.head += move.value
        if self.head < 0:
            self.tape = [BLANK] + self.tape
            self.head = 0
        if self.head >= len(self.tape):
            self.tape.append(BLANK)
        self.__trim()


class TuringMachine:
    def __init__(
            self,
            tape: Tape,
            states: Set[State],
            input_alphabet: Set[Symbol],
            tape_alphabet: Set[Symbol],
            transition_function: TransitionFunction,
            init_state: State,
            final_states: Set[State],
            description: str = ''
    ):
        self.description = description

        assert len(input_alphabet) > 0
        assert len(tape_alphabet) > 0
        assert input_alphabet.issubset(tape_alphabet)

        for c in input_alphabet:
            assert len(c) == 1

        for c in tape_alphabet:
            assert len(c) == 1

        for c in tape.tape:
            assert c in tape_alphabet or c == BLANK

        assert len(states) > 0

        assert init_state in states
        self.current_state = init_state

        for state in final_states:
            assert state in states

        for (state, symbol), (new_state, new_symbol, move) in transition_function.items():
            assert state in states
            assert symbol in tape_alphabet or symbol == BLANK
            assert new_state in states
            assert new_symbol in tape_alphabet or new_symbol == BLANK
            assert move in Move

        self.tape = tape
        self.states = states
        self.input_alphabet = input_alphabet
        self.tape_alphabet = tape_alphabet
        self.transition_function = transition_function
        self.init_state = init_state
        self.final_states = final_states

    def __str__(self):
        return f'{self.tape}'

    def __repr__(self):
        out = ''
        for (state, symbol), (new_state, new_symbol, move) in self.transition_function.items():
            out += f'\t({state} {symbol}) -> ({new_state} {new_symbol} {move.name}) \n'

        return f'\nTuringMachine:\n' \
               f'tape: {self.tape}\n' \
               f'states: {self.states},\n' \
               f'input_alph: {self.input_alphabet},\n' \
               f'tape_alph: {self.tape_alphabet},\n' \
               f'function:\n{out}' \
               f'init: {self.init_state},\n' \
               f'final: {self.final_states}\n'

    def step(self):
        current_symbol = self.tape.read()
        if self.transition_function.get((self.current_state, current_symbol)) is None:
            print(f"Invalid transition from: ({self.current_state}, {current_symbol})")
            self.current_state = Q_REJ
            return

        (new_state, new_symbol, move) = self.transition_function[(self.current_state, current_symbol)]
        print(f'({self.current_state} {current_symbol}) -> ({new_state} {new_symbol} {move.name})')
        self.tape.write(new_symbol)
        self.tape.move(move)
        self.current_state = new_state

    def run(self, tape: str = ''):
        if tape != '':
            self.tape = Tape(list(tape), 0)
        while self.current_state not in self.final_states:
            print(self, end="\t\t")
            self.step()

    def is_accepted(self):
        return self.current_state in self.final_states and self.current_state == Q_ACC

    def is_rejected(self):
        return (self.current_state in self.final_states and self.current_state == Q_REJ) or \
                  (self.current_state not in self.final_states)

    def is_final(self):
        return self.current_state in self.final_states

    def reset(self):
        self.current_state = self.init_state
        self.tape = Tape([], 0)


def tm_to_diagraph(tm: TuringMachine) -> Digraph:
    g = Digraph('G')
    for state in tm.states:
        g.node(state)

    better_edges = {}

    for (state, symbol), (new_state, new_symbol, move) in tm.transition_function.items():
        if move == Move.PLUS:
            move = '+'
        elif move == Move.MINUS:
            move = '-'
        else:
            move = move.value

        if symbol == new_symbol:
            symbol_label = symbol
        else:
            symbol_label = f'{symbol} -> {new_symbol}'

        if (state, new_state) in better_edges:
            better_edges[(state, new_state)] += f'{symbol_label}; {move}\n'
        else:
            better_edges[(state, new_state)] = f'{symbol_label}; {move}\n'

    for (state, new_state), label in better_edges.items():
        g.edge(state, new_state, label=label)

    for state in tm.final_states:
        g.node(state, style='filled', fillcolor='lime', peripheries='2')

    g.node(tm.init_state, style='filled', fillcolor='cyan')

    g.node(tm.current_state, style='filled', fillcolor='yellow')

    return g


def load_tm(path: str) -> TuringMachine:
    with open(path, 'r') as f:
        lines = f.readlines()

    json_data = json.loads(''.join(lines))

    description = json_data['description']

    states = set(json_data['states'])
    input_alphabet = set(json_data['input_alphabet'])
    tape_alphabet = set(json_data['tape_alphabet'])
    init_state = json_data['init_state']
    final_states = set(json_data['final_states'])

    transition_function = {}
    for transition in json_data['transition_function']:
        state = transition['state']
        symbol = transition['symbol']
        new_state = transition['new_state']
        new_symbol = transition['new_symbol']
        move = transition['move']
        transition_function[(state, symbol)] = (new_state, new_symbol, Move(move))

    return TuringMachine(
        Tape([], 0),
        states,
        input_alphabet,
        tape_alphabet,
        transition_function,
        init_state,
        final_states,
        description
    )


def save_tm(tm: TuringMachine, path: str):
    file = Path(path)
    file.parent.mkdir(exist_ok=True, parents=True)

    file.write_text(json.dumps({
        'description': tm.description,
        'states': list(tm.states),
        'input_alphabet': list(tm.input_alphabet),
        'tape_alphabet': list(tm.tape_alphabet),
        'init_state': tm.init_state,
        'final_states': list(tm.final_states),
        'transition_function': [
            {
                'state': state,
                'symbol': symbol,
                'new_state': new_state,
                'new_symbol': new_symbol,
                'move': move.value
            }
            for (state, symbol), (new_state, new_symbol, move) in tm.transition_function.items()
        ]
    }, indent=4))
