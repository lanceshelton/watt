#!/usr/bin/env python

"""
watt: A live midi sequencer input for the Digitech Whammy

Running a program:
python ./watt.py -p arp

Testing from the command line:
watt = WattOutput(verbose=True)
watt.write_cmd({'cmd': command, 'time': watt.last_timestamp + 10})
watt.stop()
"""

from optparse import OptionParser
import pygame
import pygame.midi
from Queue import Queue
import string
import sys
import termios
import threading
from time import sleep
import tty
from api import *  # pylint: disable=unused-wildcard-import,wildcard-import
from banks import *  # pylint: disable=unused-wildcard-import,wildcard-import

TESTFILE = './watt.out'
LOOP_BUFFER_SECS = .2
LOOP_SLEEP_SECS = .1
NODEV_BUFFER_SECS = 2 * LOOP_SLEEP_SECS

# the buffer must be longer than the loop sleep or starvation will occur
assert LOOP_BUFFER_SECS >= LOOP_SLEEP_SECS * 2

# Controls
KEYBOARD_MAP = {
    'a': P1,
    'w': MIN2,
    's': MAJ2,
    'e': MIN3,
    'd': MAJ3,
    'f': P4,
    't': AUG4,
    'g': P5,
    'y': MIN6,
    'h': MAJ6,
    'u': MIN7,
    'j': MAJ7,
    'k': P8,
    }

#
# Device I/O
#

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
            sleep(LOOP_SLEEP_SECS)

    def stop(self):
        """Stop the device
        """
        self.wait_last()
        # give the commands time to flush out to the device
        sleep(3)
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

    def write_cmd(self, command):
        """Write out a command
        """
        cmd = command['cmd']
        timestamp = command['time']
        force = True if 'force' in command and command['force'] else False
        delay = 0
        if 'stomp' in cmd:
            if cmd['stomp'] != self.stomp or force:
                self.stomp = cmd['stomp']
                self.write_out([0xb0, 0, cmd['stomp']], timestamp)
                #delay += 1
        if 'effect' in cmd:
            if cmd['effect'] != self.effect or force:
                self.effect = effect = cmd['effect']
                # Setting the effect also sets the stomp state.  Using patches
                # 0-15 enables the pedal, using 16-31 maps to the same effects
                # but bypassed.
                if 'stomp' in cmd and cmd['stomp'] == STOMP_BYPASS:
                    effect = effect + 16

                self.write_out([0xc0, effect], timestamp + delay)
                #delay += 1
        if 'toe' in cmd:
            if type(cmd['toe']) is str:
                if cmd['toe'] not in INTERVAL_MAP[self.effect]:
                    print 'not in interval map\r'
                    toe = self.toe
                else:
                    toe = INTERVAL_MAP[self.effect][cmd['toe']]
            else:
                toe = cmd['toe']
            if toe != self.toe or force:
                self.write_out([0xb0, 11, toe], timestamp + delay)
                self.toe = toe

    @staticmethod
    def beat_to_ts(bpm, beats, measure, beat):
        """Convert a music time notation to a timestamp
        """
        ms_per_beat = 60 * 1000 / bpm
        return int((beats * measure + beat) * ms_per_beat)

#
# Thread helpers
#

def write_program(watt, cmd_q, start_time, prog):
    """Queue a program
    """
    bpm = prog.bpm
    beats = prog.beats
    cur_bar = -1
    for command in prog.commands:
        if watt.verbose:
            if command['bar'] > cur_bar:
                print 'start of bar %s\r' % command['bar']
            cur_bar = command['bar']
        tstamp = watt.beat_to_ts(bpm, beats, command['bar'], command['beat'])
        cmd_q.put({'cmd': command, 'time': start_time + tstamp})

#
# Threads
#

def program_thread(watt, cmd_q, prog_q, stop_event, prog, count):
    """Generate commands from a program and push them onto the queue
    """
    # do not queue up much ahead of time without a real device with real latency
    if watt.port == -1:
        buffer_secs = NODEV_BUFFER_SECS
    else:
        buffer_secs = LOOP_BUFFER_SECS

    # Need some time to let initialization complete
    consumed_time = pygame.midi.time() + buffer_secs * 1000

    # count == -1 for infinite play
    while count != 0:
        # sleep when the buffer is full
        while consumed_time > pygame.midi.time() + buffer_secs * 1000:
            sleep(buffer_secs)
            if stop_event.is_set():
                break
        if stop_event.is_set():
            break

        # handle program commands from input
        while not prog_q.empty():
            cmd = prog_q.get()
            if 'bpm' in cmd:
                if cmd['bpm'] == '+':
                    prog.bpm = prog.bpm + 10
                elif cmd['bpm'] == '-':
                    prog.bpm = max(10, prog.bpm - 10)

        # note: watt would be more responsive if the entire program was not
        # queued at once, and instead each beat was queued as needed.
        write_program(watt, cmd_q, consumed_time, prog)
        consumed_time += watt.beat_to_ts(prog.bpm, prog.beats, prog.measures, 0)
        if count > 0:
            count -= 1

