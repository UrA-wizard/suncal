#!/usr/bin/env python
''' PSL Uncertainty Calculator - Sandia National Labs
    Command line interface to Uncertainty Calculator.

    Multiple commands are installed:
        psluncert: Calculate normal uncertainty propagation problem
        psluncertf: Calculate uncertainty problem from config (yaml) file
        psluncertrev: Calculate reverse uncertainty problem
        psluncertrisk: Calculate risk analysis
        psluncertfit: Calculate curve fit uncertainty
'''
import os
import argparse
import numpy as np

import psluncert as uc
from psluncert import project
from psluncert import output
from psluncert import reverse
from psluncert import risk
from psluncert import curvefit
from psluncert import customdists


def main_setup():
    ''' Run calculations defined in YAML setup file '''
    parser = argparse.ArgumentParser(prog='psluncertf', description='Run uncertainty calculation from setup file.')
    parser.add_argument('filename', help='Setup parameter file.', type=str)
    parser.add_argument('-o', help='Output filename. Extension determines file format.', type=argparse.FileType('w'), default='-')
    parser.add_argument('-f', help="Output format for when output filename not provided ['txt', 'html', 'md']", type=str, choices=['html', 'txt', 'md'])
    parser.add_argument('--verbose', '-v', help='Verbose mode. Include plots with one v, full report with two.', default=0, action='count')
    args = parser.parse_args()

    u = project.Project.from_configfile(args.filename)
    u.calculate()

    fmt = args.f
    if args.o and args.o.name != '<stdout>':
        _, fmt = os.path.splitext(str(args.o.name))
        fmt = fmt[1:]  # remove '.'

    if fmt in [None, 'txt']:
        math = 'text'
        fig = 'text'
    else:
        math = 'mpl'
        fig = 'svg'

    with output.report_format(math=math, fig=fig):
        if args.verbose > 1:
            r = u.report_all()
        elif args.verbose > 0:
            r = u.report_summary()
        else:
            r = u.report_short()

        if fmt == 'docx':
            r.save_docx(args.o.name)
            return
        elif fmt == 'odt':
            r.save_odt(args.o.name)
            return
        elif fmt == 'pdf':
            r.save_pdf(args.o.name)
            return
        elif fmt == 'html':
            strreport = r.get_html()
        elif fmt == 'md':
            strreport = r.get_md()
        else:
            strreport = str(r)

        with args.o as f:
            f.write(strreport)


