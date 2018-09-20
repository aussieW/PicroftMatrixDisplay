# Play = [00,80,C0,E0,F0,E0,C0,80,00]
# Stop = [00,00,F8,F8,F8,F8,F8,00,00]

#!/usr/bin/env python
#
# Note: Keep customer characters in the range 0 - 127 as unicode
#       can't handle codes above 127.

from samplebase import SampleBase
from rgbmatrix import graphics, RGBMatrixOptions
import time, datetime
import random
import datetime, time
from pytz import timezone
from whenareyou import whenareyou  # pip install whenareyou
#from playsound import playsound  # pip install playsound
#import pyaudio, wave, sys
import subprocess
#from PIL import Image  #<< Only included because pyinstaller doesn't work without it.

GreenBinReferenceDate = datetime.date(2017, 01, 24)  # Tuesday of a green bin week
defaultTrackPosY = trackPosY = 7
#trackDisplayDelay = 300  # Number of seconds to leave the track on screen after the player mode has been changed to Stop. # << Doesn't need to be global.
#playerStoppedTime = 0
rollTime = None
worldTimeZone = None
worldTimeOffsetY = 0
defaultWorldTimeOffsetY = 17
wtCity = None
#doorBellSound = AudioFile(r'/home/pi/rpi-rgb-led-matrix/python/samples/Doorbell.wav')
doorBellSound = r'/home/pi/rpi-rgb-led-matrix/python/samples/Doorbell.wav'

# Wakeword heard and now listening for user input.
listening = False

import paho.mqtt.client as MQTT
MQTTServer = '192.168.1.49'

LMSDisplayTopic = '/squeezebox/pool/track'
LMSTimeRemainingTopic = '/squeezebox/pool/remaining'
LMSModeTopic = '/squeezebox/mode/pool'

ControlTopic = 'kitchen/display/#'
MatrixSetBrightnessTopic = 'kitchen/display/brightness'
MatrixGetBrightnessTopic = '/ledmatrix/mungurrahill/kitchen/getBrightness'

#LocalTimeTopic = '/time/local'
TemperatureTopic = 'sensor/#' #mungurrahill/#'
DeckTemperatureTopic = 'sensor/temperature/deck'
LoungeRoomTempTopic = 'sensor/temperature/lounge_room'
StudyTempTopic = 'sensor/temperature/study'
KitchenTempTopic = 'sensor/temperature/kitchen'
PoolTempTopic = 'sensor/temperature/pool'
SpaTempTopic = 'sensor/temperature/spa'
OutsideTempTopic = 'sensor/temperature/outside'

HumidityTopic = '/humidity/mungurrahill/#'
DeckHumidityTopic = '/humidity/mungurrahill/deck'
OutsideHumidityTopic = '/humidity/mungurrahill/outside'

PressureTopic = '/pressure/mungurrahill/#'
OutsidePressureTopic = '/pressure/mungurrahill/outside'

DoorBellTopic = '/door/mungurrahill/front'

WorldTimeTopic = 'kitchen/display/worldtime'  # '/time/timezone'

DoorBellTopic = '/door/mungurrahill/front'

WakeWordTopic = 'kitchen/display/wakeword'
UserUtteranceTopic = 'kitchen/display/utterance'

#class AudioFile:
#    chunk = 1024
#
#    def __init__(self, file):
#        """ Init audio stream """ 
#        self.wf = wave.open(file, 'rb')
#        self.p = pyaudio.PyAudio()
#        self.stream = self.p.open(
#            format = self.p.get_format_from_width(self.wf.getsampwidth()),
#            channels = self.wf.getnchannels(),
#            rate = self.wf.getframerate(),
#            output = True
#        )
#
#    def play(self):
#        """ Play entire file """
#        data = self.wf.readframes(self.chunk)
#        while data != '':
#            self.stream.write(data)
#            data = self.wf.readframes(self.chunk)
#
#    def close(self):
#        """ Graceful shutdown """ 
#        self.stream.close()
#        self.p.terminate()

