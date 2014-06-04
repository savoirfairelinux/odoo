# -*- encoding: utf-8 -*-
###############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2013 Savoir-faire Linux
#    (<http://www.savoirfairelinux.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

import logging
import platform
import os
import sys
from raven import Client
from bzrlib.branch import Branch
from bzrlib.errors import NotBranchError
from openerp.tools import config

_logger = logging.getLogger(__name__)


class BzrClient(Client):
    """Subclass raven.Client to be able to report Bazaar revno as Module
    versions"""

    def __init__(self, dsn=None, **options):
        self.bzr_revs = {}
        return super(BzrClient, self).__init__(dsn=dsn, **options)

    def set_rev_version(self, path):
        """Given path, get source and revno, careful not to raise any
        exceptions"""
        try:
            branch, rel_path = Branch.open_containing(path)
            branch.lock_read()
            # Clean name
            name = (
                branch.get_parent().replace(u'bazaar.launchpad.net/', u'lp:')
                                   .replace(u'%7E', u'~')
                                   .replace(u'%2Bbranch/', u'')
                                   .replace(u'bzr+ssh://', u''))
            self.bzr_revs[name] = u'r%i' % branch.revno()
            branch.unlock()
        except NotBranchError:
            return
        except:
            if branch.is_locked():
                branch.unlock()
            return

    def captureException(self, params=None, exc_info=None, **kwargs):
        self.extra[u'params'] = params
        return super(BzrClient, self).captureException(
            exc_info=exc_info, **kwargs)

    def build_msg(self, event_type, data=None, date=None,
                  time_spent=None, extra=None, stack=None, public_key=None,
                  tags=None, **kwargs):
        """Add bzr revnos to msg's modules"""
        res = super(BzrClient, self).build_msg(
            event_type, data, date, time_spent, extra, stack, public_key,
            tags, **kwargs)
        res['modules'] = dict(res['modules'].items() + self.bzr_revs.items())
        return res

processors = (
    'raven.processors.SanitizePasswordsProcessor',
    'raven_sanitize_openerp.OpenerpPasswordsProcessor'
)
if config.get(u'sentry_dsn'):
    # Get DSN info from config file or ~/.openerp_serverrc (recommended)
    dsn = config.get('sentry_dsn')
    # Send the following library versions, include all eggs
    include_paths = [
        'openerp',
        'sentry',
        'raven',
        'raven_sanitize_openerp',
    ] + [os.path.basename(i).split('-')[0]
         for i in sys.path if i.endswith('.egg')]
    # Add tags, OS and bzr revisions for Server and Addons
    tags = {
        'OS': (" ".join(platform.linux_distribution()).strip() or
               " ".join(platform.win32_ver()).strip() or
               " ".join((platform.system(), platform.release(),
                         platform.machine()))),
    }
    # Create Client
    client = BzrClient(
        dsn=dsn,
        processors=processors,
        include_paths=include_paths,
        tags=tags
    )
    # Using bzrlib find revision numbers for server and addons
    client.set_rev_version(config.get(u'root_path') + u"/..", )
    # Create and test message for Sentry
    client.captureMessage(u'Sentry Tracking Activated!')
else:
    _logger.warn(u"Sentry DSN not defined in config file")
    client = None


def sentry_intercept_exception(params):
    """Intercept OpenERP exception and raise a different one if raven is well
    connected to Sentry"""
    res = False
    if not client or client.state.did_fail():
        return
    try:
        # Store exc_info in case another exception is raised.
        exc_info = sys.exc_info()
        # Using bzrlib find revision numbers for server and addons
        for path in config.get(u'addons_path').split(u','):
            client.set_rev_version(path)
        client.captureException(params, exc_info=exc_info)
        res = True
    finally:
        return res
