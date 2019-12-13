from copy import deepcopy
from matplotlib import pyplot as plt
import matplotlib.gridspec as gridspec

from pyalluv import AlluvialPlot, Cluster, Flux

# Create the sequence of clusterings
time_points = [0, 4, 9, 14, 18.2]
# Define the cluster sizes per snapshot
# at each time point {cluster_id: cluster_size})
cluster_sizes = [{0: 3}, {0: 5}, {0: 3, 1: 2}, {0: 5}, {0: 4}]
# Define the membership fluxes between neighbouring clusterings
between_fluxes = [
        {(0, 0): 3},  # key: (from cluster, to cluster), value: size
        {(0, 0): 3, (0, 1): 2},
        {(0, 0): 3, (1, 0): 2},
        {(0, 0): 4}
        ]

# set the colors
cluster_color = {0: "C1", 1: "C2"}
# create a dictionary with the time points as keys and a list of clusters
# as values
clustering_sequence = {}
for tp, clustering in enumerate(cluster_sizes):
    clustering_sequence[time_points[tp]] = [
            Cluster(
                height=clustering[cid],
                label="{0}".format(cid),
                facecolor=cluster_color[cid],
                ) for cid in clustering
            ]
# now create the fluxes between the clusters
for tidx, tp in enumerate(time_points[1:]):
    fluxes = between_fluxes[tidx]
    for from_csid, to_csid in fluxes:
        Flux(
            flux=fluxes[(from_csid, to_csid)],
            source_cluster=clustering_sequence[time_points[tidx]][from_csid],
            target_cluster=clustering_sequence[tp][to_csid],
            facecolor='source_cluster'
            )

# #############################################################################
# Create the figure
# #############################################################################
# with plt.xkcd():
if True:
    fig1 = plt.figure(figsize=(6, 4.2))
    gsCom = gridspec.GridSpec(
        9, 16,
        left=0.05, wspace=2.0, hspace=2.0, top=0.99, bottom=0.07, right=0.95
    )
    # #############################################################################
    # The sankey illustration part

    alluvial_plot_params = {
            'x_axis_offset': 0.00,
            'redistribute_vertically': 10,
            'with_cluster_labels': False,
            }
    ax_sk = fig1.add_subplot(gsCom[2:9, :],)
    ax_sk.axis('equal')
    ax_sk.set_xlim(0, 25)
    ax_sk.set_ylim(-0.6, 3)
    AlluvialPlot(clustering_sequence, ax_sk, **alluvial_plot_params)
    ax_sk.set_xticks(time_points, minor=False)
    ax_sk.set_xticklabels(
        [
            r'$\mathbf{{t_{0}}}$'.format(idx)
            for idx in range(6)
            ],
        minor=False,
        size=9
        )
    ax_sk.tick_params(axis=u'x', which=u'both', length=0)

    # #########################################################################
    # Annotation part
    sk_kwargs = {
            'xycoords': 'data',
            'textcoords': 'figure fraction',
            'arrowprops': {
                'arrowstyle': '-|>',  # "-[,widthB=2.0,lengthB=0.2",
                'facecolor': 'black',
                'connectionstyle': 'arc3,rad=0.01',  # 'angle3,angleB=45'
                'relpos': (0.5, 1.),
                'lw': 1.6
                },
            'horizontalalignment': 'right',
            'verticalalignment': 'top',
            'fontweight': 'heavy',
            'size': 8,

            }
    u_y, l_y = 0.8, 0.76
    # birth
    label = 'birth'
    xytext = (0.12, u_y)
    sk_kw = deepcopy(sk_kwargs)
    sk_kw['arrowprops']['arrowstyle'] = '-[,widthB=3.1,lengthB=0.2'
    angle = 62
    xkcd_angle = 25.5
    sk_kw['arrowprops'][
        'connectionstyle'] = 'angle3,angleA=-90,angleB={0}'.format(angle)
    sk_kw['arrowprops']['relpos'] = (0.4, 0.0)
    ax_sk.annotate(label, xy=(-0.6, 0.01), xytext=xytext, **sk_kw)
    # growth
    label = 'growth'
    xytext = (0.29, l_y)
    sgp_kw = deepcopy(sk_kwargs)
    sgp_kw['arrowprops']['arrowstyle'] = '-[,widthB=2.1,lengthB=0.2'
    angle = 39.2
    xkcd_angle = 25.5
    sgp_kw['arrowprops'][
        'connectionstyle'] = 'angle3,angleA=-90,angleB={0}'.format(angle)
    sgp_kw['arrowprops']['relpos'] = (0.4, 0.0)
    ax_sk.annotate(label, xy=(3.4, 1.5), xytext=xytext, **sgp_kw)
    # split
    label = 'split'
    xytext = (0.43, u_y)
    ax_sk.annotate(label, xy=(7.0, 2.8), xytext=xytext, **sk_kwargs)
    # merge
    label = 'merge'
    xytext = (0.60, l_y)
    ax_sk.annotate(label, xy=(12.0, 2.8), xytext=xytext, **sk_kwargs)
    # shrink
    label = 'shrinkage'
    xytext = (0.83, u_y)
    sgp_kw = deepcopy(sk_kwargs)
    sgp_kw['arrowprops']['arrowstyle'] = '-[,widthB=1.0,lengthB=0.2'
    sgp_kw['arrowprops']['connectionstyle'] = 'angle3,angleA=-90,angleB=-3.0'
    sgp_kw['arrowprops']['relpos'] = (0.8, 0.0)
    ax_sk.annotate(label, xy=(14.5, 2.0), xytext=xytext, **sgp_kw)
    # death
    label = 'death'
    xytext = (0.97, l_y)
    sk_kw = deepcopy(sk_kwargs)
    sk_kw['arrowprops']['arrowstyle'] = '-[,widthB=4.2,lengthB=0.2'
    angle = 174.0
    xkcd_angle = 165.5
    sk_kw['arrowprops'][
        'connectionstyle'] = 'angle3,angleA=-90,angleB={0}'.format(angle)
    sk_kw['arrowprops']['relpos'] = (0.85, 0.0)
    ax_sk.annotate(label, xy=(18.7, 0.0), xytext=xytext, **sk_kw)
    # ########################################3
    # save the figure
    fig1.savefig('life_cycles.pdf')
    fig1.savefig('life_cycles.png')
    # fig1.savefig('life_cycles.svg')
