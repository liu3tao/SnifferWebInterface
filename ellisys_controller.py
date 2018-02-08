import sys
import traceback
import os
import time
import tempfile
import logging
import Ice
from base_sniffer_device import BaseSnifferDevice

Ice.loadSlice("--all -I. BluetoothAnalyzerRemoteControl.ice")

import Ellisys.Platform.NetworkRemoteControl.Analyzer


class RemoteControlException(Exception):
  pass

class EllisysController(BaseSnifferDevice):
  """Controller class for Ellisys BXE400."""
  def __init__(self, host_ip='localhost', host_port=54321):
    super(EllisysController, self).__init__()
    self.host_ip = host_ip
    self.host_port = host_port
    self.proxy_string = "Ellisys.AnalyzerRemoteControl:tcp -h {0} -p {1}".format(
      host_ip, host_port)

    try:
      # Initialize ICE
      initData = Ice.InitializationData()
      initData.properties = Ice.createProperties([], initData.properties)
      initData.properties.setProperty("Ice.Default.EncodingVersion", "1.0")

      communicator = Ice.initialize(initData)
      proxy = communicator.stringToProxy(self.proxy_string)
      remote_control = Ellisys.Platform.NetworkRemoteControl.Analyzer.BluetoothAnalyzerRemoteControlPrx.checkedCast(proxy)
    except Exception as ex:
      traceback.print_exc()
      raise ex

    if not remote_control:
      raise RemoteControlException("Invalid proxy {0}".format(proxyString))
    self.communicator = communicator
    self.remote_control = remote_control
    self._is_closed = False

    # Some default capture config
    self._config['WiFi Capture Enabled'] = False
    self._config['WiFi Capture Channel'] = None
    self._config['Spectrum Capture Enabled'] = False
    self._config['BLE Capture Enabled'] = True
    self._model_string = 'Ellisys BXE400'

  def start_capture(self):
    """Start recording untill stop capture is called."""
    if self._is_closed:
      return False

    if not self.remote_control.IsRecording():
      self.remote_control.StartRecording()
    return True

  def split_capture(self, trace_path):
    """Split the capture and continue reording."""
    if self._is_closed or not self.remote_control.IsRecording():
      return ''
    self.remote_control.SplitTraceFileAndContinueRecording(trace_path)
    print("Trace splited to '{0}'".format(trace_path))
    return trace_path

  def stop_capture(self, trace_path):
    """Stop recording"""
    if self._is_closed or not self.remote_control.IsRecording():
      return ''
    # workaround to allow ftp control the saved file.
    self.remote_control.StopRecordingAndSaveTraceFile(trace_path, True)
    print("Trace saved to '{0}'".format(trace_path))
    return trace_path

  def close(self):
    if self.communicator:
      try:
        print('Destorying Ellisys Controller...')
        if self.remote_control.IsRecording():
          self.remote_control.AbortRecordingAndDiscardTraceFile()
        self.communicator.destroy()
        self._is_closed = True
        print('Done.')
      except:
        traceback.print_exc()

  @property
  def is_capturing(self):
    if (not self._is_closed) and self.remote_control.IsRecording():
      return True
    return False

  @property
  def is_closed(self):
    return self._is_closed