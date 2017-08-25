# Copyright (C) 2014 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#      add by  zhigang.yu@amlogic.com
#

from __future__ import print_function

import os
import copy
import common
import sparse_img
import add_img_to_target_files

def CopyPartitionFiles(partition, input_zip, output_zip=None, substitute=None):
  """Copies files for the partition in the input zip to the output
  zip.  Populates the Item class with their metadata, and returns a
  list of symlinks.  output_zip may be None, in which case the copy is
  skipped (but the other side effects still happen).  substitute is an
  optional dict of {output filename: contents} to be output instead of
  certain input files.
  """

  symlinks = []

  for info in input_zip.infolist():
    if info.filename.startswith(partition.upper() + "/"):
      prelen = len(partition) + 1
      basefilename = info.filename[prelen:]

      info2 = copy.copy(info)
      fn = info2.filename = partition + "/" + basefilename
      if substitute and fn in substitute and substitute[fn] is None:
        continue
      if output_zip is not None:
        if substitute and fn in substitute:
          data = substitute[fn]
        else:
          data = input_zip.read(info.filename)
        output_zip.writestr(info2, data)

  symlinks.sort()
  return symlinks

def GetImage(which, tmpdir, output_zip, info_dict):
  # Return an image object (suitable for passing to BlockImageDiff)
  # for the 'which' partition (most be "system" or "vendor").  If a
  # prebuilt image and file map are found in tmpdir they are used,
  # otherwise they are reconstructed from the individual files.

  path = os.path.join(tmpdir, "IMAGES", which + ".img")
  mappath = os.path.join(tmpdir, "IMAGES", which + ".map")

  # The image and map files must have been created prior to calling
  # ota_from_target_files.py (since LMP).
  assert os.path.exists(path) and os.path.exists(mappath)

  # Bug: http://b/20939131
  # In ext4 filesystems, block 0 might be changed even being mounted
  # R/O. We add it to clobbered_blocks so that it will be written to the
  # target unconditionally. Note that they are still part of care_map.
  clobbered_blocks = "0"

  return sparse_img.SparseImage(path, mappath, clobbered_blocks)

def Buildimage(script, info_dict, input_tmp, input_zip, output_zip):

  if "user_parts_list" not in info_dict:
    return

  partsList = info_dict.get("user_parts_list");
  upgrade_parts_image = info_dict.get("upgrade_parts_image");
  for list_i in partsList.split(' '):
    if upgrade_parts_image:
      image_tgt = GetImage(list_i, input_tmp, output_zip, info_dict)
      image_tgt.ResetFileMap()
      image_diff = common.BlockDifference(list_i, image_tgt, src = None)
      image_diff.WriteScript(script, output_zip)
    else:
      CopyPartitionFiles(list_i, input_zip, output_zip)
      recovery_mount_options = info_dict.get("recovery_mount_options")
      script.Mount("/"+list_i, recovery_mount_options)
      script.UnpackPackageDir(list_i, "/" + list_i)
      script.Unmount("/"+list_i)