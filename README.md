# patchbox-modep-stuff
Python and TouchOSC stuff to support Patchbox and MODEP

My setup
- Raspberry PI3B+ running Patchbox with MODEP
- AKAI MPKmini mkII MIDI controller connected to the Pi
- Behringer UCA222 connected to the Pi for the audio IN/OUT
- a guitar connected to the audio in on the UCA222
- an old phone running TouchOSC for additional control over the MODEP pedalboard

The MODEP pedalboard consists of a software sythn AMSythn with a ton of preset sounds (MIDI ch 1), FluidPianos (again MIDI ch 1) and FluidDrums with a load of kits on MIDI ch 2. MIDI ch1 is assigned to the MPKmini keyboard whilst ch2 is assigned to the pads. In addition to these instruments are a DS1 distortion, Chorus/Flanger (both for the guitar input), SooperLooper and a few other bits.

One aspect of Patchbox-MODEP I was really interested in getting to work was to enable/disable AMSynth and the Piano instruments from the phone via TouchOSC and also to switch presets, again using the phone. Unfortunately MIDI PGM changes don't filter through to MODEP which I understand is the way the MOD DUO changes presets.

The solution I have which is initially based on https://github.com/whofferbert/midi-cmd-server, is to get TouchOSC to send CC messages over an unused MIDI channel to Patchbox where a Python script based on the midi_cmd_server intercepts the messages and then sends those messages over a websocket to MODEP. (Websocket part was based on https://stackoverflow.com/a/56424611)

To begin with I tried mimicing the MODEP web interface GET and POST requests but whilst the GET's worked (AMSynth preset selection), the preset selection for FluidDrums required a POST which relies on a some internal session to be setup. Fortunately the websocket solution was an option.

**presets.txt**
This holds a list of AMSynth preset names each on a separate line that where the line number/array index maps to the TouchOSC button CC number.

**midi_cmd_server.py**
- connects to the amidithru service, opens a websocket to patchbox.local
- loads the AMSythn presets into an array
- listens for unused midi channels - 16 for AMSythn presets, 15 for FluidDrums presets (TouchOSC MIDI CH16 = Python msg.channel=15)
  - AMSythn sends a GET request in the form `http://patchbox.local/effect/preset/load/graph/amsynth_1?uri=http://code.google.com/p/amsynth/amsynth#<preset-name>`
  - FluidDrums sends `param_set /graph/FluidPlug_FluidDrums/program <preset index>` over a websocket to `http://patchbox.local/websocket`
  
For the script to work at startup, I edited the `/etc/rc.local` file and added the following line to the end.

``/home/patch/midi_cmd_server.py &``

