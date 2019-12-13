=======
pyAlluv
=======

Package to draw alluvial plots with matplotlib.

.. inclusion-marker-do-not-remove

Installation
=============

You can install `pyalluv` using

.. code-block::

    pip install pyalluv

Or get the latest version with

.. code-block::

    pip install --upgrade --no-deps git+https://github.com/j-i-l/pyalluv.git

Examples
=========

Minimal example
----------------

    >>> from pyalluv import AlluvialPlot
    >>> AlluvialPlot(...

Life-cycle events of a dynamic cluster
---------------------------------------

  .. figure:: _static/life_cycles.png
    
    Life-cycle events of a dynamic community. Derived from Fig.1 of `<https://arxiv.org/abs/1912.04261>`_.

  .. literalinclude:: ../examples/life_cycle_events.py
     :language: python
     :lines: 1-79
     :emphasize-lines: 5, 27-31, 37-42, 66

  The full script can be downloaded :download:`here <../examples/life_cycle_events.py>`
