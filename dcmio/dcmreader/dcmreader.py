#! /usr/bin/env python
# -*- coding: utf-8 -*-
##########################################################################
# NSAP - Copyright (C) CEA, 2013
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# Diverse dicom reading functions to extract precise information

import dicom
import os
import logging


# dataset Walker (to browse enhanced dicom efficiently)
def walk(dataset, callback, _tag, stack_values=False):
    """ Function to read DICOM files and extract fields content

    .. note::

        Recusrive function is required as new enhanced storage presents only
        one dicom containing several sub-sequence of fields.
        The walked is called on each sub-sequence
        The first corresponding tag's value is returned: the walker stops as
        soon as a value is found.

    Parameters
    ----------
    inputs :
        dataset: a dataset structure (ourput from pydicom reader) (mandatory)
            the dataset to read
        callback: function that will be called on each field (value extraction)
        _tag : the tag of the field containing the value to extract. Only the
        first field with this tag is read.
        all_value: if set to True, a list of all values is returned. The first
            value is returned otherwise.

    Returns :
    The value in the chosen field. None if the field has not been found
    dictionary of modified fields path (if asked)
    """
    taglist = sorted(dataset.keys())
    if stack_values:
        out_list = []
    for tag in taglist:
        data_element = dataset[tag]
        out = callback(data_element, _tag)
        if out:
            if stack_values:
                out_list.append(out)
            else:
                return out
        elif tag in dataset and data_element.VR == "SQ":
            sequence = data_element.value
            for sub_dataset in sequence:
                out = walk(sub_dataset, callback, _tag,
                           stack_values=stack_values)
                if out:
                    if stack_values:
                        out_list.extend(out)
                    else:
                        return out

    if stack_values:
        return out_list
    return None


def walker_callback(data_element, _tag):
    """Called from the dataset "walk" recursive function for
        all data elements. Extract field's content.

    Parameters
    ----------
    inputs :
        data_element: the field to examine
        _tag : the tag of the field containing the value to extract. Only the
        first field with this tag is read.stack_values: boolean (optional).
        Only the first field with this tag is read if False, return a list of
        values if True. Default = False

    Returns :
    The value in the chosen field. None if the field is not the one asked

    """
    if data_element.tag == _tag:
        return data_element.value
    return None


def get_phase_encoding(path_to_dicom):
    """
        Get the phase encoding direction as string ("ROW" or "COL")

    Parameters
    ----------
    inputs :
        path_to_dicom: a filepath (mandatory) to the dicom from which the
            data extraction will be made

    Returns :
        the phase encoding (none if not found)
    """
    dataset = dicom.read_file(path_to_dicom, force=True)
    value = walk(dataset, walker_callback, (0x0018, 0x1312), stack_values=True)
    if value:
        return str(value[0])
    elif value == []:
        return None
    return value


def get_b_vectors(path_to_dicom):
    """
        Get the b-vectors as list of lists

    Parameters
    ----------
    inputs :
        path_to_dicom: a filepath (mandatory) to the dicom from which the
            data extraction will be made

    Returns :
        the b-vectors (empty list if not found)
    """
    dataset = dicom.read_file(path_to_dicom, force=True)
    return walk(dataset, walker_callback, (0x0018, 0x9089), stack_values=True)


def get_b_values(path_to_dicom):
    """
        Get the b-values as list

    Parameters
    ----------
    inputs :
        path_to_dicom: a filepath (mandatory) to the dicom from which the
            data extraction will be made

    Returns :
        the b-vectors (empty list if not found)
    """
    dataset = dicom.read_file(path_to_dicom, force=True)
    return walk(dataset, walker_callback, (0x0018, 0x9087), stack_values=True)


def get_repetition_time(path_to_dicom):
    """
        Get the repetition time as string

    Parameters
    ----------
    inputs :
        path_to_dicom: a filepath (mandatory) to the dicom from which the
            data extraction will be made

    Returns :
        the repetition time value (None if the value is not found)
    """
    dataset = dicom.read_file(path_to_dicom, force=True)
    tr = walk(dataset, walker_callback, (0x0018, 0x0080))
    if tr:
        # convert in ms
        if tr < 1000:
            tr *= 1000.
        return "{0}".format(tr)
    return None


