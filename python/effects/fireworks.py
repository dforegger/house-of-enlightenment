from hoe.animation_framework import Scene
from hoe.animation_framework import Effect
from hoe.animation_framework import MultiEffect
from generic_effects import NoOpCollaborationManager
from hoe.state import STATE
from hoe.fountain_models import FountainDefinition, FountainLaunchingController
from shared import SolidBackground
# from ripple import Ripple
import time
import numpy as np
from collections import deque
import colorsys


class RisingLine(Effect):
    """
    base effect that is used for all the launchers below
    """

    def __init__(self,
                 color=(255, 255, 0),
                 start_row=2,
                 start_col=16,
                 height=5,
                 delay=0,
                 ceil=STATE.layout.rows - 1):
        self.color = color
        self.start_row = start_row
        self.start_col = start_col
        self.height = height
        self.delay = delay  # ms
        self.ceil = ceil

        self.cur_top = self.start_row
        self.cur_bottom = self.start_row
        self.start_ms = time.time() * 1000

    def next_frame(self, pixels, now, collaboration_state, osc_data):

        # don't start until after the delay
        elapsed_ms = now * 1000 - self.start_ms
        if (elapsed_ms < self.delay):
            return

        self.cur_top = self.cur_top + 4
        self.cur_bottom = self.cur_top - self.height

        # min/max to make sure we don't render out of bounds
        bottom = max(self.cur_bottom, self.start_row)
        top = min(self.cur_top, STATE.layout.rows - 1)

        for y in range(bottom, top):
            pixels[y, self.start_col] = self.color

    def is_completed(self, t, osc_data):
        return self.cur_bottom >= self.ceil


def roman_candle_fountain(start_col=16, width=8, color=(255, 0, 0), **kwargs):

    forward_cols = map(lambda col: col % STATE.layout.columns, range(start_col, start_col+width))
    backward_cols = forward_cols[::-1]  # reverse

    sequence = forward_cols + backward_cols

    #+ forward_cols + backward_cols

    # print "forward_cols", forward_cols
    # print "backward_cols", backward_cols
    # print "sequence", sequence

    def make_line((i, col)):
        return RisingLine(height=30, start_col=col, delay=i * 100, color=color)

    effects = map(make_line, enumerate(sequence))

    return MultiEffect(*effects)


def around_the_world_fountain(start_col=16, color=(0, 255, 0), **kwargs):
    """
    Around the world launcher - shoot small lines all the way around the gazebo
    """

    # [0, ..., 65]
    all_cols = range(0, STATE.layout.columns)
    # [start_col, ..., 65, 0, ..., start_col - 1]
    shifted = np.roll(all_cols, -start_col)

    # print "start_col", start_col
    # print "shifted", shifted

    def make_line((i, col)):
        return RisingLine(height=9, start_col=col, delay=i * 30, color=color, ceil=50)

    effects = map(make_line, enumerate(shifted))

    return MultiEffect(*effects)


def fzero_fountain(section=1, color=(0, 255, 255), **kwargs):
    """
        F-Zero Launcher - make a f-zero speed boost arrow around the start_col
        """
    # get 5 pixels to either side to select the 11 columns in this section
    cols = range(section*11, (section+1)*11)

    # group them by levels to make an f-zero speed boost arrow
    levels = [[cols[5]],
              [cols[4], cols[6]],
              [cols[3], cols[7]],
              [cols[2], cols[8]],
              [cols[1], cols[9]],
              [cols[0], cols[10]]]


    def make_line((i, col)):

        # fade the colors on the edges
        def get_color():
            hsv = colorsys.rgb_to_hsv(color[0] // 255, color[1] // 255, color[2] // 255)
            rgb = colorsys.hsv_to_rgb(hsv[0], hsv[1], hsv[2] - (i * 0.12))
            return (rgb[0] * 255, rgb[1] * 255, rgb[2] * 255)

        return RisingLine(height=50, start_col=col, delay=i * 80, color=get_color())

    effects = map(make_line, enumerate(levels))

    return MultiEffect(*effects)


FOUNTAINS = [
    FountainDefinition("roman", roman_candle_fountain),
    FountainDefinition("aroundtheworld", around_the_world_fountain),
    FountainDefinition("fzero", fzero_fountain),
]