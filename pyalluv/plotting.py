from __future__ import division, absolute_import, unicode_literals
from matplotlib.collections import PatchCollection
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from bisect import bisect_left


class AlluvialPlot(object):
    r"""

    Parameters
    ===========

    clusters: dict[str, dict], dict[float, list] or list[list]
      You have 2 options to create an Alluvial diagram\:

      raw data: dict[str, dict]
        *NOT IMPLEMENTED YET*

        Provide for each cluster (`key`) a dictionary specifying the
        out-fluxes in the form of a dictionary (`key`: cluster, `value`: flux).

        .. note::

          The `key` ``None`` can hold a dictionary specifying fluxes from/to
          outside the system. If is present in the provided dictionary it
          allows to specify in-fluxes, i.e. data source that were not present
          at the previous slice.

          If it is present in the out-fluxes of a cluster, the specified amount
          simply vanishes and will not lead to a flux.

      collections of :obj:`.Cluster`: dict[float, list] and list[list]
        If a `list` is provided each element must be a `list`
        of :obj:`.Cluster` objects. A `dictionary` must provide a `list` of
        :obj:`.Cluster` (*value*) for a horizontal position (*key*), e.g.
        ``{1.0: [c11, c12, ...], 2.0: [c21, c22, ...], ...}``.

    axes: :class:`matplotlib.axes.Axes`
      Axes to draw an Alluvial diagram on.
    y_pos: str
      **options:** ``'overwrite'``, ``'keep'``, ``'complement'``, ``'sorted'``

      'overwrite':
         Ignore existing y coordinates for a cluster and set the vertical
         position to minimize the vertical displacements of all fluxes.
      'keep':
        use the cluster's :attr:`~pyalluv.clusters.Cluster.y_pos`. If a
        cluster has no y position set this raises an exception.
      'complement':
        use the cluster's :attr:`~pyalluv.clusters.Cluster.y_pos` if
        set. Cluster without y position are positioned relative to the other
        clusters by minimizing the vertical displacements of all fluxes.
      'sorted':
        NOT IMPLEMENTED YET
    cluster_w_spacing: float, int (default=1)
      Vertical spacing between clusters
    cluster_kwargs: dict (default={})
      dictionary styling the Path elements of clusters.

      Keys:
        `facecolor`, `edgecolor`, `alpha`, `linewidth`, ...

    cluster_kwargs: dict (default={})
      dictionary styling the :obj:`~matplotlib.patches.PathPatch` of clusters.

      for a list of available options see
      :class:`~matplotlib.patches.PathPatch`

    flux_kwargs: dict (default={})
      dictionary styling the :obj:`~matplotlib.patches.PathPatch` of fluxes.

      for a list of available options see
      :class:`~matplotlib.patches.PathPatch`

      Note
      -----

        Passing a string to `facecolor` and/or `edgecolor` allows to color
        fluxes relative to the color of their source or target clusters.

        ``'source_cluster'`` or ``'target_cluster'``:
          will set the facecolor equal to the color of the respective cluster.

          ``'cluster'`` *and* ``'source_cluster'`` *are equivalent.*

        ``'<cluster>_reside'`` or ``'<cluster>_migration'``:
          set the color based on whether source and target cluster have the
          same color or not. ``'<cluster>'`` should be either
          ``'source_cluster'`` or ``'target_cluster'`` and determines the
          cluster from which the color is taken.

          **Examples\:**

          ``facecolor='cluster_reside'``
            set `facecolor` to the color of the source cluster if both source
            and target cluster are of the same color.

          ``edgecolor='cluster_migration'``
            set `edgecolor` to the color of the source cluster if source and
            target cluster are of different colors.

    \**kwargs optional parameter:
        x_lim: tuple
          the horizontal limit values for the :class:`~matplotlib.axes.Axes`.
        y_lim: tuple
          the vertical limit values for the :class:`~matplotlib.axes.Axes`.
        set_x_pos: bool
          if clusters is a dict then the key is set for all clusters
        cluster_width: float
          (NOT IMPLEMENTED) overwrites width of all clusters
        format_xaxis: bool (default=True)
          If set to `True` the axes is formatted according to the data
          provided. For now, this is only relevant if the horizontal positions
          are :class:`~datetime.datetime` objects.
          See :meth:`~.AlluvialPlot.set_dates_xaxis` for further informations.
        x_axis_offset: float
          how much space (relative to total height)
          should be reserved for the x_axis. If set to 0.0, then
          the x labels will not be visible.
        fill_figure: bool
          indicating whether or not set the
          axis dimension to fill up the entire figure
        invisible_x/invisible_y: bool
          whether or not to draw these axis.
        y_fix: dict
          with x_pos as keys and a list of tuples
          (cluster labels) as values. The position of clusters (tuples)
          are swapped.
        redistribute_vertically: int (default=4)
          how often the vertical pairwise swapping of clusters at a given time
          point should be performed.
        y_offset: float
          offsets the vertical position of each cluster by this amount.

          .. note::

            This ca be used to draw multiple alluvial diagrams on the same
            :obj:`~matplotlib.axes.Axes` by simply calling
            :class:`~.AlluvialPlot` repeatedly with changing offset value, thus
            stacking alluvial diagrams.

    Attributes
    ===========

    clusters: dict
      Holds for each vertical position a list of :obj:`.Cluster` objects.
    """
    def __init__(
        self, clusters, axes, y_pos='overwrite', cluster_w_spacing=1,
        cluster_kwargs={}, flux_kwargs={}, label_kwargs={},
        **kwargs
            ):
        # if clusters are given in a list of lists (each list is a x position)
        self._set_x_pos = kwargs.get('set_x_pos', True)
        self._redistribute_vertically = kwargs.get(
            'redistribute_vertically',
            4
        )
        self.with_cluster_labels = kwargs.get('with_cluster_labels', True)
        self.format_xaxis = kwargs.get('format_xaxis', True)
        self._cluster_kwargs = cluster_kwargs
        self._flux_kwargs = flux_kwargs
        self._x_axis_offset = kwargs.get('x_axis_offset', 0.0)
        self._fill_figure = kwargs.get('fill_figure', False)
        self._invisible_y = kwargs.get('invisible_y', True)
        self._invisible_x = kwargs.get('invisible_x', False)
        self.y_offset = kwargs.get('y_offset', 0)
        self.y_fix = kwargs.get('y_fix', None)
        if isinstance(clusters, dict):
            self.clusters = clusters
        else:
            self.clusters = {}
            for cluster in clusters:
                try:
                    self.clusters[cluster.x_pos].append(cluster)
                except KeyError:
                    self.clusters[cluster.x_pos] = [cluster]
        self.x_positions = sorted(self.clusters.keys())
        # set the x positions correctly for the clusters
        if self._set_x_pos:
            for x_pos in self.x_positions:
                for cluster in self.clusters[x_pos]:
                    cluster = cluster.set_x_pos(x_pos)
        self._x_dates = False
        _minor_tick = 'months'
        cluster_widths = []
        if isinstance(self.x_positions[0], datetime):
            # assign date locator/formatter to the x-axis to get proper labels
            if self.format_xaxis:
                locator = mdates.AutoDateLocator(minticks=3)
                formatter = mdates.AutoDateFormatter(locator)
                axes.xaxis.set_major_locator(locator)
                axes.xaxis.set_major_formatter(formatter)
            self._x_dates = True
            if (self.x_positions[-1] - self.x_positions[0]).days < 2*30:
                _minor_tick = 'weeks'
            self.clusters = {
                    mdates.date2num(x_pos): self.clusters[x_pos]
                    for x_pos in self.x_positions
                    }
            self.x_positions = sorted(self.clusters.keys())
            for x_pos in self.x_positions:
                for cluster in self.clusters[x_pos]:
                    # in days (same as mdates.date2num)
                    cluster.width = cluster.width.total_seconds()/60/60/24
                    cluster_widths.append(cluster.width)
                    if cluster.label_margin is not None:
                        _h_margin = cluster.label_margin[
                                0].total_seconds()/60/60/24
                        cluster.label_margin = (
                                _h_margin, cluster.label_margin[1]
                                )
                    cluster.set_x_pos(mdates.date2num(cluster.x_pos))

        # TODO: set the cluster.width property
        else:
            for x_pos in self.x_positions:
                for cluster in self.clusters[x_pos]:
                    cluster_widths.append(cluster.width)
        self.cluster_width = kwargs.get('cluster_width', None)
        self.cluster_w_spacing = cluster_w_spacing
        self.x_lim = kwargs.get(
                'x_lim',
                (
                    self.x_positions[0]
                    - 2 * min(cluster_widths),
                    # - 2 * self.clusters[self.x_positions[0]][0].width,
                    self.x_positions[-1]
                    + 2 * min(cluster_widths),
                    # + 2 * self.clusters[self.x_positions[-1]][0].width,
                    )
                )
        self.y_min, self.y_max = None, None
        if y_pos == 'overwrite':
            # reset the vertical positions for each row
            for x_pos in self.x_positions:
                self.distribute_clusters(x_pos)
            for x_pos in self.x_positions:
                self._move_new_clusters(x_pos)
            for x_pos in self.x_positions:
                nbr_clusters = len(self.clusters[x_pos])
                for _ in range(nbr_clusters):
                    for i in range(1, nbr_clusters):
                        n1 = self.clusters[x_pos][nbr_clusters-i-1]
                        n2 = self.clusters[x_pos][nbr_clusters-i]
                        if self._swap_clusters(n1, n2, 'forwards'):
                            n2.set_y_pos(n1.y_pos)
                            n1.set_y_pos(
                                    n2.y_pos + n2.height +
                                    self.cluster_w_spacing
                                    )
                            self.clusters[x_pos][nbr_clusters-i] = n1
                            self.clusters[x_pos][nbr_clusters-i-1] = n2
        else:
            # TODO: keep and complement
            pass
        if isinstance(self.y_fix, dict):
            # TODO: allow to directly get the index given the cluster label
            for x_pos in self.y_fix:
                for st in self.y_fix[x_pos]:
                    n1_idx, n2_idx = (
                            i for i, l in enumerate(
                                map(
                                    lambda x: x.label,
                                    self.clusters[x_pos])
                                )
                            if l in st
                            )
                    self.clusters[
                            x_pos][n1_idx], self.clusters[
                                    x_pos][n2_idx] = self.clusters[
                                            x_pos][n2_idx], self.clusters[
                                                    x_pos][n1_idx]
                    self._distribute_column(x_pos, self.cluster_w_spacing)

        # positions are set
        self.y_lim = kwargs.get('y_lim', (self.y_min, self.y_max))
        # set the colors
        # TODO

        # now draw
        patch_collection = self.get_patchcollection(
            cluster_kwargs=self._cluster_kwargs,
            flux_kwargs=self._flux_kwargs
        )
        axes.add_collection(patch_collection)
        if self.with_cluster_labels:
            label_collection = self.get_labelcollection(**label_kwargs)
            if label_collection:
                for label in label_collection:
                    axes.annotate(**label)
        axes.set_xlim(
                *self.x_lim
                )
        axes.set_ylim(
                *self.y_lim
                )
        if self._fill_figure:
            axes.set_position(
                [
                    0.0,
                    self._x_axis_offset,
                    0.99,
                    1.0 - self._x_axis_offset
                ]
            )
        if self._invisible_y:
            axes.get_yaxis().set_visible(False)
        if self._invisible_x:
            axes.get_xaxis().set_visible(False)
        axes.spines['right'].set_color('none')
        axes.spines['left'].set_color('none')
        axes.spines['top'].set_color('none')
        axes.spines['bottom'].set_color('none')
        if isinstance(self.x_positions[0], datetime) and self.format_xaxis:
            self.set_dates_xaxis(axes, _minor_tick)

    def distribute_clusters(self, x_pos):
        r"""
        Distribute the clusters for a given x_position vertically

        Parameters
        -----------
        x_pos: float
          The horizontal position at which the clusters should be distributed.
          This must be a `key` of the :attr:`~.AlluvialPlot.clusters`
          attribute.
        """
        nbr_clusters = len(self.clusters[x_pos])
        if nbr_clusters:
            # sort clusters according to height
            _clusters = sorted(self.clusters[x_pos], key=lambda x: x.height)
            # sort so to put biggest height in the middle
            self.clusters[x_pos] = _clusters[::-2][::-1] + \
                _clusters[nbr_clusters % 2::2][::-1]
            # set positioning
            self._distribute_column(x_pos, self.cluster_w_spacing)
            # now sort again considering the fluxes.
            old_mid_heights = [
                    cluster.mid_height for cluster in self.clusters[x_pos]
                    ]
            # do the redistribution 4 times
            _redistribute = False
            for _ in range(self._redistribute_vertically):
                for cluster in self.clusters[x_pos]:
                    weights = []
                    positions = []
                    for in_flux in cluster.in_fluxes:
                        if in_flux.source_cluster is not None:
                            weights.append(in_flux.flux_width)
                            positions.append(in_flux.source_cluster.mid_height)
                    if sum(weights) > 0.0:
                        _redistribute = True
                        cluster.set_mid_height(
                                sum(
                                    [weights[i] * positions[i]
                                        for i in range(len(weights))]
                                    ) / sum(weights)
                                )
                if _redistribute:
                    sort_key = [
                        bisect_left(
                            old_mid_heights, self.clusters[x_pos][i].mid_height
                        ) for i in range(nbr_clusters)
                    ]
                    cs, _sort_key = zip(
                        *sorted(
                            zip(
                                list(range(nbr_clusters)),
                                sort_key,
                            ),
                            key=lambda x: x[1]
                        )
                    )
                    self.clusters[x_pos] = [
                        self.clusters[x_pos][_k] for _k in cs
                    ]
                    # redistribute them
                    self._distribute_column(x_pos, self.cluster_w_spacing)
                    old_mid_heights = [
                        cluster.mid_height for cluster in self.clusters[x_pos]
                    ]
                else:
                    break
            # perform pairwise swapping for backwards fluxes
            for _ in range(int(0.5 * nbr_clusters)):
                for i in range(1, nbr_clusters):
                    n1, n2 = self.clusters[x_pos][i-1], self.clusters[x_pos][i]
                    if self._swap_clusters(n1, n2, 'backwards'):
                        n2.set_y_pos(n1.y_pos)
                        n1.set_y_pos(
                                n2.y_pos + n2.height + self.cluster_w_spacing
                                )
                        self.clusters[x_pos][i-1] = n2
                        self.clusters[x_pos][i] = n1
            for _ in range(int(0.5 * nbr_clusters)):
                for i in range(1, nbr_clusters):
                    n1 = self.clusters[x_pos][nbr_clusters-i-1]
                    n2 = self.clusters[x_pos][nbr_clusters-i]
                    if self._swap_clusters(n1, n2, 'backwards'):
                        n2.set_y_pos(n1.y_pos)
                        n1.set_y_pos(
                                n2.y_pos + n2.height + self.cluster_w_spacing
                                )
                        self.clusters[x_pos][nbr_clusters-i-1] = n2
                        self.clusters[x_pos][nbr_clusters-i] = n1

            _min_y = min(
                    self.clusters[x_pos], key=lambda x: x.y_pos
                    ).y_pos - 2 * self.cluster_w_spacing
            _max_y_cluster = max(
                    self.clusters[x_pos],
                    key=lambda x: x.y_pos + x.height
                    )
            _max_y = _max_y_cluster.y_pos + \
                _max_y_cluster.height + 2 * self.cluster_w_spacing
            self.y_min = min(
                self.y_min,
                _min_y
            ) if self.y_min is not None else _min_y
            self.y_max = max(
                self.y_max,
                _max_y
            ) if self.y_max is not None else _max_y

    def set_dates_xaxis(self, ax, resolution='months'):
        r"""
        Format the x axis in case :class:`~datetime.datetime` objects are
        provide for the horizontal placement of clusters.

        Parameters
        -----------
        ax: :class:`~matplotlib.axes.Axes`
          Object to plot the alluvial diagram on.
        resolution: str (default='months')
          Possible values are ``'months'`` and ``'weeks'``.
          This determines the resolution of the minor ticks via
          :obj:`~matplotlib.axis.Axis.set_minor_formatter`.
          The major tick is then either given in years or months.

          .. todo::

            Include further options or allow passing parameters directly to
            :meth:`~matplotlib.axis.Axis.set_minor_formatter` and
            :meth:`~matplotlib.axis.Axis.set_major_formatter`.

        """
        import matplotlib.dates as mdates
        years = mdates.YearLocator()
        months = mdates.MonthLocator()
        weeks = mdates.WeekdayLocator(mdates.MONDAY)
        if resolution == 'months':
            monthsFmt = mdates.DateFormatter('%b')
            yearsFmt = mdates.DateFormatter('\n%Y')  # add space
            ax.xaxis.set_minor_locator(months)
            ax.xaxis.set_minor_formatter(monthsFmt)
            ax.xaxis.set_major_locator(years)
            ax.xaxis.set_major_formatter(yearsFmt)
        elif resolution == 'weeks':
            monthsFmt = mdates.DateFormatter('\n%b')
            weeksFmt = mdates.DateFormatter('%b %d')
            ax.xaxis.set_minor_locator(weeks)
            ax.xaxis.set_minor_formatter(weeksFmt)
            ax.xaxis.set_major_locator(months)
            ax.xaxis.set_major_formatter(monthsFmt)

    def _swap_clusters(self, n1, n2, direction='backwards'):
        squared_diff = {}
        for cluster in [n1, n2]:
            weights = []
            sqdiff = []
            if direction in ['both', 'backwards']:
                for in_flux in cluster.in_fluxes:
                    if in_flux.source_cluster is not None:
                        weights.append(in_flux.flux_width)
                        sqdiff.append(
                                abs(
                                    cluster.mid_height -
                                    in_flux.source_cluster.mid_height
                                    )
                                )
            if direction in ['both', 'forwards']:
                for out_flux in cluster.out_fluxes:
                    if out_flux.target_cluster is not None:
                        weights.append(out_flux.flux_width)
                        sqdiff.append(
                                abs(
                                    cluster.mid_height -
                                    out_flux.target_cluster.mid_height
                                    )
                                )
            if sum(weights) > 0.0:
                squared_diff[cluster] = sum(
                            [weights[i] * sqdiff[i]
                                for i in range(len(weights))]
                            ) / sum(weights)
        # inverse order and check again
        assert n1.y_pos < n2.y_pos
        inv_mid_height = {
            n1: n2.y_pos + n2.height + self.cluster_w_spacing
            + 0.5 * n1.height,
            n2: n1.y_pos + 0.5 * n2.height
            }
        squared_diff_inf = {}
        for cluster in [n1, n2]:
            weights = []
            sqdiff = []
            if direction in ['both', 'backwards']:
                for in_flux in cluster.in_fluxes:
                    if in_flux.source_cluster is not None:
                        weights.append(in_flux.flux_width)
                        sqdiff.append(
                                abs(
                                    inv_mid_height[cluster] -
                                    in_flux.source_cluster.mid_height
                                    )
                                )
            if direction in ['both', 'forwards']:
                for out_flux in cluster.out_fluxes:
                    if out_flux.target_cluster is not None:
                        weights.append(out_flux.flux_width)
                        sqdiff.append(
                                abs(
                                    inv_mid_height[cluster] -
                                    out_flux.target_cluster.mid_height
                                    )
                                )
            if sum(weights) > 0.0:
                squared_diff_inf[cluster] = sum(
                            [weights[i] * sqdiff[i]
                                for i in range(len(weights))]
                            ) / sum(weights)
        if sum(squared_diff.values()) > sum(squared_diff_inf.values()):
            return True
        else:
            return False

    def _move_new_clusters(self, x_pos):
        r"""
        This method redistributes fluxes without in-flux so to minimize the
        vertical displacement of out-fluxes.

        Parameters
        -----------
        x_pos: float
          The horizontal position where new clusters without in-flux should be
          distributed. This must be a `key` of the
          :attr:`~.AlluvialPlot.clusters` attribute.

        Once the clusters are distributed for all x positions this method
        redistributes within a given x_positions the clusters that have no
        influx but out fluxes. The clusters are moved closer (vertically) to
        the target clusters of the out flux(es).
        """
        old_mid_heights = [
                cluster.mid_height for cluster in self.clusters[x_pos]
                ]
        _redistribute = False
        for cluster in self.clusters[x_pos]:
            if sum([_flux.flux_width for _flux in cluster.in_fluxes]) == 0.0:
                weights = []
                positions = []
                for out_flux in cluster.out_fluxes:
                    if out_flux.target_cluster is not None:
                        weights.append(out_flux.flux_width)
                        positions.append(out_flux.target_cluster.mid_height)
                if sum(weights) > 0.0:
                    _redistribute = True
                    cluster.set_mid_height(
                            sum(
                                [weights[i] * positions[i]
                                    for i in range(len(weights))]
                                ) / sum(weights)
                            )
        if _redistribute:
            sort_key = [
                bisect_left(
                    old_mid_heights, self.clusters[x_pos][i].mid_height
                ) for i in range(len(self.clusters[x_pos]))
            ]
            cs, _sort_key = zip(
                *sorted(
                    zip(
                        list(range(len(self.clusters[x_pos]))),
                        sort_key,
                    ),
                    key=lambda x: x[1]
                )
            )
            self.clusters[x_pos] = [self.clusters[x_pos][_k] for _k in cs]
            # redistribute them
            self._distribute_column(x_pos, self.cluster_w_spacing)

    def get_patchcollection(
        self, match_original=True,
        cluster_kwargs={},
        flux_kwargs={},
        *args, **kwargs
    ):
        """
        Gather the patchcollection to add to the axes

        Parameter:
        ----------
        :param kwargs:
            Options:
        """
        cluster_patches = []
        fluxes = []
        for x_pos in self.x_positions:
            out_fluxes = []
            for cluster in self.clusters[x_pos]:
                # TODO: set color
                # _cluster_color
                cluster.set_y_pos(cluster.y_pos + self.y_offset)
                cluster_patches.append(
                            cluster.get_patch(
                                **cluster_kwargs
                                )
                        )
                # sort the fluxes for minimal overlap
                cluster.set_loc_out_fluxes()
                cluster.sort_in_fluxes()
                cluster.sort_out_fluxes()
                cluster.set_anchor_in_fluxes()
                cluster.set_anchor_out_fluxes()
                out_fluxes.extend(
                        cluster.out_fluxes
                        )
            fluxes.append(out_fluxes)
        flux_patches = []
        for out_fluxes in fluxes:
            for out_flux in out_fluxes:
                flux_patches.append(
                        out_flux.get_patch(
                            **flux_kwargs
                            )
                        )
        all_patches = []
        all_patches.extend(flux_patches)
        all_patches.extend(cluster_patches)
        return PatchCollection(
                all_patches,
                match_original=match_original,
                *args, **kwargs
                )

    def get_labelcollection(self, *args, **kwargs):
        h_margin = kwargs.pop('h_margin', None)
        v_margin = kwargs.pop('v_margin', None)
        if 'horizontalalignment' not in kwargs:
            kwargs['horizontalalignment'] = 'right'
        if 'verticalalignment' not in kwargs:
            kwargs['verticalalignment'] = 'bottom'
        cluster_labels = []
        for x_pos in self.x_positions:
            for cluster in self.clusters[x_pos]:
                _h_margin = h_margin
                _v_margin = v_margin
                if cluster.label_margin:
                    _h_margin, _v_margin = cluster.label_margin
                if cluster.label is not None:
                    # # Options (example):
                    # 'a polar annotation',
                    # xy=(thistheta, thisr),  # theta, radius
                    # xytext=(0.05, 0.05),    # fraction, fraction
                    # textcoords='figure fraction',
                    # arrowprops=dict(facecolor='black', shrink=0.05),
                    cluster_label = {
                            's': cluster.label,
                            'xy': (
                                cluster.x_pos - _h_margin,
                                cluster.y_pos + _v_margin
                                )
                            }
                    cluster_label.update(kwargs)
                    cluster_labels.append(cluster_label)
        return cluster_labels

    def _distribute_column(self, x_pos, cluster_w_spacing):
        displace = 0.0
        for cluster in self.clusters[x_pos]:
            cluster.set_y_pos(displace)
            displace += cluster.height + cluster_w_spacing
        # now offset to center
        low = self.clusters[x_pos][0].y_pos
        high = self.clusters[x_pos][-1].y_pos + self.clusters[x_pos][-1].height
        cent_offset = low + 0.5 * (high - low)
        # _h_clusters = 0.5 * len(clusters)
        # cent_idx = int(_h_clusters) - 1 \
        #     if _h_clusters.is_integer() \
        #     else int(_h_clusters)
        # cent_offest = clusters[cent_idx].mid_height
        for cluster in self.clusters[x_pos]:
            cluster.set_y_pos(cluster.y_pos - cent_offset)

    def color_clusters(self, patches, colormap=plt.cm.rainbow):
        r"""
        *unused*

        Parameters
        -----------
        patches: list[:class:`~matplotlib.patches.PathPatch`]
          Cluster patches to color.
        colormap: :obj:`matplotlib.cm` (default='rainbow')
          See the matplotlib tutorial for colormaps
          (`link <https://matplotlib.org/tutorials/colors/colormaps.html>`_)
          for details.

        """
        nbr_clusters = len(patches)
        c_iter = iter(colormap([i/nbr_clusters for i in range(nbr_clusters)]))
        for i in range(nbr_clusters):
            _color = next(c_iter)
            patches[i].set_facecolor(_color)
            patches[i].set_edgecolor(_color)
        return None
