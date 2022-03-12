from dataclasses import dataclass
from tkinter import Canvas
from lib.hex.transpose_hex import hex_to_point

from core.color import Color
from core.constants import BOARD_CELL_SIZE, MARBLE_SIZE, BOARD_WIDTH, BOARD_HEIGHT

import ui.view.colors.palette as palette
from ui.view.marble import render_marble


@dataclass
class Marble:
    pos: tuple[float]
    cell: tuple[int]
    color: Color
    object_ids: list
    selected: bool = False
    focused: bool = False

class BoardView:

    PADDING = 8
    COLOR_PLAYER_NONE = "#48535A"
    MARBLE_COLORS = {
        Color.BLACK: palette.COLOR_BLUE,
        Color.WHITE: palette.COLOR_RED,
    }

    def __init__(self):
        self._canvas = None
        self._marbles = []

    def mount(self, parent, on_click):
        canvas = Canvas(parent, width=BOARD_WIDTH + self.PADDING * 2, height=BOARD_HEIGHT + self.PADDING * 2, highlightthickness=0)
        canvas.bind("<Button-1>", lambda event: on_click((event.x - self.PADDING, event.y - self.PADDING)))
        self._canvas = canvas
        return canvas

    def _setup(self, model):
        canvas = self._canvas

        marble_items = []
        for cell, color in model.game_board.enumerate():
            pos = self._find_marble_pos(cell)
            self._render_cell(canvas, pos)
            if not self._marbles and color:
                marble_items.append((pos, cell, color))

        for pos, cell, color in marble_items:
            self._marbles.append(Marble(
                pos=pos,
                cell=cell,
                color=color,
                object_ids=render_marble(
                    canvas,
                    pos=pos,
                    color=BoardView.MARBLE_COLORS[color],
                    size=MARBLE_SIZE,
                )
            ))

        return canvas

    def _find_marble_pos(self, cell):
        x, y = hex_to_point((cell.x, cell.y), BOARD_CELL_SIZE / 2)
        return (x + self.PADDING, y + self.PADDING)

    def _render_cell(self, canvas, pos):
        x, y = pos
        canvas.create_oval(
            x - MARBLE_SIZE / 2, y - MARBLE_SIZE / 2,
            x + MARBLE_SIZE / 2, y + MARBLE_SIZE / 2,
            fill=BoardView.COLOR_PLAYER_NONE,
            outline="",
        )

    def _redraw(self, model):
        for marble in self._marbles:
            self._update_marble(model, marble)

    def _update_marble(self, model, marble):
        is_marble_selected = model.selection and marble.cell in model.selection.to_array()
        is_marble_focused = model.selection and marble.cell == (model.selection.end or model.selection.start)
        if (is_marble_selected, is_marble_focused) != (marble.selected, marble.focused):
            marble.selected = is_marble_selected
            marble.focused = is_marble_focused
            self._redraw_marble(marble, selected=is_marble_selected, focused=is_marble_focused)

        marble_pos = self._find_marble_pos(marble.cell)
        for object_id in marble.object_ids:
            old_x, old_y = marble.pos
            new_x, new_y = marble_pos
            delta = (new_x - old_x, new_y - old_y)
            if delta != (0, 0):
                self._canvas.move(object_id, *delta)

        marble.pos = marble_pos

    def _clear_marble(self, marble):
        for object_id in marble.object_ids:
            self._canvas.delete(object_id)

    def _redraw_marble(self, marble, selected=False, focused=False):
        self._clear_marble(marble)
        marble.object_ids = render_marble(
            self._canvas,
            pos=marble.pos,
            color=BoardView.MARBLE_COLORS[marble.color],
            size=MARBLE_SIZE,
            selected=selected,
            focused=focused,
        )

    def _delete_marble(self, marble):
        self._clear_marble(marble)
        self._marbles.remove(marble)

    def render(self, board):
        if self._marbles:
            self._redraw(board)
        else:
            self._setup(board)

    def apply_move(self, move, board, on_end=None):
        move_color = move.selection.get_player(board) # TODO: demeter
        move_cells = move.selection.to_array() # TODO: demeter
        move_head = move.get_front()
        move_target = move_head and move_head.add(move.direction.value) # TODO: add method for target cell
        if move_target and board[move_target] == Color.next(move_color):
            sumito_selection = board.select_marbles_in_line(
                start=move_target,
                direction=move.direction
            )
            print(sumito_selection)
            move_cells += sumito_selection.to_array() if sumito_selection else []

        marble_cells = [(marble, cell) for cell in move_cells if (marble := self._find_marble_by_cell(cell))]
        for marble, cell in marble_cells:
            marble.cell = cell.add(move.direction.value)
            if marble.cell not in board:
                self._delete_marble(marble)

    def _find_marble_by_cell(self, cell):
        return next((marble for marble in self._marbles if marble.cell == cell), None)

    def update(self):
        pass