def input_thread(watt, cmd_q, prog_q):
    """Get characters from stdin, push the resulting commands onto the queue
    """
    while True:
        key = sys.stdin.read(1)
        if key in '-_':
            prog_q.put({'bpm': '-'})
        elif key in '=+':
            prog_q.put({'bpm': '+'})
        elif key in KEYBOARD_MAP:
            cmd_q.put({'cmd': {'toe': KEYBOARD_MAP[key]},
                       'time': watt.last_timestamp + 10})
        # any non-alphabet character exits
        elif key not in 'qwertyuiopasdfghjklzxcvbnm':
            print 'received key ' + key + ': exiting\r'
            # exit immediately on unmapped key
            break

def command_thread(watt, cmd_q, stop_event):
    """Pop commands from the queue and write them out
    """
    while True:
        # wait for a command
        command = cmd_q.get()
        # write out the command
        watt.write_cmd(command)
        if stop_event.is_set():
            break

def run_threads(watt, programs, program, count):
    """Initialize queue, run threads
    """
    cmd_q = Queue()
    prog_q = Queue()
    program_stop_event = threading.Event()
    command_stop_event = threading.Event()

    # command thread
    c_thread = threading.Thread(target=command_thread,
                                args=(watt, cmd_q, command_stop_event))
    c_thread.start()

    # program thread
    if program is not None:
        p_thread = threading.Thread(target=program_thread,
                                    args=(watt, cmd_q, prog_q,
                                          program_stop_event,
                                          programs[program](),
                                          int(count)))
        p_thread.start()
    else:
        # initialize to upOctave if no program is specified.  This effect works
        # well with live keyboard input
        cmd_q.put({'cmd': {'effect': Effect.upOctave,
                          'stomp': STOMP_ENABLE,
                          'toe': P1},
                   'time': watt.last_timestamp + 10})

    # use the main thread for the input thread
    input_thread(watt, cmd_q, prog_q)

    # signal program generation to stop when the input thread exits
    if program is not None:
        program_stop_event.set()

        # wait for the last program loop to finish (so that the next MUTE
        # command will be the last scheduled command
        watt.wait_last()
        p_thread.join()

    # signal the command thread to stop after the program has completed
    command_stop_event.set()

    # This is a little odd.  The command thread does not detect the stop
    # event because it is waiting on an event.  We need to give it one last
    # command to mute the device anyway, so this also serves the purpose of
    # waking the command thread so that it will detect the stop event.
    cmd_q.put({'cmd': {'effect': Effect.diveBomb,
                       'stomp': STOMP_ENABLE,
                       'toe': MUTE},
               'time': watt.last_timestamp + 10})

    c_thread.join()

#
# Setup
#

def main(args):
    """Parse arguments, set up terminal, call main loop
    """
    parser = OptionParser(description=__doc__)
    parser.add_option("-c", "--count", default='-1', help="iterations to run")
    parser.add_option("-l", "--list", action="store_true", help="list programs")
    parser.add_option("-p", "--program", default=None, help="specify program")
    parser.add_option("-v", "--verbose", action="store_true",
                      help="verbose mode")

    options = parser.parse_args(args)[0]

    # source in all subclasses of WattProgram as runnable programs
    programs = {}
    for cls in WattProgram.__subclasses__():  # pylint: disable=no-member
        programs[cls.name] = cls

    if options.list:
        print string.join(programs.keys(), '\n')
        return 0

    if options.program is not None and options.program not in programs:
        print 'Program %s not found in path' % options.program
        return -1

    watt = WattOutput(verbose=options.verbose)

    # Set the terminal to unbuffered, to catch a single keypress
    infd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(infd)
    try:
        # change TTY settings (reverting them if an exception occurs)
        tty.setraw(infd)

        # main thread execution
        run_threads(watt, programs, options.program, options.count)
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
