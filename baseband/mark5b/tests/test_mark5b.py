# Licensed under the GPLv3 - see LICENSE.rst
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import io
import pytest
import numpy as np
from astropy import units as u
from astropy.time import Time
from ... import mark5b
from ...vlbi_base.encoding import OPTIMAL_2BIT_HIGH
from ...data import SAMPLE_MARK5B as SAMPLE_FILE


# Check code on 2015-MAY-08.
# m5d /raw/mhvk/scintillometry/gp052d_wb_no0001 Mark5B-512-8-2 10
# ----> first 10016*4 bytes -> sample.m5b
# Mark5 stream: 0x256d140
#   stream = File-1/1=gp052a_wb_no0001
#   format = Mark5B-512-8-2 = 2
#   start mjd/sec = 821 19801.000000000
#   frame duration = 156250.00 ns
#   framenum = 0
#   sample rate = 32000000 Hz
#   offset = 0
#   framebytes = 10016 bytes
#   datasize = 10000 bytes
#   sample granularity = 1
#   frame granularity = 1
#   gframens = 156250
#   payload offset = 16
#   read position = 0
#   data window size = 1048576 bytes
# -3 -1  1 -1  3 -3 -3  3
# -3  3 -1  3 -1 -1 -1  1
#  3 -1  3  3  1 -1  3 -1
# Compare with my code:
# fh = Mark5BData(['/raw/mhvk/scintillometry/gp052d_wb_no0001'],
#                  channels=None, fedge=0, fedge_at_top=True)
# 'Start time: ', '2014-06-13 05:30:01.000' -> correct
# fh.header0
# <Mark5BFrameHeader sync_pattern: 0xabaddeed,
#                    year: 11,
#                    user: 3757,
#                    internal_tvg: False,
#                    frame_nr: 0,
#                    bcd_jday: 0x821,
#                    bcd_seconds: 0x19801,
#                    bcd_fraction: 0x0,
#                    crc: 0x975d>
# fh.record_read(6).astype(int)
# array([[-3, -1,  1, -1,  3, -3, -3,  3],
#        [-3,  3, -1,  3, -1, -1, -1,  1],
#        [ 3, -1,  3,  3,  1, -1,  3, -1]])


