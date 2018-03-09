#!/usr/bin/env python3

import collections
import pprint
import re
import sys


_ORIG_FNAME = './nvid.c'

_VENDOR_BASE = '../../patches/HUAWEI-P9-Lite_OpenSource/'

_VENDOR_1 = (
    _VENDOR_BASE + 'drivers/hisi/modem/include/nv/tl/lps/lt_phy_nv_define.h',
    _VENDOR_BASE + 'drivers/hisi/modem/config/nvim/include/gu/RfNvId.h',
    _VENDOR_BASE + 'drivers/hisi/modem/include/nv/tl/lps/LNvCommon.h',
)

_VENDOR_2 = (
    _VENDOR_BASE + 'drivers/hisi/modem/config/nvim/include/gu/SysNvId.h',
    _VENDOR_BASE + 'drivers/hisi/modem/config/nvim/include/gu/PsNvId.h',
    _VENDOR_BASE + 'drivers/hisi/modem/config/nvim/include/gu/CfdNvId.h',
)

_VENDOR_3 = (
    _VENDOR_BASE + 'drivers/hisi/modem/config/nvim/include/gu/CodecNvId.h',
)

_DEBUG = False
#_DEBUG = True


def _parse_orig(fname):
    with open(fname, 'r') as orig:
        list_started = False
        n = 0
        for raw_line in orig:
            n += 1
            line = raw_line.strip()

            if 'struct nvdesc nvid[] = {' in line:
                list_started = True
            elif list_started:
                line = line.lstrip('{')
                line = line.rstrip(',')
                line = line.rstrip('}')

                line = [comp.strip() for comp in line.split(',')]

                if len(line) != 3:
                    raise RuntimeError(
                        "Invalid line N%d: \"%s\"" % (n, raw_line))

                nv_id, nv_name, nv_desc = line

                nv_id = int(nv_id)

                if (nv_name == '0') or (nv_name == 'NULL'):
                    nv_name = None
                else:
                    nv_name = nv_name.strip('"')

                if (nv_desc == '0') or (nv_desc == 'NULL'):
                    nv_desc = None
                else:
                    nv_desc = nv_desc.strip('"')

                if (nv_id == 0) and (nv_name is None) and (nv_desc is None):
                    list_started = False
                else:
                    if nv_name is None:
                        raise RuntimeError(
                            "Invalid line N%d: \"%s\" (no name)" % (
                                n, raw_line))

                    yield {
                        'id': nv_id,
                        'name': nv_name,
                        'desc': nv_desc,
                    }
            else:
                # This line is not interesting.
                pass


def _normalize(item_gen):
    items = collections.OrderedDict()

    for item in item_gen:
        nv_id = item['id']

        item = {
            'name': [item['name']],
            'desc': [item['desc']],
        }

        existing = items.get(nv_id)
        if existing is None:
            items[nv_id] = item
        else:
            existing['name'].extend(item['name'])
            existing['desc'].extend(item['desc'])

    if _DEBUG:
        print("**** Duplicate IDs merged", file=sys.stderr)
        print(pprint.pformat(items), file=sys.stderr)

    return items


def _parse_vendor_1(fname):
    regexp = re.compile(r'(?i)\s*/*\**\s*([^\s]*NV[^\s]+)\s*=\s*([0-9a-fx]+).*$')

    with open(fname, 'rb') as vendor:
        for raw_line in vendor.read().decode('ascii', 'replace').split('\n'):
            line = raw_line.strip()

            match = regexp.match(line)
            if match is not None:
                yield {
                    'id': int(match.group(2), 0),
                    'name': match.group(1),
                    'desc': None,
                }


def _parse_vendor_2(fname):
    #     /* 8494  */      en_NV_Item_OPERLOCK_PLMN_INFO_WHITE = 8494,
    regexp1 = re.compile(
        r'(?i)\s*(/\*.*\*/)?\s*([^\s]*NV[^\s]+)\s*=\s*([0-9a-fx]+).*$')
    #/* 8267  */      en_NV_Item_CustomizeSimLockPlmnInfo = GU_PS_NV_ID_MIN + 74,
    regexp2 = re.compile(
        r'(?i)\s*/\*\s*([0-9a-fx]+)\s*\*/\s*([^\s]*NV[^\s,=]+).*$')

    with open(fname, 'rb') as vendor:
        for raw_line in vendor.read().decode('ascii', 'replace').split('\n'):
            line = raw_line.strip()

            match = regexp1.match(line)
            if match is not None:
                yield {
                    'id': int(match.group(3), 0),
                    'name': match.group(2),
                    'desc': None,
                }
            else:
                match = regexp2.match(line)
                if match is not None:
                    yield {
                        'id': int(match.group(1), 0),
                        'name': match.group(2),
                        'desc': None,
                    }


