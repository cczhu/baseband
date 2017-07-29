**************************
VDIF Reader Code Structure
**************************

.. _cs_vdif_base_read:

VDIF Stream Reader Classes
--------------------------

:func:`vdif.open() <baseband.vdif.open>` itself calls 
:class:`~baseband.vdif.base.VDIFFileReader` and 
:class:`~baseband.vdif.VDIFStreamReader`; the call to it in the
:ref:`code block <cs_vdif_intro>` at the start of the section is equivalent to::

    >>> import io
    >>> name = io.open(SAMPLE_VDIF, 'rb')
    >>> fhr = vdif.base.VDIFFileReader(name)
    >>> fh = vdif.base.VDIFStreamReader(fhr)

:class:`~baseband.vdif.base.VDIFFileReader` is a subclass of 
:class:`io.BufferedReader` that includes the
:meth:`~baseband.vdif.base.VDIFFileReader.read_frame()`,
:meth:`~baseband.vdif.base.VDIFFileReader.read_frameset()` and
:meth:`~baseband.vdif.base.VDIFFileReader.find_header()` methods.  The former
two simply call :meth:`VDIFFrame.fromdata() <baseband.vdif.frame.VDIFFrame.fromdata>` 
and :meth:`VDIFFrameSet.fromdata() <baseband.vdif.frame.VDIFFrameSet.fromdata>`, 
respectively.  The latter finds the next (or previous, if ``forward=False`` is 
passed to it) header from the file pointer's current position.

:class:`~baseband.vdif.VDIFStreamReader` is not a subclass of 
:class:`~baseband.vdif.base.VDIFFileReader`, but takes in a :class:`~!baseband.vdif.base.VDIFStreamReader`
object during class instance initialization.  Upon initialization, the first
header of the file is read using :class:`~baseband.vdif.header.VDIFHeader`, 
and the number of threads determined by reading the first frameset using 
:meth:`VDIFFileReader.read_frameset() <baseband.vdif.base.VDIFFileReader.read_frameset>`
and counting the number of frames found.  The payload can then be read by 
calling :meth:`VDIFStreamReader.read() <baseband.vdif.base.VDIFStreamReader.read>`,
which returns a :class:`numpy.ndarray` whose indices are counts and threads::

    >>> data = fh.read()
    >>> data.shape
    (40000, 8)

:meth:`~baseband.vdif.VDIFStreamReader.read` calls private method
:meth:`~baseband.vdif.VDIFStreamReader._read_frame_set`, which in turn
calls :meth:`VDIFFileReader.read_frameset() <!baseband.vdif.base.VDIFFileReader.read_frameset>`
to read framesets.  For the trivial case above of reading an entire file, we 
can manually replicate :meth:`~!baseband.vdif.base.VDIFStreamReader.read`'s 
behaviour with::

    >>> import numpy as np
    >>> # Read in file.
    >>> name = io.open(SAMPLE_VDIF, 'rb')
    >>> fb = vdif.base.VDIFFileReader(name)
    >>> # Determine file length in bytes.
    >>> fb_bytesize = fb.seek(0, 2)
    >>> fb.seek(0)
    0
    >>> # Determine number of threads in frameset and number of framesets in file.  
    >>> # Functionally identical to thread finder in VDIFStreamReader.__init__().
    >>> first_frameset = fb.read_frameset(None)
    >>> thread_ids = [fr['thread_id'] for fr in first_frameset.frames]
    >>> nthread = len(thread_ids)
    >>> nframe = fb_bytesize // fb.tell()
    >>> # Get number of samples per frameset.
    >>> samp_per_fset = first_frameset.header0.samples_per_frame
    >>> # Define output ndarray (number of Fourier channels nchan = 1).
    >>> out = np.empty((nthread, samp_per_fset*nframe, 1), \
    ...                 dtype=first_frameset.dtype).transpose(1, 0, 2)
    >>> # Simpler version of the "while count > 0:" loop in VDIFStreamReader.read().
    >>> fb.seek(0)
    0
    >>> for i in range(nframe):
    ...     cframe = fb.read_frameset(thread_ids)
    ...     out[i*samp_per_fset:(i + 1)*samp_per_fset] = \
    ...            cframe.data.transpose(1, 0, 2)
    >>> # Check that output is the same as fh.read() from above.
    >>> np.array_equal(out.squeeze(), data)
    True

