"""Ellisys Bluetooth Explorer BXE400 Controller."""

import traceback
from base_sniffer_device import BaseSnifferDevice
import Ice

Ice.loadSlice('--all -I. BluetoothAnalyzerRemoteControl.ice')

import Ellisys.Platform.NetworkRemoteControl.Analyzer


class RemoteControlException(Exception):
  pass


class EllisysController(BaseSnifferDevice):
  """Controller class for Ellisys BXE400."""

  def __init__(self, host_addr='localhost', host_port=54321):
    """Create connection to the Ellisys Remote Control API.

    Args:
      host_addr: str, the address of Ellisys Remote API host.
      host_port: int, the port of Ellisys Remote API host.
    """
    super(EllisysController, self).__init__()
    self.host_ip = host_addr
    self.host_port = host_port
    self.proxy_string = 'Ellisys.AnalyzerRemoteControl:tcp -h {0} -p {1}'.\
        format(host_addr, host_port)

    try:
      # Initialize ICE
      init_data = Ice.InitializationData()
      init_data.properties = Ice.createProperties([], init_data.properties)
      init_data.properties.setProperty('Ice.Default.EncodingVersion', '1.0')

      communicator = Ice.initialize(init_data)
      proxy = communicator.stringToProxy(self.proxy_string)
      remote_control = Ellisys.Platform.NetworkRemoteControl.Analyzer.\
            BluetoothAnalyzerRemoteControlPrx.checkedCast(proxy)
    except Exception as ex:
      traceback.print_exc()
      raise ex

    if not remote_control:
      raise RemoteControlException('Invalid proxy %s' % self.proxy_string)
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
    """Start recording until stop capture is called."""
    if self._is_closed:
      return False

    if not self.remote_control.IsRecording():
      self.remote_control.StartRecording()
    return True

  def split_capture(self, trace_path):
    """Split the capture and continue recording.

    Args:
      trace_path, str, the path to save the trace.

    returns: str, path of the saved trace. Empty if save failed.
    """
    if self._is_closed or not self.remote_control.IsRecording():
      return ''
    self.remote_control.SplitTraceFileAndContinueRecording(trace_path)
    print('Trace spilt to {0}'.format(trace_path))
    return trace_path

  def stop_capture(self, trace_path):
    """Stop recording and save the capture.
    Args:
      trace_path, str, the path to save the trace.

    returns: str, path of the saved trace. Empty if save failed.
    """
    if self._is_closed or not self.remote_control.IsRecording():
      return ''
    # workaround to allow ftp control the saved file.
    self.remote_control.StopRecordingAndSaveTraceFile(trace_path, True)
    print('Trace saved to {0}'.format(trace_path))
    return trace_path

  def close(self):
    """Close the controller connection."""
    if self.communicator:
      try:
        print('Destroying Ellisys Controller...')
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
