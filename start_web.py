"""Main entry point of Ellisys controller."""

import os
import sys
import signal
import time
from flask import Flask, abort, render_template, request
from base_sniffer_device import BaseSnifferDevice as SnifferDevice
from capture_manager import CaptureManager, CaptureTask
from capture_manager import CaptureTaskException, TaskNotFoundError,\
    TaskStoppedError, DuplicateTaskError
from getpass import getuser


# The one and only Flask object
app = Flask(__name__)
app.config['DEBUG'] = True

# The one and only capture manager object.
capture_manager = None


@app.route('/')
def landing_page():
  """Render a landing page for user's information"""
  # TODO: consider move this GUI page to a dedicated web portal.
  model = capture_manager.get_controller_model()
  # Put together a list of finished tasks.
  task_list = capture_manager.get_finished_tasks()
  finished_list = _task_list_to_string(task_list)
  running_list = _task_list_to_string(capture_manager.get_running_tasks())
  return render_template('index.html', controller_model=model,
                         running_tasks=running_list,
                         finished_tasks=finished_list)

@app.route('/start/<capture_uuid>')
def start_capture(capture_uuid):
  # Get task owner/host from request object.
  task_owner = request.args.get('owner', 'Unknown User')
  task_host = request.headers.get('X-Forwarded-For', request.remote_addr)
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

@app.route('/list')
def get_task_list():
  """Return a json list of capture tasks."""
  abort(404)

@app.route('/count/')
def get_task_count():
  """Return the count of capture tasks."""
  abort(404)

def get_capture_filename_by_timestamp(start_time, stop_time):
  """Generate capture filename based on the specified timestamp."""
  filename = 'cap-%s-%s.btt' % (
    time.strftime('%y%m%d_%H%M%S', time.localtime(start_time)),
    time.strftime('%y%m%d_%H%M%S', time.localtime(stop_time)))
  return filename

def _epoch_time_to_human_readable(timestamp):
  return time.strftime('%x %X', time.localtime(timestamp))

def _task_list_to_string(task_list):
  str_list = []
  for task in task_list:
    str_list.append(
      ( 'Finished' if task.is_stopped() else 'Running',
        task.id,
        task.owner,
        task.host,
        time.strftime('%x %X', time.localtime(task.start_time)),
        time.strftime('%x %X', time.localtime(task.stop_time)),
      ))
  return str_list


def sigint_handler(signal, frame):
  print('Shutting down service.')
  capture_manager.shutdown()

  sys.exit(0)


if __name__ == "__main__":
  signal.signal(signal.SIGINT, sigint_handler)
  sniffer = SnifferDevice()
  capture_manager = CaptureManager(sniffer)
  app.run(host='0.0.0.0', port=5000)
