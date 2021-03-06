# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for removing public keys to users."""
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.compute.lib import base_classes
from googlecloudsdk.compute.lib import gaia_utils
from googlecloudsdk.compute.lib import user_utils
from googlecloudsdk.compute.lib import utils


class RemoveKeys(base_classes.NoOutputAsyncMutator,
                 user_utils.UserResourceFetcher):
  """Remove a public key from a Google Compute Engine user.

  *{command}* removes public keys from a Google Compute Engine user.
  """

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--fingerprints',
        type=arg_parsers.ArgList(min_length=1),
        action=arg_parsers.FloatingListValuesCatcher(),
        metavar='FINGERPRINT',
        help='The fingerprints of the public keys to remove from the user.')

    user_utils.AddUserArgument(parser, '', custom_help=(
        'If provided, the name of the user to remove public keys from. '
        'Else, the default user will be used.'))

  @property
  def service(self):
    return self.computeaccounts.users

  @property
  def method(self):
    return 'RemovePublicKey'

  @property
  def resource_type(self):
    return 'users'

  @property
  def messages(self):
    return self.computeaccounts.MESSAGES_MODULE

  def CreateRequests(self, args):

    name = args.name
    if not name:
      name = gaia_utils.GetDefaultAccountName(self.http)

    user_ref = self.CreateAccountsReference(name, resource_type='users')

    if args.fingerprints:
      fingerprints = args.fingerprints
    else:
      fingerprints = [k.fingerprint for k in
                      self.LookupUser(user_ref.Name()).publicKeys]

    # Generate warning before deleting.
    prompt_list = ['[{0}]'.format(fingerprint) for fingerprint in fingerprints]
    prompt_title = ('The following public keys will be removed from the user ' +
                    user_ref.Name())
    utils.PromptForDeletionHelper(None, prompt_list, prompt_title=prompt_title)

    requests = []
    for fingerprint in fingerprints:
      request = self.messages.ComputeaccountsUsersRemovePublicKeyRequest(
          project=self.project,
          fingerprint=fingerprint,
          user=user_ref.Name())
      requests.append(request)

    return requests


RemoveKeys.detailed_help = {
    'EXAMPLES': """\
        To remove all public keys for a user, run:

          $ {command} example-user

        To remove a specific public key, first describe the user
        (using 'gcloud compute users describe example-user') to determine the
        fingerprints of the public keys you wish
        to remove. Then run:

          $ {command} example-user --fingerprints b3ca856958b524f3f12c3e43f6c9065d
        """,
}
