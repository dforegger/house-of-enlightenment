import numpy as np
from hoe import color_utils
import colorsys
import sys
from hoe.animation_framework import Scene, Effect, MultiEffect
from generic_effects import NoOpCollaborationManager
from generic_effects import SolidBackground
from generic_effects import FrameRotator

from hoe import color_utils
from hoe.state import STATE
from hoe.utils import faderInterpolate, sliceForStation

class SeizureMode(Effect):
    def __init__(self, station = None, duration = None):
        self.foo = 1
        if station is None:
            self.slice = ( slice(0,STATE.layout.rows), slice(0, STATE.layout.columns))
        else:
            self.slice = sliceForStation(station)

        self.on = True
        self.delta_t = 0.05
        self.last_step = 0;
        self.duration = duration
        self.station = station
        self.start_time = None

    def scene_starting(self, now):
        self.start_time = now
        print(now)

    def next_frame(self, pixels, now, collaboration_state, osc_data):

        if self.start_time is None:
            self.start_time = now

        self._set_speed_from(osc_data)

        if now - self.last_step > self.delta_t:
            self.last_step = now
            self.on = not self.on

        if self.on:
            pixels[self.slice] = (255,255,255)
        else:
            pixels[self.slice] = (0,0,0)

    def is_completed(self, now, osc_data):
        if self.duration is None:
            return False # Run Forevas

        return now > self.start_time + self.duration

    def _set_speed_from(self, osc_data):
        if self.station is None:
            return

        fader = osc_data.stations[self.station].faders[0]
        self.delta_t = faderInterpolate(fader, 0.0005, 0.2)

class LaunchSeizure(MultiEffect):

    def __init__(self, station = None, button = 0 ):
        MultiEffect.__init__(self)
        self.station = station
        self.button = 0

    def before_rendering(self, pixels, now, collaboration_state, osc_data):
        MultiEffect.before_rendering(self, pixels, now, collaboration_state, osc_data)
        if self.count() > 0:
            return

        buttons = osc_data.stations[self.station].button_presses
        if buttons and self.button in buttons:
            self.add_effect( SeizureMode(station=self.station, duration = 3) )


