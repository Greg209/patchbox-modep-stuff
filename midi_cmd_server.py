#!/usr/bin/python3

import time
import mido
import os
import subprocess
import re
import requests
import sys

import asyncio
import websockets

# midi device naming; avoid spaces
name = "MidiCmdServer2"

# system command to set up the midi thru port
# TODO would be nice to do this in python, but
# rtmidi has issues seeing ports it has created
#os.system(runCmd)
amidiProc = subprocess.Popen(['amidithru', name])

# regex to match on rtmidi port name convention
nameRegex = "(" + name + ":" + name + "\s+\d+:\d+)"
matcher = re.compile(nameRegex)
newList = list(filter(matcher.match, mido.get_input_names()))
input_name = newList[0]

# Parse list of AMSythn preset names to map to CC control values
presets = [line.rstrip('\n') for line in open('/home/patch/presetmap.txt')]

# Used to avoid resending of duplicates as there seems to be multiple MIDI requests come through
lastPresets = [ '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '' ]

# Websocket class. Makes (and restores) a single connection for multiple socket requests
class WebSocket:
  __ws = None
  __url = "ws://patchbox.local/websocket"

  def __init__(self):
    self.retryTime = 0
    self.retryRepeat = 30
    self.__create_connect()

  @asyncio.coroutine
  def __create_connect(self):
    if self.__ws is None:
      if (time.time() - self.retryTime) > self.retryRepeat:
        try:
          self.__ws = yield from websockets.connect(self.__url)
          self.retryTime = 0
        except ConnectionRefusedError:
          self.retryTime = time.time()

  def connect(self):
    if self.__ws is None:
      asyncio.get_event_loop().run_until_complete(self.__create_connect())

  def send(self, msg):
    if self.__ws is not None:
      try:
        asyncio.get_event_loop().run_until_complete(self.__async_send(msg))
      except ConnectionRefusedError:
        self.__create_connect()
    else:
      asyncio.get_event_loop().run_until_complete(self.__create_connect())

  async def __async_send(self, message):
    await self.__ws.send(message)

# Simple function for GET requests
def get(URL, PARAMS):
  global session
  return session.get(url = URL, params = PARAMS)

# keep running and watch for midi cc
while True:

  # Establish a web session for GET requests
  session = requests.Session()
  print("Session setup")
  # Establish a websocket connection
  # NOTE: needed to call .connect manually as it doesn't seem to connect through the __init__
  socket = WebSocket()
  socket.connect()
  print("socket connected")

  try:
    # set up backend
    mido.set_backend('mido.backends.rtmidi')
      
    with mido.open_input(input_name) as inport:
      print("Connected to rtmidi backend")

      # Process the MIDI messages received
      for msg in inport:
        if msg.type == "control_change":
          # TouchOSC CH16 - on/off for AMSynth Instrument preset GET requests
          if msg.channel == 15 and msg.value == 127 and lastPresets[15] != msg.control:
            r = get( 'http://patchbox.local/effect/preset/load/graph/amsynth_1', {'uri':'http://code.google.com/p/amsynth/amsynth#' + presets[msg.control]} )
            lastPresets[15] = msg.control

          # TouchOSC CH15 - FluidDrums preset selection by program number - uses websocket
          if msg.channel == 14 and lastPresets[14] != msg.control:
            cmd = "param_set " + "/graph/FluidPlug_FluidDrums/program " + str(msg.control)
            socket.send( cmd )
            lastPresets[14] = msg.control
    break
  except KeyboardInterrupt:
    print("BYE!!!!")
    break
  except:
    # If unable to connect to rtmidi backend
    # (which sometimes happens when starting), retry after 2 secs
    print("Retrying to connect to rtmidi backend")
    time.sleep(2)
