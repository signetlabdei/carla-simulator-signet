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

def parse_FVector(bytedata:bytes):
    vector = {}
    vector["x"],vector["y"],vector["z"] = struct.unpack("<fff", bytedata)
    return vector
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


def parse_position_record(bytedata:bytes):
    pos = {}
    pos["id"],pos["x"],pos["y"],pos["z"],pos["pitch"],pos["yaw"],pos["roll"] = struct.unpack("<Iffffff", bytedata)
    return pos

def parse_collision_record(bytedata:bytes):
    coll = {}
    coll["recording_id"],coll["actor_1_id"],coll["actor_2_id"],coll["is_hero_1"],coll["is_hero_2"] = struct.unpack("<III??", bytedata)
    return coll

def parse_state_record(bytedata:bytes):
    state = {}
    state["id"], state["is_frozen"], state["elapsed_time"], state["state"] = struct.unpack("<I?fc", bytedata)
    return state

def parse_animVehicle_record(bytedata:bytes):
    animVehicle = {}
    animVehicle["id"], animVehicle["Steering"], animVehicle["Throttle"], animVehicle["Brake"] , animVehicle["bHandbrake"] , animVehicle["Gear"] = struct.unpack("<Ifff?i", bytedata)
    return animVehicle

def parse_animWalker_record(bytedata:bytes):
    animWalker = {}
    animWalker["id"], animWalker["Speed"] = struct.unpack("<If", bytedata)
    return animWalker


def parse_kinematic_record(bytedata:bytes):
    kinematic = {}
    kinematic["id"] = struct.unpack("<If", bytedata[:2])[0]
    kinematic["Speed"] = parse_FVector(bytedata[2:14])
    kinematic["AngularVelocity"] = parse_FVector(bytedata[14:26])
    return kinematic

def parse_boundingbox_record(bytedata:bytes):
    bounding_box = {}
    bounding_box["id"] = struct.unpack("<If", bytedata[:2])[0]
    bounding_box["Origin"] = parse_FVector(bytedata[2:14])
    bounding_box["Estention"] = parse_FVector(bytedata[14:26])
    return bounding_box

def parse_delevent_record(bytedata:bytes):
    del_event = {}
    del_event["DatabaseId"] = struct.unpack("<I", bytedata)[0]
    return(del_event)

def parse_eventParent_record(bytedata:bytes):
    parent_event = {}
    parent_event["DatabaseId"],parent_event["DatabaseParentId"] = struct.unpack("<II", bytedata)
    return parent_event

def parse_VehicleLight_record(bytedata:bytes):
    vehicleLight = {}
    vehicleLight["DatabaseId"],vehicleLight["State"] = struct.unpack("<II", bytedata)
    return vehicleLight

def parse_SceneLight_record(bytedata:bytes):
    sceneLight = {}
    # TODO
    return sceneLight

def parse_multiple_records(packet:dict, data_bytes:bytes, record_name:str, record_length:int, f_parse_single):
    packet["n_record"] = struct.unpack("<H", data_bytes[0:2])[0]
    packet[record_name] = []
    for i in range(packet["n_record"]):
        start = 2 + i * record_length
        end = 2 + i * record_length + record_length
        packet[record_name].append(f_parse_single(data_bytes[start:end]))


def parse_packet(bytedata:bytes):
    packet = {}
    
    header_end = 5
    packet_id, data_size = struct.unpack('<BI',bytedata[:header_end])
    packet_end = header_end + data_size

    packet["id"] = packet_id

    data_bytes = bytedata[header_end:packet_end]
    
    if packet_id==0: # Frame Start
        packet["frame_id"],packet["duration"],packet["elapsed"] = struct.unpack('<Qdd',data_bytes)

    elif packet_id==1: #Frame End
        pass

    elif packet_id==2: #Add event
        pass #TODO

    elif packet_id==3: #Del event
        parse_multiple_records(packet, data_bytes, "EventsDel", 4, parse_delevent_record)

    elif packet_id==4: #EventParent
        parse_multiple_records(packet, data_bytes, "EventParent", 8, parse_eventParent_record)

    elif packet_id==5: # Collsion
        parse_multiple_records(packet, data_bytes, "collisions", 14, parse_collision_record)

    elif packet_id==6: # Position
        parse_multiple_records(packet, data_bytes, "positions", 28, parse_position_record)

    elif packet_id==7: # state
        parse_multiple_records(packet, data_bytes, "states", 10, parse_state_record)
        
    elif packet_id==8: # anim vehicle
        parse_multiple_records(packet, data_bytes, "AnimVehicle", 21, parse_animVehicle_record)

    elif packet_id==9: # anim walkers
        parse_multiple_records(packet, data_bytes, "AnimWalkers", 8, parse_animWalker_record)

    elif packet_id==10: #VehicleLight
        parse_multiple_records(packet, data_bytes, "VehicleLight", 8, parse_VehicleLight_record)

    elif packet_id==11: #SceneLight
        #parse_multiple_records(packet, data_bytes, "SceneLight", 0, parse_SceneLight_record)
        pass
        
    elif packet_id==12: #Kinematics
        parse_multiple_records(packet, data_bytes, "Kinematics", 28, parse_kinematic_record)
        
    elif packet_id==13: #BoundingBox
        parse_multiple_records(packet, data_bytes, "BoundingBoxes", 28, parse_boundingbox_record)

    elif packet_id==14: #PlatformTime
        packet['time'] = struct.unpack('<d',data_bytes)

    elif packet_id==15:
        pass

    elif packet_id==16:
        pass

    elif packet_id==17: #TriggerVolume
        parse_multiple_records(packet, data_bytes, "TriggerVolume", 26, parse_boundingbox_record)
        
    elif packet_id==18:
        packet['FrameCounter'] = struct.unpack('<Q',data_bytes)

    elif packet_id==19:
        pass

    elif packet_id==20:
        packet['time'] = struct.unpack('<d',data_bytes)
        
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
        