##
# This runs an explicit 2d wave equation.
# Slider => Damping: Higher value, more damping
# Up/Down (3/2): => Input force from strong negitive to strong positive, force is applied based on all white pixels
# Left/Right (1/0): => Slower / Faster wave propagation.
# Center (4): Reset => Zeros out waves
#
class FiniteDifference(Effect):
    def __init__(self, station = None, master_station=None):
        self.pixels = []
        self.time = []
        self.forceConstant = 400
        self.velocityConstant = 20000.0 # Lower Value == Faster Speed
        self.diffusionConstant = 0.00001 # Bigger Value == More Damping
        self.influence = 0b1111
        self.isFixedBounary = False
        self.X_MAX = STATE.layout.rows
        self.Y_MAX = STATE.layout.columns
        self.master_station = master_station

    def next_frame(self, pixels, now, collaboration_state, osc_data):
        if len(self.pixels) == 0 or self._should_zero(osc_data):
            self.pixels = []
            self.pixels.append(np.empty([self.X_MAX, self.Y_MAX], dtype=float))
            self.pixels.append(np.empty([self.X_MAX, self.Y_MAX], dtype=float))
            self.time = [now*1000, (now-0.3)*1000]

        deltaT  = (now*1000 - self.time[0])
        deltaT2 = deltaT*(self.time[0]-self.time[1])
        self.time[1] = self.time[0]
        self.time[0] = now*1000

        self.pixels.append(np.empty([self.X_MAX, self.Y_MAX], dtype=np.uint16))

        self._set_damping(osc_data)
        self._set_velocity(osc_data)
        self._set_force(osc_data)

        self.wave(pixels, deltaT, deltaT2)
        self.setPixels(pixels)

    def _should_zero(self, osc_data):
        if self.master_station is None:
            return

        buttons = osc_data.stations[self.master_station].button_presses
        return buttons and 4 in buttons

    def _set_force(self, osc_data):
        if self.master_station is None:
            return

        buttons = osc_data.stations[self.master_station].button_presses
        if not buttons:
            return

        if 2 in buttons:
            self.forceConstant = max(-1000, self.forceConstant - 100)
            print(self.forceConstant)

        if 3 in buttons:
            self.forceConstant = min(1000, self.forceConstant + 100)
            print(self.forceConstant)


    def _set_velocity(self, osc_data):
        if self.master_station is None:
            return

        buttons = osc_data.stations[self.master_station].button_presses
        if not buttons:
            return

        if 1 in buttons:
            self.velocityConstant = min(50000, self.velocityConstant*1.1)
            print(self.velocityConstant)

        if 0 in buttons:
            self.velocityConstant = max(3000, self.velocityConstant*0.9)
            print(self.velocityConstant)


    def _set_damping(self, osc_data):
        if self.master_station is None:
            return

        fader = osc_data.stations[self.master_station].faders[0]
        self.diffusionConstant = faderInterpolate(fader, 0.00000001, 0.001)

    def setPixels(self, pixels):

        hsv = np.zeros((self.X_MAX, self.Y_MAX, 3), np.uint8)
        hsv[:,:,0] = self.pixels[2]/0xFFFF*0xFF
        hsv[:,:,1] = 0xFF
        hsv[:,:,2] = 0xFF

        rgb = color_utils.hsv2rgb(hsv)
        pixels[:self.X_MAX,:self.Y_MAX] = rgb

        self.pixels.pop(0)

    ##
    # Calculate next frame of explicit finite difference wave
    #
    def wave(self, pixels, deltaT, deltaT2):
        self.pixels.append(np.empty([self.X_MAX, self.Y_MAX], dtype=float))

        if deltaT2 < 10:
            return

        # Calculate Force based on if if pixel is all white
        pix = np.array(pixels[:,:][:], dtype=np.uint32)
        color = (pix[:,:,0] << 16) | (pix[:,:,1] << 8) | (pix[:,:,2])
        f = np.where(color >= 0xFFFFFF, self.forceConstant, 0)[:self.X_MAX,:self.Y_MAX]

        c = self.velocityConstant
        beta = self.diffusionConstant
        h1 = self.pixels[0]
        h = np.zeros([self.X_MAX,self.Y_MAX], dtype=float)

        h0 = self.pixels[1]
        h, idx = self.hCalc()
        h = (h - h0*idx)/c
        h = (h - beta*(h0-h1)/deltaT)*deltaT2 + 2*h0 - h1 + f

        h = np.clip(h, 0, 0xFFFF)
        self.pixels[2] = h

    def diffuse(self, delta_t):
        self.pixels.append(np.empty([self.X_MAX, self.Y_MAX], dtype=float))

        if delta_t < 10:
            return

        v = self.diffusionConstant
        h0 = self.pixels[1]
        h, idx = self.hCalc()
        hDiff = (h - h0*idx)
        h = hDiff*delta_t/v + h0

        self.pixels[2] = np.clip(h, 0, 0xFFFF)

    ##
    # This is the differences between node i,j and it's closest neighbors
    # it's used in calculateing spatial derivitives
    #
    def hCalc(self):
        h = np.zeros([self.X_MAX,self.Y_MAX], dtype=np.uint32)
        idx = 0
        h0 = self.pixels[1]

        if (self.influence & 0b0001) > 0:
            h[1:,:] = h[1:,:] + h0[:self.X_MAX-1,:]
            h[0,:] = h[0,:] + h0[1,:]
            idx = idx+1

        if (self.influence & 0b0010) > 0:
            h[:self.X_MAX-1,:] = h[:self.X_MAX-1,:] + h0[1:,:]
            h[self.X_MAX-1:,:] = h[self.X_MAX-1,:] + h0[0,:]
            idx = idx+1

        if (self.influence & 0b0100) > 0:
            h[:,1:] = h[:,1:] + h0[:,:self.Y_MAX-1]
            h[:,0] = h[:,0] + h0[:,self.Y_MAX-1]
            idx = idx+1

        if (self.influence & 0b1000) > 0:
            h[:,:self.Y_MAX-1] = h[:,:self.Y_MAX-1] + h0[:,1:]
            h[:,self.Y_MAX-1] = h[:,self.Y_MAX-1] + h0[:,0]
            idx = idx+1

        return h, idx

    def wave_old(self, x, y, is_on, deltaT2):
        if deltaT2 < 10:
            return

        u = [0,0,0,0]
        idx = 0

        boundary = 0 if self.isFixedBounary else self.pixels[1][x,y]

        if (self.influence & 0b0001) > 0:
            value = boundary if x == 0 else self.pixels[1][x-1, y]
            u[idx] = value
            idx = idx + 1
        if (self.influence & 0b0010) > 0:
            value = boundary if x == self.X_MAX-1 else self.pixels[1][x+1, y]
            u[idx] = value
            idx = idx + 1
        if (self.influence & 0b0100) > 0:
            value = self.pixels[1][x, self.Y_MAX-1] if y == 0 else self.pixels[1][x, y-1]
            u[idx] = value
            idx = idx + 1
        if (self.influence & 0b0100) > 0:
            value = self.pixels[1][x,0] if y == self.Y_MAX-1 else self.pixels[1][x, y+1]
            u[idx] = value
            idx = idx + 1

        c = self.velocityConstant
        h0 = self.pixels[1][x,y]
        h1 = self.pixels[0][x,y]
        h = 0.0

        for i in range(idx):
            h = h + u[i] - h0

        f = self.forceConstant if is_on else 0

        h = 2*h0 - h1 + h*deltaT2/c + f;

        if h < 0 :
            h = 0
        elif h > 0xFFFF:
            h = 0xFFFF

        self.pixels[2][x,y] = h


