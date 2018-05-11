# Licensed under the GPLv3 - see LICENSE
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from ..vlbi_base.file_info import VLBIFileReaderInfo


class GUPPIFileReaderInfo(VLBIFileReaderInfo):
    _header0_attrs = ('bps', 'complex_data', 'sample_rate', 'sample_shape')

    def _collect_info(self):
        super(GUPPIFileReaderInfo, self)._collect_info()
        if self:
            # Use stream's samples_per_frame to avoid inconsistency if user
            # passes it into baseband.open.
            self.samples_per_frame = (self.header0.samples_per_frame -
                                      self.header0.overlap)
