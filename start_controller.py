"""Main entry point of Ellisys controller."""

import uuid
import os
import sys
import signal
import time
import json
from threading import Thread
from flask import Flask, render_template, abort, request
from controller_util import EllisysController
try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty  # python 3.x

app = Flask(__name__)
# Global ellisys controller.
g_controller = None
g_capture_dict = {}

# Some default values
DEFAULT_CAP_DIR = r'C:\Users\tao\bxe400_traces'
DEFAULT_SPLIT_INTERVAL = 120  # split trace every 2 minutes.
DEFAULT_FTP_LINK = r'ftp://100.96.38.40/'

@app.route('/')
def landing_page():
  return 'Ellisys BXE400 Controller Interface'

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

class CaptureTask(object):
  """Data class for capture tasks"""
  def __init__(self, uuid_str):
    self.uuid = uuid_str
    self._self._previous_start_time = None
    self._stop_time = None
    self._capture_list = []

  def add_capture(self, cpature_name):
    self._capture_list.append(capture_name)

  def start(self):
    """Mark the start of the task"""
    self._self._previous_start_time = time.time()

  def stop(self):
    self._stop_time = time.time()

  @property
  def start_time(self):
    return self._self._previous_start_time

  @property
  def stop_time(self):
    return self._stop_time

  @property
  def capture_list(self):
    return self._capture_list


class CaptureManager(object):
  def __init__(self, controller,
               capture_dir=DEFAULT_CAP_DIR,
               split_interval=DEFAULT_SPLIT_INTERVAL):
    """Maitain the capture thread.

      Args:
        controller: the Ellisys controller.
        capture_dir: str, the capture directory
        split_interval: float, the time interval before each 
    """
    self._controller = controller
    self._is_capturing = False
    self._shutdown = False
    self._capture_dir = capture_dir
    self._split_interval = split_interval
    self._running_tasks = Queue()  # Queues of capture tasks.
    self._finished_tasks = Queue()
    self._capture_thread = Thread(target=self._thread_func)
    self._capture_thread.daemon = True # thread dies with the program
    self._capture_thread.start()
    self._previous_start_time = 0

  def _thread_func(self):
    """Thread function for capture management."""
    print('Capture thread started.')
    while not self._shutdown:
      curr_time = time.time()
      if self._has_pending_tasks():
        # Start capture if necessary.
        if not self._is_capturing:
          if self.controller.start_capture():
            self._is_capturing = True
            self._previous_start_time = curr_time
          else:
            print('Capture thread: failed to start Ellisys recording.')
        # split trace based on interval
        if self._should_split():
          cap_path = self.get_capture_filename_by_timestamp(
              self._previous_start_time, curr_time)
          self._controller.split_capture(cap_path)
          self._previous_start_time = curr_time
          # and add the new capture to all running tasks
          for task in self._running_tasks.queue:
            task.add_capture(cap_path)
      else:
        # No running task, so stop Ellisys recording. Thread is still running.
        if self._is_capturing:
          cap_path = self.get_capture_filename_by_timestamp(
              self._previous_start_time, curr_time)
          if not self._controller.stop_capture(cap_path):
            print('Capture thread: failed to stop Ellisys recording.')
          self._previous_start_time = 0
          self._is_capturing = False
          # TODO: add the last capture to previous tasks.
      time.sleep(0.5)  # check every 0.5 seconds.

    # Capture thread will shutdown. Stop capture and close the controller.
    cap_path = self.get_capture_filename_by_timestamp(
      self._previous_self._previous_start_time, curr_time)
    self._controller.stop_capture(cap_path)
    self._controller.close()
    self._is_capturing = False
    print('Capture thread shutdown.')

  def _should_split(self):
    """Determine if we should split the file."""
    if self._split_interval > 0 and self._previous_self._previous_start_time > 0:
      if time.time() - self._previous_self._previous_start_time >= self._split_interval:
        return True
    return False

  def _has_pending_tasks(self):
    return not self._running_tasks.empty()

  def _update_pending_tasks(self, capture_name):
    pass

  def add_task(self, task):
    self._running_tasks.put(task)
    task.start()

  def get_finished_tasks(self):
    return (t for t in self._finished_tasks.queue)

  def get_task(self, task_uuid):
    pass

if __name__ == "__main__":
  signal.signal(signal.SIGINT, sigint_handler)
  g_controller = EllisysController()
  # g_manager = CaptureManager(g_controller)
  app.run(host='0.0.0.0', port=5000)
