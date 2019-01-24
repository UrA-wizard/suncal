''' Class for managing a project, that is a list of calculator objects.

    Supported calculator objects include:

    - UncertCalc
    - UncertSweep
    - UncertReverse
    - UncertSweepReverse
    - UncertRisk
    - CurveFit

    New calculation objects must support the following methods:

    - calculate()  -- Return an output object with report() method
    - get_config() -- Return a configuration dictionary
    - from_config() -- Build a calculator object from the config dictionary
    - from_configfile()  -- Build a calculator object from the yaml file

'''

from io import StringIO
import shutil
import yaml

from . import uncertainty
from . import anova
from . import sweeper
from . import output
from . import curvefit
from . import risk
from . import reverse
from . import dist_explore


class Project(object):
    ''' Uncertainty Project container. Holds a list of calculation objects
        (i.e. uncertainty propagations, sweeps, risks, datasets, etc.)
    '''
    def __init__(self, items=None):
        self.items = []
        if items is not None:
            self.items = items

    def count(self):
        ''' Get number of items in project '''
        return len(self.items)

    def get_mode(self, index):
        ''' Get calculation mode for the index '''
        item = self.items[index]
        # NOTE: order is important here, for example UncertSweepReverse is an instance of UncertSweep too
        if isinstance(item, sweeper.UncertSweepReverse):
            mode = 'reversesweep'
        elif isinstance(item, sweeper.UncertSweep):
            mode = 'sweep'
        elif isinstance(item, reverse.UncertReverse):
            mode = 'reverse'
        elif isinstance(item, uncertainty.UncertCalc):
            mode = 'uncertainty'
        elif isinstance(item, risk.UncertRisk):
            mode = 'risk'
        elif isinstance(item, curvefit.CurveFit):
            mode = 'curvefit'
        elif isinstance(item, anova.ArrayGrouped) or isinstance(item, anova.ArrayGroupedSummary):
            mode = 'anova'
        elif isinstance(item, dist_explore.DistExplore):
            mode = 'distributions'
        else:
            raise ValueError('Unknown item {}'.format(item))
        return mode

    def add_item(self, item):
        ''' Add calculator item to project.

            Parameters
            ----------
            item: object
                Item to add. Should be a valid uncertainty calculation object,
                such as UncertCalc, UncertSweep, etc.

            Notes
            -----
            Valid project items must have methods for save_config(), from_config(), and calculate().
        '''
        item.project = self  # Add reference to project the item is in (useful for building project tree)
        self.items.append(item)

    def rem_item(self, item):
        ''' Remove item from project

            Parameters
            ----------
            item: int or string
                If int, will remove item at index[int]. If string, will remove first item with
                that name.
        '''
        try:
            self.items.pop(item)
        except TypeError:
            names = self.get_names()
            self.items.pop(names.index(item))

        try:
            del item.project
        except AttributeError:
            pass

    def rename_item(self, index, name):
        ''' Rename an item '''
        self.items[index].name = name

    def save_config(self, fname):
        ''' Save project config file '''
        fstr = StringIO()
        for item in self.items:
            item.save_config(fstr)
        fstr.seek(0)
        try:
            shutil.copyfileobj(fstr, fname)  # fname is file object
        except AttributeError:  # fname is string name of file
            fstr.seek(0)
            with open(fname, 'w') as f:
                shutil.copyfileobj(fstr, f)

    @classmethod
    def from_configfile(cls, fname):
        ''' Load project from config file.

        Parameters
        ----------
        fname: string or file object
            File name or file object to read from

        Returns
        -------
        Project instance
            Project loaded from config. Returns None if file cannot be loaded.
        '''
        try:
            try:
                yml = fname.read()  # fname is file object
            except AttributeError:
                with open(fname, 'r') as fobj:  # fname is string
                    yml = fobj.read()
        except UnicodeDecodeError:
            # file is binary, can't be read as yaml
            return None

        try:
            config = yaml.safe_load(yml)
        except (yaml.scanner.ScannerError, yaml.parser.ParserError, yaml.composer.ComposerError):
            return None  # Can't read YAML

        if not isinstance(config, list):
            config = [config]  # Old (<1.1) style config files are dict at top level, wrap in a list

        newproj = cls()
        for configdict in config:
            if not hasattr(configdict, 'get'): # Something not right with file
                return None

            mode = configdict.get('mode', 'uncertainty')
            if mode == 'uncertainty':
                item = uncertainty.UncertCalc.from_config(configdict)
                if item is None:
                    return   # Could have loaded valid YAML that isn't PSLUC data
            elif mode == 'sweep':
                item = sweeper.UncertSweep.from_config(configdict)
            elif mode == 'reverse':
                item = reverse.UncertReverse.from_config(configdict)
            elif mode == 'reversesweep':
                item = sweeper.UncertSweepReverse.from_config(configdict)
            elif mode == 'risk':
                item = risk.UncertRisk.from_config(configdict)
            elif mode == 'curvefit':
                item = curvefit.CurveFit.from_config(configdict)
            elif mode == 'anova':
                item = anova.ArrayGrouped.from_config(configdict)
            elif mode == 'distributions':
                item = dist_explore.DistExplore.from_config(configdict)
            else:
                raise ValueError('Unsupported project mode {}'.format(mode))
            newproj.add_item(item)
        return newproj

    def get_names(self):
        ''' Get names of all project components '''
        names = [item.name for item in self.items]
        return names

    def calculate(self):
        ''' Run calculate() method on all items and append all reports '''
        r = output.MDstring()
        for item in self.items:
            r += '# {}\n\n'.format(item.name)
            r += item.calculate().report()
            r += '---\n\n'
        return r

    def report_all(self):
        ''' Report_all for every project component '''
        r = output.MDstring()
        for i in range(self.count()):
            r += '# {}\n\n'.format(self.items[i].name)
            out = self.items[i].get_output()
            if out is not None:
                r += out.report_all() + '\n\n'
            else:
                r += 'Calculation not run\n\n'
            r += '---\n\n'
        return r

    def report_short(self):
        ''' Report() for every project component '''
        r = output.MDstring()
        for i in range(self.count()):
            r += '# {}\n\n'.format(self.items[i].name)
            out = self.items[i].get_output()
            if out is not None:
                r += out.report() + '\n\n'
            else:
                r += 'Calculation not run\n\n'
            r += '---\n\n'
        return r

    def report_summary(self):
        ''' Report_summary() for every project component '''
        r = output.MDstring()
        for i in range(self.count()):
            r += '# {}\n\n'.format(self.items[i].name)
            out = self.items[i].get_output()
            if out is not None:
                r += out.report_summary() + '\n\n'
            else:
                r += 'Calculation not run\n\n'
            r += '---\n\n'
        return r
