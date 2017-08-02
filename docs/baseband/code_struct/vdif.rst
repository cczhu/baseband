****************************
VDIF File I/O Code Structure
****************************

.. _cs_vdif_intro:

VDIF Files
==========

The `VLBI Data Interchange Format (VDIF) <http://www.vlbi.org/vdif/>`_ was
introduced in 2009 to standardize VLBI data transfer and storage.  Detailed
specifications are found in VDIF's `specification document
<http://www.vlbi.org/vdif/docs/VDIF_specification_Release_1.1.1.pdf>`_; here
we give a brief overview of the VDIF file structure and define commonly-used
terms.

A VDIF file, sequence of files or data transmission is composed of a sequence
of data frames, each of which is comprised of a self-identifying data frame
header followed by an array, or "payload", of data covering a single time
segment of observations from one or more frequency sub-bands.  The header is a
pre-defined 32-bytes long, while the payload is task-specific and can range from
32 bytes to ~134 megabytes.  Both are little-endian and grouped into 32-bit
"words".  Further details will be discussed in the :ref:`header
<cs_vdif_header>` and :ref:`payload sections <cs_vdif_payload>` of the document.

A data frame may carry one or multiple frequency sub-bands (called "channels"
in the VDIF specification, but deliberately called "sub-bands" here to avoid
confusion with Fourier channels).  A sequence of data frames all carrying the
same (set of) sub-band(s) is called a "data thread", denoted by its thread ID.
A data set consisting of multiple concurrent threads is transmitted or stored
as a serial sequence of frames called a "data stream".  Strict time ordering
of frames in the stream, while part of VDIF best practices, is not mandated,
and cannot be guaranteed during data transmission over the internet.


.. _cs_vdif_base:

VDIF Base
=========

:file:`baseband/vdif/base.py` contains master input/output function
:func:`vdif.open() <baseband.vdif.open>`.  To read in the sample VDIF file 
:file:`baseband/data/sample.vdif` (``SAMPLE_VDIF`` in :class:`baseband.data`),
then output its first 20000 data samples as a numpy array::

    >>> from baseband import vdif
    >>> from baseband.data import SAMPLE_VDIF
    >>> fh = vdif.open(SAMPLE_VDIF, 'rs')
    >>> d = fh.read(count=20000)

For this file, ``count=20000`` corresponds to all data from its first
dataframe set.  We define a dataframe set (or just "frame set") as the
collection of frames that cover all threads for a single time segment.
To write this set to a file::

    >>> fw = vdif.open('./dummy_out.vdif', 'ws', nthread=8, header=fh.header0)
    >>> fw.write(d)

:func:`vdif.open() <baseband.vdif.open>` is the only function or class in the 
``vdif`` module directly accessible from :class:`~baseband.vdif` as, in lieu of
troubeshooting, it is the only thing users should access.  

When called, :func:`vdif.open() <!baseband.vdif.open>` uses :func:`io.open` to
open the binary file, then passes the `io` object to one of the VDIF base 
read/write classes.

.. _cs_vdif_base_read:

VDIF Base Reader Classes
------------------------

We can mimic the reader functionality of :func:`vdif.open() 
<!baseband.vdif.open>` showcased above with the following::

    >>> import io
    >>> fio = io.open(SAMPLE_VDIF, 'rb')
    >>> fhr = vdif.base.VDIFFileReader(fio)
    >>> fh = vdif.base.VDIFStreamReader(fhr)

:class:`~baseband.vdif.base.VDIFFileReader`, a subclass of 
:class:`io.BufferedReader`, reads data frames.  It includes the 
:meth:`~baseband.vdif.base.VDIFFileReader.read_frame()` and
:meth:`~baseband.vdif.base.VDIFFileReader.read_frameset()` methods, which are
simply calls to :meth:`VDIFFrame.fromdata() <baseband.vdif.frame.VDIFFrame.fromdata>` 
and :meth:`VDIFFrameSet.fromdata() <baseband.vdif.frame.VDIFFrameSet.fromdata>`, 
respectively, that return data frames or frame sets.
:class:`~!baseband.vdif.base.VDIFFileReader` also includes 
:meth:`~baseband.vdif.base.VDIFFileReader.find_header()`, which
finds the next (or previous, if ``forward=False`` is passed to it) header from
the file pointer's current position.

