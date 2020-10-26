#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

###############################################################
###############################################################
###############################################################
#
#
#   O. Devauchelle, A. Fournier, P. Godefroy
#
#   March 2016
#
#   The arduino must be installed with StandardFirmata
#   On the arduino IDE: Fichiers/Examples/Firmata/StandardFirmata
#
#
###############################################################
###############################################################
###############################################################

from pylab import *
from time import time, sleep
import matplotlib.animation as animation
import pyfirmata as pf
import easygui as gui

################################################################# Default configuration and gui

config = [
    ( u'Fichier de sauvegarde', './temperatures_plan_solaire.csv' ),
    ( u"Pas de temps [s]", '1' ),
    ( u"Résistance pont 1 [Ohm]", '7490' ),
    ( u"Résistance pont 2 [Ohm]", '7490' ),
    ( u'Calibration sonde 1 (A,B)', '( 0.000600, 0.00276 )' ),
    ( u'Calibration sonde 2 (A,B)', '( 0.000581, 0.002954 )' ),
    ]

title = "Configuration de la mesure de température"

message = u'''
Arduino fonctionnant avec PyFirmata:
Fichiers/Examples/Firmata/StandardFirmata

1: sonde blanche, connectée au port A0
2: sonde noire, connectée au port A1

Formule de calibration :
T = 1./( A*log10( R ) + B ) - 273.15
T [°C], R [kOhm]
'''

config_keys = [ field[0] for field in config ]
config_values = [ field[1] for field in config ]

config_values = gui.multenterbox( message, title, config_keys, config_values )

config = dict( zip(config_keys, config_values))

def string_to_tuple(s):
    AB = s.translate( None,'()' ).split(',')
    AB = [ float(value) for value in AB ]
    return tuple(AB)

################################################

dt = 1000.*float( config[u"Pas de temps [s]"] ) #ms, time between measurements

U_ref = 5. # volts, reference tension of the Arduino, and of the resistance bridge, typically 5V

calib_sonde_TH1 = (0.000600, 0.00276 )#string_to_tuple( config[u'Calibration sonde 1 (A,B)'] ) # sonde blanche
calib_sonde_TH2 = (0.000581, 0.002954 )#string_to_tuple( config[u'Calibration sonde 2 (A,B)'] ) # sonde noire

R_pont_1 = float( config[u"Résistance pont 1 [Ohm]"] ) # ohm
R_pont_2 = float( config[u"Résistance pont 2 [Ohm]"] ) # ohm

pin_1, pin_2 = 0,1 # Arduino connectors

the_line_width = 1.5
style_1 = { 'label':'T1', 'color': 'orange', 'lw': the_line_width }
style_2 = { 'label':'T2', 'color': 'green', 'lw': the_line_width }

number_of_measurements_per_block = 2
data_file_name = config[u'Fichier de sauvegarde']

data_save = not( data_file_name == '' )

#################################################

for port in '/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyACM2':

    try:

        print('Connecting to Arduino on port ' + port)

        arduino = pf.Arduino(port)
        pf.util.Iterator(arduino).start()
        for pin in pin_1, pin_2:
            arduino.analog[pin].enable_reporting()

        print('Connected to Arduino.')

        break

    except:

        print('Failed to connect to Arduino on port ' + port)

################################################

def tension_arduino( the_pin, nb_mes = number_of_measurements_per_block ):

    mesure = []

    for i in range(nb_mes) :
        try :
            mesure += [ U_ref*float( arduino.analog[the_pin].read() ) ] # volts

        except :
            mesure += [ nan ]
            print('Arduino nan.')

    return nanmean(mesure)


def tension_to_resistance( U_therm, R_pont ):
    try:
        return R_pont/( U_ref/U_therm - 1. )*1e-3 # kohm
    except:
        return nan
        print('Resistance nan.')

def resistance_to_temperature( R_therm, calib_sonde ):
    A, B = calib_sonde
    try:
        return 1./( A*log10(R_therm) + B ) - 273.15
    except:
        return nan
        print('Temperature nan.')

def measure():

    t0 = time()

    while True:

        t = time() - t0
        T_1 = resistance_to_temperature( tension_to_resistance( tension_arduino( pin_1 ), R_pont_1 ), calib_sonde_TH1 )
        T_2 = resistance_to_temperature( tension_to_resistance( tension_arduino( pin_2 ), R_pont_2 ), calib_sonde_TH2 )

        yield t, T_1, T_2


##############################################"

fig, ax = subplots()
line_1, = ax.plot( [], [], **style_1 )
line_2, = ax.plot( [], [], **style_2 )
legend( loc = 'best')

t_list, T_1_list, T_2_list = [], [], []

def init():

    ax.set_ylim(0., 100.)
    ax.set_xlim(0, 10)

    ax.set_xlabel( 'Temps [s]' )
    ax.set_ylabel( u'Température [°C]' )

    del t_list[:]
    del T_1_list[:]
    del T_2_list[:]

    line_1.set_data( t_list, T_1_list )
    line_2.set_data( t_list, T_2_list )

    if data_save :
        with open( data_file_name, 'w' ) as data_file:
            data_file.write(u'# temps [s], temperature sonde 1 [deg C], temperature sonde 2 [deg C]\n')

    return line_1, line_2

def update_plot( data ):

    t, T_1, T_2 = data

    t_list.append(t)
    T_1_list.append(T_1)
    T_2_list.append(T_2)

    xmin, xmax = ax.get_xlim()

    if t >= xmax:
        ax.set_xlim(xmin, 2*xmax)
        ax.figure.canvas.draw()

    line_1.set_data(t_list, T_1_list)
    line_2.set_data(t_list, T_2_list)

    if data_save :
        with open( data_file_name, 'a' ) as data_file:
            data_file.write( str( t ) + ', ' + str( T_1 ) + ', ' +str( T_2 ) + '\n' )

    return line_1, line_2

#######################################

ani = animation.FuncAnimation( fig, update_plot, measure, blit=False, interval = dt, repeat=False, init_func=init )
plt.show()