class AudioFile:
    def __init__(self, file):
        """ Init audio stream """ 
        self.wf = wave.open(file, 'rb')
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format = self.p.get_format_from_width(self.wf.getsampwidth()),
            channels = self.wf.getnchannels(),
            rate = self.wf.getframerate(),
            output = True,
            stream_callback = self.callback
        )


    def callback(self, in_data, frame_count, time_info, status):
        data = self.wf.readframes(frame_Count)
        return (data, pyaudio.paContinue)




def dateOfNextMonday():
    today = d = datetime.date.today()
    while d.weekday() != 0:
        d += datetime.timedelta(1)
    return d

def on_connect(mqttClient, userdata, flags, rc): # Works with paho mqtt version 1.3.0
#def on_connect(mqttClient, userdata, rc):  # Works with paho mqtt version 1.2.3
    print("Connecting.......")
    print("connected to %s with result code %s" %(MQTTServer, rc))
    mqttClient.subscribe(LMSDisplayTopic)
    mqttClient.subscribe(LMSTimeRemainingTopic)
    mqttClient.subscribe(LMSModeTopic)
    mqttClient.subscribe(TemperatureTopic)
    mqttClient.subscribe(HumidityTopic)
    mqttClient.subscribe(PressureTopic)
    mqttClient.subscribe(WorldTimeTopic)
    mqttClient.subscribe(DoorBellTopic)
    mqttClient.subscribe(ControlTopic)
    #mqttClient.subscribe(LocalTimeTopic)
    mqttClient.loop_start() #<<< WHY IS THIS ALSO IN THE __MAIN__ FUNCTION??????

def on_message(mqttClient, userdata, msg):
    global track, timeRemaining, mode, prevMode, modeChanged, decktemp, formaltemp, kitchentemp, pooltemp, spatemp, studytemp, playerStoppedTime, trackRolledOff, defaultTrackPosY, trackPosY, trackDisplayed, rollTime, worldTimeZone, worldTimeOffsetY, wtCity, listening, utterance, utteranceDisplayed  #, localtime
#    print('Topic: %s, \nMessage: %s' %(msg.topic, msg.payload))
    if msg.topic == LMSDisplayTopic:
        track = msg.payload
        #for l in track:
        #    print(ord(l))  # Print the ascii represenation of the character.
        return
    elif msg.topic == LMSModeTopic:
        prevMode = mode
        mode = msg.payload
        modeChanged = True
        rollTime = time.time()
        # Store the time the player stopped. This is used to remove the track after a delay.
        if mode == 'stop':
            playerStoppedTime = time.time()
            print 'Player Stopped Time: %s' %playerStoppedTime
            trackRolledOff = False
        else:
            trackPosY = defaultTrackPosY
            trackDisplayed = True
        return
    elif msg.topic == UserUtteranceTopic:
        utterance = msg.payload
        utteranceDisplayed = True
        return
    elif msg.topic == DeckTemperatureTopic:
        decktemp = msg.payload + chr(126)
        return
    elif msg.topic == KitchenTempTopic:
        kitchentemp = msg.payload + chr(126)
	return
    elif msg.topic == LoungeRoomTempTopic:
        formaltemp = msg.payload + chr(126)
        return
    elif msg.topic == StudyTempTopic:
        studytemp = msg.payload + chr(126)
  	return
    elif msg.topic == PoolTempTopic:
        pooltemp = msg.payload + chr(126)
        return
    elif msg.topic == SpaTempTopic:
        spatemp = msg.payload + chr(126)
        return
    elif msg.topic == WakeWordTopic:
        if msg.payload == 'begin':
            listening = True
        else:
            listening = False
        return
    elif msg.topic == LMSTimeRemainingTopic:
        mins = str(int(msg.payload) / 60)
        secs = str(int(msg.payload) % 60)
        if len(secs) == 1:
            timeRemaining = mins + ":0" + secs
        else:
            timeRemaining = mins + ':' + secs
        return
    elif msg.topic == WorldTimeTopic:
        # If the worldTimeZone is set to None then it will not be displayed.
        try:
            wtCity = msg.payload
            worldTimeZone = whenareyou(wtCity) #timezone(msg.payload)
            worldTimeOffsetY = defaultWorldTimeOffsetY
            print "------- Displaying the World Time --------"
        except:
            print "+++++++ Hiding the World Time ++++++++"
            worldTimeOffsetY = 0
            worldTimeZone = None
        return
    elif msg.topic == DoorBellTopic:
        #playsound(doorBellSound, False)  # False = non blocking
        #doorBellSound = AudioFile(r'/home/pi/Doorbell.wav')
        #doorBellSound.play()
        #doorBellSound.close()
        #doorBellSound.stream.start_stream()
