import os
import pathlib
import json
from matplotlib import pyplot as plt
import matplotlib
matplotlib.use('TkAgg')

try:
    from pyalluv import AlluvialPlot, Cluster, Flux
except ImportError:
    os.sys.path.append(os.path.dirname('..'))
    from pyalluv import AlluvialPlot, Cluster, Flux

with open(os.path.join(
        pathlib.Path(__file__).parent.absolute(),
        'example_data.json'
        ), 'r') as fobj:
    eg_data = json.load(fobj)

fc_clusters = 'xkcd:gray'
fc_edges = 'lightgray'

clusters = []
# first create the clusters
for a_slice in eg_data:
    slice_clusters = dict()
    for target, fluxes in a_slice.items():
        if target is None or target == 'null':
            pass
        else:
            if target not in slice_clusters:
                slice_clusters[target] = Cluster(
                    height=sum(fluxes.values()),
                    label=target,
                    width=0.2,
                    facecolor=fc_clusters
                )
    clusters.append(dict(slice_clusters))
# now the fluxes

for idx, a_slice in enumerate(eg_data):
    slice_clusters = clusters[idx]
    if idx:
        prev_clusters = clusters[idx-1]
        for target, fluxes in a_slice.items():
            if target is not None and target != 'null':
                for source, amount in fluxes.items():
                    if source is not None and source != 'null':
                        Flux(
                            flux=amount,
                            source_cluster=prev_clusters[source],
                            target_cluster=slice_clusters[target],
                            facecolor=fc_edges
                        )
fig, ax = plt.subplots()
AlluvialPlot(
        axes=ax,
        clusters=[list(_clusters.values()) for _clusters in clusters]
        )
plt.show()
