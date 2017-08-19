"""Effects that translate the existing pixels.

Each effect has a source and then a shift.
"""
import time

import numpy as np

from hoe import color_utils
from hoe.distance import *
from hoe import pixels
from hoe import transitions


class UpAndRotateEffect(object):
    """Copy rows up with a rotation

    Args:
        layout: layout object
        row: the source for the new rows at the bottom
    """

    def __init__(self, layout, row, up_speed=None, rotate_speed=None):
        self.layout = layout
        self.up_speed = up_speed or consistent_speed_to_pixels(50)  # rows / second
        # is this redundant with the bottom row also rotating?
        self.rotate_speed = rotate_speed or consistent_speed_to_pixels(30)  # columns / second
        self.row = row

    def start(self, now):
        self.last_time = now
        self.row.start(now)
        self.up_speed.start(now)
        self.rotate_speed.start(now)
        # need my own copy of pixels
        self.pixels = pixels.Pixels(self.layout)

    def next_frame(self, now, pixels):
        pixels_up = self.up_speed(now)
        pixels_rotate = int(self.rotate_speed(now))
        #print 'Rotating Structure', pixels_rotate
        # if now - self.last_time > 3:
        #     self.rotate_speed.pixels_per_frame = (
        #         self.rotate_speed.pixels_per_frame + np.random.randint(-5, 5)) % 66
        #     print self.rotate_speed.pixels_per_frame
        #     self.last_time = now
        print 'rotation:', pixels_rotate
        rainbow = self.row(now)
        # copy existing pixels up and rotate
        self.up_and_rotate(pixels_up, pixels_rotate)
        # fill in the bottom rows
        for i in range(pixels_up):
            self.pixels[10 + i, :] = rainbow
        pixels[:] = self.pixels[:]

    def up_and_rotate(self, up, rotate):
        if up == 0 and rotate == 0:
            return
        if up == 0:
            before_idx = self.layout.grid[10:, :]
        else:
            before_idx = self.layout.grid[10:-up, :]
        if rotate == 0:
            after_idx = self.layout.grid[10 + up:, :]
        else:
            a = self.layout.grid[10 + up:, rotate:]
            b = self.layout.grid[10 + up:, :rotate]
            after_idx = np.concatenate((a, b), axis=1)
        self.pixels[after_idx] = self.pixels[before_idx]


# This needs some work...
#
# First, the movement isn't that exciting, but I like the idea
#  of being able to set a flexible width
# Second, the color source should be a parameter and the sine
#  wave made into a seperate source
class UpAndExpandEffect(object):
    def __init__(self, layout):
        self.layout = layout
        self.count = 0
        # track a color and width
        self.center = 40
        # a column of color. We set the pixels at the bottom
        # and move the rest of them up
        self.color = np.zeros((216, 3), np.uint8)
        # the width of the pixels at each row.
        self.width = np.zeros(216, np.float)
        # how fast we move the pixels up
        self.speed = consistent_speed_to_pixels(50)

    def start(self, now):
        self.speed.start(now)
        self.color[0] = (255, 0, 0)
        self.width[0] = 1
        self.clr = 0

    def next_frame(self, now, pixels):
        self.paint_color_widths(pixels)
        self.set_new_color_widths(now)

    def set_new_color_widths(self, now):
        px = self.speed(now)
        if px > 0:
            self.color[px:] = self.color[:-px]
            self.color[:px] = (self.clr, 0, 0)
            self.clr = self.new_color(now)
            self.width[px:] = self.width[:-px] + .25
            self.width[px] = 1

    def paint_color_widths(self, pixels):
        for row, (color, width) in enumerate(zip(self.color, self.width)):
            width = int(width)
            if (2 * width) + 1 > self.layout.columns:
                pixels[row, :] = color
                continue
            start = (self.center - width) % self.layout.columns
            end = (self.center + width + 1) % self.layout.columns
            if start < end:
                pixels[row, start:end] = color
            else:
                pixels[row, start:] = color
                pixels[row, :end] = color

    def new_color(self, now):
        # need this to follow a linear brightness
        return color_utils.color_correct(
            int(color_utils.remap(np.sin(4 * np.pi * now), -1, 1, 0, 255)))


class Rotate(object):
    """Rotates / rolls an array at a varying speed.

    Args:
        n: number of items in the array
        rotation_speed: a transition instance that returns how fast we're rotating
    """

    def __init__(self, n, rotation_speed=None):
        self.rotation = 0
        self.n = n
        self.rotation_speed = rotation_speed or transitions.SpeedTransition(5, 55)

    def start(self, now):
        self.last_time = now
        self.rotation_speed.start(now)

    def __call__(self, arr, now):
        # vary the rotation speed
        speed = self.rotation_speed.update(now)
        print '--', speed
        delta = (now - self.last_time) * speed
        self.last_time = now
        self.rotation = (self.rotation + delta) % self.n
        # using negative rotation here seems to be less impressive
        # I think its because it matches with the rotation of
        # the entire structure.
        return rotate(arr, int(self.rotation))


# idx can be negative
def rotate(arr, idx):
    return np.roll(arr, idx, axis=0)


# constants to make moving easier to specify
# Can do like: 2*UP + 3*LEFT
UP = np.array((1, 0))
DOWN = np.array((-1, 0))
LEFT = np.array((0, -1))
RIGHT = np.array((0, 1))


def move(position, movement, shape, clip_or_wrap):
    """Apply `movement` to `position` and then clip/wrap as necessary

    Args:
        position: numpy array
        movement: numpy array
        shape: max values allowed for each dimension
    """
    new_position = np.array(position) + np.array(movement)
    print new_position
    clip = np.clip(new_position, 0, shape)
    wrap = new_position % shape
    return np.where(clip_or_wrap, clip, wrap)
