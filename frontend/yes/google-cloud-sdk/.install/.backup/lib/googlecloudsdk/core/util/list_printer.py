# Copyright 2014 Google Inc. All Rights Reserved.

"""List printer for Cloud Platform resources."""

from googlecloudsdk.core.util import attrpath
from googlecloudsdk.core.util import console_io


def PrintResourceList(collection, items):
  """Print a list of cloud resources.

  Args:
    collection: str, The name of the collection to which the items belong.
    items: iterable, A list or otherwise iterable object that generates the
        rows of the list.
  """
  console_io.PrintExtendedList(items, COLLECTION_COLUMNS[collection])


def _Select(path, transform=None):
  """Get a column fetcher for the given attr path and transform.

  Args:
    path: str, The attr path that keys into the resource.
    transform: func(str)->str, A func that takes something found by the path
        and maps it to some other strip.

  Returns:
    func(obj)->str, A func that takes an object and returns the value
    for a particular column.
  """

  getter = attrpath.Selector(path)

  if transform is None:
    return getter

  def GetAndTransform(obj):
    return transform(getter(obj))
  return GetAndTransform


def _NameOnly(value):
  """Get only the last token from a longer path, usually the name.

  Intended to be a selector transform for URLs.

  Args:
    value: str, The value whose last token will be returned.

  Returns:
    str, The name from value.
  """
  if value:
    return value.split('/')[-1]
  return value


def _CommaList(default=None):
  def Transform(items):
    if not items:
      return default
    return ', '.join(items)
  return Transform


def _DiskSize(value):
  """Returns a human readable string representation of the disk size.

  Args:
    value: str, Disk size represented as number of bytes.

  Returns:
    A human readable string representation of the disk size.
  """
  size = float(value)
  the_unit = 'TB'
  for unit in ['bytes', 'KB', 'MB', 'GB']:
    if size < 1024.0:
      the_unit = unit
      break
    size = float(size) / 1024.0
  if size == int(size):
    return '%d %s' % (size, the_unit)
  else:
    return '%3.1f %s' % (size, the_unit)


def _ScreenResolution(model):
  """Build a human readable string representation of a screen resolution.

  Args:
    model: a Test_v1.AndroidModel message (from ApiTools)

  Returns:
    Returns a human readable string representation of a screen resolution.
  """
  return '{y} x {x}'.format(y=model.screenY, x=model.screenX)


# Guidelines for choosing your resource columns:
# - Column headers are ANGRY_SNAKE_CASE, just like user input in usage. This
#   casing has a side effect in that column headers will never be confused for
#   fields in the API responses, which are camelCase.
# - Fields that are URL parameters (that is, they disambiguate your
#   resource) go first, starting at the end of the URL. So, often the first
#   column will be NAME. PROJECT is an exception: no PROJECT column unless the
#   resource being listed can be in a different project than the one found in
#   the project property.
# - If your resource has a STATUS column or something similar, put it last.
# - Aim for an 80-char-wide table, but if someone has a 70-char NAME it's not
#   your fault.


def _Default(default):
  def Transform(item):
    return default if item is None else item
  return Transform


def _SelectTime(path):
  return _Select(path, transform=lambda x: x and x.isoformat())


def _FormatOperationErrors(errs):
  if not errs:
    return None
  else:
    return '\n'.join(['[%s: %s]' % (e.code, e.message) for e in errs])


def _FormatResourceErrors(errs):
  if not errs:
    return None
  else:
    return '\n'.join(['[%s]' % e for e in errs])