def _parse_vendor_3(fname):
    # en_NV_Item_MaxVolLevel = 0x7530,                                          /* 30000 */
    regexp1 = re.compile(
        r'(?i)\s*(/\*.*\*/)?\s*([^\s]*NV[^\s]+)\s*=\s*([0-9a-fx]+).*$')
    #      en_NV_WB_HandSet1,                                                        /* 30038 */                                                       /* 12335 */
    regexp2 = re.compile(
        r'(?i)\s*(/\*.*\*/)?\s*([^\s]*NV[^\s,=]+)\s*,\s*/\*\s*([0-9a-fx]+)\s*\*/.*$')

    with open(fname, 'rb') as vendor:
        for raw_line in vendor.read().decode('ascii', 'replace').split('\n'):
            line = raw_line.strip()

            match = regexp1.match(line)
            if match is not None:
                yield {
                    'id': int(match.group(3), 0),
                    'name': match.group(2),
                    'desc': None,
                }
            else:
                match = regexp2.match(line)
                if match is not None:
                    yield {
                        'id': int(match.group(3), 0),
                        'name': match.group(2),
                        'desc': None,
                    }


def _deduplicate_names(items):
    for item in items.values():
        names = item['name']
        n_names = len(names)

        if n_names == 1:
            # Single name/description, nothing to deduplicate.
            continue

        for i in range(0, n_names - 1):
            name = names[i]
            try:
                duplicate_idx = names[i + 1:].index(name) + i + 1

                names[duplicate_idx] = None
                item['desc'][duplicate_idx] = None
            except ValueError:
                # No duplicate name.
                pass

    if _DEBUG:
        print("**** Original list (duplicate names removed):", file=sys.stderr)
        print(pprint.pformat(items), file=sys.stderr)

    return items


def _merge(items_into, items_new):
    for k, v in items_new.items():
        if k not in items_into:
            items_into[k] = v


def _generate_c(items, description):
    #print("// **** C code (%s):" % (description, ))

    items = collections.OrderedDict(sorted(items.items()))

    for nv_id, nv_name_desc in items.items():
        names = nv_name_desc['name']
        descs = nv_name_desc['desc']
        n_names = len(names)

        nv_name = ''
        nv_desc = ''
        for i in range(0, n_names):
            if names[i] is None:
                continue

            if nv_name:
                nv_name += '.' + names[i]
            else:
                nv_name = names[i]

            if nv_desc:
                if descs[i]:
                    nv_desc += ' | ' + descs[i]
            else:
                if descs[i]:
                    nv_desc += descs[i]

        nv_name = '"' + nv_name + '"'
        if nv_desc:
            nv_desc = '"' + nv_desc + '"'
        else:
            nv_desc = '0'

        print('{%5d,%s,%s},' % (nv_id, nv_name, nv_desc))

    print('{0,0,0}')


def main():
    original_list = _normalize(_parse_orig(_ORIG_FNAME))
    original_list = _deduplicate_names(original_list)
    #_generate_c(original_list, "original, without duplicates")

    for vendor1_fname in _VENDOR_1:
        vendor1 = _normalize(_parse_vendor_1(vendor1_fname))
        vendor1 = _deduplicate_names(vendor1)
        _merge(original_list, vendor1)
    #_generate_c(original_list, "+ %r" % (_VENDOR_1, ))

    for vendor2_fname in _VENDOR_2:
        vendor2 = _normalize(_parse_vendor_2(vendor2_fname))
        vendor2 = _deduplicate_names(vendor2)
        _merge(original_list, vendor2)
    #_generate_c(original_list, "+ %r" % (_VENDOR_2, ))

    for vendor3_fname in _VENDOR_3:
        vendor3 = _normalize(_parse_vendor_3(vendor3_fname))
        vendor3 = _deduplicate_names(vendor3)
        _merge(original_list, vendor3)
    _generate_c(original_list, "+ %r" % (_VENDOR_3, ))


main()