:class:`~baseband.vdif.VDIFStreamReader`, a subclass of 
:class:`~baseband.vdif.base.VDIFStreamBase` and
:class:`vlbi_base.base.VLBIStreamReaderBase <baseband.vlbi_base.base.VLBIStreamReaderBase>`,
translates files into data streams.  Its constructor takes in a
:class:`~!baseband.vdif.base.VDIFFileReader` instance, and during
initialization uses :meth:`VDIFFileReader.read_frameset()
<!baseband.vdif.base.VDIFFileReader.read_frameset>` to read the file's first
frame set, obtaining the first frame header and the number of threads in the
stream in the process.  The frame set is stored in the ``_frameset``
class attribute.

:class:`~!baseband.vdif.VDIFStreamReader` inherits from 
:class:`~!baseband.vlbi_base.base.VLBIStreamReaderBase`
a file pointer that advances in data samples rather than bytes.  This pointer
is accessible using::

    >>> fh.offset
    0
    >>> fh.seek(0, 2)  # Position in units of samples.
    40000

It is further discussed in the :ref:`VLBI-Base section <cs_vlbi_base_read>`.

The payload can be read by calling :meth:`VDIFStreamReader.read()
<baseband.vdif.base.VDIFStreamReader.read>`, which uses the sample-based
pointer to return a :class:`numpy.ndarray` with a user-defined number of
samples::

    >>> fh.seek(0)          # Return file pointer to start.
    0
    >>> data = fh.read(10)  # Return 10 samples of data in array.
    >>> data.shape
    (10, 8)

Here, ``8`` is the number of threads in the stream.

