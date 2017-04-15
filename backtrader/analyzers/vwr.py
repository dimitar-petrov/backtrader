#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
#
# Copyright (C) 2015, 2016, 2017 Daniel Rodriguez
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import math

import backtrader as bt
from backtrader import TimeFrameAnalyzerBase
from . import Returns
from ..mathsupport import standarddev


class VWR(TimeFrameAnalyzerBase):
    '''Variability-Weighted Return: Better SharpeRatio with Log Returns

    Alias:

      - VariabilityWeightedReturn

    See:

      - https://www.crystalbull.com/sharpe-ratio-better-with-log-returns/

    Params:

      - ``timeframe`` (default: ``None``)
        If ``None`` then the complete return over the entire backtested period
        will be reported

        Pass ``TimeFrame.NoTimeFrame`` to consider the entire dataset with no
        time constraints

      - ``compression`` (default: ``None``)

        Only used for sub-day timeframes to for example work on an hourly
        timeframe by specifying "TimeFrame.Minutes" and 60 as compression

        If ``None`` then the compression of the 1st data of the system will be
        used

      - ``tann`` (default: ``None``)

        Number of periods to use for the annualization (normalization) of the
        average returns. If ``None``, then standard ``t`` values will be used,
        namely:

          - ``days: 252``
          - ``weeks: 52``
          - ``months: 12``
          - ``years: 1``

      - ``tau`` (default: ``2.0``)

        factor for the calculation (see the literature)

      - ``sdev_max`` (default: ``0.20``)

        max standard deviation (see the literature)

    Methods:

      - get_analysis

        Returns a dictionary with returns as values and the datetime points for
        each return as keys

        The returned dict contains the following keys:

          - ``vwr``: Variability-Weighted Return
    '''

    params = (
        ('tann', None),
        ('tau', 0.20),
        ('sdev_max', 2.0),
    )

    _TANN = {
        bt.TimeFrame.Days: 252.0,
        bt.TimeFrame.Weeks: 52.0,
        bt.TimeFrame.Months: 12.0,
        bt.TimeFrame.Years: 1.0,
    }

    def __init__(self):
        # Children log return analyzer
        self._returns = Returns(timeframe=self.p.timeframe,
                                compression=self.p.compression,
                                tann=self.p.tann)

    def start(self):
        super(VWR, self).start()
        # Add an initial placeholder for [-1] operation
        self._pis = [self.strategy.broker.getvalue()]  # keep initial value
        self._pns = [None]  # keep final prices (value)

    def stop(self):
        super(VWR, self).stop()

        # Check if no value has been seen after the last 'dt_over'
        # If so, there is one 'pi' out of place and a None 'pn'. Purge
        if self._pns[-1] is None:
            self._pis.pop()
            self._pns.pop()

        # Get results from children
        rs = self._returns.get_analysis()
        ravg = rs['ravg']
        rnorm100 = rs['rnorm100']

        # make n 1 based in enumerate (number of periods and not index)
        # skip initial placeholders for synchronization
        dts = []
        for n, pipn in enumerate(zip(self._pis, self._pns), 1):
            pi, pn = pipn

            dt = pn / (pi * math.exp(ravg * n)) - 1.0
            dts.append(dt)

        sdev_p = standarddev(dts, bessel=True)

        # In case the std is greater than max, adjust it
        # other wise VWR will be big positive number

        if sdev_p > self.p.sdev_max:
            sdev_p = self.p.sdev_max

        vwr = rnorm100 * (1.0 - pow(sdev_p / self.p.sdev_max, self.p.tau))
        self.rets['vwr'] = vwr

    def notify_cashvalue(self, cash, value):
        self._pns[-1] = value  # annotate last seen pn for current period

    def _on_dt_over(self):
        self._pis.append(self._pns[-1])  # last pn is pi in next period
        self._pns.append(None)  # placeholder for [-1] operation


VariabilityWeightedReturn = VWR
