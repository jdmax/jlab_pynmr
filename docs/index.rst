.. JLab PyNMR documentation master file, created by
   sphinx-quickstart on Thu Jul  2 23:17:56 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to JLab PyNMR's documentation!
======================================

PyNMR is designed to act as the DAQ hub of the different systems required for the JLab Polarized Target NMR system. It is written in Python3 with PyQt5 for GUI. Run PyNMR from the main directory with ``python main.py``. 

The majority of the code is in the 'app' directory and is organized as follows: 'main.py' calls the 'MainWindow' class in 'gui.py', which creates the main application window. In the main window, each task is split into a different tab, each of which is its own QWidget class and contains the code to create and corrodinate the actions of the GUI elements. The :class:`RunTab <app.gui_run_tab.RunTab>` is the main tab containing the running sweeps and current status. The :class:`TuneTab <app.gui_tune_tab.TuneTab>` shows a running average of the diode and phase signals to facilitate tuning. The :class:`BaseTab <app.gui_base_tab.BaseTab>` allows the selection of a baseline sweep, and shows the magnet controls. The 'classes.py' module contains most of the actual workings of the analysis, separated into classes, such as :class:`Config <app.classes.Config>`, :class:`Scan <app.classes.Scan>`, :class:`Event <app.classes.Event>`, :class:`Status <app.classes.Status>`, and :class:`History <app.classes.History>`.

DAQ Communication
=================
The interface with data acquisition is handled with the :class:`DAQConnection <app.daq.DAQConnection>` class. An option in the configuration file allows the selection of the DAQ system to be used. By listing the DAQ type as "Test" in the config file, DAQ communication is bypassed and example NMR signals are used.

When the daq_type is listed as "FPGA," the program communicates with the FPGA to coordinate the ADC, DAC and RF source interface. A write-up on the operation of the FPGA is available at `this link <https://userweb.jlab.org/~jmaxwell/nmr/PyNMR/FPGA_Control_Manual.pdf>`_. The FPGA receives commands over :class:`UDP <app.daq.UDP>`, and sends back data over :class:`TCP <app.daq.TCP>`. When the command to start is given, the FPGA starts readings from the FPGA, iterating through the list of frequency points provided. The FPGA continues the sweeps, summing the frequency channels and returning them in chunks after a certain number have been performed. This software performs an average on the summed channels using the number of sweeps in the chunk. Once all the chunks required to make up the total number of sweeps are received, the event is finished.

When the daq_type is listed as "NIDAQ," a National Instruments DAQ board is used to perform the ADC reads and DAC writes, as was used with the previous LabView PDP software. This still needs testing.

Communication with the Rohde and Schwarz RF signal generator is handled via Telnet through :class:`RS Connection <app.daq.RS_Connection>`, avoiding the need for VISA. Telnet commands are the same as those used for GPIB.


Required modules
================
To run the scripts, a number of python modules are required to be installed. In general, this can be done on a system with pip using ``pip install PyQt5``. 

* PyQt5
* numpy
* scipy
* pyqtgraph
* socket
* serial
* dateutil
* pytz
* json
* yaml
* pyepics

Configuration File
==================

The configuration file is in the `YAML <yaml.org>`_ format. The channel list allows any number of NMR channels to be defined for different target positions, for example. One of the channel settings is 'sweep_file,' which will load a sweep profile (a set of integers from -32768 to 32767 for the 16 bit position of the point) from the given file location, or use a standard triangle wave if the file does not exist. EPICS variables to be fetched and included both in the interface and in the event data file are listed under "epics_reads," and attributes of the :class:`Event <app.classes.Event>` class can be sent to EPICS by listing them under "epics_writes." Log files are rotated at midnight and live in the directory specified in the config file.

.. literalinclude:: ../pynmr_config.yaml
   :language: yaml



.. toctree::
   :maxdepth: 2
   :caption: Contents:


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
