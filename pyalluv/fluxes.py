# -*- coding: utf-8 -*-


from matplotlib.path import Path
import matplotlib.patches as patches


class Flux(object):
    r"""

    Parameters
    -----------
    relative_flux: bool
      If ``True`` the fraction of the height of parameter `source_cluster`
      is taken, if the source_cluster is none, then the
      relative height form the target_cluster is taken.
    source_cluster: :class:`pyalluv.clusters.Cluster` (default=None)
      Cluster from which the flux originates.
    target_cluster: :class:`pyalluv.clusters.Cluster` (default=None)
      Cluster into which the flux leads.
    \**kwargs optional parameter:
      interpolation_steps:

      out_flux_vanish: str (default='top')

      default_fc: (default='gray')

      default_ec: (default='gray')

      default_alpha: int (default=0.3)

      closed
      readonly
      facecolors
      edgecolors
      linewidths
      linestyles
      antialiaseds

    Attributes
    -----------

    flux: float
      The size of the flux which will translate to the height of the flux in
      the Alluvial diagram.
    source_cluster: :class:`pyalluv.clusters.Cluster` (default=None)
      Cluster from which the flux originates.
    target_cluster: :class:`pyalluv.clusters.Cluster` (default=None)
      Cluster into which the flux leads.
    """
    def __init__(
            self, flux,
            source_cluster=None, target_cluster=None,
            relative_flux=False,
            **kwargs):
        self._interp_steps = kwargs.pop('interpolation_steps', 1)
        self.out_flux_vanish = kwargs.pop('out_flux_vanish', 'top')
        self.default_fc = kwargs.pop('default_fc', 'gray')
        self.default_ec = kwargs.pop('default_ec', 'gray')
        self.default_alpha = kwargs.pop('default_alpha', 0.3)
        # self.default_alpha = kwargs.pop(
        #         'default_alpha',
        #         kwargs.get('alpha', {}).pop('default', 0.3)
        #         )
        self.closed = kwargs.pop('closed', False)
        self.readonly = kwargs.pop('readonly', False)
        self.patch_kwargs = kwargs
        self.patch_kwargs['lw'] = self.patch_kwargs.pop(
                'linewidth', self.patch_kwargs.pop('lw', 0.0)
                )

        if isinstance(flux, (list, tuple)):
            self.flux = len(flux)
        else:
            self.flux = flux
        self.relative_flux = relative_flux
        self.source_cluster = source_cluster
        self.target_cluster = target_cluster
        if self.source_cluster is not None:
            if self.relative_flux:
                self.flux_width = self.flux * self.source_cluster.height
            else:
                self.flux_width = self.flux
        else:
            if self.target_cluster is not None:
                if self.relative_flux:
                    self.flux_width = self.flux * self.target_cluster.height
                else:
                    self.flux_width = self.flux
        # append the flux to the clusters
        if self.source_cluster is not None:
            self.source_cluster.out_fluxes.append(self)
        if self.target_cluster is not None:
            self.target_cluster.in_fluxes.append(self)

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
            _set_alpha = _kwargs.pop('alpha', None)
            if isinstance(_set_alpha, (int, float)):
                _kwargs['alpha'] = _set_alpha
                _set_alpha = None
            color_is_set = False
            if _set_color == 'source_cluster' or _set_color == 'cluster':
                from_cluster = self.source_cluster
                color_is_set = True
            elif _set_color == 'target_cluster':
                from_cluster = self.target_cluster
                color_is_set = True
            elif isinstance(_set_color, str) and '__' in _set_color:
                which_cluster, flow_type = _set_color.split('__')
                if which_cluster == 'target_cluster':
                    from_cluster = self.target_cluster
                else:
                    from_cluster = self.source_cluster
                if flow_type == 'migration' \
                        and self.source_cluster.patch_kwargs.get(_color) \
                        != self.target_cluster.patch_kwargs.get(_color):
                    color_is_set = True
                    if _set_alpha:
                        _kwargs['alpha'] = _set_alpha.get(
                                'migration', _set_alpha.get(
                                    'default',
                                    self.default_alpha
                                    )
                                )
                elif flow_type == 'reside'  \
                        and self.source_cluster.patch_kwargs.get(_color) \
                        == self.target_cluster.patch_kwargs.get(_color):
                    color_is_set = True
                    if _set_alpha:
                        _kwargs['alpha'] = _set_alpha.get(
                                'reside', _set_alpha.get(
                                    'default',
                                    self.default_alpha
                                    )
                                )
                else:
                    _set_color = None
            if color_is_set:
                _kwargs[_color] = from_cluster.patch_kwargs.get(
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
                if _set_alpha:
                    _kwargs['alpha'] = _set_alpha.get(
                            'default',
                            self.default_alpha
                            )
        # line below is probably not needed as alpha is set with the color
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
                        self.target_cluster.in_['bottom'][0] -
                        self.source_cluster.out_['bottom'][0]
                        )
            else:
                _dist = 2 * self.source_cluster.width
                _kwargs = _out_kwargs
        else:
            if self.in_loc is not None:
                _kwargs = _in_kwargs
            else:
                raise Exception('Flux with neither source nor target cluster')

        # now complete the path points
        if self.anchor_out is not None:
            anchor_out_inner = (
                self.anchor_out[0] - 0.5 * self.source_cluster.width,
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
                self.top_out[0] - 0.5 * self.source_cluster.width,
                self.top_out[1]
            )
            # 2nd point 2/3 of distance between clusters
            dir_out_top = (self.top_out[0] + _dist, self.top_out[1])
        else:
            # TODO set to form vanishing flux
            # top_out = top_out_inner =
            # dir_out_top =
            pass
        if self.anchor_in is not None:
            anchor_in_inner = (
                self.anchor_in[0] + 0.5 * self.target_cluster.width,
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
                self.top_in[0] + 0.5 * self.target_cluster.width,
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