COLLECTION_COLUMNS = {
    # APPENGINE
    'app.module_versions': (
        ('MODULE', _Select('module')),
        ('VERSION', _Select('version')),
        ('IS_DEFAULT', _Select('is_default',
                               transform=lambda x: '*' if x else '-')),
    ),

    # AUTOSCALER
    'autoscaler.instances': (
        ('NAME', _Select('name')),
        ('DESCRIPTION', _Select('description')),
        ('STATE', _Select('state')),
        ('STATE_DETAILS', _Select('state_details')),
    ),

    # BIGQUERY
    'bigquery.datasets': (
        ('DATASET_ID', _Select('datasetReference.datasetId')),
    ),
    'bigquery.jobs.describe': (
        ('JOB_TYPE', _Select('job_type')),
        ('STATE', _Select('state')),
        ('START_TIME', _Select('start_time')),
        ('DURATION', _Select('duration')),
        ('BYTES_PROCESSED', _Select('bytes_processed')),
    ),
    'bigquery.jobs.list': (
        ('JOB_ID', _Select('job_id')),
        ('JOB_TYPE', _Select('job_type')),
        ('STATE', _Select('state')),
        ('START_TIME', _Select('start_time')),
        ('DURATION', _Select('duration')),
    ),
    'bigquery.jobs.wait': (
        ('JOB_TYPE', _Select('job_type')),
        ('STATE', _Select('state')),
        ('START_TIME', _Select('start_time')),
        ('DURATION', _Select('duration')),
        ('BYTES_PROCESSED', _Select('bytes_processed')),
    ),
    'bigquery.projects': (
        ('PROJECT_ID', _Select('projectReference.projectId')),
        ('FRIENDLY_NAME', _Select('friendlyName')),
    ),
    'bigquery.tables.list': (
        ('ID', _Select('id')),
        ('TABLE_OR_VIEW', _Select('type')),
    ),

    # COMPUTE
    'compute.instances': (
        ('NAME', _Select('name')),
        ('ZONE', _Select('zone', _NameOnly)),
        ('MACHINE_TYPE', _Select('machineType', _NameOnly)),
        ('INTERNAL_IP', _Select('networkInterfaces[0].networkIP')),
        ('EXTERNAL_IP', _Select('networkInterfaces[0].accessConfigs[0].natIP')),
        ('STATUS', _Select('status')),
    ),

    # CONTAINER V1BETA1
    # TODO(user): remove this once v1 is fully rolled out
    'containerv1beta1.projects.zones.clusters': (
        ('NAME', _Select('name')),
        ('ZONE', _Select('zone')),
        ('CLUSTER_API_VERSION', _Select('clusterApiVersion')),
        ('MASTER_IP', _Select('endpoint')),
        ('MACHINE_TYPE', _Select(
            'nodeConfig', transform=
            lambda x: '%s, %s' % (x.machineType, _NameOnly(x.sourceImage)))),
        ('NODES', _Select('numNodes')),
        ('STATUS', _Select('status')),
    ),
    'containerv1beta1.projects.zones.operations': (
        ('NAME', _Select('name')),
        ('TYPE', _Select('operationType')),
        ('ZONE', _Select('zone')),
        ('TARGET', _Select('target')),
        ('ERROR_MESSAGE', _Select('errorMessage')),
        ('STATUS', _Select('status')),
    ),
    # CONTAINER
    'container.projects.zones.clusters': (
        ('NAME', _Select('name')),
        ('ZONE', _Select('zone')),
        ('MASTER_VERSION', _Select('currentMasterVersion')),
        ('MASTER_IP', _Select('endpoint')),
        ('MACHINE_TYPE', _Select(
            'nodeConfig', transform=lambda x: '%s' % (x.machineType))),
        ('STATUS', _Select('status')),
    ),

    'container.projects.zones.operations': (
        ('NAME', _Select('name')),
        ('TYPE', _Select('operationType')),
        ('ZONE', _Select('zone')),
        ('TARGET', _Select('targetLink', _NameOnly)),
        ('STATUS_MESSAGE', _Select('statusMessage')),
        ('STATUS', _Select('status')),
    ),

    # DATAFLOW
    'dataflow.jobs': (
        ('ID', _Select('job_id')),
        ('NAME', _Select('job_name')),
        ('TYPE', _Select('job_type')),
        ('CREATION_TIME', _Select('creation_time')),
        ('STATUS', _Select('status')),
    ),

    # DNS
    'dns.changes': (
        ('ID', _Select('id')),
        ('START_TIME', _Select('startTime')),
        ('STATUS', _Select('status')),
    ),
    'dns.managedZones': (
        ('NAME', _Select('name')),
        ('DNS_NAME', _Select('dnsName')),
        ('DESCRIPTION', _Select('description')),
    ),
    'dns.resourceRecordSets': (
        ('NAME', _Select('name')),
        ('TYPE', _Select('type')),
        ('TTL', _Select('ttl')),
        ('DATA', _Select('rrdatas', _CommaList(''))),
    ),

    # TODO(user): Remove this section when dm-v2 is removed from preview.
    # DEPLOYMENTMANAGER V2BETA1
    'deploymentmanager.deployments': (
        ('NAME', _Select('name')),
        ('ID', _Select('id')),
        ('DESCRIPTION', _Select('description')),
        ('MANIFEST', _Select('manifest')),
    ),
    'deploymentmanager.operations': (
        ('NAME', _Select('name')),
        ('TYPE', _Select('operationType')),
        ('STATUS', _Select('status')),
        ('TARGET_LINK', _Select('targetLink')),
        ('ERRORS', _Select('error.errors')),
    ),
    'deploymentmanager.resources': (
        ('NAME', _Select('name')),
        ('TYPE', _Select('type')),
        ('ID', _Select('id')),
        ('STATE', _Select('state')),
        ('ERRORS', _Select('errors')),
    ),

    # DEPLOYMENTMANAGER V2BETA2
    'deploymentmanagerv2beta2.deployments': (
        ('NAME', _Select('name')),
        ('STATE', _Select('state')),
        ('INTENT', _Select('intent')),
        ('ID', _Select('id')),
        ('DESCRIPTION', _Select('description')),
        ('MANIFEST', _Select('manifest', transform=
                             lambda x: x.split('/')[-1] if x else None)),
        ('ERRORS', _Select('update.errors', transform=_FormatResourceErrors)),
    ),
    'deploymentmanagerv2beta2.operations': (
        ('NAME', _Select('name')),
        ('TYPE', _Select('operationType')),
        ('STATUS', _Select('status')),
        ('TARGET', _Select('targetLink', transform=
                           lambda x: x.split('/')[-1] if x else None)),
        ('ERRORS', _Select('error.errors', transform=_FormatOperationErrors)),
    ),
    'deploymentmanagerv2beta2.resources': (
        ('NAME', _Select('name')),
        ('TYPE', _Select('type')),
        ('ID', _Select('id')),
        ('UPDATE_STATE', _Select('update.state', transform=
                                 lambda x: 'COMPLETED' if x is None else x)),
        ('ERRORS', _Select('update.errors', transform=_FormatResourceErrors)),
    ),

    # GENOMICS
    'genomics.datasets': (
        ('ID', _Select('id')),
        ('NAME', _Select('name')),
    ),

    # SQL
    'sql.backupRuns': (
        ('DUE_TIME', _SelectTime('dueTime')),
        ('ERROR', _Select('error.code')),
        ('STATUS', _Select('status')),
    ),
    'sql.flags': (
        ('NAME', _Select('name')),
        ('TYPE', _Select('type')),
        ('ALLOWED_VALUES', _Select('allowedStringValues', _CommaList(''))),
    ),
    'sql.instances': (
        ('NAME', _Select('instance')),
        ('REGION', _Select('region')),
        ('TIER', _Select('settings.tier')),
        ('ADDRESS', _Select('ipAddresses[0].ipAddress')),
        ('STATUS', _Select('state')),
    ),
    'sql.operations': (
        ('OPERATION', _Select('operation')),
        ('TYPE', _Select('operationType')),
        ('START', _SelectTime('startTime')),
        ('END', _SelectTime('endTime')),
        ('ERROR', _Select('error[0].code')),
        ('STATUS', _Select('state')),
    ),
    'sql.sslCerts': (
        ('NAME', _Select('commonName')),
        ('SHA1_FINGERPRINT', _Select('sha1Fingerprint')),
        ('EXPIRATION', _Select('expirationTime')),
    ),
    'sql.tiers': (
        ('TIER', _Select('tier')),
        ('AVAILABLE_REGIONS', _Select('region', _CommaList(''))),
        ('RAM', _Select('RAM', _DiskSize)),
        ('DISK', _Select('DiskQuota', _DiskSize)),
    ),

    # projects
    'cloudresourcemanager.projects': (
        ('PROJECT_ID', _Select('projectId')),
        ('NAME', _Select('name')),
        ('PROJECT_NUMBER', _Select('projectNumber')),
    ),

    # source
    'source.jobs.list': (
        ('REPO_NAME', _Select('name', _Default('default'))),
        ('PROJECT_ID ', _Select('projectId')),
        ('VCS', _Select('vcs')),
        ('STATE', _Select('state')),
        ('CREATE_TIME', _Select('createTime')),
    ),

    # Cloud Updater
    'replicapoolupdater.rollingUpdates': (
        ('ID', _Select('id')),
        ('GROUP_NAME', _Select('instanceGroupManager', _NameOnly)),
        ('TEMPLATE_NAME', _Select('instanceTemplate', _NameOnly)),
        ('STATUS', _Select('status')),
        ('STATUS_MESSAGE', _Select('statusMessage')),
    ),
    'replicapoolupdater.rollingUpdates.instanceUpdates': (
        ('INSTANCE_NAME', _Select('instance', _NameOnly)),
        ('STATUS', _Select('status')),
    ),

    # TEST
    'test.android.devices': (
        ('DEVICE_ID', _Select('id')),
        ('MAKE', _Select('manufacturer')),
        ('MODEL', _Select('name')),
        ('FORM', _Select('form')),
        ('SCREEN_RES', _ScreenResolution),
        ('OS_VERSION_IDS', _Select('supportedVersionIds', _CommaList('none'))),
        ('TAGS', _Select('tags', _CommaList('')))
    ),
    'test.run.outcomes': (
        ('OUTCOME', _Select('outcome')),
        ('STEP', _Select('step_name')),
        ('TEST_AXIS_VALUE', _Select('axis_value')),
    ),

    # Cloud Logging
    'logging.logs': (
        ('NAME', _Select('name')),
    ),
    'logging.sinks': (
        ('NAME', _Select('name')),
        ('DESTINATION', _Select('destination')),
    ),
    'logging.typedSinks': (
        ('NAME', _Select('name')),
        ('DESTINATION', _Select('destination')),
        ('TYPE', _Select('type')),
    ),
    'logging.metrics': (
        ('NAME', _Select('name')),
        ('DESCRIPTION', _Select('description')),
        ('FILTER', _Select('filter')),
    ),

    # Service Management (Inception)
    'servicemanagement-v1.services': (
        ('NAME', _Select('serviceName')),
        ('TITLE', _Select('serviceConfig.title')),
    ),
}