def get_date_scan(path_to_dicom):
    """
        Get the date scan as string

    Parameters
    ----------
    inputs :
        path_to_dicom: a filepath (mandatory) to the dicom from which the
            data extraction will be made

    Returns :
        the date scan value ('0' if the value is not found)
    """
    dataset = dicom.read_file(path_to_dicom, force=True)
    value = walk(dataset, walker_callback, (0x0008, 0x0022))
    if value:
        return value
    return '0'


def get_echo_time(path_to_dicom):
    """
        Get the echo time as string

    Parameters
    ----------
    inputs :
        path_to_dicom: a filepath (mandatory) to the dicom from which the
            data extraction will be made

    Returns :
        the echo time value (-1 if the value is not found)
    """
    dataset = dicom.read_file(path_to_dicom, force=True)
    value = walk(dataset, walker_callback, (0x0018, 0x0081))
    if value:
        return value
    return -1


def get_all_sop_instance_uids(path_to_dicom):
    """
        Get all the Referenced SOP Instance UID (used fot the pilot, proof
        of concept)

    Parameters
    ----------
    inputs :
        path_to_dicom: a filepath (mandatory) to the dicom from which the
            data extraction will be made

    Returns :
        the Referenced SOP Instance UID values ([] if no fields are found)
    """
    dataset = dicom.read_file(path_to_dicom, force=True)
    return walk(dataset, walker_callback, (0x0008, 0x1155), stack_values=True)


def get_sop_storage_type(path_to_dicom):
    """
        Get the storage type as boolean (True if enhanced, False otherwise)
        dafault=False

    Parameters
    ----------
    inputs :
        path_to_dicom: a filepath (mandatory) to the dicom from which the
            data extraction will be made

    Returns :
        the storage type ('False' if the value is not found)
    """
    dataset = dicom.read_file(path_to_dicom, force=True)
    value = walk(dataset, walker_callback, (0x0008, 0x0016))
    if value:
        if "Enhanced" in str(value):
            return True
    return False


def get_raw_data_run_number(path_to_dicom):
    """
    Get the raw data run number as string

    ..note: private field: designed for GE scan (LONDON IOP centre)

    Parameters
    ----------
    inputs :
        path_to_dicom: a filepath (mandatory) to the dicom from which the
            data extraction will be made

    Returns :
        the raw data run number (-1 if the value is not found)
    """
    dataset = dicom.read_file(path_to_dicom, force=True)
    value = walk(dataset, walker_callback, (0x0019, 0x10a2))
    if value:
        return value
    return -1


def get_sequence_number(path_to_dicom):
    """
    Get the sequence number as string

    Parameters
    ----------
    inputs :
        path_to_dicom: a filepath (mandatory) to the dicom from which the
            data extraction will be made

    Returns :
        the sequence number ('0' if the value is not found)
    """
    dataset = dicom.read_file(path_to_dicom, force=True)
    value = walk(dataset, walker_callback, (0x0020, 0x0011))
    if value:
        return value
    return '0'


def get_nb_slices(path_to_dicom):
    """
    Get the number of slices as Integer

    Parameters
    ----------
    inputs :
        path_to_dicom: a filepath (mandatory) to the dicom from which the
            data extraction will be made

    Returns :
        the number of slices (0 if the value is not found)
    """
    dataset = dicom.read_file(path_to_dicom, force=True)
    value = walk(dataset, walker_callback, (0x0020, 0x1002))
    if value:
        return int(value)
    else:
        value = walk(dataset, walker_callback, (0x2001, 0x1018))
        if value:
            return int(value)
    return 0


def get_nb_temporal_position(path_to_dicom):
    """
    Get the number of volumes (temporal positions) as Integer

    Parameters
    ----------
    inputs :
        path_to_dicom: a filepath (mandatory) to the dicom from which the
            data extraction will be made

    Returns :
        the number of volumes (temporal positions)
        (0 if the value is not found)
    """
    dataset = dicom.read_file(path_to_dicom, force=True)
    value = walk(dataset, walker_callback, (0x0020, 0x0105))
    if value:
        return int(value)
    return 0


def get_manufacturer_name(path_to_dicom):
    """
    Get manufacturer name as string

    ..note: spaces are replaced by "_" in the extracted value

    Parameters
    ----------
    inputs :
        path_to_dicom: a filepath (mandatory) to the dicom from which the
            data extraction will be made

    Returns :
        the manufacturer name ('unknown' if the value is not found)
    """
    dataset = dicom.read_file(path_to_dicom, force=True)
    value = walk(dataset, walker_callback, (0x0008, 0x0070))
    if value:
        return value.replace(" ", "_")
    return "unknown"