:class:`~baseband.vdif.base.VDIFFileReader`, however, has an ``offset`` data 
pointer that increments in units of samples. (As discussed below, it works 
directly on the data stream, and is **not** a file pointer!  The original byte
pointer is available through ``VDIFStreamReader.fh_raw`` and functions 
indepently from ``offset``.)  It controls where 
:meth:`~!baseband.vdif.base.VDIFStreamReader.read` starts reading data, and can 
be used to read subsections of the data even if we start and end in the middle
of framesets::

    >>> # Set offset pointer to halfway into the first frame
    >>> fh.seek(fh.samples_per_frame // 2)
    10000
    >>> data_m = fh.read(fh.samples_per_frame)  # Read 1 frame worth of samples
    >>> data_m.shape
    (20000, 8)
    >>> # Check that first sample read is from middle of first frameset
    >>> np.array_equal(data_m[0], data[fh.samples_per_frame // 2])
    True

:class:`~baseband.vdif.VDIFStreamReader` is a subclass of
:class:`~baseband.vdif.base.VDIFStreamBase` and 
:class:`~baseband.vlbi_base.base.VLBIStreamReaderBase`.
:class:`~baseband.vdif.base.VDIFStreamBase` is subclassed from
:class:`~baseband.vlbi_base.base.VLBIStreamBase`, and only appends private
methods for printing class information to screen and calculating times for 
headers.  The ``offset`` data pointer, which also has the ability to
increment in time units, is inherited from the :mod:`~baseband.vlbi_base` 
classes.

.. _cs_vdif_header:

VDIF Header Module
------------------

When :class:`~baseband.vdif.VDIFStreamReader` is initialized, it calls classes
from :mod:`baseband.vdif.header` to read the header, specifically by passing the
:class:`~baseband.vdif.VDIFFileReader` instance into method
:meth:`VDIFHeader.fromfile() <baseband.vdif.VDIFHeader.fromfile>`.  We can
reproduce this behaviour with::

    >>> import baseband.vdif.header as vhdr
    >>> name = io.open(SAMPLE_VDIF, 'rb')
    >>> header = vhdr.VDIFHeader.fromfile(name)
    >>> header.ref_epoch  # Number of 6-month periods after Jan 1, 2000.
    28

We can also call :meth:`VDIFHeader.fromvalues() <baseband.vdif.VDIFHeader.fromkeys>`
to manually define a header::

    >>> # Dereference header info to feed into VDIFHeader.fromkeys
    >>> header_fromkeys = vdif.VDIFHeader.fromkeys(**header)
    >>> header_fromkeys == header
    True

A similar method is :meth:`VDIFHeader.fromvalues() <baseband.vdif.VDIFHeader.fromvalues>`,
which also takes derived properties like ``bps`` and ``time``.
(:class:`~baseband.vdif.VDIFFileReader` can be directly initialized with an 
array of words, but this is not used in practice.)

Perhaps unintuitively, the ``type`` of header is 
:class:`~baseband.vdif.header.VDIFHeader3`::

    >>> isinstance(header, vhdr.VDIFHeader3)
    True

Modern VDIF headers are composed of 8 "words", each 32 bits long.  Words 0 - 3
have fixed meanings, but words 4 - 7 hold optional "extended user data" that
is telescope or experiment-specific.  The layout of this data is specified 
by its "extended-data version" (EDV) in word 4, bit 24, and registered EDV 
formats are found on the `VDIF specification site <http://www.vlbi.org/vdif/>`_.
Baseband pairs each EDV format with its own header class 
(:class:`~baseband.vdif.header.VDIFHeader3` is for ``EDV = 0x03``, or NRAO data), 
and currently accommodates EDVs 1 through 4, as well as the 4-word legacy VDIF 
header and Mark 5B headers transformed into VDIF (``EDV = 0xab``).
:meth:`VDIFHeader.fromfile() <!baseband.vdif.VDIFHeader.fromfile>`, 
:meth:`VDIFHeader.fromvalues() <!baseband.vdif.VDIFHeader.fromkeys>`, and
:meth:`VDIFHeader.fromvalues() <!baseband.vdif.VDIFHeader.fromvalues>` are class
methods that call :meth:`VDIFHeader.__new__() <!baseband.vdif.VDIFHeader.__new__>`,
which accesses the registry of EDV classes within the metaclass
:class:`_VDIFHeaderRegistry <!baseband.vdif._VDIFHeaderRegistry>`
to create the appropriate class instance.

New header classes can be added to the registry by subclassing them from
:class:`~!baseband.vdif.header.VDIFHeader`, using :class:`~!baseband.vdif._VDIFHeaderRegistry`
as their metaclass, and including an ``edv`` attribute whose value is not 
already in use by another class.  For example::

    >>> from six import with_metaclass  # For Python 2 and 3 compatibilty
    >>> from baseband.vlbi_base.header import HeaderParser
    >>> class MyVDIFHeader(with_metaclass(vhdr._VDIFHeaderRegistry, 
    ...                                   vhdr.VDIFSampleRateHeader)):
    ...     edv = 47
    ... 
    ...     _header_parser = vhdr.VDIFSampleRateHeader._header_parser + \
    ...                          HeaderParser(
    ...                              (('nonsense', (6, 0, 32, 0x0)),))
    ... 

This class can then be used like any other::

    >>> myheader = vdif.VDIFHeader.fromvalues(
    ...     edv=47, time=header.time,
    ...     samples_per_frame=header.samples_per_frame,
    ...     station=header.station, bandwidth=header.bandwidth,
    ...     bps=header.bps, complex_data=header['complex_data'],
    ...     thread_id=header['thread_id'], nonsense=2000000000)
    >>> isinstance(myheader, MyVDIFHeader)
    True
    >>> myheader['nonsense'] == 2000000000
    True

Each EDV class defines a ``_struct`` attribute that refers to a
:class:`struct.Struct` binary reader and a ``_header_parser`` one that stores
the bit positions and lengths of header values and produces associated binary 
readers and writers.  One ``_header_parser`` can be appended to another: for 
example, ``MyVDIFHeader``, above, combines the parser from 
:class:`~baseband.vdif.header.VDIFSampleRateHeader` with one that only has
"nonsense" in word 6.  Binary readers, parsers and the methods that use them
are all inherited from the VLBI-Base Header.

.. _cs_vlbi_header:

VLBI-Base Header Module
-----------------------

The VLBI-Base Header module, in :file:`baseband/vlbi_base/header.py`

:class:`~baseband.vdif.header.VDIFHeader`, alongside all other header classes,
is a subclass of :class:`vlbi_base.header.VLBIBaseHeader <baseband.vlbi_base.header.VLBIBaseHeader>`,
a class that houses methods and attributes common across all of Baseband's supported
formats.  :meth:``VLBIBaseHeader.__init__() <!baseband.vlbi_base.header.VLBIBaseHeader.__init__>`` creates the ``words`` attribute
that stores the header in 32-bit integer form.  :class:``~!baseband.vlbi_base.header.VLBIBaseHeader`` defines ``__getitem__``, ``__setitem__`` and ``keys`` methods to enable dict-like access to header values, and a``mutable`` property that
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
readers :obj:``~baseband.vlbi_base.header.four_word_struct``
and :obj:``~baseband.vlbi_base.header.eight_word_struct`` that pack and unpack 4 
and 8 32-bit unsigned integers, respectively, to and from their (little-endian) 
binary form.  These are used by VDIF and Mark5B readers.


VDIF Writer
===========
