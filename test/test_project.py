''' Test project class - saving/loading config file for multiple calculations '''

from io import StringIO
import os
import numpy as np
from scipy import stats

import psluncert
from psluncert import project
from psluncert import anova
from psluncert import sweeper
from psluncert import reverse
from psluncert import risk
from psluncert import curvefit
from psluncert import dist_explore


def test_saveload_fname(tmpdir):
    # Set up a Project with all types of calculations. Save it to a file (both using file NAME
    # and file OBJECT, read back the results, and compare the output report.
    # Make sure to store seeds for everything that does MC.

    np.random.seed(588132535)
    # Set up several project components of the different types
    u = psluncert.UncertCalc('f = m/(pi*r**2)', seed=44444)
    u.set_input('m', nom=2, std=.2)
    u.set_input('r', nom=1, std=.1)

    u2 = psluncert.UncertCalc('g = m * 5', seed=4444)
    u2.set_input('m', nom=5, std=.5)

    rsk = risk.UncertRisk()
    rsk.set_process_dist(stats.t(loc=.5, scale=1, df=9))

    swp = sweeper.UncertSweep(u)
    swp.add_sweep_nom('m', values=[.5, 1, 1.5, 2])

    x = np.linspace(-10, 10, num=21)
    y = x*2 + np.random.normal(loc=0, scale=.5, size=len(x))
    arr = curvefit.Array(x, y, uy=0.5)
    fit = curvefit.CurveFit(arr, seed=909090)

    rev = reverse.UncertReverse('f = m/(pi*r**2)', seed=5555, targetnom=20, targetunc=.5, solvefor='m')
    rev.set_input('r', nom=5, std=.05)

    revswp = sweeper.UncertSweepReverse(rev)
    revswp.add_sweep_unc('r', values=[.01, .02, .03, .04], comp='u(r)', param='std')

    explore = dist_explore.DistExplore()
    explore.add_dist('a', stats.norm(loc=3, scale=2))
    explore.add_dist('b', stats.uniform(loc=0, scale=2))
    explore.add_dist('a+b')
    explore.get_config()

    anv = anova.ArrayGrouped()
    anv.set_xy(np.vstack((np.repeat(np.arange(5), 5), np.random.normal(loc=10, scale=1, size=25))).transpose())

    proj = project.Project()
    proj.add_item(u)
    proj.add_item(u2)
    proj.add_item(rsk)
    proj.add_item(swp)
    proj.add_item(fit)
    proj.add_item(rev)
    proj.add_item(revswp)
    proj.add_item(explore)
    reportorig = proj.calculate()

    # Save_config given file NAME
    outfile = tmpdir.join('projconfig.yaml')
    proj.save_config(outfile)

    # Save_config given file OBJECT
    outfileobj = StringIO()
    proj.save_config(outfileobj)
    outfileobj.seek(0)

    proj2 = project.Project.from_configfile(outfile)
    reportnew = proj2.calculate()
    assert str(reportorig) == str(reportnew)

    proj3 = project.Project.from_configfile(outfileobj)
    reportobj = proj3.calculate()
    assert str(reportorig) == str(reportobj)
    outfileobj.close()


def test_projrem():
    # Test add/remove items from project
    u = psluncert.UncertCalc('f = a*b', name='function1')
    u2 = psluncert.UncertCalc('g = c*d', name='function2')

    proj = project.Project()
    proj.add_item(u)
    proj.add_item(u2)
    assert proj.get_names() == ['function1', 'function2']
    proj.rem_item(0)
    assert proj.get_names() == ['function2']

    proj = project.Project()
    proj.add_item(u)
    proj.add_item(u2)
    proj.rem_item('function2')
    assert proj.get_names() == ['function1']

