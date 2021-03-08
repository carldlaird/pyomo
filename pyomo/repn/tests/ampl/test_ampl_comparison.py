#  ___________________________________________________________________________
#
#  Pyomo: Python Optimization Modeling Objects
#  Copyright 2017 National Technology and Engineering Solutions of Sandia, LLC
#  Under the terms of Contract DE-NA0003525 with National Technology and
#  Engineering Solutions of Sandia, LLC, the U.S. Government retains certain
#  rights in this software.
#  This software is distributed under the 3-clause BSD License.
#  ___________________________________________________________________________
#
# Test the Pyomo NL writer against the AMPL NL writer
#

import json
import re
import glob
import subprocess
import os
from os.path import abspath, dirname
currdir = dirname(abspath(__file__))+os.sep

import pyomo.common.unittest as unittest
import pyomo.common

import pyomo.scripting.pyomo_main as main

parameterized, param_available = pyomo.common.dependencied.attempt_import('parameterized')
if not param_available:
    raise unittest.SkipTest('Parameterized is not available.')

# https://github.com/ghackebeil/gjh_asl_json
has_gjh_asl_json = False
if os.system('gjh_asl_json -v') == 0:
    has_gjh_asl_json = True

names = []
# add test methods to classes
for f in glob.glob(currdir+'*_testCase.py'):
    names.append(re.split('[._]',os.path.basename(f))[0])


class Tests(unittest.TestCase):

    def pyomo(self, cmd):
        os.chdir(currdir)
        output = main.main(['convert', '--logging=quiet', '-c']+cmd)
        return output


class BaselineTests(Tests):
    def __init__(self, *args, **kwds):
        Tests.__init__(self, *args, **kwds)

    #
    #The following test generates an nl file for the test case
    #and checks that it matches the current pyomo baseline nl file
    #
    @parameterized.expand(input=names)
    def nlwriter_baseline_test(self, name):
        if os.path.exists(currdir+name+'.dat'):
            self.pyomo(['--output='+currdir+name+'.test.nl',
                        currdir+name+'_testCase.py',
                        currdir+name+'.dat'])
        else:
            self.pyomo(['--output='+currdir+name+'.test.nl',
                        currdir+name+'_testCase.py'])

        # Check that the pyomo nl file matches its own baseline
        with open(currdir+name+'.test.nl', 'r') as f1, \
                open(currdir+name+'.pyomo.nl', 'r') as f2:
                    f1_contents = list(filter(None, f1.read().split()))
                    f2_contents = list(filter(None, f2.read().split()))
                    for item1, item2 in zip(f1_contents, f2_contents):
                        if item1.startswith('n'):
                            continue
                        try:
                            self.assertEqual(item1, item2)
                        except:
                            self.assertEqual(float(item1), float(item2))
        os.remove(currdir+name+'.test.nl')


class ASLTests(Tests):

    def __init__(self, *args, **kwds):
        Tests.__init__(self, *args, **kwds)

    #
    # The following test calls the gjh_asl_json executable to
    # generate JSON files corresponding to both the
    # AMPL-generated nl file and the Pyomo-generated nl
    # file. The JSON files are then diffed using the pyomo.common.unittest
    # test class method assertStructuredAlmostEqual
    #
    @parameterized.expand(input=names)
    def nlwriter_asl_test(self, name):
        if not has_gjh_asl_json:
            self.skipTest("'gjh_asl_json' executable not available")
            return
        if os.path.exists(currdir+name+'.dat'):
            self.pyomo(['--output='+currdir+name+'.test.nl',
                        '--file-determinism=3',
                        '--symbolic-solver-labels',
                        currdir+name+'_testCase.py',
                        currdir+name+'.dat'])
        else:
            self.pyomo(['--output='+currdir+name+'.test.nl',
                        '--file-determinism=3',
                        '--symbolic-solver-labels',
                        currdir+name+'_testCase.py'])

        # compare AMPL and Pyomo nl file structure
        try:
            os.remove(currdir+name+'.ampl.json')
        except Exception:
            pass
        try:
            os.remove(currdir+name+'.test.json')
        except Exception:
            pass

        # obtain the nl file summary information for comparison with ampl
        p = subprocess.run(['gjh_asl_json',
                            currdir+name+'.test.nl',
                            'rows='+currdir+name+'.test.row',
                            'cols='+currdir+name+'.test.col'],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           universal_newlines=True)
        self.assertTrue(p.returncode == 0, msg=p.stdout)

        # obtain the nl file summary information for comparison with pyomo
        p = subprocess.run(['gjh_asl_json',
                            currdir+name+'.ampl.nl',
                            'rows='+currdir+name+'.ampl.row',
                            'cols='+currdir+name+'.ampl.col'],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           universal_newlines=True)
        self.assertTrue(p.returncode == 0, msg=p.stdout)

        with open(currdir+name+'.test.json', 'r') as f1, \
            open(currdir+name+'.ampl.json', 'r') as f2:
                self.assertStructuredAlmostEqual(json.load(f1),
                                                 json.load(f2),
                                                 abstol=1e-8)

        os.remove(currdir+name+'.ampl.json')

        # delete temporary test files
        os.remove(currdir+name+'.test.col')
        os.remove(currdir+name+'.test.row')
        os.remove(currdir+name+'.test.nl')


if __name__ == "__main__":
    unittest.main()