The sample-based pointer is not tied to the binary file pointer from the
:class:`~!baseband.vdif.base.VDIFFileReader` instance.  For example::

    >>> # Set sample-based pointer to halfway into the first frame
    >>> # (output is position in sample counts)
    >>> fh.seek(fh.samples_per_frame // 2)
    10000
    >>> fh.fh_raw.seek(0, 2)   # Binary pointer from fhr.
    80512
    >>> fh.tell()              # Equivalent to fh.offset.
    10000
    >>> fh.fh_raw.tell()
    80512

:meth:`~!baseband.vdif.base.VDIFStreamReader.read` advances the sample-based
pointer forward when reading data, converting it to a time to check whether
that time falls within the time segment of the currently stored frame set
(in ``_frameset``).  If not, a new frame set is read in using private method
:meth:`~baseband.vdif.VDIFStreamReader._read_frame_set`, which shifts the
binary file pointer to match the sample-based one, then uses
:meth:`VDIFFileReader.read_frameset() <!baseband.vdif.base.VDIFFileReader.read_frameset>`
to read in a new frameset.  This check is made each time the sample-based
pointer is advanced, and so :meth:`~!baseband.vdif.base.VDIFStreamReader.read`
is able to read subsections of data that span multiple frame sets and start
and end in the middle of sets.

To showcase the methodology of :meth:`~!baseband.vdif.base.VDIFStreamReader.read`,
we replicate its behavior for the simple case above of reading an entire file,
by obtaining the number of frames and threads in the file and then
using :meth:`VDIFFileReader.read_frameset() 
<!baseband.vdif.base.VDIFFileReader.read_frameset>`.::

    >>> import numpy as np
    >>> fb_bytesize = fh.fh_raw.seek(0, 2)
    >>> fh.fh_raw.seek(0)
    0
    >>> # Determine number number of frame sets in file and
    >>> # number of samples per frame set.
    >>> first_frameset = fh.fh_raw.read_frameset()
    >>> nframe = fb_bytesize // fh.fh_raw.tell()
    >>> nthread = first_frameset.data.shape[0]
    >>> samp_per_fset = first_frameset.header0.samples_per_frame
    >>> # Define output ndarray.  Number of Fourier channels = 1.
    >>> out = np.empty((nthread, samp_per_fset*nframe, 1), \
    ...                 dtype=first_frameset.dtype).transpose(1, 0, 2)
    >>> # Simplified version of the "while count > 0:" loop in VDIFStreamReader.read().
    >>> out[:samp_per_fset] = first_frameset.data.transpose(1, 0, 2)
    >>> for i in range(1, nframe):
    ...     cframe = fh.fh_raw.read_frameset()
    ...     out[i*samp_per_fset:(i + 1)*samp_per_fset] = \
    ...            cframe.data.transpose(1, 0, 2)
    >>> # Check that output is the same as fh.read() from above.
    >>> fh.seek(0)
    0
    >>> np.array_equal(out.squeeze(), fh.read())
    True


.. _cs_vdif_base_write:

VDIF Base Writer Classes
------------------------

As with :class:`~baseband.vdif.base.VDIFFileReader`,
:class:`~baseband.vdif.base.VDIFFileWriter` simply calls methods from
:mod:`baseband.vdif.frame` - specifically, :meth:`VDIFFileWriter.write_frame()
<baseband.vdif.base.VDIFFileWriter.write_frame>` calls :meth:`VDIFFrame.todata()
<baseband.vdif.frame.VDIFFrame.todata>` and :meth:`VDIFFileWriter.write_frameset()
<baseband.vdif.base.VDIFFileWriter.write_frameset>` calls :meth:`VDIFFrameSet.todata()
<baseband.vdif.frame.VDIFFrameSet.todata>`.  For example, to write out the
frame set stored in ``fh``::

    >>> fwio = io.open('./dummy_out.vdif', 'wb')
    >>> # This is identical to VDIFFileWriter.write_frameset(fh._frameset)
    >>> fh._frameset.tofile(fwio)
    >>> fwio.close()
    >>> # Re-open saved file to check if it's identical to the frame set
    >>> fh_saved = vdif.open('./dummy_out.vdif', 'rs')
    >>> np.array_equal(fh._frameset.data.transpose(1, 0, 2).squeeze(), 
    ...                fh_saved.read())
    True

:class:`~baseband.vdif.VDIFStreamWriter`, a subclass of 
:class:`~baseband.vdif.base.VDIFStreamBase` and
:class:`vlbi_base.base.VLBIStreamWriterBase <baseband.vlbi_base.base.VLBIStreamWriterBase>`,
writes :class:`numpy.ndarray` data to a user-defined data stream, then writes
that stream to file.  The class initializer takes a
:class:`~!baseband.vdif.base.VDIFFileWriter` object and, to partition the
data stream into frame sets, the number of threads ``nthread`` and either
the first header of the data stream, or the set of values needed to construct
the first header from scratch.  This information is used to determine the
number of samples per frame (and frame set), and time segment of each frame.
To write to file, :meth:`VDIFStreamWriter.write() <baseband.vdif.base.VDIFStreamWriter.write>`
advances the sample counter in steps of samples-per-frame; at each step, it
generates an appropriately time-shifted header and writes it and the
corresponding data block to file using :meth:`VDIFFileWriter.write_frameset()
<!baseband.vdif.base.VDIFFileWriter.write_frameset>`.  Proper assignment of
thread numbers is done within :meth:`VDIFFileWriter.write_frameset()
<!baseband.vdif.base.VDIFFileWriter.write_frameset>`.

To show how :meth:`VDIFStreamWriter.write() <!baseband.vdif.base.VDIFStreamWriter.write>` 
works, we replicate its behavior for the simple case of writing all data to a
file using :meth:`VDIFFileWriter.write_frameset() 
<!baseband.vdif.base.VDIFFileReader.read_frameset>`::

    >>> # Read in data to be output to file.
    >>> fh = vdif.open(SAMPLE_VDIF, 'rs')
    >>> data = fh.read()
    >>> # data is squeezed; unsqueeze here
    >>> data = np.expand_dims(data, axis=-1)
    >>> 
    >>> # Open output file.
    >>> fwio = io.open('./dummy_out.vdif', 'wb')
    >>> fwr = vdif.base.VDIFFileWriter(fwio)
    >>> 
    >>> # Initialize data frame payload storage (with VDIFStreamWriter, stored in
    >>> # ._data) with 8 threads, 1 channel
    >>> nsample = fh.samples_per_frame
    >>> payload = np.zeros((fh.nthread, nsample, fh.nchan),
    ...                    np.float32)
    >>> 
    >>> # Obtain count (# of samples to write to file), and set sample and
    >>> # frame number to 0
    >>> count = data.shape[0]
    >>> sample = 0
    >>> frame_nr = 0
    >>> # frame is a transposed view of payload.
    >>> frame = payload.transpose(1, 0, 2)
    >>> while count > 0:
    ...     # Generate a header with the new time and frame number.
    ...     c_header = fh.header0.copy()
    ...     c_header['seconds'] = fh.header0['seconds'] + \
    ...                           frame_nr // fh.frames_per_second
    ...     c_header['frame_nr'] = frame_nr 
    ...     # Write frame to file.
    ...     frame[:] = data[sample:sample + nsample]
    ...     fwr.write_frameset(payload, c_header)
    ...     # Advance sample and frame number, decrease count
    ...     sample += nsample
    ...     count -= nsample
    ...     frame_nr += 1
    >>> 
    >>> fwr.close()
    >>> 
    >>> # Check that we made a successful write (fh.header0 not equal
    >>> # to  fh_w.header0 because SAMPLE_VDIF's threads not in order)
    >>> fh_w = vdif.open('./dummy_out.vdif', 'rs')
    >>> np.array_equal(data.squeeze(), fh_w.read())
    True

The above takes advantage of the fact that ``data`` is exactly two frames long.
To handle situations where :meth:`VDIFStreamWriter.write()
<!baseband.vdif.base.VDIFStreamWriter.write>` begins or ends writing in the
middle of a frame, it keeps track of its current position using its sample-based
pointer (also inherited from :class:`~!baseband.vlbi_base.base.VLBIStreamReaderBase`),
The modulo of the sample pointer position with the number of samples per frame
(itself derived from the header) is used to determine when a frame is full
and ready to be flushed to file using :meth:`VDIFFileWriter.write_frameset()
<!baseband.vdif.base.VDIFFileWriter.write_frameset>`.

:class:`~!baseband.vdif.base.VDIFFileWriter`, and consequently
:class:`~baseband.vdif.VDIFStreamWriter`, cannot automatically write a data set
to a sequence of files.


.. _cs_vdif_frame:

VDIF Frame
==========

The file I/O operations above rely on data frame classes defined in the
:mod:`baseband.vdif.frame` module.


.. _cs_vdif_header:

VDIF Header
===========

Each VDIF frame begins with a 32-byte, or 8-word, header (16-bytes for the 
"VDIF legacy headers")

.. figure:: VDIFHeader.png
   :scale: 50 %

   Schematic of the standard 32-bit VDIF header, from `VDIF specification 
   release 1.1.1 document, Fig. 3
   <http://www.vlbi.org/vdif/docs/VDIF_specification_Release_1.1.1.pdf>`_.
   32-bit words are labelled on the left, while byte and bit numbers above
   indicate relative addresses within each word.  Subscripts indicate field
   length in bits.

where the abbreviated labels are

- :math:`\mathrm{I}_1` - invalid data
- :math:`\mathrm{L}_1` - if 1, header is VDIF legacy
- :math:`\mathrm{V}_3` - VDIF version number
- :math:`\mathrm{log}_2\mathrm{(\#chns)}_5` - :math:`\mathrm{log}_2` of the
  number of sub-bands in the frame
- :math:`\mathrm{C}_1` - if 1, complex data
- :math:`\mathrm{EDV}_8` - "extended data version" number; see below

Detailed definitions of terms are found on pg. 5 - 7 of the VDIF specification.

Words 4 - 7 hold optional extended user data that is telescope or experiment-
specific.  The layout of this data is specified by the "extended-data version",
or EDV, in word 4, bit 24 of the header.  Registered EDV formats, found on
the VDIF website, are all supported by Baseband, and the code is written so that
new EDVs can be defined by the user.

When :class:`~baseband.vdif.VDIFStreamReader` is initialized, it calls classes
from :mod:`baseband.vdif.header` to read the header, specifically by passing the
:class:`~baseband.vdif.VDIFFileReader` instance into method
:meth:`VDIFHeader.fromfile() <baseband.vdif.VDIFHeader.fromfile>`.  We can
reproduce this behaviour with::

    >>> import io
    >>> import baseband.vdif as vdif
    >>> fio = io.open(SAMPLE_VDIF, 'rb')
    >>> fhr = vdif.base.VDIFFileReader(fio)
    >>> header = vdif.header.VDIFHeader.fromfile(fhr)
    >>> header.ref_epoch  # Number of 6-month periods after Jan 1, 2000.
    28

We can also call :meth:`VDIFHeader.fromvalues() <baseband.vdif.VDIFHeader.fromkeys>`
to manually define a header::

    >>> # Dereference header info to feed into VDIFHeader.fromkeys
    >>> header_fromkeys = vdif.header.VDIFHeader.fromkeys(**header)
    >>> header_fromkeys == header
    True

A similar method is :meth:`VDIFHeader.fromvalues() <baseband.vdif.VDIFHeader.fromvalues>`,
which also takes derived properties like ``bps`` and ``time``.
(:class:`~baseband.vdif.VDIFFileReader` can be directly initialized with an 
array of words, but this is not used in practice.)

Perhaps unintuitively, the ``type`` of header is 
:class:`~baseband.vdif.header.VDIFHeader3`::

    >>> isinstance(header, vdif.header.VDIFHeader3)
    True

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

    >>> from baseband import vlbi_base
    >>> class MyVDIFHeader(vdif.header.VDIFSampleRateHeader):
    ...     _edv = 47
    ...
    ...     _header_parser = vdif.header.VDIFSampleRateHeader._header_parser +\
    ...         vlbi_base.header.HeaderParser(
    ...                             (('nonsense', (6, 0, 32, 0x0)),))

This class can then be used like any other::

    >>> myheader = vdif.header.VDIFHeader.fromvalues(
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


.. _cs_vdif_payload:

VDIF Payload
============
