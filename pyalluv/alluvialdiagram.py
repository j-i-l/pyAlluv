from __future__ import division, absolute_import, unicode_literals
from matplotlib.collections import PatchCollection
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as patches
from matplotlib.path import Path
from datetime import datetime
from bisect import bisect_left


class AlluvialPlot(object):
    def __init__(
        self, nodes, axes, y_pos='overwrite', node_w_spacing=1,
        node_kwargs={}, flux_kwargs={}, label_kwargs={},
        **kwargs
            ):
        """
        :param nodes: either a list of Node objects or a dict holding for each
            x position a list of nodes.
            If a dict is provided then the x position for each node is set
            to the key.
        :param axes: a `~matplotlib.axes.Axes` object to draw the Sankey plot
            on.
        :param y_pos: 'overwrite', 'keep', 'complement'
            'overwrite': ignores existing y coordinates for a node and
                determines the y position according to the fluxes.
            'keep': uses for each node the set y_pos. If a node has no y
                position set this raises an exception.
            'complement': uses the y position of each node, if set. If a node
                has no y position then it is determined relative to the other
                nodes.
        :param node_w_spacing: vertical spacing between nodes
        :param node_kwargs: dictionary styling the Path elements of nodes.
                Options:
                    facecolor, edgecolor, alpha, linewidth, ...
        :param flux_kwargs: dictionary styling the Path elements of fluxes.
                Options:
                    facecolor, edgecolor, alpha, linewidth, ...
        :param kwargs:
            Options:
                - x_lim: tuple
                - y_lim: tuple
                - set_x_pos: boolean if nodes is a dict then the key is set
                    for all nodes
                - node_width: (NOT IMPLEMENTED) overwrites width of all nodes
                - x_axis_offset: how much space (relative to total height)
                    should be reserved for the x_axis. If set to 0.0, then
                    the x labels will not be visible.
                - fill_figure: Boolean indicating whether or not set the
                    axis dimension to fill up the entire figure
                - invisible_x/invisible_y: booleans whether or not to draw
                    these axis.
                - y_fix: Dict with x_pos as keys and a list of tuples
                    (node labels) as values. The position of nodes (tuples)
                    are swapped.
        """
        # if the nodes are given in a list of lists (each list is a x position)
        self._set_x_pos = kwargs.get('set_x_pos', True)
        self._redistribute_vertically = kwargs.get(
            'redistribute_vertically',
            4
        )
        self.with_node_labels = kwargs.get('with_node_labels', True)
        self.format_xaxis = kwargs.get('format_xaxis', False)
        self._node_kwargs = node_kwargs
        self._flux_kwargs = flux_kwargs
        self._x_axis_offset = kwargs.get('x_axis_offset', 0.0)
        self._fill_figure = kwargs.get('fill_figure', False)
        self._invisible_y = kwargs.get('invisible_y', True)
        self._invisible_x = kwargs.get('invisible_x', False)
        self.y_fix = kwargs.get('y_fix', None)
        if isinstance(nodes, dict):
            self.nodes = nodes
        else:
            self.nodes = {}
            for node in nodes:
                try:
                    self.nodes[node.x_pos].append(node)
                except KeyError:
                    self.nodes[node.x_pos] = [node]
        self.x_positions = sorted(self.nodes.keys())
        # set the x positions correctly for the nodes
        if self._set_x_pos:
            for x_pos in self.x_positions:
                for node in self.nodes[x_pos]:
                    node.x_pos = x_pos
        self._x_dates = False
        _minor_tick = 'months'
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
            self.nodes = {
                    mdates.date2num(x_pos): self.nodes[x_pos]
                    for x_pos in self.x_positions
                    }
            self.x_positions = sorted(self.nodes.keys())
            for x_pos in self.x_positions:
                for node in self.nodes[x_pos]:
                    # in days (same as mdates.date2num)
                    node.width = node.width.total_seconds()/60/60/24
                    if node.label_margin is not None:
                        _h_margin = node.label_margin[
                                0].total_seconds()/60/60/24
                        node.label_margin = (
                                _h_margin, node.label_margin[1]
                                )
                    node.set_x_pos(mdates.date2num(node.x_pos))

        # TODO: set the node.width property with this
        self.node_width = kwargs.get('node_width', None)
        self.node_w_spacing = node_w_spacing
        self.x_lim = kwargs.get(
                'x_lim',
                (
                    self.x_positions[0]
                    - 2 * self.nodes[self.x_positions[0]][0].width,
                    self.x_positions[-1]
                    + 2 * self.nodes[self.x_positions[-1]][0].width,
                    )
                )
        self.y_min, self.y_max = None, None
        if y_pos == 'overwrite':
            # reset the vertical positions for each row
            for x_pos in self.x_positions:
                self.distribute_nodes(x_pos)
            for x_pos in self.x_positions:
                self.move_new_nodes(x_pos)
            for x_pos in self.x_positions:
                nbr_nodes = len(self.nodes[x_pos])
                for _ in range(nbr_nodes):
                    for i in range(1, nbr_nodes):
                        n1 = self.nodes[x_pos][nbr_nodes-i-1]
                        n2 = self.nodes[x_pos][nbr_nodes-i]
                        if self._swap_nodes(n1, n2, 'forwards'):
                            n2.set_y_pos(n1.y_pos)
                            n1.set_y_pos(
                                    n2.y_pos + n2.height + self.node_w_spacing
                                    )
                            self.nodes[x_pos][nbr_nodes-i] = n1
                            self.nodes[x_pos][nbr_nodes-i-1] = n2
        else:
            # TODO: keep and complement
            pass
        if isinstance(self.y_fix, dict):
            # TODO: allow to directly get the index given the node label
            for x_pos in self.y_fix:
                for st in self.y_fix[x_pos]:
                    n1_idx, n2_idx = (
                            i for i, l in enumerate(
                                map(
                                    lambda x: x.label,
                                    self.nodes[x_pos])
                                )
                            if l in st
                            )
                    self.nodes[
                            x_pos][n1_idx], self.nodes[
                                    x_pos][n2_idx] = self.nodes[
                                            x_pos][n2_idx], self.nodes[
                                                    x_pos][n1_idx]
                    self._distribute_column(x_pos, self.node_w_spacing)

        # positions are set
        self.y_lim = kwargs.get('y_lim', (self.y_min, self.y_max))
        # set the colors
        # TODO

        # now draw
        patch_collection = self.get_patchcollection(
            node_kwargs=self._node_kwargs,
            flux_kwargs=self._flux_kwargs
        )
        axes.add_collection(patch_collection)
        if self.with_node_labels:
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
        if self.format_xaxis:  # self._x_dates:
            # set dates as x-axis
            self.set_dates_xaxis(axes, _minor_tick)

    def distribute_nodes(self, x_pos):
        """
        Distribute the nodes for a given x_position vertically
        """
        nbr_nodes = len(self.nodes[x_pos])
        # sort nodes according to height
        _nodes = sorted(self.nodes[x_pos], key=lambda x: x.height)
        # sort so to put biggest height in the middle
        self.nodes[x_pos] = _nodes[::-2][::-1] + \
            _nodes[nbr_nodes % 2::2][::-1]
        # set positioning
        self._distribute_column(x_pos, self.node_w_spacing)
        # now sort again considering the fluxes.
        old_mid_heights = [node.mid_height for node in self.nodes[x_pos]]
        # do the redistribution 4 times
        _redistribute = False
        for _ in range(self._redistribute_vertically):
            for node in self.nodes[x_pos]:
                weights = []
                positions = []
                for in_flux in node.in_fluxes:
                    if in_flux.source_node is not None:
                        weights.append(in_flux.flux_width)
                        positions.append(in_flux.source_node.mid_height)
                if sum(weights) > 0.0:
                    _redistribute = True
                    node.set_mid_height(
                            sum(
                                [weights[i] * positions[i]
                                    for i in range(len(weights))]
                                ) / sum(weights)
                            )
            if _redistribute:
                sort_key = [
                    bisect_left(
                        old_mid_heights, self.nodes[x_pos][i].mid_height
                    ) for i in range(nbr_nodes)
                ]
                cs, _sort_key = zip(
                    *sorted(
                        zip(
                            list(range(nbr_nodes)),
                            sort_key,
                        ),
                        key=lambda x: x[1]
                    )
                )
                self.nodes[x_pos] = [self.nodes[x_pos][_k] for _k in cs]
                # redistribute them
                self._distribute_column(x_pos, self.node_w_spacing)
                old_mid_heights = [
                    node.mid_height for node in self.nodes[x_pos]
                ]
            else:
                break
        # perform pairwise swapping for backwards fluxes
        for _ in range(int(0.5 * nbr_nodes)):
            for i in range(1, nbr_nodes):
                n1, n2 = self.nodes[x_pos][i-1], self.nodes[x_pos][i]
                if self._swap_nodes(n1, n2, 'backwards'):
                    n2.set_y_pos(n1.y_pos)
                    n1.set_y_pos(
                            n2.y_pos + n2.height + self.node_w_spacing
                            )
                    self.nodes[x_pos][i-1], self.nodes[x_pos][i] = n2, n1
        for _ in range(int(0.5 * nbr_nodes)):
            for i in range(1, nbr_nodes):
                n1 = self.nodes[x_pos][nbr_nodes-i-1]
                n2 = self.nodes[x_pos][nbr_nodes-i]
                if self._swap_nodes(n1, n2, 'backwards'):
                    n2.set_y_pos(n1.y_pos)
                    n1.set_y_pos(
                            n2.y_pos + n2.height + self.node_w_spacing
                            )
                    self.nodes[x_pos][nbr_nodes-i-1] = n2
                    self.nodes[x_pos][nbr_nodes-i] = n1

        _min_y = min(
                self.nodes[x_pos], key=lambda x: x.y_pos
                ).y_pos - 2 * self.node_w_spacing
        _max_y_node = max(
                self.nodes[x_pos],
                key=lambda x: x.y_pos + x.height
                )
        _max_y = _max_y_node.y_pos + \
            _max_y_node.height + 2 * self.node_w_spacing
        self.y_min = min(
            self.y_min,
            _min_y
        ) if self.y_min is not None else _min_y
        self.y_max = max(
            self.y_max,
            _max_y
        ) if self.y_max is not None else _max_y

    def set_dates_xaxis(self, ax, resolution='months'):
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

    def _swap_nodes(self, n1, n2, direction='backwards'):
        squared_diff = {}
        for node in [n1, n2]:
            weights = []
            sqdiff = []
            if direction in ['both', 'backwards']:
                for in_flux in node.in_fluxes:
                    if in_flux.source_node is not None:
                        weights.append(in_flux.flux_width)
                        sqdiff.append(
                                abs(
                                    node.mid_height -
                                    in_flux.source_node.mid_height
                                    )
                                )
            if direction in ['both', 'forwards']:
                for out_flux in node.out_fluxes:
                    if out_flux.target_node is not None:
                        weights.append(out_flux.flux_width)
                        sqdiff.append(
                                abs(
                                    node.mid_height -
                                    out_flux.target_node.mid_height
                                    )
                                )
            if sum(weights) > 0.0:
                squared_diff[node] = sum(
                            [weights[i] * sqdiff[i]
                                for i in range(len(weights))]
                            ) / sum(weights)
        # inverse order and check again
        assert n1.y_pos < n2.y_pos
        inv_mid_height = {
            n1: n2.y_pos + n2.height + self.node_w_spacing + 0.5 * n1.height,
            n2: n1.y_pos + 0.5 * n2.height
            }
        squared_diff_inf = {}
        for node in [n1, n2]:
            weights = []
            sqdiff = []
            if direction in ['both', 'backwards']:
                for in_flux in node.in_fluxes:
                    if in_flux.source_node is not None:
                        weights.append(in_flux.flux_width)
                        sqdiff.append(
                                abs(
                                    inv_mid_height[node] -
                                    in_flux.source_node.mid_height
                                    )
                                )
            if direction in ['both', 'forwards']:
                for out_flux in node.out_fluxes:
                    if out_flux.target_node is not None:
                        weights.append(out_flux.flux_width)
                        sqdiff.append(
                                abs(
                                    inv_mid_height[node] -
                                    out_flux.target_node.mid_height
                                    )
                                )
            if sum(weights) > 0.0:
                squared_diff_inf[node] = sum(
                            [weights[i] * sqdiff[i]
                                for i in range(len(weights))]
                            ) / sum(weights)
        if sum(squared_diff.values()) > sum(squared_diff_inf.values()):
            return True
        else:
            return False

    def move_new_nodes(self, x_pos):
        """
        Once the nodes are distributed for all x positions this method
        redistributes within a given x_positions the nodes that have no
        influx but out fluxes. The nodes are moved closer (vertically) to
        the target nodes of the out flux(es).
        """
        old_mid_heights = [node.mid_height for node in self.nodes[x_pos]]
        _redistribute = False
        for node in self.nodes[x_pos]:
            if sum([_flux.flux_width for _flux in node.in_fluxes]) == 0.0:
                weights = []
                positions = []
                for out_flux in node.out_fluxes:
                    if out_flux.target_node is not None:
                        weights.append(out_flux.flux_width)
                        positions.append(out_flux.target_node.mid_height)
                if sum(weights) > 0.0:
                    _redistribute = True
                    node.set_mid_height(
                            sum(
                                [weights[i] * positions[i]
                                    for i in range(len(weights))]
                                ) / sum(weights)
                            )
        if _redistribute:
            sort_key = [
                bisect_left(
                    old_mid_heights, self.nodes[x_pos][i].mid_height
                ) for i in range(len(self.nodes[x_pos]))
            ]
            cs, _sort_key = zip(
                *sorted(
                    zip(
                        list(range(len(self.nodes[x_pos]))),
                        sort_key,
                    ),
                    key=lambda x: x[1]
                )
            )
            self.nodes[x_pos] = [self.nodes[x_pos][_k] for _k in cs]
            # redistribute them
            self._distribute_column(x_pos, self.node_w_spacing)

    def get_patchcollection(
        self, match_original=True,
        node_kwargs={},
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
        node_patches = []
        fluxes = []
        for x_pos in self.x_positions:
            out_fluxes = []
            for node in self.nodes[x_pos]:
                # TODO: set color
                # _node_color
                node_patches.append(
                            node.get_patch(
                                **node_kwargs
                                )
                        )
                # sort the fluxes for minimal overlap
                node.set_loc_out_fluxes()
                node.sort_in_fluxes()
                node.sort_out_fluxes()
                node.set_anchor_in_fluxes()
                node.set_anchor_out_fluxes()
                out_fluxes.extend(
                        node.out_fluxes
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
        all_patches.extend(node_patches)
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
        node_labels = []
        for x_pos in self.x_positions:
            for node in self.nodes[x_pos]:
                _h_margin = h_margin
                _v_margin = v_margin
                if node.label_margin:
                    _h_margin, _v_margin = node.label_margin
                if node.label is not None:
                    # # Options (example):
                    # 'a polar annotation',
                    # xy=(thistheta, thisr),  # theta, radius
                    # xytext=(0.05, 0.05),    # fraction, fraction
                    # textcoords='figure fraction',
                    # arrowprops=dict(facecolor='black', shrink=0.05),
                    node_label = {
                            's': node.label,
                            'xy': (
                                node.x_pos - _h_margin,
                                node.y_pos + _v_margin
                                )
                            }
                    node_label.update(kwargs)
                    node_labels.append(node_label)
        return node_labels

    def _distribute_column(self, x_pos, node_w_spacing):
        displace = 0.0
        for node in self.nodes[x_pos]:
            node.set_y_pos(displace)
            displace += node.height + node_w_spacing
        # now offset to center
        low = self.nodes[x_pos][0].y_pos
        high = self.nodes[x_pos][-1].y_pos + self.nodes[x_pos][-1].height
        cent_offset = low + 0.5 * (high - low)
        # _h_nodes = 0.5 * len(nodes)
        # cent_idx = int(_h_nodes) - 1 \
        #     if _h_nodes.is_integer() \
        #     else int(_h_nodes)
        # cent_offest = nodes[cent_idx].mid_height
        for node in self.nodes[x_pos]:
            node.set_y_pos(node.y_pos - cent_offset)

    def color_nodes(self, _patches, colormap=plt.cm.rainbow):
        nbr_nodes = len(_patches)
        c_iter = iter(colormap([i/nbr_nodes for i in range(nbr_nodes)]))
        for i in range(nbr_nodes):
            _color = next(c_iter)
            _patches[i].set_facecolor(_color)
            _patches[i].set_edgecolor(_color)
        return None


class Node(object):
    def __init__(self, height, anchor=None, width=1, **kwargs):
        """
        Parameter:
        ----------

        You either need to set the
        :param kwargs: Possible are:
            x_anchor: 'center'(default), 'left', 'right'
            facecolors
            edgecolors
            linewidths
            linestyles
            antialiaseds
            label: node label
            label_margin: (horizontal, vertical)

        """
        self._interp_steps = kwargs.pop('_interpolation_steps', 1)
        self.x_anchor = kwargs.pop('x_anchor', 'center')
        self.label = kwargs.pop('label', None)
        self.label_margin = kwargs.pop('label_margin', None)
        self._closed = kwargs.pop('closed', False)
        self._readonly = kwargs.pop('readonly', False)
        self.patch_kwargs = kwargs
        if isinstance(height, (list, tuple)):
            self.height = len(height)
            self.elements = height
        else:
            self.height = height
            self.elements = None
        self.width = width
        if isinstance(anchor, (list, tuple)):
            self.set_x_pos(anchor[0])
            self.set_y_pos(anchor[1])
        else:
            self.set_x_pos(anchor)
            self.set_y_pos(None)

        # init the in and out fluxes:
        self.out_fluxes = []
        self.in_fluxes = []
        self.in_margin = {
                'bottom': 0,
                'top': 0
                }
        self.out_margin = {
                'bottom': 0,
                'top': 0}

        # ref points to add fluxes
        self.in_ = None
        self.out_ = None

    def set_x_pos(self, x_pos):
        self.x_pos = x_pos
        if self.x_pos is not None:
            if self.x_anchor == 'center':
                self.x_pos -= 0.5 * self.width
            elif self.x_anchor == 'right':
                self.x_pos -= self.width

    def get_patch(self, **kwargs):
        _kwargs = dict(kwargs)
        _kwargs.update(self.patch_kwargs)
        self.set_in_out_anchors()

        vertices = [
                (self.x_pos, self.y_pos),
                (self.x_pos, self.y_pos + self.height),
                (self.x_pos + self.width, self.y_pos + self.height),
                (self.x_pos + self.width, self.y_pos),
                # this is just ignored as the code is CLOSEPOLY
                (self.x_pos, self.y_pos)
                ]
        codes = [
                Path.MOVETO,
                Path.LINETO,
                Path.LINETO,
                Path.LINETO,
                Path.CLOSEPOLY
                ]

        return patches.PathPatch(
                Path(
                    vertices,
                    codes,
                    self._interp_steps,
                    self._closed,
                    self._readonly
                    ),
                **_kwargs
                )

    def set_loc_out_fluxes(self,):
        for out_flux in self.out_fluxes:
            # TODO: if self.elements is not None, pin each element to its
            # position in the node. In location of the out flux does not
            # need to change.
            in_loc = None
            out_loc = None
            if out_flux.target_node is not None:
                if self.mid_height > out_flux.target_node.mid_height:
                    # draw to top
                    if self.mid_height >= \
                            out_flux.target_node.in_['top'][1]:
                        # draw from bottom to in top
                        out_loc = 'bottom'
                        in_loc = 'top'
                    else:
                        # draw from top to top
                        out_loc = 'top'
                        in_loc = 'top'
                else:
                    # draw to bottom
                    if self.mid_height <= \
                            out_flux.target_node.in_['bottom'][1]:
                        # draw from top to bottom
                        out_loc = 'top'
                        in_loc = 'bottom'
                    else:
                        # draw form bottom to bottom
                        out_loc = 'bottom'
                        in_loc = 'bottom'
            else:
                out_flux.out_loc = out_flux.out_flux_vanish
            out_flux.in_loc = in_loc
            out_flux.out_loc = out_loc

    def sort_out_fluxes(self,):
        _top_fluxes = [
                (i, self.out_fluxes[i])
                for i in range(len(self.out_fluxes))
                if self.out_fluxes[i].out_loc == 'top'
                ]
        _bottom_fluxes = [
                (i, self.out_fluxes[i])
                for i in range(len(self.out_fluxes))
                if self.out_fluxes[i].out_loc == 'bottom'
                ]
        if _top_fluxes:
            sorted_top_idx, _fluxes_top = zip(*sorted(
                _top_fluxes,
                key=lambda x: x[1].target_node.mid_height
                if x[1].target_node
                else -10000,
                reverse=True
                ))
        else:
            sorted_top_idx = []
        if _bottom_fluxes:
            sorted_bottom_idx, _fluxes_bottom = zip(*sorted(
                _bottom_fluxes,
                key=lambda x: x[1].target_node.mid_height
                if x[1].target_node
                else -10000,
                reverse=False
                ))
        else:
            sorted_bottom_idx = []
        sorted_idx = list(sorted_top_idx) + list(sorted_bottom_idx)
        self.out_fluxes = [self.out_fluxes[i] for i in sorted_idx]

    def sort_in_fluxes(self,):
        _top_fluxes = [
                (i, self.in_fluxes[i])
                for i in range(len(self.in_fluxes))
                if self.in_fluxes[i].in_loc == 'top'
                ]
        _bottom_fluxes = [
                (i, self.in_fluxes[i])
                for i in range(len(self.in_fluxes))
                if self.in_fluxes[i].in_loc == 'bottom'
                ]
        if _top_fluxes:
            sorted_top_idx, _fluxes_top = zip(*sorted(
                _top_fluxes,
                key=lambda x: x[1].source_node.mid_height
                if x[1].source_node
                else -10000,
                reverse=True
                ))
        else:
            sorted_top_idx = []
        if _bottom_fluxes:
            sorted_bottom_idx, _fluxes_bottom = zip(*sorted(
                _bottom_fluxes,
                key=lambda x: x[1].source_node.mid_height
                if x[1].source_node
                else -10000,
                reverse=False
                ))
        else:
            sorted_bottom_idx = []
        sorted_idx = list(sorted_top_idx) + list(sorted_bottom_idx)
        self.in_fluxes = [self.in_fluxes[i] for i in sorted_idx]

    def get_loc_out_flux(self, flux_width, out_loc, in_loc):
        anchor_out = (
            self.out_[
                out_loc][0],
            self.out_[out_loc][1] +
            self.out_margin[out_loc] +
            (flux_width if in_loc == 'bottom' else 0)
            )
        top_out = (
            self.out_[
                out_loc][0],
            self.out_[out_loc][1] +
            self.out_margin[out_loc] +
            (flux_width if in_loc == 'top' else 0)
            )
        self.out_margin[out_loc] += flux_width
        return anchor_out, top_out

    def set_anchor_out_fluxes(self,):
        for out_flux in self.out_fluxes:
            out_width = out_flux.flux_width \
                    if out_flux.out_loc == 'bottom' else - out_flux.flux_width
            out_flux.anchor_out, out_flux.top_out = self.get_loc_out_flux(
                    out_width, out_flux.out_loc, out_flux.in_loc
                    )

    def set_anchor_in_fluxes(self,):
        for in_flux in self.in_fluxes:
            in_width = in_flux.flux_width \
                    if in_flux.in_loc == 'bottom' else - in_flux.flux_width
            in_flux.anchor_in, in_flux.top_in = self.get_loc_in_flux(
                    in_width, in_flux.out_loc, in_flux.in_loc
                    )

    def get_loc_in_flux(self, flux_width, out_loc, in_loc):
        anchor_in = (
            self.in_[
                in_loc][0],
            self.in_[in_loc][1] +
            self.in_margin[in_loc] +
            (flux_width if out_loc == 'bottom' else 0)
            )
        top_in = (
            self.in_[
                in_loc][0],
            self.in_[in_loc][1] +
            self.in_margin[in_loc] +
            (flux_width if out_loc == 'top' else 0)
            )
        self.in_margin[in_loc] += flux_width
        return anchor_in, top_in

    def set_mid_height(self, mid_height):
        self.mid_height = mid_height
        if self.mid_height is not None:
            self.y_pos = self.mid_height - 0.5 * self.height
            self.set_in_out_anchors()
        else:
            self.y_pos = None

    def set_y_pos(self, y_pos):
        self.y_pos = y_pos
        if self.y_pos is not None:
            self.mid_height = self.y_pos + 0.5 * self.height
            self.set_in_out_anchors()
        else:
            self.mid_height = None

    def set_in_out_anchors(self,):
        """
        This sets the proper anchor points for fluxes to enter/leave
        """
        # if self.y_pos is None or self.mid_height is None:
        #     self.set_y_pos()

        self.in_ = {
                'bottom': (self.x_pos, self.y_pos),  # left, bottom
                'top': (self.x_pos, self.y_pos + self.height)  # left, top
                }
        self.out_ = {
                # right, top
                'top': (self.x_pos + self.width, self.y_pos + self.height),
                'bottom': (self.x_pos + self.width, self.y_pos)  # right,bottom
        }


class Flux(object):
    def __init__(
            self, flux,
            source_node=None, target_node=None,
            relative_flux=False,
            **kwargs):
        """
        Parameter:
        ----------
        :param relative_flux: If true then the fraction of the height of the
            source_node is taken, if the source_node is none, then the
            relative height form the target_node is taken.

        :param kwargs: Possible are:
            out_flux_vanish: location ('top', 'bottom') where the vanishing
                out flux should be positioned, default is 'top'
            For the Path object:
                interpolation_steps
                closed
                readonly
            facecolors
            edgecolors
            linewidths
            linestyles
            antialiaseds
        """
        self._interp_steps = kwargs.pop('interpolation_steps', 1)
        self.out_flux_vanish = kwargs.pop('out_flux_vanish', 'top')
        self.default_fc = kwargs.pop('default_fc', 'gray')
        self.default_ec = kwargs.pop('default_ec', 'gray')
        self.default_alpha = kwargs.pop('default_alpha', 0.4)
        self.closed = kwargs.pop('closed', False)
        self.readonly = kwargs.pop('readonly', False)
        self.patch_kwargs = kwargs

        if isinstance(flux, (list, tuple)):
            self.flux = len(flux)
            self.elements = flux
        else:
            self.flux = flux
            self.elements = None
        self.relative_flux = relative_flux
        self.source_node = source_node
        self.target_node = target_node
        if self.source_node is not None:
            if self.relative_flux:
                self.flux_width = self.flux * self.source_node.height
            else:
                self.flux_width = self.flux
        else:
            if self.target_node is not None:
                if self.relative_flux:
                    self.flux_width = self.flux * self.target_node.height
                else:
                    self.flux_width = self.flux
        # append the flux to the nodes
        if self.source_node is not None:
            self.source_node.out_fluxes.append(self)
        if self.target_node is not None:
            self.target_node.in_fluxes.append(self)

    def get_patch(self, **kwargs):
        _kwargs = dict(kwargs)
        _to_in_kwargs = {}
        _to_out_kwargs = {}
        for kw in _kwargs:
            if kw.startswith('in_'):
                _to_in_kwargs[kw[3:]] = _kwargs.pop(kw)
            elif kw.startswith('out_'):
                _to_out_kwargs[kw[3:]] = _kwargs.pop(kw)
        # update with Flux specific styling
        _kwargs.update(self.patch_kwargs)
        for _color in ['facecolor', 'edgecolor']:
            _set_color = _kwargs.pop(_color, None)
            if _set_color == 'source_node' or _set_color == 'node':
                _kwargs[_color] = self.source_node.patch_kwargs.get(
                    _color, None
                )
            elif _set_color == 'target_node':
                _kwargs[_color] = self.target_node.patch_kwargs.get(
                    _color, None
                )
            # set it back
            else:
                _kwargs[_color] = _set_color
                if _set_color is None:
                    if _color == 'facecolor':
                        _kwargs[_color] = self.default_fc
                    elif _color == 'edgecolor':
                        _kwargs[_color] = self.default_ec
        _kwargs['alpha'] = _kwargs.get('alpha', self.default_alpha)
        # set in/out only flux styling
        _in_kwargs = dict(_kwargs)
        _in_kwargs.update(_to_in_kwargs)
        _out_kwargs = dict(_kwargs)
        _out_kwargs.update(_to_out_kwargs)

        _dist = None
        if self.out_loc is not None:
            if self.in_loc is not None:
                _dist = 2/3 * (
                        self.target_node.in_['bottom'][0] -
                        self.source_node.out_['bottom'][0]
                        )
            else:
                _dist = 2 * self.source_node.width
                _kwargs = _out_kwargs
        else:
            if self.in_loc is not None:
                _kwargs = _in_kwargs
            else:
                raise Exception('Flux with neither source nor target node')

        # now complete the path points
        if self.anchor_out is not None:
            anchor_out_inner = (
                self.anchor_out[0] - 0.5 * self.source_node.width,
                self.anchor_out[1]
            )
            dir_out_anchor = (self.anchor_out[0] + _dist, self.anchor_out[1])
        else:
            # TODO set to form vanishing flux
            # anchor_out = anchor_out_inner =
            # dir_out_anchor =
            pass
        if self.top_out is not None:
            top_out_inner = (
                self.top_out[0] - 0.5 * self.source_node.width,
                self.top_out[1]
            )
            # 2nd point 2/3 of distance between nodes
            dir_out_top = (self.top_out[0] + _dist, self.top_out[1])
        else:
            # TODO set to form vanishing flux
            # top_out = top_out_inner =
            # dir_out_top =
            pass
        if self.anchor_in is not None:
            anchor_in_inner = (
                self.anchor_in[0] + 0.5 * self.target_node.width,
                self.anchor_in[1]
            )
            dir_in_anchor = (self.anchor_in[0] - _dist, self.anchor_in[1])
        else:
            # TODO set to form new in flux
            # anchor_in = anchor_in_inner =
            # dir_in_anchor =
            pass
        if self.top_in is not None:
            top_in_inner = (
                self.top_in[0] + 0.5 * self.target_node.width,
                self.top_in[1]
            )
            dir_in_top = (self.top_in[0] - _dist, self.top_in[1])
        else:
            # TODO set to form new in flux
            # top_in = top_in_inner =
            # dir_in_top =
            pass

        vertices = [
                self.anchor_out,
                dir_out_anchor, dir_in_anchor, self.anchor_in,
                anchor_in_inner, top_in_inner, self.top_in,
                dir_in_top, dir_out_top, self.top_out,
                top_out_inner, anchor_out_inner,
                self.anchor_out
                ]
        codes = [
                Path.MOVETO,
                Path.CURVE4, Path.CURVE4, Path.CURVE4,
                Path.LINETO, Path.LINETO, Path.LINETO,
                Path.CURVE4, Path.CURVE4, Path.CURVE4,
                Path.LINETO, Path.LINETO,
                Path.CLOSEPOLY
                ]
        _path = Path(
                vertices, codes,
                self._interp_steps,
                self.closed,
                self.readonly
                )

        flux_patch = patches.PathPatch(
                _path, **_kwargs
                )
        return flux_patch
