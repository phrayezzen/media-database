# Copyright 2015 Google Inc. All Rights Reserved.

"""Wrapper to manipulate GCP git repository."""

import errno
import os
import re
import subprocess
import textwrap
import uritemplate

from googlecloudsdk.core import log
from googlecloudsdk.core.util import compat26
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import platforms

# This regular expression is used to extract the URL of the 'origin' remote by
# scraping 'git remote show origin'.
_ORIGIN_URL_RE = re.compile(r'remote origin\n.*Fetch URL: (?P<url>.+)\n', re.M)
# This is the minimum version of git required to use credential helpers.
_HELPER_MIN = (1, 7, 9)


class Error(Exception):
  """Exceptions for this module."""


class UnknownRepositoryAliasException(Error):
  """Exception to be thrown when a repository alias provided cannot be found."""


class CannotInitRepositoryException(Error):
  """Exception to be thrown when a repository cannot be created."""


class CannotFetchRepositoryException(Error):
  """Exception to be thrown when a repository cannot be fetched."""


class GitVersionException(Error):
  """Exceptions for when git version is too old."""

  def __init__(self, fmtstr, cur_version, min_version):
    super(GitVersionException, self).__init__(
        fmtstr.format(cur_version=cur_version, min_version=min_version))


class InvalidGitException(Error):
  """Exceptions for when git version is empty or invalid."""

  def __init__(self, message):
    super(InvalidGitException, self).__init__(message)


def CheckGitVersion(version_lower_bound):
  """Returns true when version of git is >= min_version.

  Args:
    version_lower_bound: (int,int,int), The lowest allowed version.

  Returns:
    True if version >= min_version.
  """
  try:
    output = compat26.subprocess.check_output(['git', 'version'])
    if not output:
      raise InvalidGitException('The git version string is empty.')
    if not output.startswith('git version '):
      raise InvalidGitException(('The git version string must start with '
                                 'git version .'))
    match = re.search(r'(\d+)\.(\d+)\.(\d+)', output)
    if not match:
      raise InvalidGitException('The git version string must contain a '
                                'version number.')
    cur_version = match.group(1, 2, 3)
    current_version = tuple([int(item) for item in cur_version])
    if current_version < version_lower_bound:
      min_version = '.'.join(str(i) for i in version_lower_bound)
      raise GitVersionException(
          ('Your git version {cur_version} is older than the minimum version '
           '{min_version}. Please install a newer version of git.'),
          output, min_version)
  except OSError as e:
    if e.errno == errno.ENOENT:
      raise NoGitException()
    raise
  return True


class NoGitException(Error):
  """Exceptions for when git is not available."""

  def __init__(self):
    super(NoGitException, self).__init__(
        textwrap.dedent("""\
        Cannot find git. Please install git and try again.

        You can find git installers at [http://git-scm.com/downloads], or use
        your favorite package manager to install it on your computer.
        """))


def _GetRepositoryURI(project, alias):
  """Get the URI for a repository, given its project and alias.

  Args:
    project: str, The project name.
    alias: str, The repository alias.

  Returns:
    str, The repository URI.
  """
  return uritemplate.expand(
      'https://source.developers.google.com/p/{project}/r/{alias}',
      {'project': project, 'alias': alias})


class Git(object):
  """Represents project git repo."""

  def __init__(self, project_id, repo_name, uri=None):
    """Clone a repository associated with a Google Cloud Project.

    Looks up the URL of the indicated repository, and clones it to alias.

    Args:
      project_id: str, The name of the project that has a repository associated
          with it.
      repo_name: str, The name of the repository to clone.
      uri: str, The URI of the repository to clone, or None if it will be
          inferred from the name.

    Raises:
      UnknownRepositoryAliasException: If the repo name is not known to be
          associated with the project.
    """
    self._project_id = project_id
    self._repo_name = repo_name
    self._uri = uri or _GetRepositoryURI(project_id, repo_name)
    if not self._uri:
      raise UnknownRepositoryAliasException()

  def GetName(self):
    return self._repo_name

  def Clone(self, destination_path):
    """Clone a git repository into a gcloud workspace.

    If the resulting clone does not have a .gcloud directory, create one. Also,
    sets the credential.helper to use the gcloud credential helper.

    Args:
      destination_path: str, The relative path for the repository clone.

    Returns:
      str, The absolute path of cloned repository.

    Raises:
      CannotInitRepositoryException: If there is already a file or directory in
          the way of creating this repository.
      CannotFetchRepositoryException: If there is a problem fetching the
          repository from the remote host, or if the repository is otherwise
          misconfigured.
    """
    abs_repository_path = os.path.abspath(destination_path)
    if os.path.exists(abs_repository_path):
      # First check if it's already the repository we're looking for.
      with files.ChDir(abs_repository_path) as _:
        try:
          output = compat26.subprocess.check_output(
              ['git', 'remote', 'show', 'origin'])
        except subprocess.CalledProcessError:
          raise CannotFetchRepositoryException(
              'Repository in [{path}] is misconfigured.'.format(
                  path=abs_repository_path))
        output_match = _ORIGIN_URL_RE.search(output)
        if not output_match or output_match.group('url') != self._uri:
          raise CannotInitRepositoryException(
              ('Repository [{url}] cannot be cloned to [{path}]: there'
               ' is something already there.').format(
                   url=self._uri, path=abs_repository_path))
        else:
          # Repository exists and is correctly configured: abort.
          log.err.Print(
              ('Repository in [{path}] already exists and maps to [{uri}].'
               .format(path=abs_repository_path, uri=self._uri)))
          return None

    # Nothing is there, make a brand new repository.
    try:
      if (self._uri.startswith('https://code.google.com') or
          self._uri.startswith('https://source.developers.google.com')):

        # If this is a Google-hosted repo, clone with the cred helper.
        try:
          CheckGitVersion(_HELPER_MIN)
        except GitVersionException:
          log.warn(textwrap.dedent("""\
              You are cloning a Google-hosted repository with a version of git
              older than 1.7.9. If you upgrade to 1.7.9 or later, gcloud can
              handle authentication to this repository. Otherwise, to
              authenticate, use your Google account and the password found by
              running the following command.
               $ gcloud auth print-refresh-token
              """))
          cmd = ['git', 'clone', self._uri, abs_repository_path]
          log.debug('Executing %s', cmd)
          subprocess.check_call(cmd)
        else:
          if (platforms.OperatingSystem.Current() ==
              platforms.OperatingSystem.WINDOWS):
            helper_name = 'gcloud.cmd'
          else:
            helper_name = 'gcloud.sh'
          cmd = ['git', 'clone', self._uri, abs_repository_path,
                 '--config', 'credential.helper=%s' % helper_name]
          log.debug('Executing %s', cmd)
          subprocess.check_call(cmd)
      else:
        # Otherwise, just do a simple clone. We do this clone, without the
        # credential helper, because a user may have already set a default
        # credential helper that would know the repo's auth info.
        subprocess.check_call(
            ['git', 'clone', self._uri, abs_repository_path])
    except subprocess.CalledProcessError as e:
      raise CannotFetchRepositoryException(e)
    return abs_repository_path