def get_manufacturer_model_name(path_to_dicom):
    """
    Get manufacturer model name as string

    ..note: spaces are replaced by "_" in the extracted value

    Parameters
    ----------
    inputs :
        path_to_dicom: a filepath (mandatory) to the dicom from which the
            data extraction will be made

    Returns :
        the manufacturer model name ('unknown' if the value is not found)
    """
    dataset = dicom.read_file(path_to_dicom, force=True)
    value = walk(dataset, walker_callback, (0x0008, 0x1090))
    if value:
        return value.replace(" ", "_")
    return "unknown"


def get_sequence_name(path_to_dicom):
    """
    Get sequence name as string

    ..note: spaces are replaced by "_" in the extracted value

    Parameters
    ----------
    inputs :
        path_to_dicom: a filepath (mandatory) to the dicom from which the
            data extraction will be made

    Returns :
        the sequence name ('unknown' if the value is not found)
    """
    dataset = dicom.read_file(path_to_dicom, force=True)
    value = walk(dataset, walker_callback, (0x0008, 0x103e))
    if value:
        return value.replace(" ", "_")
    return "unknown"


def get_SOPInstanceUID(path_to_dicom):
    """
    Get SOP instance uid name as string

    ..note: spaces are replaced by "_" in the extracted value

    Parameters
    ----------
    inputs :
        path_to_dicom: a filepath (mandatory) to the dicom from which the
            data extraction will be made

    Returns :
        the uid ('unknown' if the value is not found)
    """
    dataset = dicom.read_file(path_to_dicom, force=True)
    value = walk(dataset, walker_callback, (0x0008, 0x0018))
    if value:
        return value.replace(" ", "_")
    return "unknown"


def get_InstanceCreationTime(path_to_dicom):
    """
    Get screation time as float

    Parameters
    ----------
    inputs :
        path_to_dicom: a filepath (mandatory) to the dicom from which the
            data extraction will be made

    Returns :
        the creation time ('unknown' if the value is not found)
    """
    dataset = dicom.read_file(path_to_dicom, force=True)
    value = walk(dataset, walker_callback, (0x0008, 0x0013))
    if value:
        return float(value)
    return "unknown"



def get_protocol_name(path_to_dicom):
    """
    Get protocol name as string

    ..note: spaces are replaced by "_" in the extracted value

    Parameters
    ----------
    inputs :
        path_to_dicom: a filepath (mandatory) to the dicom from which the
            data extraction will be made

    Returns :
        the protocol name ('unknown' if the value is not found)
    """

    dataset = dicom.read_file(path_to_dicom, force=True)
    value = walk(dataset, walker_callback, (0x0018, 0x1030))
    if value:
        return value.replace(" ", "_")
    return "unknown"


def get_serie_serieInstanceUID(path_to_dicom):
    """
    Get serie UID as string

    ..note: spaces are replaced by "_" in the extracted value

    Parameters
    ----------
    inputs :
        path_to_dicom: a filepath (mandatory) to the dicom from which the
            data extraction will be made

    Returns :
        the serie UID ('unknown' if the value is not found)
    """
    dataset = dicom.read_file(path_to_dicom, force=True)
    value = walk(dataset, walker_callback, (0x0020, 0x000e))
    if value:
        return value.replace(" ", "_")
    return "unknown"


def get_number_of_slices_philips(path_to_dicom):
    """
    Get number of slices for Philips scans as integer

    Parameters
    ----------
    inputs :
        path_to_dicom: a filepath (mandatory) to the dicom from which the
            data extraction will be made

    Returns :
        value of "NumberOfSlicesMR" field, 0 if value not found
    """
    try:
        # run dcmdump and read number of slices inside. pydicom is unable
        # to extract the information
        temporary_text_file = os.path.join(os.path.dirname(path_to_dicom),
                                           "temp.txt")
        os.system("dcmdump {0} > {1}".format(path_to_dicom,
                                             temporary_text_file))
        # load text file
        buff = open(temporary_text_file, "r")
        for line in buff.readlines():
            if "StackNumberOfSlices" in line:
                temp = line
                break
        buff.close()
        # Remove temp file
        os.remove(temporary_text_file)
        # Now we have the line, remove spaces
        value = temp.replace(' ', '')
        # return the last 2 character as integer (we assume that there will
        # always be more than 9 slices)
        return int(value.split('#')[0][-2:])
    except:
        logging.warning("WARNING: no 'NumberOfSlicesMR' field")
        return 0