#        subprocess.Popen(['aplay', doorBellSound]) ## <<-- THIS WORKS!
	subprocess.Popen("aplay Doorbell.wav", shell=True)  # from https://community.mycroft.ai/t/need-help-creating-a-sounds-skill-doable-not-doable/2234
        return
    elif msg.topic == MatrixSetBrightnessTopic:
        parser.setBrightness(int(msg.payload))
        print('Brightness set to %s' %msg.payload)
    elif msg.topic == MatrixGetBrightnessTopic:
        print parser.getBrightness()

#    elif msg.topic == LocalTimeTopic:
#        localtime = msg.payload
#        if localtime[-1:] == '<':
#            localtime = localtime[:-1] + ' AM'
#        else:
#            localtime = localtime[:-1] + ' PM'
#        return


class Display(SampleBase):
    def __init__(self, *args, **kwargs):
        super(Display, self).__init__(*args, **kwargs)

    def run(self):
        global modeChanged, prevMode, trackRolledOff, playerStoppedTime, trackDisplayed, trackPosY, rollTime, worldTimeZone, worldTimeOffsetY, wtCity, listening, utterance, utteranceDisplayed  #, trackDisplayDelay

        offscreenCanvas = self.matrix.CreateFrameCanvas()

        # Define fonts.
        utterancefont = graphics.Font()
        utterancefont.LoadFont("../../fonts/4x6.bdf")
        trackfont = graphics.Font()
        trackfont.LoadFont("../../fonts/6x9.bdf")
        symbolfont = graphics.Font()
        symbolfont.LoadFont("../../fonts/6x9_Symbols.bdf")
        hourMinuteFont = graphics.Font()
        hourMinuteFont.LoadFont("../../fonts/7x13B.bdf")
        secondsFont = graphics.Font()
        secondsFont.LoadFont("../../fonts/5x7.bdf")
        wtCityFont = graphics.Font()
        wtCityFont.LoadFont("../../fonts/4x6.bdf")
        wtHourMinuteFont = graphics.Font()
        wtHourMinuteFont.LoadFont("../../fonts/7x13B.bdf")
        wtSecondsFont = graphics.Font()
        wtSecondsFont.LoadFont("../../fonts/5x7.bdf")
        dayDateFont = graphics.Font()
        dayDateFont.LoadFont("../../fonts/4x6.bdf")
        tempTextFont = graphics.Font()
        tempTextFont.LoadFont("../../fonts/4x6.bdf")
        tempFont = graphics.Font()
        tempFont.LoadFont("../../fonts/5x7.bdf")

        # Define font colours.
        trackColor = graphics.Color(255,0,0)
        playerStatusColor = graphics.Color(127,127,127)
        #textColor1 = graphics.Color(random.randint(0,255), random.randint(0,255), random.randint(0,255))
        timeColor = graphics.Color(255,255,255)
        worldTimeColor = graphics.Color(0,0,0)
        temperatureTextColor = graphics.Color(0,255,110) #(0,234,148) #(198,0,92) #(255,180,255) #(148,242,7)
        tempColor = graphics.Color(0,75,175) #(0,198,125) #(255,0,120) #(255,10,255)
        greenBinColor = graphics.Color(0,0,255)
        yellowBinColor = graphics.Color(255,0,255)



        # Set up screen positions.
        maxX = trackPosX = utterancePosX = offscreenCanvas.width
        posX = 0
        #y = offscreenCanvas.height
        timePosX = 1
        timePosY = 5 ####### <<<<< Set back to 13
        dayTextPosX = 43
        dayTextPosY = -1 #0 #7
        dateTextPosX = 42
        dateTextPosY = 5 #13
        temp_0_PosX = 2
        temp_1_PosX = 33
        tempTextLine_0_PosY = 18 #22 #29
        tempLine_0_PosY = 25 #29 #36	
        tempTextLine_1_PosY = 32 #36 #43
        tempLine_1_PosY = 39 #43 #50
        tempTextLine_2_PosY = 46 #50 #57
        tempLine_2_PosY = 53 #57 #64
        #tempLine_3_PosY = 64
        #tempTextLine_3_PosY = 64
	
        # Set up some configurable parameters.
        trackDisplayed = True #False   # Control whether the track is displayed.
        print 'Went passed here again'
        trackDisplayDelay = 10 #300  # Number of seconds to leave the track on screen after the player mode has been changed to Stop.
        trackPosY = 7
        trackOffsetY = trackPosY + 1
        #localTimeOffsetY = 13
        #trackRollOffPosY = trackPosY

        utterancePosY = 0

        # Get the current mode of LMS.
        mqttClient.publish('/squeezebox/control', 'mode')
        # On startup set prevMode to mode to prevent animations.
        prevMode = mode

        # Get the current track.
        mqttClient.publish('/squeezebox/control', 'track')

