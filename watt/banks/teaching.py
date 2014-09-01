"""
Example watt programs designed to show what is possible, not to be musical.
"""

from api import *  # pylint: disable=unused-wildcard-import,wildcard-import

class WattDefault(WattProgram):
    """default program on start
    """
    name = 'default'
    bpm = 240
    beats = 4
    measures = 2
    commands = [
        {'bar': 0, 'beat': 0, 'stomp': STOMP_BYPASS},
        {'bar': 0, 'beat': 2, 'stomp': STOMP_ENABLE},
        {'bar': 1, 'beat': 0, 'effect': Effect.upOctave, 'toe':FWD},
        {'bar': 1, 'beat': 1, 'toe': BACK},
        {'bar': 1, 'beat': 2, 'effect': Effect.downOctave, 'toe':FWD},
        {'bar': 1, 'beat': 3, 'toe': BACK},
        ]

class WattCycle(WattProgram):
    """Cycle through effects
    """
    name = 'cycle'
    bpm = 280
    beats = 16
    measures = 1

    @property
    def commands(self):  # pylint: disable=no-self-use
        """commands setter"""
        for effect in range(0, 16):
            yield {'bar': 0, 'beat': effect, 'effect': effect}

class WattGliss(WattProgram):
    """Sweep toe up
    """
    name = 'gliss'
    bpm = 280
    beats = 1
    measures = 1

    @property
    def commands(self):  # pylint: disable=no-self-use
        """commands setter"""
        yield {'bar': 0, 'beat': 0, 'effect': Effect.up2Octaves}
        for toe in range(0, 128):
            yield {'bar': 0, 'beat': float(toe)/128, 'toe': toe}

class WattSiren(WattProgram):
    """Sounds like a siren
    """
    name = 'siren'
    bpm = 60
    beats = 1
    measures = 2

    @property
    def commands(self):  # pylint: disable=no-self-use
        """commands setter"""
        yield {'bar': 0, 'beat': 0, 'effect': Effect.up2Octaves}
        for toe in range(0, 128):
            yield {'bar': 0, 'beat': float(toe)/128, 'toe': toe}
        for toe in range(127, -1, -1):
            yield {'bar': 1, 'beat': float(128-toe-1)/128, 'toe': toe}

class WattMajor(WattProgram):
    """Walk up a scale
    """
    name = 'major'
    bpm = 240
    scale = IONIAN
    beats = len(scale)
    measures = 1

    @property
    def commands(self):
        """commands setter"""
        for beat, note in enumerate(self.scale):
            yield {'bar': 0, 'beat': beat, 'effect': Effect.upOctave,
                   'toe': note}

class WattArpeggio(WattProgram):
    """Arpeggiate
    """
    name = 'arpeggio'
    bpm = 240
    scale = IONIAN
    beats = 8
    measures = 1
    commands = [
        {'bar': 0, 'beat': 0, 'effect': Effect.up2Octaves, 'toe': scale[0]},
        {'bar': 0, 'beat': 1, 'toe': scale[2]},
        {'bar': 0, 'beat': 2, 'toe': scale[4]},
        {'bar': 0, 'beat': 3, 'toe': scale[7]},
        {'bar': 0, 'beat': 4, 'toe': scale[6]},
        {'bar': 0, 'beat': 5, 'toe': scale[4]},
        {'bar': 0, 'beat': 6, 'toe': scale[3]},
        {'bar': 0, 'beat': 7, 'toe': scale[1]},
        ]
