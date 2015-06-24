Concord plug-in
===============

The `LabManager <http://github.com/gateway4labs/labmanager/>`_ provides an API for
supporting more Remote Laboratory Management Systems (RLMS). This project is the
implementation for the `Concord
<http://lab.concord.org/>`_ virtual laboratories.

Usage
-----

First install the module::

  $ pip install git+https://github.com/gateway4labs/rlms_concord.git

Then add it in the LabManager's ``config.py``::

  RLMS = ['concord', ... ]

Profit!
