from unittest import TestCase
import pyalluv


class TestObjectCreations(TestCase):
    def test_Node(self):
        node = pyalluv.Cluster(
                height=10,
                anchor=(0, 0),
                widht=4,
                x_anchor='left',
                label='test node',
                label_margin=(1, 2)
                )
        # make sure x_anchor works fine
        self.assertTrue(node.x_pos == 0)
