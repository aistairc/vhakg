import os
import pickle
import numpy
import base64
from PIL import Image
from rdflib import Graph, Literal, URIRef, Namespace, RDF, RDFS, XSD
import glob
import io
import json
import math
import chardet
from decimal import Decimal, ROUND_HALF_UP
# from SPARQLWrapper import SPARQLWrapper, JSON
folder_path = "" # Path to the folder containing the person_bbox.pkl files
dataset_path = "path/to/the/dataset" # Path to the dataset folder
folder_list = os.listdir(folder_path)
activity_categories = [folder for folder in folder_list if os.path.isdir(os.path.join(folder_path, folder))]
ftaa_map = {}


def load_executed_program(category, scene, activity):
    file_path = dataset_path + category + "/executed_program/" + scene + "/" + activity + ".txt" # Path to the executed program file
    program = ""
    with open(file_path, 'r') as file:
        program = file.readlines()
        program = program[4:]

    # print(program)
    program = [line.strip() for line in program]
    return program


def load_ftaa(category, scene, activity):
    file_path = dataset_path + category + "/" + scene + "/" + activity + "/0/ftaa_" + activity + ".txt" # Path to the ftaa file
    ftaa = ""
    with open(file_path, 'r') as file:
        ftaa = file.readlines()

    # print(ftaa)
    ftaa = [line.strip() for line in ftaa]
    return ftaa

def create_frame_list(ftaa):
    # Align action script lines and ftaa
    start_frame = 0
    end_frame = 0
    tmp_id = 0
    frame_list = []
    ftaa_map = {}
    for line in ftaa:
        arr = line.split(" ")
        current_id = int(arr[0])
        action = arr[1]
        if current_id != tmp_id:
            if current_id > 0:
                frame_list.append((start_frame, end_frame))
            start_frame = arr[2]
        end_frame = arr[3]
        tmp_id = current_id
    frame_list.append((start_frame, end_frame))
    return frame_list

def detect_encoding(file_path):
    with open(file_path, 'rb') as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        confidence = result['confidence']
        return encoding, confidence

def load_2dbbox_json(category, scene, activity, frame, camera_mode):
    file_path = dataset_path + category + "/" + scene + "/" + activity + "/0/" + activity.replace("_", " ") + "_" + camera_mode + "/" + "Action_" + frame + "_" + camera_mode + "_2D.json" # Path to the 2D bbox json file
    encoding, confidence = detect_encoding(file_path)
    # print(encoding, confidence)

    json_str = None

    with open(file_path, 'r', encoding=encoding.lower()) as file:
        content = file.read()
        if "}{" in content:
            contents = content.split("}{")
            json_str = contents[0] + "}"
    if json_str is None:
        with open(file_path, 'r', encoding=encoding.lower()) as file:
            data = json.load(file)
    else:
        data = json.loads(json_str)
    return data["voList"]

def create_object_bbox_resource(g=None, frame_r=None, object_bbox_r=None, object_bbox_str=None, object_name=None, object_id=None, scene=None):
    ex = Namespace("http://kgrc4si.home.kg/virtualhome2kg/instance/")
    vh2kg = Namespace("http://kgrc4si.home.kg/virtualhome2kg/ontology/")
    mssn = Namespace("http://mssn.sigappfr.org/mssn/")
    g.add((object_bbox_r, RDF.type, mssn.BoundingBoxDescriptor))
    g.add((object_bbox_r, vh2kg["bbox-2d-value"], Literal(object_bbox_str)))
    g.add((frame_r, mssn.hasMediaDescriptor, object_bbox_r))
    g.add((object_bbox_r, RDFS.label, Literal(object_name)))
    g.add((object_bbox_r, vh2kg.is2DbboxOf, ex[object_name.replace(" ", "_") + str(object_id) + "_" + scene]))
    return g

def encodeVideoToBase64(file_path):
    encoded_string = None
    with open(file_path, 'rb') as file:
        encoded_string = base64.b64encode(file.read()).decode('utf-8')
    return encoded_string

