"""Main entry point of Ellisys controller."""

import os
import sys
import signal
import time
from flask import Flask, abort, render_template
from base_sniffer_device import BaseSnifferDevice as SnifferDevice
from capture_manager import CaptureManager, CaptureTask
from capture_manager import CaptureTaskException, TaskNotFoundError,\
    TaskStoppedError, DuplicateTaskError
from getpass import getuser


# The one and only Flask object
app = Flask(__name__)

# The one and only capture manager object.
capture_manager = None


@app.route('/')
def landing_page():
  model = capture_manager.get_controller_model()
  # Put together a list of finished tasks.
  task_list = capture_manager.get_finished_tasks()
  print(task_list)
  for t in task_list:
    print(t.id, t.owner, t.host)
  return render_template('index.html', controller_model=model,
                         running_tasks=[],
                         finished_tasks=task_list)

@app.route('/start/<capture_uuid>')
def start_capture(capture_uuid):
  # TODO: get user/host from request object.
  task_owner = getuser()
  task_host = 'localhost'
  try:
    capture_manager.start_new_task(capture_uuid, task_owner, task_host)
  except DuplicateTaskError:
    abort(409)  # Conflict
  return capture_uuid

@app.route('/stop/<capture_uuid>')
def stop_capture(capture_uuid):
  try:
    capture_manager.stop_task(capture_uuid)
  except TaskNotFoundError:
    abort(404)
  except TaskStoppedError:
    abort(409)
  except CaptureTaskException:
    abort(500)
  return capture_uuid

@app.route('/status/<capture_uuid>')
def get_status(capture_uuid):
  abort(404)

def get_capture_filename_by_timestamp(start_time, stop_time):
  """Generate capture filename based on the specified timestamp."""
  filename = 'cap-%s-%s.btt' % (
    time.strftime('%y%m%d_%H%M%S', time.localtime(start_time)),
    time.strftime('%y%m%d_%H%M%S', time.localtime(stop_time)))
  return filename

def _epoch_time_to_human_readable(timestamp):
  return time.strftime('%x %X', time.localtime(timestamp))

def sigint_handler(signal, frame):
  print('Shutting down service.')
  capture_manager.shutdown()

  sys.exit(0)


if __name__ == "__main__":
  signal.signal(signal.SIGINT, sigint_handler)
  sniffer = SnifferDevice()
  capture_manager = CaptureManager(sniffer)
  app.run(host='0.0.0.0', port=5000)