def main_unc():
    ''' Run uncertainty propagation problem '''
    parser = argparse.ArgumentParser(prog='psluncert', description='Compute combined uncertainty of a system.')
    parser.add_argument('funcs', nargs='+', help='Measurement model functions (e.g. "f = x + y")', type=str)
    parser.add_argument('--variables', nargs='+', help='List of variable measured values (e.g. "x=10")', type=str)
    parser.add_argument('--uncerts', nargs='+', help='List of uncertainty components, parameters separated by semicolons. First parameter must be variable name. (e.g. "x; unc=2; k=2")', type=str)
    parser.add_argument('--correlate', nargs='+', help='List of correlation coefficients between pairs of variables. (e.g. "x; y; .8")', type=str)
    parser.add_argument('-o', help='Output filename. Extension determines file format.', type=argparse.FileType('w'), default='-')
    parser.add_argument('-f', help="Output format for when output filename not provided ['txt', 'html', 'md']", type=str, choices=['html', 'txt', 'md'])
    parser.add_argument('--samples', help='Number of Monte Carlo samples', type=int, default=1000000)
    parser.add_argument('-s', help='Short output format, prints values only. Prints (GUM mean, GUM std. uncert, GUM expanded, GUM k, MC mean, MC std. uncert, MC expanded min, MC expanded max, MC k) for each function', action='store_true')
    parser.add_argument('--verbose', '-v', help='Verbose mode. Include plots with one v, full report with two.', action='count', default=0)
    args = parser.parse_args()

    u = uc.UncertaintyCalc(args.funcs, samples=args.samples)
    if args.variables is not None:
        for var in args.variables:
            name, val = var.split('=')
            u.set_input(name.strip(), nom=float(val))

    if args.uncerts is not None:
        for uncert in args.uncerts:
            var, *uncargs = uncert.split(';')
            uncargs = dict([u.split('=') for u in uncargs])
            keys = uncargs.keys()
            for key in keys:
                uncargs[key.strip()] = uncargs.pop(key)
            u.set_uncert(var.strip(), **uncargs)

    if args.correlate is not None:
        for corr in args.correlate:
            x, y, c = corr.split(';')
            u.correlate_vars(x.strip(), y.strip(), float(c))
    u.calculate()

    if args.s:   # Print out short-format results
        with args.o as f:
            for func in u.functions:
                vals = [func.out.gum.mean[0], func.out.gum.uncert[0], *func.out.gum.expanded(.95),
                        func.out.mc.mean[0], func.out.mc.uncert[0], *func.out.mc.expanded(.95)]
                f.write(', '.join(['{:.9g}'.format(v) if isinstance(v, float) else '{:.9g}'.format(v[0]) for v in vals]))  # expanded() returns length-1 arrays
                f.write('\n')

    else:    # Print a formatted report
        fmt = args.f
        if args.o and args.o.name != '<stdout>':
            _, fmt = os.path.splitext(str(args.o.name))
            fmt = fmt[1:]  # remove '.'
        if fmt in [None, 'txt']:
            math = 'text'
            fig = 'text'
        else:
            math = 'mpl'
            fig = 'svg'

        with output.report_format(math=math, fig=fig):
            if args.verbose > 1:
                r = u.out.report_all()
            elif args.verbose > 0:
                r = u.out.report_summary()
            else:
                r = u.out.report()

            if fmt == 'docx':
                r.save_docx(args.o.name)
                return
            elif fmt == 'odt':
                r.save_odt(args.o.name)
                return
            elif fmt == 'pdf':
                r.save_pdf(args.o.name)
                return
            elif fmt == 'html':
                strreport = r.get_html()
            elif fmt == 'md':
                strreport = r.get_md()
            else:
                strreport = str(r)

            with args.o as f:
                f.write(strreport)


def main_reverse():
    ''' Run reverse uncertainty propagation problem '''
    parser = argparse.ArgumentParser(prog='psluncertrev', description='Compute reverse uncertainty propagation.')
    parser.add_argument('funcs', nargs='+', help='Measurement model functions (e.g. "f = x + y")', type=str)
    parser.add_argument('--solvefor', help='Name of variable to solve for.', type=str, required=True)
    parser.add_argument('--target', help='Target nominal value for solve-for variable', type=float, required=True)
    parser.add_argument('--targetunc', help='Target uncertainty value for solve-for variable', type=float, required=True)
    parser.add_argument('--fidx', help='Index of function (when more than one function is defined).', type=int, default=-1)
    parser.add_argument('--variables', nargs='+', help='List of variable measured values (e.g. "x=10")', type=str)
    parser.add_argument('--uncerts', nargs='+', help='List of uncertainty components, parameters separated by semicolons. First parameter must be variable name. (e.g. "x; unc=2; k=2")', type=str)
    parser.add_argument('--correlate', nargs='+', help='List of correlation coefficients between pairs of variables. (e.g. "x; y; .8")', type=str)
    parser.add_argument('-o', help='Output filename. Extension determines file format.', type=argparse.FileType('w'), default='-')
    parser.add_argument('-f', help="Output format for when output filename not provided ['txt', 'html', 'md']", type=str, choices=['html', 'txt', 'md'])
    parser.add_argument('--samples', help='Number of Monte Carlo samples', type=int, default=1000000)
    parser.add_argument('-s', help='Short output format, prints values only. Prints (GUM mean, GUM std. uncert, MC mean, MC std. uncert) for solve-for variable.', action='store_true')
    parser.add_argument('--verbose', '-v', help='Verbose mode (include plots)', action='count', default=0)
    args = parser.parse_args()

    u = reverse.UncertReverse(args.funcs, targetnom=args.target, targetunc=args.targetunc, solvefor=args.solvefor, samples=args.samples)
    if args.variables is not None:
        for var in args.variables:
            name, val = var.split('=')
            u.set_input(name.strip(), nom=float(val))

    if args.uncerts is not None:
        for uncert in args.uncerts:
            var, *uncargs = uncert.split(';')
            uncargs = dict([u.split('=') for u in uncargs])
            keys = uncargs.keys()
            for key in keys:
                uncargs[key.strip()] = uncargs.pop(key)
            u.set_uncert(var.strip(), **uncargs)

    if args.correlate is not None:
        for corr in args.correlate:
            x, y, c = corr.split(';')
            u.correlate_vars(x.strip(), y.strip(), float(c))
    out = u.calculate()

    if args.s:   # Print out short-format results
        with args.o as f:
            vals = [out.gumdata['i'], out.gumdata['u_i'],
                    out.mcdata['i'], out.mcdata['u_i']]
            f.write(', '.join(['{:.9g}'.format(v) for v in vals]))
            f.write('\n')

    else:    # Print a formatted report
        fmt = args.f
        if args.o and args.o.name != '<stdout>':
            _, fmt = os.path.splitext(str(args.o.name))
            fmt = fmt[1:]  # remove '.'
        if fmt in [None, 'txt']:
            math = 'text'
            fig = 'text'
        else:
            math = 'mpl'
            fig = 'svg'

        with output.report_format(math=math, fig=fig):
            if args.verbose > 1:
                r = u.out.report_all()
            elif args.verbose > 0:
                r = u.out.report_summary()
            else:
                r = u.out.report()

            if fmt == 'docx':
                r.save_docx(args.o.name)
                return
            elif fmt == 'odt':
                r.save_odt(args.o.name)
                return
            elif fmt == 'pdf':
                r.save_pdf(args.o.name)
                return
            elif fmt == 'html':
                strreport = r.get_html()
            elif fmt == 'md':
                strreport = r.get_md()
            else:
                strreport = str(r)

            with args.o as f:
                f.write(strreport)


