#!/usr/bin/env python

"""
watt: A live midi sequencer input for the Digitech Whammy

Running a program:
python ./watt.py -p arp

Testing from the command line:
watt = WattOutput(verbose=True)
watt.write_cmd(command, watt.last_timestamp + 10, force=True)
watt.stop()
"""

from optparse import OptionParser
import pygame
import pygame.midi
import sys
import termios
import thread
from time import sleep
import tty
from api import (Effect, INTERVAL_MAP, STOMP_BYPASS, STOMP_ENABLE, MUTE,
                 WattProgram)
from banks import *  # pylint: disable=unused-wildcard-import,wildcard-import

TESTFILE = './watt.out'
LOOP_BUFFER_MSECS = 3 * 1000
LOOP_SLEEP_MSECS = 100
NODEV_BUFFER_MSECS = 2 * LOOP_SLEEP_MSECS

# Controls
BPM_OFFSET = 0

# the buffer must be longer than the loop sleep or starvation will occur
assert LOOP_BUFFER_MSECS >= LOOP_SLEEP_MSECS * 2

class WattOutput(pygame.midi.Output):
    """Manage the MIDI output.  There are currently some simplifications here
    that assume only one device will be used at a time.

    """

    def __init__(self, verbose=False, latency=2000):
        pygame.init()
        pygame.midi.init()
        self.verbose = verbose
        self.port = pygame.midi.get_default_output_id()
        self.fdev = None
        # -1 means no device detected, use file device
        if self.port == -1:
            print 'No device detected, using file device\r'
            self.fdev = open(TESTFILE, 'w')
            self.fdev.write('Starting watt output file\n')
        else:
            pygame.midi.Output.__init__(self, self.port, latency)
        # Track the state of the hardware, starts in an unknown state
        self.stomp = None
        self.effect = None
        self.toe = None
        # Keep track of when scheduled commands will finish
        self.last_timestamp = 0

    def update_last_timestamp(self, timestamp):
        """If this command is later than all scheduled commands, update
        """
        if timestamp > self.last_timestamp:
            self.last_timestamp = timestamp

    def wait_last(self):
        """Wait until all scheduled commands have completed
        """
        while self.last_timestamp > pygame.midi.time():
            sleep(1)
        print "Waited until %s for last command at %s\r" % (
            pygame.midi.time(), self.last_timestamp)

    def stop(self):
        """Stop the device
        """
        self.write_cmd({'effect': Effect.diveBomb,
                        'stomp': STOMP_ENABLE,
                        'toe': MUTE}, self.last_timestamp + 10, force=True)
        self.write_cmd({'effect': Effect.diveBomb,
                        'stomp': STOMP_ENABLE,
                        'toe': MUTE}, self.last_timestamp + 1000, force=True)
        self.wait_last()
        if self.fdev is not None:
            self.fdev.close()
        if self.port != -1:
            self.abort()
            self.close()
        pygame.midi.quit()

    def write_out(self, byte_array, timestamp):
        """Write out to midi device
        """
        if self.verbose:
            print '[%s] %s %s\r' % (pygame.midi.time(), byte_array, timestamp)
        if self.fdev is not None:
            self.fdev.write('%s %s\n' % (byte_array, timestamp))
        if self.port != -1:
            self.write([[byte_array, timestamp]])
        self.update_last_timestamp(timestamp)

    def write_cmd(self, command, timestamp, force=False):
        """Write out a command
        """
        delay = 0
        if 'stomp' in command:
            if command['stomp'] != self.stomp or force:
                self.stomp = command['stomp']
                self.write_out([0xb0, 0, command['stomp']], timestamp)
                #delay += 1
        if 'effect' in command:
            if command['effect'] != self.effect or force:
                self.effect = effect = command['effect']
                # Setting the effect also sets the stomp state.  Using patches
                # 0-15 enables the pedal, using 16-31 maps to the same effects
                # but bypassed.
                if 'stomp' in command and command['stomp'] == STOMP_BYPASS:
                    effect = effect + 16

                self.write_out([0xc0, effect], timestamp + delay)
                #delay += 1
        if 'toe' in command:
            if type(command['toe']) is str:
                if command['toe'] not in INTERVAL_MAP[self.effect]:
                    raise Exception
                toe = INTERVAL_MAP[self.effect][command['toe']]
            else:
                toe = command['toe']
            if toe != self.toe or force:
                self.write_out([0xb0, 11, toe], timestamp + delay)
                self.toe = toe

    @staticmethod
    def beat_to_ts(bpm, beats, measure, beat):
        """Convert a music time notation to a timestamp
        """
        ms_per_beat = 60 * 1000 / bpm
        return int((beats * measure + beat) * ms_per_beat)

    def write_program(self, start_time, prog):
        """Write out a program
        """
        bpm = prog.bpm
        beats = prog.beats
        cur_bar = -1
        for command in prog.commands:
            if self.verbose:
                if command['bar'] > cur_bar:
                    print 'start of bar %s\r' % command['bar']
                cur_bar = command['bar']
            tstamp = self.beat_to_ts(bpm, beats, command['bar'],
                                     command['beat'])
            self.write_cmd(command, start_time + tstamp)

