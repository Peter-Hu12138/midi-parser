## What is the output format?

The output is all MIDI events across channels, condensed into a list of events arranged in chronological order. One can play these individual events in the order they are read in list for playback.

## motives
In CSC258, Computer Organization course at UofT, playing theme music of an old game on a MIPS simulator with a syscall only able to play a MIDI event with arguments pitch, duration, and instrument, is a feature in the project. I hence write this parser.

## standards that are not implemented:

### MIDI Modes (omni mode and poly/ mono mode)
As of right now, poly mode with omni on is assumed.

### pitch bend & sensitivity adjustment
Due to the limit of MIPS simulator syscall, these are currently unuseful for the midi files I collected.

### And most of the controller messages

## Reference
https://www.youtube.com/watch?v=P27ml4M3V7A

http://www.somascape.org/midi/tech/spec.html

https://www.lim.di.unimi.it/IEEE/LYON/META.HTM

https://studiocode.dev/kb/MIDI/midi-pitch-bend/
