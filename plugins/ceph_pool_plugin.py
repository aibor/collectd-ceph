#!/usr/bin/env python
#
# vim: tabstop=4 shiftwidth=4

# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; only version 2 of the License is applicable.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA
#
# Authors:
#   Ricardo Rocha <ricardo@catalyst.net.nz>
#
# About this plugin:
#   This plugin collects information regarding Ceph pools.
#
# collectd:
#   http://collectd.org
# collectd-python:
#   http://collectd.org/documentation/manpages/collectd-python.5.shtml
# ceph pools:
#   http://ceph.com/docs/master/rados/operations/pools/
#

import collectd
import json
import traceback
import subprocess

import base

class CephPoolPlugin(base.Base):

    def __init__(self):
        base.Base.__init__(self)
        self.prefix = 'ceph'

    def get_stats(self):
        """Retrieves stats from ceph pools"""

        data = { self.prefix: { self.cluster: {} } }

        stats_output = None
        try:
            stats_output = subprocess.check_output(['ceph', 'osd', 'pool', 'stats', '-f', 'json'])
            df_output = subprocess.check_output(['ceph', 'df', '-f', 'json'])
        except Exception as exc:
            collectd.error("ceph-pool: failed to ceph pool stats :: %s :: %s"
                    % (exc, traceback.format_exc()))
            return

        if stats_output is None:
            collectd.error('ceph-pool: failed to ceph osd pool stats :: output was None')

        if df_output is None:
            collectd.error('ceph-pool: failed to ceph df :: output was None')

        json_stats_data = json.loads(stats_output)
        json_df_data = json.loads(df_output)

        # push osd pool stats results
        for pool in json_stats_data:
            data[self.prefix][self.cluster][pool['pool_name']] = {}
            pool_data = data[self.prefix][self.cluster][pool['pool_name']]
            for stat in ('read_bytes_sec', 'write_bytes_sec', 'op_per_sec'):
                if pool['client_io_rate'].has_key(stat):
                    pool_data[stat] = pool['client_io_rate'][stat]

        # push df results
        for pool in json_df_data['pools']:
            pool_data = data[self.prefix][self.cluster][pool['name']]
            for stat in ('bytes_used', 'kb_used', 'objects'):
                if pool.has_key(stat):
                  pool_data[stat] = pool['stats'][stat]

        # push totals from df
        data[self.prefix][self.cluster]['cluster'] = {}
        data[self.prefix][self.cluster]['cluster']['total_space'] = int(json_df_data['stats']['total_space']) * 1024.0
        data[self.prefix][self.cluster]['cluster']['total_used'] = int(json_df_data['stats']['total_used']) * 1024.0
        data[self.prefix][self.cluster]['cluster']['total_avail'] = int(json_df_data['stats']['total_avail']) * 1024.0

        return data

try:
    plugin = CephPoolPlugin()
except Exception as exc:
    collectd.error("ceph-pool: failed to initialize ceph pool plugin :: %s :: %s"
            % (exc, traceback.format_exc()))

def configure_callback(conf):
    """Received configuration information"""
    plugin.config_callback(conf)

def read_callback():
    """Callback triggerred by collectd on read"""
    plugin.read_callback()

collectd.register_config(configure_callback)
collectd.register_read(read_callback)

