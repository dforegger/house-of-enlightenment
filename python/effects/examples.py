from hoe import color_utils
from hoe.animation_framework import Scene
from hoe.animation_framework import Effect
from hoe.animation_framework import CollaborationManager
from hoe.animation_framework import EffectFactory
from hoe.animation_framework import MultiEffect
import generic_effects
import debugging_effects


class SpatialStripesBackground(Effect):
    def next_frame(self, pixels, t, collaboration_state, osc_data):
        for ii, coord in enumerate(self.layout.pixels):
            self.spatial_stripes(pixels, t, coord, ii)

    #-------------------------------------------------------------------------------
    # color function
    def spatial_stripes(self, pixels, t, coord, ii):
        """Compute the color of a given pixel.

        t: time in seconds since the program started.
        ii: which pixel this is, starting at 0
        coord: the (x, y, z) position of the pixel as a tuple
        n_pixels: the total number of pixels

        Returns an (r, g, b) tuple in the range 0-255

        """
        if pixels[ii]:
            return

        # make moving stripes for x, y, and z
        x, y, z = coord["point"]
        r = color_utils.scaled_cos(x, offset=t / 4, period=1, minn=0, maxx=0.7)
        g = color_utils.scaled_cos(y, offset=t / 4, period=1, minn=0, maxx=0.7)
        b = color_utils.scaled_cos(z, offset=t / 4, period=1, minn=0, maxx=0.7)
        r, g, b = color_utils.contrast((r, g, b), 0.5, 2)
        pixels[ii] = (r * 256, g * 256, b * 256)


class MovingDot(Effect):
    def __init__(self, spark_rad=8, t=0, layout=None, n_pixels=None):
        Effect.__init__(self, layout, n_pixels)
        self.spark_rad = spark_rad
        self.start_time = t

    def next_frame(self, pixels, t, collaboration_state, osc_data):
        spark_ii = ((t - self.start_time) * 80) % self.n_pixels

        # TODO this should be way faster
        for ii, c in [(int((spark_ii + x) % self.n_pixels), 255 - x * 128 / self.spark_rad)
                      for x in range(self.spark_rad)]:
            pixels[ii] = pixels[ii] if pixels[ii] else (c, c, c)


class SampleEffectLauncher(MultiEffect):
    def before_rendering(self, pixels, t, collaboration_state, osc_data):
        if osc_data.stations[0].buttons:
            self.launch_effect(t)

    def launch_effect(self, t):
        print "Adding Effect"
        e = MovingDot(t=t, layout=self.layout, n_pixels=self.n_pixels)
        self.effects.append(e)


"""osc_printing_effect = Effect("print osc", PrintOSC)
red_effect=EffectDefinition("all red", DadJokes)
spatial_background=EffectDefinition("spatial background", SpatialStripesBackground)
moving_dot = EffectDefinition("moving dot", MovingDot)
green_fill = EffectDefinition("green fill", AdjustableFillFromBottom)

__all__= [
    SceneDefinition("red printing scene", osc_printing_effect, red_effect),
    SceneDefinition("red with green bottom", osc_printing_effect, green_fill, red_effect),
    SceneDefinition("spatial scene", spatial_background),
    SceneDefinition("red scene with dot", moving_dot, red_effect),
    SceneDefinition("spatial scene with dot", moving_dot, spatial_background)
]"""


class SampleFeedbackEffect(CollaborationManager, Effect):
    def next_frame(self, pixels, t, collaboration_state, osc_data):
        for ii in self.layout.row[0] + self.layout.row[1]:
            pixels[ii] = (0, 255, 0)

    def compute_state(self, t, collaboration_state, osc_data):
        pass


osc_printing_effect = debugging_effects.PrintOSC()
spatial_background = SpatialStripesBackground()
red_background = generic_effects.SolidBackground((255, 0, 0))
blue_background = generic_effects.SolidBackground((0, 0, 255))
moving_dot = MovingDot()

default_feedback_effect = SampleFeedbackEffect()

__all__ = [
    Scene("launchdots", default_feedback_effect, osc_printing_effect,
          SampleEffectLauncher(), generic_effects.SolidBackground((0, 255, 255))),
    Scene("redgreenprinting", default_feedback_effect, osc_printing_effect,
          generic_effects.SolidBackground()),
    Scene("adjustablebackground", default_feedback_effect,
          generic_effects.AdjustableFillFromBottom(), red_background),
    Scene("bluewithdot", default_feedback_effect, moving_dot, blue_background),
    Scene("spatial scene", default_feedback_effect, spatial_background)
]
