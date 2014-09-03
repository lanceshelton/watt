watt
====
A live MIDI sequencer input for the Digitech Whammy IV

About
----

The Digitech Whammy is a guitar effects pedal that includes a number of pitch-shifting effects. It has a MIDI input that can be used to control all the settings on the pedal.

watt turns the Whammy into a sequencer by playing programs into the MIDI in.  A program cannot control the input pitch, only the effects added to the input pitch.  So rather than defining absolute pitches, a program defines output intervals based on the input to the pedal.

The result is a unique sounding programmable pitch shifter than can make a guitar or any other input sound like a polyphonic synth and sequencer while not destroying the characteristics of the original signal.

A number of key commands are available to allow live modification to the program or the effect currently playing.

Above all watt is a technology-in-music experiment created to explore composition through programming without losing the live component that makes music spontaneous.

Requirements
----

- [Digitech Whammy IV](http://en.wikipedia.org/wiki/DigiTech_Whammy#DigiTech_Whammy_IV)
- midi cable
- computer with a midi output running OSX, WIndows, or Linux
- [pygame](http://www.pygame.org/)

Usage
----

####Programs

List the available programs:

    python watt.py -l

Run a program:

    python watt.py -p [program]

This will run a sequencer program in a loop.

While a program is running you can adjust the BPM using the keyboard:

**+** : go faster

**-** : go slower

####Live
Run without a program:

    python watt.py

This will put watt in octave mode with no sequencer.  Use these keys like a keybaord:


**&nbsp; w &nbsp; e &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; t &nbsp; y &nbsp; u**  
**a &nbsp; s &nbsp; d &nbsp; f &nbsp; g &nbsp; h &nbsp; j &nbsp; k**

These will map to the following intervals from the input pitch:

**&nbsp; m2 m3 &nbsp;&nbsp;&nbsp;&nbsp; A4 m6 m7**  
**P1 M2 M3 P4 P5 M6 M7 P8**

Composition
---
watt programs are not easy to create yet, but there are a couple of tricks:

- Feed a tone generator into the pedal while composing (a looping pedal works great for this)
- Use the live keyboard to write melodies and sequences

Thinking in intervals is a great exercise for learning composition.

Future possibilities
----

- more program banks
- more live controls
- MIDI file input/output support
- recording live key commands to a program
- audio input as a control source
- a watt hardware device