def main_risk():
    ''' Calculate risk analysis '''
    parser = argparse.ArgumentParser(prog='psluncertrisk', description='Risk Analysis Calculation')
    parser.add_argument('-LL', help='Lower specification limit', type=float, required=True)
    parser.add_argument('-UL', help='Upper specification limit', type=float, required=True)
    parser.add_argument('-GBL', help='Lower guardband as offset from lower limit', type=float, default=0)
    parser.add_argument('-GBU', help='Upper guardband as offset from upper limit', type=float, default=0)
    parser.add_argument('--procdist', help='Process distribution parameters, semicolon-separated. (e.g. "dist=uniform; median=10; a=3")', type=str, required=True)
    parser.add_argument('--testdist', help='Test distribution parameters, semicolon-separated. (e.g. "median=10; std=.75")', type=str)
    parser.add_argument('-o', help='Output filename. Extension determines file format.', type=argparse.FileType('w'), default='-')
    parser.add_argument('-f', help="Output format for when output filename not provided ['txt', 'html', 'md']", type=str, choices=['html', 'txt', 'md'])
    parser.add_argument('-s', help='Short output format, prints values only (Process Risk, PFA, PFR)', action='store_true')
    parser.add_argument('--verbose', '-v', help='Verbose mode (include plots)', action='count', default=0)
    args = parser.parse_args()

    dproc = {}
    for keyval in str(args.procdist).split(';'):
        key, val = keyval.split('=')
        if key.strip() != 'dist':
            dproc[key.strip()] = float(val)
        else:
            dproc[key.strip()] = val
    dproc = customdists.from_config(dproc)

    dtest = None
    if args.testdist is not None:
        dtest = {}
        for keyval in str(args.testdist).split(';'):
            key, val = keyval.split('=')
            if key.strip() != 'dist':
                dtest[key.strip()] = float(val)
            else:
                dtest[key.strip()] = val
        dtest = customdists.from_config(dtest)

    rsk = risk.UncertRisk(dproc=dproc, dtest=dtest)
    rsk.set_speclimits(LL=args.LL, UL=args.UL)
    rsk.set_guardband(GBL=args.GBL, GBU=args.GBU)

    if args.s:
        procrisk = rsk.process_risk()[1]
        try:
            pfa = rsk.PFA()
            pfr = rsk.PFR()
        except ValueError:
            pfa = np.nan
            pfr = np.nan
        with args.o as f:
            f.write('{:.5f}, {:.5f}, {:.5f}\n'.format(procrisk, pfa, pfr))

    else:
        out = rsk.calculate()

        fmt = args.f
        if args.o and args.o.name != '<stdout>':
            _, fmt = os.path.splitext(str(args.o.name))
            fmt = fmt[1:]  # remove '.'
        if fmt in [None, 'txt']:
            math = 'text'
            fig = 'text'
        else:
            math = 'mpl'
            fig = 'svg'

        with output.report_format(math=math, fig=fig):
            if args.verbose > 0:
                r = out.report_all()
            else:
                r = out.report()

            fmt = str(args.f)
            if args.o and args.o.name != '<stdout>':
                _, fmt = os.path.splitext(str(args.o.name))
                fmt = fmt[1:]  # remove '.'

            if fmt == 'docx':
                r.save_docx(args.o.name)
                return
            elif fmt == 'odt':
                r.save_odt(args.o.name)
                return
            elif fmt == 'pdf':
                r.save_pdf(args.o.name)
                return
            elif fmt == 'html':
                strreport = r.get_html()
            elif fmt == 'md':
                strreport = r.get_md()
            else:
                strreport = str(r)

            with args.o as f:
                f.write(strreport)


