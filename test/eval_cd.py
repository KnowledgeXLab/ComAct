import numpy as np
from plyfile import PlyData, PlyElement
import trimesh
from scipy.spatial import cKDTree as KDTree

def read_ply(path):
    with open(path, 'rb') as f:
        plydata = PlyData.read(f)
        x = np.array(plydata['vertex']['x'])
        y = np.array(plydata['vertex']['y'])
        z = np.array(plydata['vertex']['z'])
        vertex = np.stack([x, y, z], axis=1)
    return vertex

def write_ply(points, filename, text=False):
    """ input: Nx3, write points to filename as PLY format. """
    points = [(points[i,0], points[i,1], points[i,2]) for i in range(points.shape[0])]
    vertex = np.array(points, dtype=[('x', 'f4'), ('y', 'f4'),('z', 'f4')])
    el = PlyElement.describe(vertex, 'vertex', comments=['vertices'])
    with open(filename, mode='wb') as f:
        PlyData([el], text=text).write(f)

def normalize_pc(pc):
    mn = pc.min(axis=0)
    mx = pc.max(axis=0)
    center = (mn + mx) / 2
    scale = np.linalg.norm(mx - mn)  # bbox 对角线
    pc_n = (pc - center) / (scale + 1e-12)
    return pc_n

def chamfer_dist(gt_points, gen_points, offset=0, scale=1):
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

def stl2pc(stl_path, n_points=8192, seed=123):
    mesh = trimesh.load(stl_path)
    np.random.seed(seed)
    pc_samples, _ = trimesh.sample.sample_surface(mesh, n_points)
    return pc_samples


def rot_x(deg: float) -> np.ndarray:
    a = np.deg2rad(deg)
    c, s = np.cos(a), np.sin(a)
    return np.array([
        [1, 0,  0],
        [0, c, -s],
        [0, s,  c],
    ], dtype=float)

def rot_y(deg: float) -> np.ndarray:
    a = np.deg2rad(deg)
    c, s = np.cos(a), np.sin(a)
    return np.array([
        [ c, 0, s],
        [ 0, 1, 0],
        [-s, 0, c],
    ], dtype=float)

def rot_z(deg: float) -> np.ndarray:
    a = np.deg2rad(deg)
    c, s = np.cos(a), np.sin(a)
    return np.array([
        [c, -s, 0],
        [s,  c, 0],
        [0,  0, 1],
    ], dtype=float)

def rotate_stl_trimesh(in_path: str, out_path: str,
                       ex=-90.0, ey=0.0, ez=-90.0):
    mesh = trimesh.load(in_path, force='mesh')
    if mesh.is_empty:
        raise ValueError("Loaded mesh is empty. Check input STL.")

    R = rot_z(ez) @ rot_y(ey) @ rot_x(ex)

    T = np.eye(4, dtype=float)
    T[:3, :3] = R

    mesh.apply_transform(T)
    mesh.export(out_path)
    # print(f"Saved rotated STL to: {out_path}")
    return out_path
    