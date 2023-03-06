from ctypes import *
import datetime
import numpy as np
import binascii
from pathlib import Path
import struct
import carla


# class LogParser(structure):

def parse_string(byte_string:bytes):
    null_byte = b'\x00'
    splits = byte_string.split(null_byte,1)
    str_length = int(splits[0].hex(),16)

    string_data = struct.unpack(f'<{str_length}s',splits[1][:str_length])[0].decode()
    
    string_end = len(splits[0]) + 1 + str_length  # first index after the string end

    return string_data, string_end

# class LogHeader(Structure):
#     _fields_ = [
#         ("version",c_uint16),
#         ("magic_str",c_char,8),
#         ("date",c_time)
#     ]

def parse_infoheader(bytedata:bytes):
    header_info = {}
    start_idx = 0

    # version
    version_hexsize = 2
    version_end = start_idx+version_hexsize
    header_info["version"] = struct.unpack('<H',bytedata[start_idx:version_end])[0]

    # magic
    magic_start = version_end
    header_info["magic_str"], magic_end = parse_string(bytedata[magic_start:])

    # date
    date_bytesize = 8
    date_start = magic_start+magic_end
    date_end = date_start+date_bytesize
    header_info["date"] = struct.unpack('<Q',bytedata[date_start:date_end])[0]

    # map
    map_start = date_end
    header_info["map"], map_end = parse_string(bytedata[map_start:])

    header_end = map_start+map_end

    return header_info, header_end

def parse_packet(bytedata:bytes):
    packet = {}
    
    header_end = 5
    packet_id, data_size = struct.unpack('<BI',bytedata[:header_end])
    packet_end = header_end + data_size

    data_bytes = bytedata[header_end:packet_end]
    
    if packet_id==0:
        # Frame Start
        packet["frame_id"],packet["duration"],packet["elapsed"] = struct.unpack('<Qdd',data_bytes)
    elif packet_id==2:
        # Add
        total, id = struct.unpack('<HI',data_bytes[:6])[0]
    return packet, packet_end

host = 'localhost'
port = 2000
client = carla.Client(host,port)

logfile = Path('')

# format = Struct("Info")
# data_dict = np.fromfile(logfile,dtype=[("Info",[("version",np.uint16),("magic",str),("date",np.uint64),("map",str)])])
# print(data_dict)
client.set_timeout(120.0)
parsed = client.show_recorder_file_info(str(logfile), True)
with open(logfile,'rb') as f:
    # print(f.readline())
    lines = f.read()
    infoheader, infoheader_end = parse_infoheader(lines)
    packet0, packet0_end = parse_packet(lines[infoheader_end:])
    packet1, packet1_end = parse_packet(lines[infoheader_end+packet0_end:])
        