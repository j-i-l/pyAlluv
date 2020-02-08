# -*- coding: utf-8 -*-


from matplotlib.path import Path
import matplotlib.patches as patches


class Cluster(object):
    r"""
    This class defines the cluster objects for an alluvial diagram.

    Note
    -----

    The vertical position of a cluster will be set when creating a
    :class:`~pyalluv.plotting.AlluvialPlot`.

    Parameters
    -----------

    height: float, int
      The cluster size which will translate into the height of this cluster.
    anchor: float (default=None)
      Set the anchor position. Either only the horizontal position, both
      :math:`(x, y)` or nothing can be provided.
    width: float (default=1.0)
      Set the cluster width.
    label: str (default=None)
      The label for this cluster, that can be shown in the diagram
    \**kwargs optional parameter:
      x_anchor: ``'center'``, ``'left'`` or ``'right'`` (default='center')
        Determine where the anchor position is relative to the rectangle
        that will represent this cluster. Options are either the left or
        right corner or centered:
      linewidth: float (default=0.0)
        Set the width of the line surrounding a cluster.
      label_margin: tuple(horizontal, vertical)
        Sets horizontal and vertical margins for the label of a cluster.

    Attributes
    -----------
    x_pos: float
      Horizontal position of the cluster anchor.
    y_pos: float
      Vertical position of the cluster center.
    x_anchor: str
      Anchor position relative to the rectangle representing the cluster.
      Possible values are: ``'center'``, ``'left'`` or ``'right'``.
    height: float
      Size of the cluster that will determine its height in the diagram.
    width: float
      Width of the cluster. In the same units as ``x_pos``.
    label: str
      Label, id or name of the cluster.
    in_fluxes: list[:class:`~pyalluv.fluxes.Flux`]
      All incoming fluxes of this cluster.
    out_fluxes: list[:class:`~pyalluv.fluxes.Flux`]
      All outgoing fluxes of this cluster.

    """
    def __init__(self, height, anchor=None, width=1.0, label=None, **kwargs):
        self._interp_steps = kwargs.pop('_interpolation_steps', 1)
        self.x_anchor = kwargs.pop('x_anchor', 'center')
        self.label = label
        self.label_margin = kwargs.pop('label_margin', None)
        self._closed = kwargs.pop('closed', False)
        self._readonly = kwargs.pop('readonly', False)
        self.patch_kwargs = kwargs
        self.patch_kwargs['lw'] = self.patch_kwargs.pop(
                'linewidth', self.patch_kwargs.pop('lw', 0.0)
                )
        if isinstance(height, (list, tuple)):
            self.height = len(height)
        else:
            self.height = height
        self.width = width
        if isinstance(anchor, (list, tuple)):
            x_coord, y_coord = anchor
        else:
            x_coord, y_coord = anchor, None
        self = self.set_x_pos(x_coord).set_y_pos(y_coord)

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
        r"""
        Set the horizontal position of a cluster.

        The position is set according to the value provided in ``x_pos`` and
        ``self.x_anchor``.

        Parameters
        -----------
        x_pos: float
          Horizontal position of the anchor for the cluster.

        Returns
        --------
        self: :class:`.Cluster`
          with new property ``x_pos``.

        """
        self.x_pos = x_pos
        if self.x_pos is not None:
            self.x_pos -= 0.5 * self.width
            if self.x_anchor == 'left':
                self.x_pos += 0.5 * self.width
            elif self.x_anchor == 'right':
                self.x_pos -= 0.5 * self.width

        return self

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
            in_loc = None
            out_loc = None
            if out_flux.target_cluster is not None:
                if self.mid_height > out_flux.target_cluster.mid_height:
                    # draw to top
                    if self.mid_height >= \
                            out_flux.target_cluster.in_['top'][1]:
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
                            out_flux.target_cluster.in_['bottom'][1]:
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
                key=lambda x: x[1].target_cluster.mid_height
                if x[1].target_cluster
                else -10000,
                reverse=True
                ))
        else:
            sorted_top_idx = []
        if _bottom_fluxes:
            sorted_bottom_idx, _fluxes_bottom = zip(*sorted(
                _bottom_fluxes,
                key=lambda x: x[1].target_cluster.mid_height
                if x[1].target_cluster
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
                key=lambda x: x[1].source_cluster.mid_height
                if x[1].source_cluster
                else -10000,
                reverse=True
                ))
        else:
            sorted_top_idx = []
        if _bottom_fluxes:
            sorted_bottom_idx, _fluxes_bottom = zip(*sorted(
                _bottom_fluxes,
                key=lambda x: x[1].source_cluster.mid_height
                if x[1].source_cluster
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

        return self

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