#        prevMode = mode
#        modeChanged = False
        symbolPosX = 0
        modeSymbol = {'play':'>', 'pause':'|', 'stop':'*'}
        symbolDisplayed = 'none'
        symbolHoldDelay = 10
        symbol = mode

        trackPosXx = 6

        # Define a sine table lookup.
        sineTable = [127,152,176,198,217,233,245,252,254,252,245,233,217,198,176,152,128,103,79,57,38,22,10,3,0,10,22,38,57,79,103]
        smoothSineTable = [128,130,132,134,136,139,141,143,145,148,150,152,154,156,158,161,163,165,167,169,171,173,175,178,180,182,184,186,188,190,192,193,195,197,199,201,203,205,206,208,210,211,213,215,216,218,220,221,223,224,226,227,228,230,231,232,234,235,236,237,238,239,241,242,243,244,244,245,246,247,248,249,249,250,251,251,252,252,253,253,254,254,254,255,255,255,255,255,255,255,256,255,255,255,255,255,255,255,254,254,254,253,253,252,252,251,251,250,249,249,248,247,246,245,244,244,243,242,241,239,238,237,236,235,234,232,231,230,228,227,226,224,223,221,220,218,216,215,213,211,210,208,206,205,203,201,199,197,195,193,192,190,188,186,184,182,180,178,175,173,171,169,167,165,163,161,158,156,154,152,150,148,145,143,141,139,136,134,132,130,128,125,123,121,119,116,114,112,110,107,105,103,101,99,97,94,92,90,88,86,84,82,80,77,75,73,71,69,67,65,64,62,60,58,56,54,52,50,49,47,45,44,42,40,39,37,35,34,32,31,29,28,27,25,24,23,21,20,19,18,17,16,14,13,12,11,11,10,9,8,7,6,6,5,4,4,3,3,2,2,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,2,2,3,3,4,4,5,6,6,7,8,9,10,11,11,12,13,14,16,17,18,19,20,21,23,24,25,27,28,29,31,32,34,35,37,39,40,42,44,45,47,49,50,52,54,56,58,60,62,63,65,67,69,71,73,75,77,80,82,84,86,88,90,92,94,97,99,101,103,105,107,110,112,114,116,119,121,123,125]
        breatheTable = [150, 176, 198, 217, 233, 245, 252, 254, 252, 245 ,233, 217, 198  ,176 , 150 , 121, 85, 45, 16 ,0, 16, 45, 85, 121]
        appleBreatheTable = [28,29,30,33,37,41,48,55,65,76,90,107,126,148,174,204,238,204,174,148,126,107,90,76,65,55,48,41,37,33,30,29,28] # Loosely based on y = 0.0009x^4 - 0.045x^3 + 1.136x^2 - 16.031x + 119.26 with x ranging between 0 and 32.
        pulseTime = time.time()

        # Define track scrolling parameters
        lastScroll = time.time()
        scrollDelay = 0.035

        # Define utterance scrolling parameters
        utteranceLastScroll = time.time()

        while True:
            offscreenCanvas.Clear()
            #print mode, trackDisplayed
            # Display track information.
            if trackDisplayed == True:
                # # If the mode has changed set some parameters.
                # if modeChanged:
                #     rollTime = time.time()
                #     modeChanged = False
                # If no track playing set text to start at left of screen and set a timer to remove the track display
                # after a configurable amount of time.
                if mode == 'stop':
                    symbolDisplayed = mode  #modeSymbol[mode]  # << Remove this after testing. 
                    if prevMode != 'stop':
                        if modeChanged:
                            symbolPosX = -5
                            trackPosXx = 1
                            r = 0
                            modeChanged = False
                            rollTime = time.time()
                        elif symbolPosX < 0 and trackPosXx < 6: 
                            symbolPosX += 1
                            trackPosXx += 1
                            pulseTime = time.time()
                        else:
                            # Pulse the stop symbol using a sine wave to set the color.
                            if time.time() - pulseTime > 0.12:
                                pulseTime = time.time()
                                r += 1
                                if r > len(breatheTable)-1:
                                    r = 0
                                #colorIndex = self.valmap(sineTable[r], 0, 254, 30, 180)
                                colorIndex = self.valmap(breatheTable[r], 0, 254, 20, 190)
                                playerStatusColor = graphics.Color(colorIndex, 0, 0)
                    #graphics.DrawText(offscreenCanvas, trackfont, symbolPosX, trackPosY , playerStatusColor, '*')
                    # If the player is stopped and the delay time has been reached then roll the track off the display. 
                    if time.time() - playerStoppedTime > trackDisplayDelay:
                        if not trackRolledOff and (time.time() - rollTime > 0.35):
                            rollTime = time.time()
                            trackPosY -= 1
                            #print 'Print trackPosY: %s' % trackPosY
                            if trackPosY < -1:
                                trackRolledOff = True
                                #print 'trackDisplayed: %s' %trackDisplayed
                                trackDisplayed = False
                        ## Reset the track Y position
                        #trackPosY = defaultTrackPosY
                        #print trackPosY
                    graphics.DrawText(offscreenCanvas, trackfont, trackPosXx , trackPosY , trackColor, track)
                    graphics.DrawText(offscreenCanvas, symbolfont, symbolPosX, trackPosY , playerStatusColor, '*')
                elif mode == 'pause':
                    symbolDisplayed = mode  #modeSymbol[mode]  # << Remove this after testing.
                    symbol = mode
                    if prevMode != 'pause':
                    #    # Slowly bring the pause symbol back on to the screen from the left.
                        if modeChanged:
                            symbolPosX = -5
                            trackPosXx = 1
                            r = 0
                            modeChanged = False
                        elif symbolPosX < 0 and trackPosXx < 6:
                            symbolPosX += 1
                            trackPosXx += 1
                            pulseTime = time.time()
                        #else:symbolDisplayed = mode  #modeSymbol[mode]  # << Remove this after testing.
                            #modeChanged = False
                        else:
                            # Pulse the pause symbol using a sine wave to set the color.
                            if time.time() - pulseTime > 0.1:
                                pulseTime = time.time()
                                r += 1
                                if r > len(appleBreatheTable)-1:
                                    r = 0
                                #colorIndex = self.valmap(sineTable[r], 0, 254, 30, 180)
                                colorIndex = self.valmap(appleBreatheTable[r], 0, 254, 20, 190)
                                playerStatusColor = graphics.Color(colorIndex, colorIndex, colorIndex)
                    graphics.DrawText(offscreenCanvas, trackfont, trackPosXx , trackPosY , trackColor, track)
                    graphics.DrawText(offscreenCanvas, symbolfont, symbolPosX, trackPosY , playerStatusColor, modeSymbol[mode])
                elif mode == 'play':
