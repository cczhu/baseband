.. _new_format:

.. include:: ../tutorials/glossary_substitutions.rst

***********************
Supporting a New Format
***********************

This tutorial describes how to add support for a new file format into Baseband,
and also provides an overview of Baseband's code structure.  It uses
implementing support for the :ref:`GUPPI file format <guppi>` as an example.

.. _code_structure:

Baseband Code Structure
=======================

All radio baseband file formats feature a timeseries, or :term:`stream`, of
|samples| split up into discrete data blocks, or |frames|.  Each of these
features a :term:`header` containing metadata and a :term:`payload` of 
(encoded) samples.  Baseband's purpose is to decode either individual frames or
a sequence of frames interpreted as a stream of samples when reading, and to
encode frames when writing.  To do this for a given file format, it needs to be
able to decode and encode that format's header and payload, combine header and
payload into a frame, and read (write) individual frames and frame sequences
from (to) file.

Baseband's source code is located under the ``baseband`` directory, and
supported file formats are each given its own subdirectory.  Within each
subdirectory, the classes and functions for each file I/O task described above
are located within their own file.  The files are:

- :file:`baseband/<format>/base.py` - defines a master ``open()`` read/write
  function, and classes for reading frames and streams from and writing to
  files.
- :file:`baseband/<format>/file_info.py` - defines a file descriptor to be
  used by the `baseband.open` general file opener.  Not all formats need to
  create this file; see :ref:`below <new_format_general_opener>`.
- :file:`baseband/<format>/frame.py` - defines a frame class for the format 
  (as well as a frameset class in the case of VDIF).  The frame class uses the
  header and payload classes discussed below.
- :file:`baseband/<format>/header.py` - defines a header class that includes
  reading and writing methods.
- :file:`baseband/<format>/payload.py` - defines a payload class that includes
  reading and writing methods.
- :file:`baseband/<format>/tests/test_<format>.py` - defines the test suite for
  the above.

Additionally, Baseband has:

- ``baseband/vlbi_base`` - base classes for all formats.  The directory
  structure is identical to that for formats, above.
- ``baseband/data`` - data snippets of all supported formats, used for
  testing and tutorials.  Files are registered in
  :file:`baseband/data/__init__.py`.
- ``baseband/helpers`` - helper functions and classes.  Currently this
  includes the `baseband.helpers.sequentialfile` module for reading a file
  sequence as if it were a single file.
- ``baseband/tests`` - configuration files for the test suite, and general
  tests.
- :file:`baseband/core.py` - contains the `baseband.open` general file opener.

All other files in the root directory are to link Baseband with the
`astropy-helpers module <https://github.com/astropy/astropy-helpers>`_
(which, among other things, enables the test suite and Sphinx documentation
builder).

Baseband's documentation is located under ``docs``, which has a file structure
very similar to the ``baseband`` code directory.  Documentation for file
formats are located in their own subfolders.

.. _new_format_tutorial:

New Format Tutorial
===================

To support a new file format, in our case the `Green Bank Ultimate Pulsar
Processing Instrument <https://safe.nrao.edu/wiki/bin/view/CICADA/NGNPP>`_, or
GUPPI, raw format, we follow the framework above and create a
``baseband/guppi`` subfolder.  Within, we create the following files and
subdirectories:

- :file:`baseband/guppi/base.py`
- :file:`baseband/guppi/frame.py`
- :file:`baseband/guppi/header.py`
- :file:`baseband/guppi/payload.py`
- :file:`baseband/guppi/tests/test_guppi.py`

GUPPI general specifications can be found at the `SERA Project
<http://seraproject.org/mw/index.php?title=GBT_FIle_Formats>`_ and on `Paul
Demorest's site <https://www.cv.nrao.edu/~pdemores/GUPPI_Raw_Data_Format>`_.
The `DSPSR package <https://github.com/demorest/dspsr>`_ also supports GUPPI,
and provided a reference for some of our code.  However, much of our
code was also designed by reverse-engineering examples of GUPPI, and, in
general, reverse-engineering is required since many formats have sparse
documentation.  As such, it is often useful (and conducive to test-driven
development) to create a sample file and test suite early on in the
development, typically as soon as one has figured out how to read the header
and payload.

It is also useful to determine which format already within Baseband is closest
to the new one.  For GUPPI, its ASCII headers and very large payloads are
reminscent of DADA, and so some of our GUPPI classes can be based off of, or
even directly descended from, the DADA ones.

.. _new_format_header:

The Header Class
----------------

aa

.. _new_format_payload:

The Payload Class
-----------------

bb

.. _new_format_sample_and_test:

A Sample File and Test Suite
----------------------------

cc

.. _new_format_frame:

The Frame Class
---------------

dd

.. _new_format_readers:

File and Stream Readers
-----------------------

ee

.. _new_format_general_opener:

General File Info and Opener
----------------------------

ff

.. _new_format_docs:

Documentation
-------------

Finally, it is necessary to add to the documentation some basic information
about the format and a short tutorial on how to read and write it.  Since there
is already a :ref:`Getting Started <getting_started>` general tutorial, our
tutorial should highlight format-specific details, such as GUPPI's overlap
samples, or :ref:`Mark 4's <mark4>` dummy samples in place of the header.
Ideally one can include references to the format's full specifications and a
brief description of the format's structure, though in some cases this is not
possible (such as with :ref:`DADA <dada>`).