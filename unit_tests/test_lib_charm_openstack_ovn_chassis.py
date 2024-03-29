# Copyright 2019 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import io
import mock
import os

import charms_openstack.test_utils as test_utils

import charm.openstack.ovn_chassis as ovn_chassis


class TestOVNConfigProperties(test_utils.PatchHelper):

    def test_ovn_key(self):
        self.assertEquals(ovn_chassis.ovn_key(None),
                          os.path.join(ovn_chassis.OVS_ETCDIR, 'key_host'))

    def test_ovn_cert(self):
        self.assertEquals(ovn_chassis.ovn_cert(None),
                          os.path.join(ovn_chassis.OVS_ETCDIR, 'cert_host'))

    def test_ovn_ca_cert(self):
        cls = mock.MagicMock()
        cls.charm_instance.name = mock.PropertyMock().return_value = 'name'
        self.assertEquals(ovn_chassis.ovn_ca_cert(cls),
                          os.path.join(ovn_chassis.OVS_ETCDIR, 'name.crt'))


class Helper(test_utils.PatchHelper):

    def setUp(self):
        super().setUp()
        self.patch_release(ovn_chassis.OVNChassisCharm.release)
        self.target = ovn_chassis.OVNChassisCharm()

    def patch_target(self, attr, return_value=None):
        mocked = mock.patch.object(self.target, attr)
        self._patches[attr] = mocked
        started = mocked.start()
        started.return_value = return_value
        self._patches_start[attr] = started
        setattr(self, attr, started)


class TestOVNChassisCharm(Helper):

    def test_disable_metadata(self):
        self.patch_object(ovn_chassis.ch_core.unitdata, 'kv')
        db = mock.MagicMock()
        self.kv.return_value = db
        self.target.disable_metadata()
        db.unset.assert_called_once_with(self.target.metadata_kv_key)

    def test_enable_metadata(self):
        self.patch_object(ovn_chassis.ch_core.unitdata, 'kv')
        db = mock.MagicMock()
        self.kv.return_value = db
        self.target.enable_metadata()
        db.set.assert_called_once_with(self.target.metadata_kv_key, True)

    def test_run(self):
        self.patch_object(ovn_chassis.subprocess, 'run')
        self.patch_object(ovn_chassis.ch_core.hookenv, 'log')
        self.target.run('some', 'args')
        self.run.assert_called_once_with(
            ('some', 'args'),
            stdout=ovn_chassis.subprocess.PIPE,
            stderr=ovn_chassis.subprocess.STDOUT,
            check=True,
            universal_newlines=True)

    def test_configure_tls(self):
        self.patch_target('get_certs_and_keys')
        self.get_certs_and_keys.return_value = [{
            'cert': 'fakecert',
            'key': 'fakekey',
            'cn': 'fakecn',
            'ca': 'fakeca',
            'chain': 'fakechain',
        }]
        with mock.patch('builtins.open', create=True) as mocked_open:
            mocked_file = mock.MagicMock(spec=io.FileIO)
            mocked_open.return_value = mocked_file
            self.target.configure_cert = mock.MagicMock()
            self.target.run = mock.MagicMock()
            self.target.configure_tls()
            mocked_open.assert_called_once_with(
                '/etc/openvswitch/ovn-chassis.crt', 'w')
            mocked_file.__enter__().write.assert_called_once_with(
                'fakeca\nfakechain')
            self.target.configure_cert.assert_called_once_with(
                ovn_chassis.OVS_ETCDIR,
                'fakecert',
                'fakekey',
                cn='host')

    def test_configure_ovs(self):
        self.patch_target('run')
        self.patch_target('restart_all')
        self.patch_object(ovn_chassis, 'ovn_key')
        self.patch_object(ovn_chassis, 'ovn_cert')
        self.patch_object(ovn_chassis, 'ovn_ca_cert')
        ovsdb_interface = mock.MagicMock()
        db_sb_connection_strs = mock.PropertyMock().return_value = ['dbsbconn']
        ovsdb_interface.db_sb_connection_strs = db_sb_connection_strs
        cluster_local_addr = mock.PropertyMock().return_value = (
            'cluster_local_addr')
        ovsdb_interface.cluster_local_addr = cluster_local_addr
        self.target.configure_ovs(ovsdb_interface)
        self.run.assert_has_calls([
            mock.call('ovs-vsctl', 'set-ssl', mock.ANY, mock.ANY, mock.ANY),
            mock.call('ovs-vsctl', 'set', 'open', '.',
                      'external-ids:ovn-remote=dbsbconn'),
            mock.call('ovs-vsctl', 'set', 'open', '.',
                      'external-ids:ovn-encap-type=geneve'),
            mock.call('ovs-vsctl', 'set', 'open', '.',
                      'external-ids:ovn-encap-ip=cluster_local_addr'),
        ])