#                    print 'Mode changed: %s' %modeChanged
#                    print symbolDisplayed
#                    print 'Prev Mode: %s' %prevMode
                    if modeChanged:
                        r = 0
                        modeChanged = False
#                        symbol = mode
                    if prevMode != 'play':
                        # If there is a symbol still displayed from a previous mode, scroll it off.
                        if len(symbolDisplayed) > 0 and symbolDisplayed in ['pause', 'stop']:
                            #print 'Passed this test. symbolDisplayed: %s symbolPosX: %s  trackPosXx: %s' %(symbolDisplayed,symbolPosX, trackPosXx)  
                            # Roll the current symbol off the screen before displaying the new one.
                            if symbolPosX > -5 and trackPosXx > 1:
                                #print 'and passed this test'
                                if time.time() - rollTime > 0.25:
                                    symbolPosX -= 1
                                    trackPosXx -= 1
                                    rollTime = time.time()
                                    symbol = prevMode
                            else:
                                symbolDisplayed = 'rollon'
                                symbol = mode
 #                               symbolPosX = -5
 #                               trackPosXx = 1
 #                               r = 0
 #                               rollTime = time.time()
                        # If there is no symbol displayed, set up for the current mode's symbol.
                        elif symbolDisplayed == 'none':
                            symbol = mode
                            print 'Just set symbol to %s' %symbol
                            symbolPosX = -5
                            trackPosXx = 1
                            r = 0
                            rollTime = time.time()
                            symbolDisplayed = 'rollon'
                        # If the current mode's symbol is not fully displayed, scroll it on.
                        elif symbolDisplayed == 'rollon':
                            #print symbolPosX, trackPosXx  
                            if symbolPosX < 0 and trackPosXx < 6:
                                if time.time() - rollTime > 0.25:
                                    symbolPosX += 1
                                    trackPosXx += 1
                                    #print symbolPosX, trackPosXx
                                    pulseTime = time.time()
                                    rollTime = time.time()
                            else:
                                symbolDisplayed = 'rolloff'
                                rollTime = time.time() + symbolHoldDelay  # Hold the symbol on the display for symbolHoldDelay before rolling it off.
                        elif symbolDisplayed == 'rolloff':
                            if symbolPosX > -5 and trackPosXx > 1:
                                if time.time() - rollTime > 0.25:
                                    symbolPosX -= 1
                                    trackPosXx -= 1
                                    rollTime = time.time()
                            else:
                                symbolDisplayed = 'None'


                        # If the current mode's symbol is not fully displayed, scroll it on.
                        elif symbolDisplayed == modeSymbol[mode]:
                            if symbolPosX < 0 and trackPosXx < 6:
                                symbolPosX += 1
                                trackPosXx += 1
                                # Draw a black rectangle to prevent the track from scrolling over the play symbol.
                                #????????
                                pulseTime = time.time()
                    if symbolDisplayed <> 'None':
                        # Pulse the pause symbol using a sine wave to set the color.
                        if time.time() - pulseTime > .05:
                            pulseTime = time.time()
                            r += 1
                            if r > len(appleBreatheTable)-1:
                                r = 0
                            colorIndex = self.valmap(appleBreatheTable[r], 0, 254, 30, 180)
                            playerStatusColor = graphics.Color(0, 0, colorIndex)
                    length = graphics.DrawText(offscreenCanvas, trackfont, trackPosX , trackPosY , trackColor, track)
                    if symbolDisplayed:
                        # If there is a symbol displayed (either full or partial) then black out part of the scrolling track name.
                        for y in range(10):
                            graphics.DrawLine(offscreenCanvas, 0,y,symbolPosX+5,y,graphics.Color(0,0,0));
                        #print 'Symbol: %s' %symbol
                        graphics.DrawText(offscreenCanvas, symbolfont, symbolPosX, trackPosY , playerStatusColor, modeSymbol[symbol])

                    # Draw a black rectangle over the last few characters, then show the time remaining in mins:seconds.
                    for y in range(10):
                        graphics.DrawLine(offscreenCanvas, 48,y,64,y,graphics.Color(0,0,0));
                    # Display remaining time.
                    graphics.DrawText(offscreenCanvas, dayDateFont, 49, trackPosY, trackColor, timeRemaining)

                    # Scroll the text from right to left.
                    if time.time() - lastScroll > scrollDelay:
                        lastScroll = time.time()
                        trackPosX -= 1
                        if (trackPosX + length < 0):
                            trackPosX = maxX

            # Display the local time and date.
            graphics.DrawText(offscreenCanvas, hourMinuteFont, timePosX, timePosY+trackPosY, timeColor, time.strftime('%H:%M'))
            graphics.DrawText(offscreenCanvas, secondsFont, timePosX+31, timePosY+trackPosY, timeColor, time.strftime('%S'))
            # Colour the date and day based on the bin type for the week (i.e. Green waste or Recycle).
            if (dateOfNextMonday() - GreenBinReferenceDate ).days%14 == 6: 
                #Green Bin
                dayDateTextColor = greenBinColor 
            else:
                # Yellow Bin
                dayDateTextColor = yellowBinColor  
            graphics.DrawText(offscreenCanvas, dayDateFont, dayTextPosX, dayTextPosY+trackPosY, dayDateTextColor, time.strftime('%a'))
            graphics.DrawText(offscreenCanvas, dayDateFont, dateTextPosX, dateTextPosY+trackPosY, dayDateTextColor, time.strftime('%d %b'))              

            # Display the world time and date.
            if worldTimeZone:
                # Draw a white background.
                for y in range(timePosY+worldTimeOffsetY+trackPosY-16,timePosY+worldTimeOffsetY+trackPosY+1):
                    graphics.DrawLine(offscreenCanvas, 0,y,64,y,graphics.Color(100,100,100));
                worldTime = datetime.datetime.now(worldTimeZone)
                graphics.DrawText(offscreenCanvas, wtCityFont, timePosX, timePosY+worldTimeOffsetY+trackPosY-10, worldTimeColor, wtCity)
                graphics.DrawText(offscreenCanvas, wtHourMinuteFont, timePosX, timePosY+worldTimeOffsetY+trackPosY, worldTimeColor, worldTime.strftime('%H:%M'))
                graphics.DrawText(offscreenCanvas, wtSecondsFont, timePosX+31, timePosY+worldTimeOffsetY+trackPosY, worldTimeColor, worldTime.strftime('%S')) 
                graphics.DrawText(offscreenCanvas, dayDateFont, dayTextPosX, dayTextPosY+worldTimeOffsetY+trackPosY, worldTimeColor, worldTime.strftime('%a'))
                graphics.DrawText(offscreenCanvas, dayDateFont, dateTextPosX, dateTextPosY+worldTimeOffsetY+trackPosY, worldTimeColor, worldTime.strftime('%d %b')) 

            if listening:
                # Draw a red square around the perimiter of the screen.
                graphics.DrawLine(offscreenCanvas, 0, 0, 0, 63, trackColor)
                graphics.DrawLine(offscreenCanvas, 0, 63, 63, 63, trackColor)
                graphics.DrawLine(offscreenCanvas, 63, 63, 63, 0, trackColor)
                graphics.DrawLine(offscreenCanvas, 0, 0, 63, 0, trackColor)

            # Display the utterance
            if utteranceDisplayed:
                utteranceLength = graphics.DrawText(offscreenCanvas, utterancefont, utterancePosX, 63, trackColor, utterance)
                # Scroll the text from right to left.
                if time.time() - utteranceLastScroll > scrollDelay:
                    utteranceLastScroll = time.time()
                    utterancePosX -= 1
                    if (utterancePosX + utteranceLength < 1):
                        utterancePosX = maxX



            graphics.DrawText(offscreenCanvas, tempTextFont, temp_0_PosX, tempTextLine_0_PosY+worldTimeOffsetY, temperatureTextColor, 'Kitchen')
            graphics.DrawText(offscreenCanvas, tempFont, temp_0_PosX, tempLine_0_PosY+worldTimeOffsetY, tempColor, kitchentemp)
            graphics.DrawText(offscreenCanvas, tempTextFont, temp_1_PosX, tempTextLine_0_PosY+worldTimeOffsetY, temperatureTextColor, 'Deck')
            graphics.DrawText(offscreenCanvas, tempFont, temp_1_PosX, tempLine_0_PosY+worldTimeOffsetY, tempColor, decktemp)

            graphics.DrawText(offscreenCanvas, tempTextFont, temp_0_PosX, tempTextLine_1_PosY+worldTimeOffsetY, temperatureTextColor, 'Formal')
            graphics.DrawText(offscreenCanvas, tempFont, temp_0_PosX, tempLine_1_PosY+worldTimeOffsetY, tempColor, formaltemp)
            graphics.DrawText(offscreenCanvas, tempTextFont, temp_1_PosX, tempTextLine_1_PosY+worldTimeOffsetY, temperatureTextColor, 'Study')
            graphics.DrawText(offscreenCanvas, tempFont, temp_1_PosX, tempLine_1_PosY+worldTimeOffsetY, tempColor, studytemp)

            graphics.DrawText(offscreenCanvas, tempTextFont, temp_0_PosX, tempTextLine_2_PosY+worldTimeOffsetY, temperatureTextColor, 'Pool')
            graphics.DrawText(offscreenCanvas, tempFont, temp_0_PosX, tempLine_2_PosY+worldTimeOffsetY, tempColor, pooltemp)
            graphics.DrawText(offscreenCanvas, tempTextFont, temp_1_PosX, tempTextLine_2_PosY+worldTimeOffsetY, temperatureTextColor, 'Spa')
            graphics.DrawText(offscreenCanvas, tempFont, temp_1_PosX, tempLine_2_PosY+worldTimeOffsetY, tempColor, spatemp)

