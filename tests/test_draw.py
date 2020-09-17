import unittest
import pyalluv


class TestObjectCreations(unittest.TestCase):
    def setUp(self):
        self.cluster = dict(
            height=10,
            anchor=(0, 0),
            width=4,
            x_anchor='left',
            label='test node',
            label_margin=(1, 2)
        )

    def test_Node(self):
        node = pyalluv.Cluster(
            **self.cluster
        )
        # make sure x_anchor works fine
        self.assertTrue(node.x_pos == 0)

    def test_Flux(self):
        c1 = pyalluv.Cluster(**self.cluster)
        c2 = pyalluv.Cluster(**self.cluster)
        f = pyalluv.Flux(10, source_cluster=c1, target_cluster=c2)
        self.assertIsInstance(f, pyalluv.Flux)
        # relations between fluxes and clusters
        self.assertEqual(f.source_cluster, c1)
        self.assertEqual(f.target_cluster, c2)
        self.assertIn(f, c1.out_fluxes)
        self.assertIn(f, c2.in_fluxes)

    def test_AlluvialDiagram_with_axes(self):
        r"""
        Deprecated initialization using a  dict.
        """
        from matplotlib import pyplot as plt
        c1 = pyalluv.Cluster(**self.cluster)
        c2 = pyalluv.Cluster(**self.cluster)
        pyalluv.Flux(10, source_cluster=c1, target_cluster=c2)
        sequence = {1: [c1], 2: [c2]}
        fig, ax = plt.subplots()
        pyalluv.AlluvialPlot(clusters=sequence, axes=ax)

    def test_AlluvialDiagram_wo_axes(self):
        r"""
        Deprecated initialization using a  dict.
        """
        from matplotlib import pyplot as plt
        c1 = pyalluv.Cluster(**self.cluster)
        c2 = pyalluv.Cluster(**self.cluster)
        pyalluv.Flux(10, source_cluster=c1, target_cluster=c2)
        sequence = {1: [c1], 2: [c2]}
        # create a pyalluvplot and draw_on axes after creation
        pap = pyalluv.AlluvialPlot(clusters=sequence)
        fig, ax = plt.subplots()
        pap.draw_on(ax)


if __name__ == '__main__':
    unittest.main()
