"""
Contains Abalone-specific hex grid logic.
"""

from __future__ import annotations

from core.constants import BOARD_SIZE
from core.selection import Selection
from core.move import Move
from core.color import Color
from core.hex import Hex
from lib.hex.hex_grid import HexGrid


class Board(HexGrid):
    """
    A hex grid specific to the game of Abalone.
    Implements serialization, extra iteration helpers, and a reference to
    starting layout data for headlessly calculating game score.
    """

    MAX_SUMITO = 3

    @staticmethod
    def create_from_data(data):
        """
        Creates a board from the given board data.
        The original board data is cached within the board for score calculations.
        :param data: an array of arrays of domain 0..2
        :return: a Board
        """
        board = Board()
        board._layout = data
        for r, line in enumerate(data):
            for q, val in enumerate(line):
                q += board.offset(r)  # offset coords - board storage starts at x with size - 1
                cell = Hex(q, r)
                try:
                    board[cell] = Color(val)
                except ValueError:
                    board[cell] = None
        return board

    def __init__(self):
        """
        Initializes a game board.
        """
        super().__init__(size=BOARD_SIZE)
        self._layout = None
        self._items = None

    @property
    def layout(self):
        """
        Gets the board's starting layout.
        Used for headlessly calculating game score.
        """
        return self._layout

    def enumerate(self):
        """
        Returns all positions and values on the game board a la `enumerate`.
        :return: a list of (Hex, T) tuples
        """
        if not self._items:
            self._items = []
            for r, line in enumerate(self._data):
                for q, val in enumerate(line):
                    q += self.offset(r)
                    item = (Hex(q, r), val)
                    self._items.append(item)
        return self._items

    def cell_in_bounds(self, cell: Hex) -> bool:
        """
        :return: If the cell is in bounds.
        """
        return cell in self

    def cell_owned_by(self, cell: Hex, player: Color) -> bool:
        """
        :return: If the cell is owned by the player.
        """
        return self.cell_in_bounds(cell) and self[cell] and self[cell] == player

    def is_valid_move(self, move: Move, current_player: Color) -> bool:
        """
        :return: If the move is valid.
        """
        if move.is_single():
            return self._is_valid_single_move(move)

        if move.is_inline():
            return self._is_valid_inline_move(move, current_player)

        return self._is_valid_sidestep_move(move)

    def get_score(self, player: Color):
        enemy = Color.next(player)

        layout_count = 0
        for line in self._layout:
            for data in line:
                if data == enemy.value:
                    layout_count += 1

        board_count = 0
        for _, color in self.enumerate():
            if color == enemy:
                board_count += 1

        return layout_count - board_count

    def apply_move(self, move: Move):
        """
        Applies a move to the board, changing the position of cells.
        """
        self._apply_sumito_move(move) if move.is_sumito(self) else self._apply_base_move(move)

    def _is_valid_single_move(self, move: Move) -> bool:
        """
        :return: Is a valid single cell move.
        :precondition: Selection is a single cell.
        """
        destination = move.selection.start.add(move.direction.value)

        if not self.cell_in_bounds(destination):
            return False

        if self[destination]:
            return False

        return True

    def _is_valid_inline_move(self, move: Move, current_player: Color) -> bool:
        """
        :return: Is a valid inline move.
        :precondition: Move is inline.
        """
        destination = move.get_front()
        out_of_bounds_valid = False
        for i in range(1, self.MAX_SUMITO + 1):
            destination = destination.add(move.direction.value)
            if not self.cell_in_bounds(destination):
                return out_of_bounds_valid
            if not self[destination]:
                return True
            if self[destination] == current_player:
                return False
            else:
                if i >= move.selection.get_size():
                    return False

                out_of_bounds_valid = True

        return True

    def _is_valid_sidestep_move(self, move: Move) -> bool:
        """
        :return: Is a valid sidestep move.
        :precondition: Move is sidestep.
        """
        for cell in move.selection.to_array():
            destination = cell.add(move.direction.value)

            if not self.cell_in_bounds(destination):
                return False

            if self[destination]:
                return False

        return True

    def _apply_base_move(self, move: Move):
        """
        Applies a move to the board, moving cells at origin to destination.
        :precondition: Move is not sumito.
        """
        player = move.selection.get_player(self)

        for cell in move.selection.to_array():
            self[cell] = None

        for cell in move.get_destinations():
            self[cell] = player

    def select_marbles_in_line(self, start, direction):
        """
        Selects all marbles in the line specified by the given start and direction.
        Selection ends when the destination goes out of bounds or highlights a new color.
        :param start: the Hex to start selecting from
        :param direction: the HexDirection to select in
        :return: a Selection
        """

        color = self[start]
        if color == None:
            return None

        dest_cell = start
        next_cell = start
        while next_cell in self and self[next_cell] == color:
            dest_cell = next_cell
            next_cell = next_cell.add(direction.value)

        return Selection(start, Hex(dest_cell.x, dest_cell.y))

    def _apply_sumito_move(self, move: Move):
        """
        Applies a sumito move to the board, first moves blocking cells in the direction of the move,
        then applies the base move after.
        :precondition: Move is sumito.
        """
        sumito_selection = self.select_marbles_in_line(
            start=move.get_front().add(move.direction.value),
            direction=move.direction,
        )
        sumito_move = Move(sumito_selection, move.direction)

        player = sumito_move.selection.get_player(self)

        for cell in sumito_move.selection.to_array():
            if not self.cell_in_bounds(cell):
                print(sumito_move.selection)
            else:
                self[cell] = None

        for cell in sumito_move.get_destinations():
            if self.cell_in_bounds(cell):
                self[cell] = player

        self._apply_base_move(move)

    def __str__(self):
        # TODO: return a list of comma-separated "pieces", e.g. A1w
        return super().__str__()

    def __setitem__(self, cell, value):
        """
        Sets the value on the board at position `cell` to `value`.
        :param cell: a Hex
        :param value: the value to set
        """
        super().__setitem__(cell, value)
        if cell in self:
            # mark enumeration struct as in need of recalculation
            # TODO(B): only change the value for the associated item
            self._items = None
