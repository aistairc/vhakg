# VHAKG

VHAKG is a multi-modal temporal knowledge graph (MMTKG) of multi-view videos of daily activities.
This repository explains VHAKG and provides sample files.

The dataset is available on Zenodo.  
**The URL is hidden for double-blined review.**

## Schema

The KG schema is defined as [OWL file](./vh2kg_schema_v2.0.0.ttl).

![KG](./kg.png)

## Sample data

- [image_rdf](./sample/image_rdf/)/*.ttl
    - MMTKG with video frame image data directly embedded as literal values
- [video_rdf](./sample/video_rdf/)/*.ttl
    - MMTKG with video data directly embedded as literal values