class Diffusion(Effect):
    def __init__(self):
        self.pixels = []
        self.last_step = 0
        self.influence = 0b1111
        self.diffusionConstant = 1000
        self.isFixedBounary = True
        self.X_MAX = STATE.layout.rows
        self.Y_MAX = STATE.layout.columns

    def next_frame(self, pixels, now, collaboration_state, osc_data):
        if len(self.pixels) == 0:
            self.pixels.append(np.empty([self.X_MAX, self.Y_MAX], dtype=np.uint16))

        delta_t = (now - self.last_step)*1000
        self.last_step = now

        self.pixels.append(np.empty([self.X_MAX, self.Y_MAX], dtype=np.uint16))

        for i in range(self.X_MAX):
            for j in range(self.Y_MAX):
                is_on = True if pixels[i,j][0] > 0 else False
                self.diffuse(i,j, is_on, delta_t)

        self.setPixels(pixels)

    def setPixels(self, pixels):
        for i in range(self.X_MAX):
            for j in range(self.Y_MAX):
                v = float(self.pixels[1][i,j])
                if v < 0xFFFF:
                    (r,g,b) =  colorsys.hsv_to_rgb(v/0xFFFF,1,1)
                    pixels[i,j] = (r*255, g*255, b*255)

        self.pixels.pop(0)

    def diffuse(self, x, y, is_on, delta_t):
        if delta_t < 10:
            return

        if is_on:
            self.pixels[1][x,y] = 0xFFFF
            return

        u = []
        idx = 0

        boundary = 0 if self.isFixedBounary else self.pixels[0][x,y]

        if (self.influence & 0b0001) > 0:
            value = boundary if x == 0 else self.pixels[0][x-1, y]
            u.append(value)
            idx = idx + 1
        if (self.influence & 0b0010) > 0:
            value = boundary if x == self.X_MAX-1 else self.pixels[0][x+1, y]
            u.append(value)
            idx = idx + 1
        if (self.influence & 0b0100) > 0:
            value = self.pixels[0][x, self.Y_MAX-1] if y == 0 else self.pixels[0][x, y-1]
            u.append(value)
            idx = idx + 1
        if (self.influence & 0b0100) > 0:
            value = self.pixels[0][x,0] if y == self.Y_MAX-1 else self.pixels[0][x, y+1]
            u.append(value)
            idx = idx + 1

        v = self.diffusionConstant
        h0 = self.pixels[0][x,y]
        h = 0.0

        for i in range(idx):
            h = h + u[i] - h0

        h = h*delta_t/v + h0


        if h < 0 :
            h = 0
        elif h > 0xFFFF:
            h = 0xFFFF

        #if h > 0 and h < 0xFFFF:
            #print(h)

        self.pixels[1][x,y] = h

__all__ = [
    Scene("seizure_mode",
         collaboration_manager=NoOpCollaborationManager(),
         effects=[
             SolidBackground(),
             SeizureMode()
         ]
        ),
    Scene("seizure",
        collaboration_manager=NoOpCollaborationManager(),
        effects=[
            LaunchSeizure(station = 0)
         ]
        ),
    Scene("waves_of_diffusion",
        tags=[Scene.TAG_BACKGROUND],
        collaboration_manager=NoOpCollaborationManager(),
        effects=[
            SolidBackground(color=(255,255,255), start_col=0, end_col=2, start_row=100, end_row=105),
            FrameRotator(rate = 0.5),
            FiniteDifference(master_station=0)
            ]
        )
]


