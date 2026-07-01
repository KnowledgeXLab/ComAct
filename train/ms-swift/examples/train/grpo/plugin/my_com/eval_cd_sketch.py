import numpy as np
import matplotlib.pyplot as plt
from plyfile import PlyData, PlyElement
import trimesh
from scipy.spatial import cKDTree as KDTree
import ezdxf
from ezdxf import path
import os

def write_ply_2d(points_2d, filename, text=False):
    """ 
    Input: Nx2 (X, Y), expand it to Nx3 (X, Y, 0) and write it in PLY format.
    """
    n = points_2d.shape[0]
    points_3d = np.zeros((n, 3))
    points_3d[:, :2] = points_2d
    
    vertex_data = [(points_3d[i,0], points_3d[i,1], points_3d[i,2]) for i in range(n)]
    vertex = np.array(vertex_data, dtype=[('x', 'f4'), ('y', 'f4'), ('z', 'f4')])
    
    el = PlyElement.describe(vertex, 'vertex', comments=['vertices'])
    with open(filename, mode='wb') as f:
        PlyData([el], text=text).write(f)


def render_pc_to_image(ply_path, image_path, point_size=15.0, elev=90, azim=-90):
    """
    Expand Nx2 to Nx3, and fill the Z-axis with zeros.
    """
    mesh = trimesh.load(ply_path)
    points = np.asarray(mesh.vertices)

    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, projection="3d")
    
    try:
        ax.set_proj_type("ortho")
    except Exception:
        pass

    c = points[:, 0] 
    
    ax.scatter(
        points[:, 0], points[:, 1], points[:, 2],
        s=point_size,
        c=c,
        cmap="viridis",
        alpha=0.8,
        edgecolors='none'
    )

    ax.view_init(elev=elev, azim=azim)

    x, y = points[:, 0], points[:, 1]
    max_range = max(x.max()-x.min(), y.max()-y.min()) / 2.0
    mid_x, mid_y = (x.max()+x.min())/2, (y.max()+y.min())/2
    
    ax.set_xlim(mid_x - max_range, mid_x + max_range)
    ax.set_ylim(mid_y - max_range, mid_y + max_range)
    ax.set_zlim(-max_range, max_range)

    ax.set_axis_off()
    
    plt.savefig(image_path, dpi=200, bbox_inches="tight", pad_inches=0.1)
    plt.close()
    print(f"Image saved: {image_path}")


def normalize_pc_2d(pc):
    mn = pc.min(axis=0)
    mx = pc.max(axis=0)
    center = (mn + mx) / 2
    scale = np.max(mx - mn) # 2D
    pc_n = (pc - center) / (scale + 1e-12)
    return pc_n


def chamfer_dist_2d(gt_points, gen_points, offset=0, scale=1):
    gen_points = gen_points / scale - offset

    # one direction
    gen_points_kd_tree = KDTree(gen_points)
    one_distances, one_vertex_ids = gen_points_kd_tree.query(gt_points)
    gt_to_gen_chamfer = np.mean(np.square(one_distances))

    # other direction
    gt_points_kd_tree = KDTree(gt_points)
    two_distances, two_vertex_ids = gt_points_kd_tree.query(gen_points)
    gen_to_gt_chamfer = np.mean(np.square(two_distances))

    return gt_to_gen_chamfer + gen_to_gt_chamfer


def dxf2pc(dxf_path, n_samples=10000):
    try:
        doc = ezdxf.readfile(dxf_path)
    except Exception as e:
        print(f"Cannot open dxf file: {e}")
        return np.zeros((n_samples, 2))

    msp = doc.modelspace()
    all_raw_points = []

    for entity in msp:
        try:
            if entity.dxftype() == 'INSERT':
                sub_entities = entity.virtual_entities()
            else:
                sub_entities = [entity]

            for e in sub_entities:
                if e.dxftype() in ('LINE', 'ARC', 'CIRCLE', 'LWPOLYLINE', 'SPLINE', 'POLYLINE'):
                    p = path.make_path(e)
                    pts = [v.vec2 for v in p.flattening(distance=0.01, segments=4)]
                    if pts:
                        all_raw_points.extend(pts)
        except Exception:
            continue

    if not all_raw_points:
        print(f"WARNING: {os.path.basename(dxf_path)} contains no valid path!")
        # return np.zeros((n_samples, 2))
        return None

    raw_pc = np.array(all_raw_points)
    curr_n = raw_pc.shape[0]

    if curr_n >= n_samples:
        indices = np.linspace(0, curr_n - 1, n_samples).astype(int)
        final_pc = raw_pc[indices]
    else:
        diff = np.diff(raw_pc, axis=0)
        dist = np.sqrt((diff**2).sum(axis=1))
        accum_dist = np.concatenate(([0], np.cumsum(dist)))
        
        new_dist = np.linspace(0, accum_dist[-1], n_samples)
        final_pc_x = np.interp(new_dist, accum_dist, raw_pc[:, 0])
        final_pc_y = np.interp(new_dist, accum_dist, raw_pc[:, 1])
        final_pc = np.stack([final_pc_x, final_pc_y], axis=1)

    return final_pc


def eval_cd_sketch(gt_dxf_path, gen_dxf_path):
    pc_gt =  dxf2pc(gt_dxf_path)
    pc_gen =  dxf2pc(gen_dxf_path)
    if (pc_gt is not None) and (pc_gen is not None):
        return chamfer_dist(normalize_pc_2d(pc_gt), normalize_pc_2d(pc_gen))
    else:
        return -2
        