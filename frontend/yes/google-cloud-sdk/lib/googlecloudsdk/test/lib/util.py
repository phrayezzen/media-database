# Copyright 2014 Google Inc. All Rights Reserved.

"""A shared library to support implementation of Cloud Test Lab commands."""

import json

from googlecloudapis.apitools.base import py as apitools_base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import properties


def GetError(error):
  """Returns a ready-to-print string representation from the http response.

  Args:
    error: the Http error response, whose content is a JSON-format string for
      most cases (e.g. invalid test dimension), but can be just a string other
      times (e.g. invalid URI for CLOUDSDK_TEST_ENDPOINT).

  Returns:
    A ready-to-print string representation of the error.
  """
  try:
    data = json.loads(error.content)
  except ValueError:  # message is not JSON
    return error.content

  code = data['error']['code']
  message = data['error']['message']
  return 'ResponseError {0}: {1}'.format(code, message)


def GetProject():
  """Get the user's project id from the core project properties.

  Returns:
    The id of the GCE project to use while running the test.

  Raises:
    ToolException if the user did not specify a project id via the
      --project flag or via running "gcloud config set project PROJECT_ID".
  """
  project = properties.VALUES.core.project.Get()
  if not project:
    raise exceptions.ToolException(
        'No project specified. Please add --project PROJECT_ID to the command'
        ' line or first run\n  $ gcloud config set project PROJECT_ID')
  return project


def GetAndroidCatalog(context):
  """Gets the Android catalog from the TestEnvironmentDiscoveryService.

  Args:
    context: {str:object}, The current context, which is a set of key-value
      pairs that can be used for common initialization among commands.

  Returns:
    The android catalog.

  Raises:
    exceptions.HttpException: If it could not connect to the service.
  """
  client = context['testing_client']
  messages = context['testing_messages']

  request = messages.TestingTestEnvironmentCatalogGetRequest()
  request.environmentType = request.EnvironmentTypeValueValuesEnum.ANDROID
  try:
    response = client.testEnvironmentCatalog.Get(request)
    return response.androidDeviceCatalog
  except apitools_base.HttpError as error:
    raise exceptions.HttpException(GetError(error))