def create_rdf(person_bbox_pickle_file_path):
    file_path_array = person_bbox_pickle_file_path.split("/")
    category = file_path_array[8]
    scene = file_path_array[9]
    activity = file_path_array[10]
    camera = file_path_array[12]
    camera_mode = camera[-1]

    # program = load_executed_program(category, scene, activity)
    ftaa = load_ftaa(category, scene, activity)

    if (activity + "_" + scene) not in ftaa_map:
        frame_list = create_frame_list(ftaa) # [(start, end), (start, end), ...]
        ftaa_map[activity + "_" + scene] = frame_list
    else:
        frame_list = ftaa_map[activity + "_" + scene]
    
    # Load the person bbox pickle file
    person_bbox_pickle = None
    with open(person_bbox_pickle_file_path, 'rb') as file:
        person_bbox_pickle = pickle.load(file)


    # Print the loaded data
    i = 1
    init = True
    frame_rate = 14.5
    original_frame_rate = 30.0
    tmp_mult = original_frame_rate / frame_rate
    fr_co = Decimal(tmp_mult).quantize(Decimal('0.01'), ROUND_HALF_UP)  #フレームレート変換係数
    g = Graph()
    ex = Namespace("http://kgrc4si.home.kg/virtualhome2kg/instance/")
    vh2kg = Namespace("http://kgrc4si.home.kg/virtualhome2kg/ontology/")
    mssn = Namespace("http://mssn.sigappfr.org/mssn/")
    schema = Namespace("https://schema.org/")
    sosa = Namespace("http://www.w3.org/ns/sosa/")
    g.bind("ex", ex)
    g.bind("mssn", mssn)
    g.bind("vh2kg", vh2kg)
    g.bind("schema", schema)
    g.bind("sosa", sosa)
    camera_recorded_r = ex[activity.replace(" ", "_").lower() + "_" + scene + "_camera" + camera_mode]
    activity_r = ex[activity.replace(" ", "_").lower() + "_" + scene]
    g.add((camera_recorded_r, RDF.type, mssn.MultimediaData))
    g.add((activity_r, vh2kg.hasVideo, camera_recorded_r))
    g.add((camera_recorded_r, vh2kg.isVideoOf, activity_r))
    g.add((camera_recorded_r, vh2kg.originalFrameRate, Literal(original_frame_rate, datatype=XSD.float)))
    g.add((camera_recorded_r, vh2kg.frameRate, Literal(frame_rate, datatype=XSD.float)))
    g.add((camera_recorded_r, vh2kg.hasResolution, Literal("640x480")))
    g.add((camera_recorded_r, sosa.madeBySensor, ex["camera" + camera_mode + "_" + scene]))
    g.add((camera_recorded_r, schema.encodingFormat, Literal("video/mp4")))
    base64text = encodeVideoToBase64(dataset_path + category + "/" + scene + "/movies/" + camera + ".mp4")
    g.add((camera_recorded_r, vh2kg.video, Literal(base64text, datatype=XSD.base64Binary)))
    
    event_counter = 0
    prev_object_bbox_dict = {}
    prev_image_resource_list = [] #前のフレームにおける分割された画像のリソース

    for person_img_file in sorted(person_bbox_pickle):

        dir_array = person_img_file.split("/")
        frame = dir_array[5].split("_")[1] # current frame
            
        ftaa_entity = frame_list[event_counter]
        start_frame = ftaa_entity[0]
        end_frame = ftaa_entity[1]

        if (int(frame) < int(start_frame) or int(frame) >=int(end_frame)) and event_counter < len(frame_list) - 1:
            # The current frame is within the scope of the next event.
            event_counter += 1
            ftaa_entity = frame_list[event_counter]
            start_frame = ftaa_entity[0]
            end_frame = ftaa_entity[1]
        
        video_segment_r = ex[camera.replace(" ", "_").lower() + "_" + scene + "_video_segment" + str(event_counter)]
        if (video_segment_r, vh2kg.hasStartFrame, None) not in g:
            g.add((video_segment_r, RDF.type, mssn.VisualSegment))
            g.add((video_segment_r, vh2kg.hasStartFrame, Literal(start_frame, datatype=XSD.integer)))
            g.add((video_segment_r, vh2kg.hasEndFrame, Literal(end_frame, datatype=XSD.integer)))
            
            # start time
            start_time_r = ex[camera.replace(" ", "_").lower() + "_" + scene + "_video_segment" + str(event_counter) + "_start_time"]
            g.add((start_time_r, RDF.type, mssn.MediaTimePointDescriptor))

            g.add((start_time_r, RDF.value, Literal((float(frame) * float(fr_co))/original_frame_rate, datatype=XSD.float)))
            g.add((video_segment_r, mssn.hasMediaDescriptor, start_time_r))
            # Duration is in EVENT and is not added individually.
            
            g.add((camera_recorded_r, mssn.hasMediaSegment, video_segment_r))
            event_r = ex["event" + str(event_counter) + "_" + activity.replace(" ", "_").lower() + "_" + scene]
            g.add((video_segment_r, vh2kg.isVideoSegmentOf, event_r))
            g.add((event_r, vh2kg.hasVideoSegment, video_segment_r))


        frame_r = ex[camera.replace(" ", "_").lower() + "_" + scene + "_frame" + frame]
        g.add((frame_r, RDF.type, mssn.VisualSegment))
        # g.add((frame_r, RDF.type, schema.ImageObject))
        g.add((frame_r, vh2kg.frameNumber, Literal(int(frame), datatype=XSD.integer)))
        g.add((video_segment_r, mssn.hasMediaDescriptor, frame_r))

        all_object_2dbboxes = load_2dbbox_json(category, scene, activity, frame, camera_mode)

        for object_bbox in all_object_2dbboxes:
            object_name = object_bbox["name"]
            object_id = object_bbox["id"]
            object_bbox_leftTop = str(object_bbox["leftTop"]["x"]) + "," + str(object_bbox["leftTop"]["y"])
            object_bbox_rightBottom = str(object_bbox["rightBottom"]["x"]) + "," + str(object_bbox["rightBottom"]["y"])
            predicate = object_bbox["predicate"]
            object_bbox_str = object_bbox_leftTop + "," + object_bbox_rightBottom
            if object_bbox_str == "0,0,0,0":
                continue
            if (object_name + str(object_id)) in prev_object_bbox_dict:
                prev_object_bbox_r = prev_object_bbox_dict[object_name + str(object_id)]
                prev_object_bbox_str = str(g.value(prev_object_bbox_r, vh2kg["bbox-2d-value"], None))
                # print("current_object_bbox_str, " + object_name +  ": " + object_bbox_str)
                # print("prev_object_bbox_str, " + object_name + ": " + prev_object_bbox_str)
                if prev_object_bbox_str == object_bbox_str:
                    # print("same bbox")
                    g.add((frame_r, mssn.hasMediaDescriptor, prev_object_bbox_r))
                else:
                    object_bbox_r = ex[camera.replace(" ", "_").lower() + "_" + scene + "_frame" + frame + "_" + object_name.replace(" ", "_") + str(object_id)]
                    g = create_object_bbox_resource(g=g, frame_r=frame_r, object_bbox_r=object_bbox_r, object_bbox_str=object_bbox_str, object_name=object_name, object_id=object_id, scene=scene)
                    prev_object_bbox_dict[object_name + str(object_id)] = object_bbox_r
            else:
                object_bbox_r = ex[camera.replace(" ", "_").lower() + "_" + scene + "_frame" + frame + "_" + object_name.replace(" ", "_") + str(object_id)]
                g = create_object_bbox_resource(g=g, frame_r=frame_r, object_bbox_r=object_bbox_r, object_bbox_str=object_bbox_str, object_name=object_name, object_id=object_id, scene=scene)
                prev_object_bbox_dict[object_name + str(object_id)] = object_bbox_r
    
    # Create the scene1 folder if it doesn't exist
    scene_folder_path = os.path.join("./output/vhakg_video_base64/" + category + "/", scene)
    if not os.path.exists(scene_folder_path):
        os.makedirs(scene_folder_path)
    g.serialize(destination="./output/vhakg_video_base64/" + category + "/" + scene + "/vhakg_" + activity + "_" + scene + "_camera" + camera_mode +  "_2dbbox.ttl", format="turtle")
    return False

person_bbox_pickle_files = sorted(glob.glob(folder_path + "*/*/*/0/*/person_bbox.pkl"))
# person_bbox_pickle_files = sorted(glob.glob(folder_path + activity_categories[0] + "/*/*/0/*/person_bbox.pkl"))
# object_bbox_pickle_files = sorted(glob.glob(folder_path + activity_categories[0] + "/scene1/*/0/*/object_bbox_and_relationship.pkl"))

for person_bbox_pickle_file_path in person_bbox_pickle_files:
    # Load the pickle file
    print(person_bbox_pickle_file_path)
    create_rdf(person_bbox_pickle_file_path)