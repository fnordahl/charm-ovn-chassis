import json
import subprocess


class SimpleOVSDB(object):
    """Simple interface to OVSDB through the use of command line tools.

    OVS and OVN is managed through a set of databases.  These databases have
    similar command line tools to manage them.  We make use of the similarity
    to provide a generic class that can be used to manage them.

    The OpenvSwitch project does provide a Python API, but on the surface it
    appears to be a bit too involved for our simple use case.

    Examples:
    chassis = SimpleOVSDB('ovn-sbctl', 'chassis')
    for chs in chassis:
        print(chs)

    bridges = SimpleOVSDB('ovs-vsctl', 'bridge')
    for br in bridges:
        if br['name'] == 'br-test':
            bridges.set(br['uuid'], 'external_ids:charm', 'managed')
    """

    def __init__(self, tool, table):
        """SimpleOVSDB constructor

        :param tool: Which tool with database commands to operate on.
                     Usually one of `ovs-vsctl`, `ovn-nbctl`, `ovn-sbctl`
        :type tool: str
        :param table: Which table to operate on
        :type table: str
        """
        self.tool = tool
        self.tbl = table

    def run(self, *args):
        cp = subprocess.run(
            args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True,
            universal_newlines=True)
        return cp

    def _find_tbl(self, condition=None):
        cmd = [self.tool, '-f', 'json', 'find', self.tbl]
        if condition:
            cmd.append(condition)
        cp = self.run(*cmd)
        data = json.loads(cp.stdout)
        for row in data['data']:
            values = []
            for col in row:
                if isinstance(col, list):
                    values.append(col[1])
                else:
                    values.append(col)
            yield dict(zip(data['headings'], values))

    def __iter__(self):
        return self._find_tbl()

    def clear(self, rec, col):
        self.run(self.tool, 'clear', self.tbl, rec, col)

    def find(self, condition):
        return self._find_tbl(condition=condition)

    def remove(self, rec, col, value):
        self.run(self.tool, 'remove', self.tbl, rec, col, value)

    def set(self, rec, col, value):
        self.run(self.tool, 'set', self.tbl, rec, '{}={}'.format(col, value))