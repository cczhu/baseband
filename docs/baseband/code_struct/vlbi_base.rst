****************************
VLBI Base I/O Code Structure
****************************

Code that is wi

.. _cs_vlbi_base:

VLBI-Base Base
==============


.. _cs_vlbi_frame:

VLBI-Base Frame
===============

VDIFHeaderBase is not an abstract base class because not all of its attributes and methods are used (for example Dada doesn't use _struct), so it is unreasonable to expect subclasses to follow the same template.


.. _cs_vlbi_header:

VLBI-Base Header
================

The VLBI-Base Header module, in :file:`baseband/vlbi_base/header.py`

:class:`~baseband.vdif.header.VDIFHeader`, alongside all other header classes,
is a subclass of :class:`vlbi_base.header.VLBIBaseHeader <baseband.vlbi_base.header.VLBIBaseHeader>`,
a class that houses methods and attributes common across all of Baseband's supported
formats.  :meth:`VLBIBaseHeader.__init__() <!baseband.vlbi_base.header.VLBIBaseHeader.__init__>` creates the ``words`` attribute
that stores the header in 32-bit integer form.  :class:`~!baseband.vlbi_base.header.VLBIBaseHeader` defines ``__getitem__``, ``__setitem__`` and ``keys`` methods to enable dict-like access to header values, and a``mutable`` property that
controls whether the header is writeable.  It also defines the prototypical
methods :meth:`VLBIBaseHeader.fromfile() <baseband.vlbi_base.VLBIBaseHeader.fromfile>`,
:meth:`VLBIBaseHeader.fromvalues() <baseband.vlbi_base.VLBIBaseHeader.fromvalues>`,
and :meth:`VLBIBaseHeader.fromkeys() <baseband.vlbi_base.VLBIBaseHeader.fromkeys>`.
:class:`~!baseband.vdif.header.VDIFHeader` is not directly used in practice, since
it **DOES NOT DEFINE** the ``_struct`` and ``_header_parser`` attributes needed by its
methods. Instead, derived classes like :class:`~!baseband.vdif.header.VDIFHeader`
inherit its attributes or make calls to its methods using ``super()`` (eg.
:meth:`VDIFHeader.fromvalues() <!baseband.vdif.VDIFHeader.fromvalues>` calls
:meth:`VLBIBaseHeader.fromvalues() <!baseband.vlbi_base.VLBIBaseHeader.fromvalues>`).

Also defined in the file are 4-word and 8-word :class:`struct.Struct` binary
readers :obj:`~baseband.vlbi_base.header.four_word_struct`
and :obj:`~baseband.vlbi_base.header.eight_word_struct` that pack and unpack 4 
and 8 32-bit unsigned integers, respectively, to and from their (little-endian) 
binary form.  These are used by VDIF and Mark5B readers.


.. _cs_vlbi_payload:

VLBI-Base Payload
=================
