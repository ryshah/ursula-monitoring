#!/usr/bin/python
#
# Copyright 2014, Craig Tracey <craigtracey@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import json
import re

from sensu_plugin import SensuPluginCheck
from subprocess import Popen, PIPE


class SwiftDispersionCheck(SensuPluginCheck):

    def setup(self):
        self.parser.add_argument('-c', '--container-crit', type=int,
                                 help='Container critical dispersion percent')
        self.parser.add_argument('-d', '--container-warn', type=int,
                                 help='Container warning dispersion percent')
        self.parser.add_argument('-o', '--object-crit', type=int,
                                 help='Object critical dispersion percent')
        self.parser.add_argument('-n', '--object-warn', type=int,
                                 help='Object warning dispersion percent')

    def run(self):
        output = None
        # This should at most run twice when populate is not
        # run. If populate is run error message would be different
        # causing check to return immediately
        while True:
            proc_rep = Popen(['swift-dispersion-report', '-j'],
                             stdout=PIPE, stderr=PIPE)
            output, error = proc_rep.communicate()
            if proc_rep.returncode == 0:
                break
            else:
                # If dispersion populate is not run report returns error saying
                # no containers present. So once populate is run successfully
                # this should error out if report fails
                if "No containers to query" not in error:
                    self.critical("Unable to run swift-dispersion-check: %s" %
                                  error)
                    return
                else:
                    # Run dispersion populate and retry
                    proc_pop = Popen(['swift-dispersion-populate'],
                                     stdout=PIPE, stderr=PIPE)
                    pop_out, pop_error = proc_pop.communicate()
                    # Error out if populate fails for some reason
                    if proc_pop.returncode != 0:
                        self.critical("Unable to run swift-dispersion-check: "
                                      "%s" % pop_error)
                        return
        p = re.compile(r'(\{.*\})')
        m = p.search(output)
        output = m.group(1)
        dispersion = json.loads(output)
        container_pct = int(dispersion['container']['pct_found'])
        object_pct = int(dispersion['object']['pct_found'])

        msg = "Swift %s dispersion %s threshold %d > %d"
        if ((self.options.container_crit and
             self.options.container_crit > container_pct)):
            self.critical(msg % ('container', 'CRITICAL',
                                 self.options.container_crit, container_pct))
        elif ((self.options.object_crit and
               self.options.object_crit > object_pct)):
            self.critical(msg % ('object', 'CRITICAL',
                                 self.options.object_crit, object_pct))
        elif ((self.options.container_warn and
               self.options.container_warn > container_pct)):
            self.critical(msg % ('container', 'WARNING',
                                 self.options.container_warn, container_pct))
        elif ((self.options.object_warn and
               self.options.object_warn > object_pct)):
            self.critical(msg % ('object', 'WARNING',
                                 self.options.object_warn, object_pct))
        else:
            self.ok()

if __name__ == "__main__":
    SwiftDispersionCheck()
