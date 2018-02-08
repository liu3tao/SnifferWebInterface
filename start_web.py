"""Main entry point of Ellisys controller."""

import os
import sys
import signal
import time
from flask import Flask, abort, render_template, request, jsonify
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
  finished_list = _task_list_to_string(capture_manager.get_finished_tasks())
  running_list = _task_list_to_string(capture_manager.get_running_tasks())
  pending_list = _task_list_to_string(capture_manager.get_pending_tasks())
  running_list.extend(pending_list)
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
  """Stop the capture"""
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
  """Returns JSON of the capture task."""
  task = capture_manager.get_task_by_id(capture_uuid)
  if task is None:
    abort(404)
  return jsonify(task.to_dict())

@app.route('/trace/<capture_uuid>')
def get_trace(capture_uuid):
  """Returns JSON list of the captured traces of the task."""
  task = capture_manager.get_task_by_id(capture_uuid)
  if task is None:
    abort(404)
  return jsonify(task.to_dict()['trace_list'])

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
    task_dict = task.to_dict()
    str_list.append(task_dict)
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