def main_curvefit():
    ''' Calculate curvefit uncertainty '''
    parser = argparse.ArgumentParser(prog='psluncertfit', description='Curve fit uncertainty')
    parser.add_argument('--model', help='Curve model to fit.', choices=['line', 'poly', 'exp'], default='line', type=str)
    parser.add_argument('-x', '--x', help='X-values', nargs='+', type=float)
    parser.add_argument('-y', '--y', help='Y-values', nargs='+', type=float)
    parser.add_argument('--uy', help='Y uncertainty value(s)', nargs='+', type=float)
    parser.add_argument('--ux', help='X uncertainty value(s)', nargs='+', type=float)
    parser.add_argument('--order', help='Order of polynomial fit', type=int, default=2)
    parser.add_argument('--methods', help='Uncertainty calculation method', choices=['lsq', 'mc', 'mcmc', 'gum'], default='lsq', nargs='+', type=str)
    parser.add_argument('-o', help='Output filename. Extension determines file format.', type=argparse.FileType('w'), default='-')
    parser.add_argument('-f', help="Output format for when output filename not provided ['txt', 'html', 'md']", type=str, choices=['html', 'txt', 'md'])
    parser.add_argument('-s', help='Short output format, prints values only. First line is fit parameter values (a, b, ...), second is parameter uncertainties. Lines repeat for each method.', action='store_true')
    parser.add_argument('--verbose', '-v', help='Verbose mode. Include plots with one v, full report with two.', default=0, action='count')
    args = parser.parse_args()

    x = np.array(args.x)
    y = np.array(args.y)
    ux = args.ux if args.ux else 0
    uy = args.uy if args.uy else 0

    arr = curvefit.Array(x, y, ux, uy)
    fit = curvefit.CurveFit(arr, args.model, polyorder=args.order)
    methods = dict([(m, True) for m in args.methods])
    fit.calculate(**methods)

    if args.s:
        with args.o as f:
            for base in fit.out._baseoutputs:
                f.write(', '.join(['{:.9g}'.format(m) for m in base.mean]) + '\n')
                f.write(', '.join(['{:.9g}'.format(m) for m in base.uncert]) + '\n')

    else:
        fmt = args.f
        if args.o and args.o.name != '<stdout>':
            _, fmt = os.path.splitext(str(args.o.name))
            fmt = fmt[1:]  # remove '.'

        if fmt in [None, 'txt']:
            math = 'text'
            fig = 'text'
        else:
            math = 'mpl'
            fig = 'svg'

        with output.report_format(math=math, fig=fig):
            if args.verbose > 1:
                r = fit.out.report_all()
            elif args.verbose > 0:
                r = fit.out.report_summary()
            else:
                r = fit.out.report()
            if fmt == 'docx':
                r.save_docx(args.o.name)
                return
            elif fmt == 'odt':
                r.save_odt(args.o.name)
                return
            elif fmt == 'pdf':
                r.save_pdf(args.o.name)
                return
            elif fmt == 'html':
                strreport = r.get_html()
            elif fmt == 'md':
                strreport = r.get_md()
            else:
                strreport = str(r)

            with args.o as f:
                f.write(strreport)


if __name__ == '__main__':
    main_setup()
