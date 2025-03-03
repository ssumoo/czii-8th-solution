import argparse
from omegaconf import OmegaConf
import numpy as np
import pandas as pd
import re

# Define dotdict for easy attribute access
class dotdict(dict):
    """Dot-access dictionary."""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def get_args():
  parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("--config", type=str, default="config.yaml")
  parser.add_argument("opts", default=[], nargs=argparse.REMAINDER,
                      help="Modify config options using the command-line")
  args = parser.parse_args()
  return args

def get_cfg(path):
    args = get_args()
    cfg = OmegaConf.load(path)

    cfg = OmegaConf.merge(cfg, OmegaConf.from_cli(args.opts))
    return cfg

def seed_everything(seed):
    print(f"seeding code with: {seed=}")
    import random, os
    import numpy as np
    import torch

    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = True


def dict_to_df(coord_dict, experiment_name):
    """
    Convert dictionary of coordinates to pandas DataFrame.
    """
    # Create lists to store data
    all_coords = []
    all_labels = []
    
    # Process each label and its coordinates
    for label, coords in coord_dict.items():
        all_coords.append(coords)
        all_labels.extend([label] * len(coords))
    
        # Concatenate all coordinates
    all_coords = np.vstack(all_coords)
    
    df = pd.DataFrame({
        'experiment': experiment_name,
        'particle_type': all_labels,
        'x': all_coords[:, 0],
        'y': all_coords[:, 1],
        'z': all_coords[:, 2]
    })
    
    return df

def calculate_patch_starts(dimension_size: int, patch_size: int) -> list[int]:
    """
    Calculate the starting positions of patches along a single dimension
    with minimal overlap to cover the entire dimension.
    """
    if dimension_size <= patch_size:
        return [0]
        
    # Calculate number of patches needed
    n_patches = np.ceil(dimension_size / patch_size)
    
    if n_patches == 1:
        return [0]
    
    # Calculate overlap
    total_overlap = (n_patches * patch_size - dimension_size) / (n_patches - 1)
    
    # Generate starting positions
    positions = []
    for i in range(int(n_patches)):
        pos = int(i * (patch_size - total_overlap))
        if pos + patch_size > dimension_size:
            pos = dimension_size - patch_size
        if pos not in positions:  # Avoid duplicates
            positions.append(pos)
    
    return positions
    
def extract_3d_patches_minimal_overlap(
    arrays: list[np.ndarray],
    patch_size: tuple[int, int, int]
) -> tuple[list[np.ndarray], list[tuple[int, int, int]]]:
    """
    Extract 3D patches from multiple arrays with minimal overlap to cover the entire array.
    Now supports different patch sizes per dimension (e.g., (184, 96, 96)).
    """
    if not arrays or not isinstance(arrays, list):
        raise ValueError("Input must be a non-empty list of arrays")
    
    # Verify all arrays have the same shape
    shape = arrays[0].shape
    print(shape)
    if not all(arr.shape == shape for arr in arrays):
        raise ValueError("All input arrays must have the same shape")
    
    # patch_size is now a tuple
    px, py, pz = patch_size
    if px > shape[0] or py > shape[1] or pz > shape[2]:
        raise ValueError(
            f"Patch size {patch_size} cannot exceed volume shape {shape}"
        )
    
    m, n, l = shape
    patches = []
    coordinates = []
    
    # Calculate starting positions for each dimension
    x_starts = calculate_patch_starts(m, px)
    y_starts = calculate_patch_starts(n, py)
    z_starts = calculate_patch_starts(l, pz)
    
    # Extract patches from each array
    for arr in arrays:
        for x in x_starts:
            for y in y_starts:
                for z in z_starts:
                    patch = arr[x:x + px, y:y + py, z:z + pz]
                    patches.append(patch)
                    coordinates.append((x, y, z))
    
    return patches, coordinates


def select_model(model_ckpt_paths, target='dice_score'):

    assert target in ['dice_score', 'val_loss']

    model_scores = {}

    for model_ckpt_path in model_ckpt_paths:
        pattern = r"val_dice_mean=(\d\.[\d]+)-val_loss=(\d\.[\d]+)"

        match = re.search(pattern, model_ckpt_path)
        
        if match:
            dice_mean = float(match.group(1))
            val_loss = float(match.group(2))
            model_scores[model_ckpt_path] = {"dice_score": dice_mean, "val_loss": val_loss}

    
    if target == 'dice_score':
        return max(model_scores.items(), key=lambda item: item[1]["dice_score"])[0]

    return min(model_scores.items(), key=lambda item: item[1]["val_loss"])[0]


def write_copick(copick_config_path):

    config_blob = """
    {
        "name": "czii_cryoet_mlchallenge_2024",
        "description": "2024 CZII CryoET ML Challenge training data.",
        "version": "1.0.0",

        "pickable_objects": [
            {
                "name": "apo-ferritin",
                "is_particle": true,
                "pdb_id": "4V1W",
                "label": 1,
                "color": [  0, 117, 220, 128],
                "radius": 60,
                "map_threshold": 0.0418
            },
            {
                "name": "beta-amylase",
                "is_particle": true,
                "pdb_id": "1FA2",
                "label": 2,
                "color": [153,  63,   0, 128],
                "radius": 65,
                "map_threshold": 0.035
            },
            {
                "name": "beta-galactosidase",
                "is_particle": true,
                "pdb_id": "6X1Q",
                "label": 3,
                "color": [ 76,   0,  92, 128],
                "radius": 90,
                "map_threshold": 0.0578
            },
            {
                "name": "ribosome",
                "is_particle": true,
                "pdb_id": "6EK0",
                "label": 4,
                "color": [  0,  92,  49, 128],
                "radius": 150,
                "map_threshold": 0.0374
            },
            {
                "name": "thyroglobulin",
                "is_particle": true,
                "pdb_id": "6SCJ",
                "label": 5,
                "color": [ 43, 206,  72, 128],
                "radius": 130,
                "map_threshold": 0.0278
            },
            {
                "name": "virus-like-particle",
                "is_particle": true,
                "pdb_id": "6N4V",            
                "label": 6,
                "color": [255, 204, 153, 128],
                "radius": 135,
                "map_threshold": 0.201
            }
        ],

        "overlay_root": "./data/overlay",

        "overlay_fs_args": {
            "auto_mkdir": true
        },
        "static_root": "./data/test/static"
    }
    """

    with open(copick_config_path, "w") as f:
        f.write(config_blob)