#            time.sleep(0.035)  # <<<--- IS THIS STILL REQUIRED.

            offscreenCanvas = self.matrix.SwapOnVSync(offscreenCanvas)

    def valmap(self, x, inMin, inMax, outMin, outMax):
        return int((x - inMin) * (outMax - outMin) / (inMax - inMin) + outMin)    


# Main function
if __name__ == "__main__":

    mqttClient = MQTT.Client()
    mqttClient.on_connect = on_connect
    mqttClient.on_message = on_message
    print("Attempting to connect")
    mqttClient.connect(MQTTServer, 1883, 60)
    print("Should be connected")

    # Initialise global variables.
    ### CONSIDER MOVING THESE OUTSIDE OF ANY FUNCTIONS (i.e. Near the GreenBinReferenceDate). ###
    ### THEN MAY NOT NEED THE GLOBAL DECLARATION IN on_message().                             ###
    track = ''
    utterance = ''
    utteranceDisplayed = False
    mode = None
    prevMode = mode
    modeChanged = False #True
    playerStoppedTime = None
    trackRolledOff = False
    timeRemaining = ''
#    localtime = '00:00 AM'
    decktemp = '---'  + chr(126)
    kitchentemp = '---'  + chr(126)
    formaltemp = '---' + chr(126)
    masterbedtemp = '---' + chr(126)
    cellartemp = '---' + chr(126)
    cellarhumidity = '---%'
    studytemp = '---' + chr(126)
    garagetemp = '---' + chr(126)
    pooltemp = '---' + chr(126)
    spatemp = '---' + chr(126)

    mqttClient.loop_start()

    parser = Display()

    if (not parser.process()):
        parser.print_help()