class TestMark5B(object):
    def test_header(self):
        with open(SAMPLE_FILE, 'rb') as fh:
            header = mark5b.Mark5BHeader.fromfile(
                fh, ref_mjd=Time('2014-06-01').mjd)
        assert header.size == 16
        assert header.kday == 56000.
        assert header.jday == 821
        mjd, frac = divmod(header.time.mjd, 1)
        assert mjd == 56821
        assert round(frac * 86400) == 19801
        assert header.payloadsize == 10000
        assert header.framesize == 10016
        assert header['frame_nr'] == 0
        with io.BytesIO() as s:
            header.tofile(s)
            s.seek(0)
            header2 = mark5b.Mark5BHeader.fromfile(s, header.kday)
        assert header2 == header
        header3 = mark5b.Mark5BHeader.fromkeys(header.kday, **header)
        assert header3 == header
        # Try initialising with properties instead of keywords.
        # Here, we let year, bcd_jday, bcd_seconds, and bcd_fraction be
        # set by giving the time, and let the crc be calculated from those.
        header4 = mark5b.Mark5BHeader.fromvalues(
            time=header.time,
            user=header['user'], internal_tvg=header['internal_tvg'],
            frame_nr=header['frame_nr'])
        assert header4 == header
        # Check ref_mjd
        header5 = mark5b.Mark5BHeader(header.words,
                                      ref_mjd=(header.time.mjd - 499.))
        assert header5.time == header.time
        header6 = mark5b.Mark5BHeader(header.words,
                                      ref_mjd=(header.time.mjd + 499.))
        assert header6.time == header.time
        # check payload and framesize setters
        header6.payload = 10000
        header6.framesize = 10016
        with pytest.raises(ValueError):
            header6.payloadsize = 9999
        with pytest.raises(ValueError):
            header6.framesize = 20
        # Regression test
        header7 = header.copy()
        header7.time = Time('2016-09-10T12:26:40.000000000')
        assert header7.ns == 0

    def test_decoding(self):
        """Check that look-up levels are consistent with mark5access."""
        o2h = OPTIMAL_2BIT_HIGH
        assert np.all(mark5b.payload.lut1bit[0] == -1.)
        assert np.all(mark5b.payload.lut1bit[0xff] == 1.)
        assert np.all(mark5b.payload.lut1bit.astype(int) ==
                      ((np.arange(256)[:, np.newaxis] >>
                        np.arange(8)) & 1) * 2 - 1)
        assert np.all(mark5b.payload.lut2bit[0] == -o2h)
        assert np.all(mark5b.payload.lut2bit[0x55] == 1.)
        assert np.all(mark5b.payload.lut2bit[0xaa] == -1.)
        assert np.all(mark5b.payload.lut2bit[0xff] == o2h)

    def test_payload(self):
        with open(SAMPLE_FILE, 'rb') as fh:
            fh.seek(16)  # skip header
            payload = mark5b.Mark5BPayload.fromfile(fh, nchan=8, bps=2)
        assert payload._size == 10000
        assert payload.size == 10000
        assert payload.shape == (5000, 8)
        assert payload.dtype == np.float32
        assert np.all(payload[:3].astype(int) ==
                      np.array([[-3, -1, +1, -1, +3, -3, -3, +3],
                                [-3, +3, -1, +3, -1, -1, -1, +1],
                                [+3, -1, +3, +3, +1, -1, +3, -1]]))
        with io.BytesIO() as s:
            payload.tofile(s)
            s.seek(0)
            payload2 = mark5b.Mark5BPayload.fromfile(s, payload.nchan,
                                                     payload.bps)
            assert payload2 == payload
            with pytest.raises(EOFError):
                # Too few bytes.
                s.seek(100)
                mark5b.Mark5BPayload.fromfile(s, payload.nchan, payload.bps)

        payload3 = mark5b.Mark5BPayload.fromdata(payload.data, bps=payload.bps)
        assert payload3 == payload
        with pytest.raises(ValueError):
            mark5b.Mark5BPayload.fromdata(np.zeros((5000, 8), np.complex64),
                                          bps=2)

    @pytest.mark.parametrize('item', (2, (), -1, slice(1, 3), slice(2, 4),
                                      slice(2, 4), slice(-3, None),
                                      (2, slice(3, 5)), (10, 4),
                                      (slice(None), 5)))
    def test_payload_getitem_setitem(self, item):
        with open(SAMPLE_FILE, 'rb') as fh:
            fh.seek(16)  # skip header
            payload = mark5b.Mark5BPayload.fromfile(fh, nchan=8, bps=2)
        sel_data = payload.data[item]
        assert np.all(payload[item] == sel_data)
        payload2 = mark5b.Mark5BPayload(payload.words.copy(), nchan=8, bps=2)
        assert payload2 == payload
        payload2[item] = -sel_data
        check = payload.data
        check[item] = -sel_data
        assert np.all(payload2[item] == -sel_data)
        assert np.all(payload2.data == check)
        assert payload2 != payload
        payload2[item] = sel_data
        assert np.all(payload2[item] == sel_data)
        assert payload2 == payload

    def test_frame(self):
        with mark5b.open(SAMPLE_FILE, 'rb') as fh:
            header = mark5b.Mark5BHeader.fromfile(fh, ref_mjd=57000.)
            payload = mark5b.Mark5BPayload.fromfile(fh, nchan=8, bps=2)
            fh.seek(0)
            frame = fh.read_frame(nchan=8, bps=2, ref_mjd=57000.)

        assert frame.header == header
        assert frame.payload == payload
        assert frame == mark5b.Mark5BFrame(header, payload)
        assert np.all(frame.data[:3].astype(int) ==
                      np.array([[-3, -1, +1, -1, +3, -3, -3, +3],
                                [-3, +3, -1, +3, -1, -1, -1, +1],
                                [+3, -1, +3, +3, +1, -1, +3, -1]]))
        with io.BytesIO() as s:
            frame.tofile(s)
            s.seek(0)
            frame2 = mark5b.Mark5BFrame.fromfile(s, ref_mjd=57000.,
                                                 nchan=frame.shape[1],
                                                 bps=frame.payload.bps)
        assert frame2 == frame
        frame3 = mark5b.Mark5BFrame.fromdata(payload.data, header, bps=2)
        assert frame3 == frame
        frame4 = mark5b.Mark5BFrame.fromdata(payload.data, bps=2,
                                             ref_mjd=57000, **header)
        assert frame4 == frame
        frame5 = mark5b.Mark5BFrame(header, payload, valid=False)
        assert frame5.valid is False
        assert np.all(frame5.data == 0.)
        frame5.valid = True
        assert frame5 == frame
        frame6 = mark5b.Mark5BFrame.fromdata(payload.data, header, bps=2,
                                             valid=False)
        assert frame6.valid is False
        assert np.all(frame6.payload.words == 0x11223344)

    def test_header_times(self):
        with mark5b.open(SAMPLE_FILE, 'rb') as fh:
            header0 = mark5b.Mark5BHeader.fromfile(fh, ref_mjd=57000.)
            time0 = header0.time
            samples_per_frame = header0.payloadsize * 8 // 2 // 8
            frame_rate = 32. * u.MHz / samples_per_frame
            frame_duration = 1./frame_rate
            fh.seek(0)
            while True:
                try:
                    frame = fh.read_frame(nchan=8, bps=2, ref_mjd=57000.)
                except EOFError:
                    break
                header_time = frame.header.time
                expected = time0 + frame.header['frame_nr'] * frame_duration
                assert abs(header_time - expected) < 1. * u.ns

    def test_filestreamer(self):
        with open(SAMPLE_FILE, 'rb') as fh:
            header = mark5b.Mark5BHeader.fromfile(fh, kday=56000)

        with mark5b.open(SAMPLE_FILE, 'rs', nchan=8, bps=2,
                         sample_rate=32*u.MHz, ref_mjd=57000) as fh:
            assert header == fh.header0
            assert fh.fh_raw.tell() == header.framesize
            assert fh.samples_per_frame == 5000
            assert fh.frames_per_second == 6400
            header1 = fh.header1
            assert fh.size == 20000
            record = fh.read(12)
            assert fh.tell() == 12
            fh.seek(10000)
            record2 = fh.read(2)
            assert fh.tell() == 10002
            assert fh.fh_raw.tell() == 3.*header.framesize
            assert np.abs(fh.tell(unit='time') -
                          (fh.time0 + 10002 / (32*u.MHz))) < 1. * u.ns
            fh.seek(fh.time0 + 1000 / (32*u.MHz))
            assert fh.tell() == 1000

        assert header1['frame_nr'] == 3
        assert header1['user'] == header['user']
        assert header1['bcd_jday'] == header['bcd_jday']
        assert header1['bcd_seconds'] == header['bcd_seconds']
        assert header1['bcd_fraction'] == 4
        assert (round((1./((header1.time-header.time)/3.)).to(u.Hz).value) ==
                6400)
        assert record.shape == (12, 8)
        assert np.all(record.astype(int)[:3] ==
                      np.array([[-3, -1, +1, -1, +3, -3, -3, +3],
                                [-3, +3, -1, +3, -1, -1, -1, +1],
                                [+3, -1, +3, +3, +1, -1, +3, -1]]))
        assert record2.shape == (2, 8)
        assert np.all(record2.astype(int) ==
                      np.array([[-1, -1, -1, +3, +3, -3, +3, -1],
                                [-1, +1, -3, +3, -3, +1, +3, +1]]))

        # Read all data and check that it can be written out.
        with mark5b.open(SAMPLE_FILE, 'rs', nchan=8, bps=2,
                         sample_rate=32*u.MHz, ref_mjd=57000) as fh:
            time0 = fh.tell(unit='time')
            record = fh.read(20000)
            time1 = fh.tell(unit='time')

        with io.BytesIO() as s, mark5b.open(s, 'ws', time=time0, nchan=8,
                                            bps=2, sample_rate=32*u.MHz) as fw:
            fw.write(record)
            assert fw.tell(unit='time') == time1
            fw.fh_raw.flush()

            s.seek(0)
            fh = mark5b.open(s, 'rs', nchan=8, bps=2, sample_rate=32*u.MHz,
                             ref_mjd=57000)
            assert fh.tell(unit='time') == time0
            record2 = fh.read(20000)
            assert fh.tell(unit='time') == time1
            assert np.all(record2 == record)

        # Check files can be made byte-for-byte identical.
        with io.BytesIO() as s, mark5b.open(
                s, 'ws', time=time0, nchan=8, bps=2, sample_rate=32*u.MHz,
                user=header['user'], internal_tvg=header['internal_tvg'],
                frame_nr=header['frame_nr']) as fw:

            fw.write(record)
            s.seek(0)
            with open(SAMPLE_FILE, 'rb') as fr:
                orig_bytes = fr.read()
                conv_bytes = s.read()
                assert conv_bytes == orig_bytes