def wait_for_input():
    """Get a single character of input, validate
    """
    global BPM_OFFSET  # pylint: disable=global-statement
    while True:
        key = sys.stdin.read(1)
        if key == '-' or key == '_':
            BPM_OFFSET -= 10
        elif key == '=' or key == '+':
            BPM_OFFSET += 10
        else:
            print 'received key ' + key + ': exiting\r'
            # exit immediately on unmapped key
            thread.interrupt_main()
            break

def play_loop(watt, prog, count):
    """Queue commands
    """
    # do not queue up much ahead of time without a real device with real latency
    if watt.port == -1:
        buffer_msecs = NODEV_BUFFER_MSECS
    else:
        buffer_msecs = LOOP_BUFFER_MSECS

    default_bpm = prog.bpm

    # Need some time to let initialization complete
    consumed_time = pygame.midi.time() + buffer_msecs

    # count == -1 for infinite play
    while count != 0:
        # sleep when the buffer is full
        while consumed_time > pygame.midi.time() + buffer_msecs:
            sleep(.1)
        prog.bpm = max(1, default_bpm + BPM_OFFSET)
        watt.write_program(consumed_time, prog)
        consumed_time += watt.beat_to_ts(prog.bpm, prog.beats, prog.measures, 0)
        if count > 0:
            count -= 1

def main(args):
    """Parse arguments, set up terminal, call main loop
    """

    parser = OptionParser(description=__doc__)
    parser.add_option("-c", "--count", default='-1',
                      help="iterations to run")
    parser.add_option("-p", "--program", default='default',
                      help="specify program")
    parser.add_option("-v", "--verbose", action="store_true",
                      help="verbose mode")

    options = parser.parse_args(args)[0]

    # source in all subclasses of WattProgram as runnable programs
    programs = {}
    for cls in WattProgram.__subclasses__():  # pylint: disable=no-member
        programs[cls.name] = cls

    if options.program not in programs:
        print 'Program %s not found in path' % options.program
        return -1

    # Set the terminal to unbuffered, to catch a single keypress
    infd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(infd)
    watt = None
    try:
        # change TTY settings (reverting them if an exception occurs)
        tty.setraw(infd)

        # input thread
        thread.start_new_thread(wait_for_input, tuple())

        watt = WattOutput(verbose=options.verbose)
        play_loop(watt, programs[options.program](), int(options.count))
    except (KeyboardInterrupt, SystemExit):
        # return term to normal state before exception is displayed
        termios.tcsetattr(infd, termios.TCSADRAIN, old_settings)
    finally:
        if watt:
            watt.stop()
        # always return term to normal state
        termios.tcsetattr(infd, termios.TCSADRAIN, old_settings)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
