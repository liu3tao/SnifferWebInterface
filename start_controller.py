"""Main entry point of Ellisys controller."""

import os
import sys
import signal
import time
from flask import Flask, abort
from base_sniffer_device import BaseSnifferDevice as SnifferDevice
frim
try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty  # python 3.x

# The one and only Flask object
app = Flask(__name__)

# sniffer controller.
g_controller = None

# Capture manager object.
g_capture_manager = None


@app.route('/')
def landing_page():
  return 'Sniffer Controller Interface'

@app.route('/start/<test_uuid>')
def start_capture(test_uuid):
  if g_controller.start_capture():
    g_capture_dict[test_uuid] = time.time()
    return test_uuid
  else:
    return 'Failed to start capture'

@app.route('/stop/<test_uuid>')
def stop_capture(test_uuid):
  if test_uuid not in g_capture_dict:
    abort(404)
  capture_name = get_capture_filename_by_timestamp(
      g_capture_dict[test_uuid], time.time())
  cap_path = os.path.join(DEFAULT_CAP_DIR, capture_name)
  if g_controller.stop_capture(cap_path):
    download_url = DEFAULT_FTP_LINK + capture_name
    return download_url
  else:
    return 'Failed to stop capture'

def get_capture_filename_by_timestamp(start_time, stop_time):
  """Generate capture filename based on the specified timestamp."""
  filename = 'cap-%s-%s.btt' % (
    time.strftime('%y%m%d_%H%M%S', time.localtime(start_time)),
    time.strftime('%y%m%d_%H%M%S', time.localtime(stop_time)))
  return filename

def sigint_handler(signal, frame):
  print('Shutting down service.')
  g_controller.close()
  sys.exit(0)


if __name__ == "__main__":
  signal.signal(signal.SIGINT, sigint_handler)
  g_controller = SnifferDevice()
  # g_manager = CaptureManager(g_controller)
  app.run(host='0.0.0.0', port=5000)
