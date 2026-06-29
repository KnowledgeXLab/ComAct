import math
def check_mass_property_json_res(gt, gen, rel_tol=1e-3, abs_tol=1e-12):

    def _normalize(x):
        if x == 0:
            return 0.0
        exp = math.floor(math.log10(abs(x)))
        return x / (10 ** exp)

    def _is_equal(val_gt, val_gen):
        if isinstance(val_gt, dict) and isinstance(val_gen, dict):
            for k, v in val_gt.items():
                if k not in val_gen:
                    return False
                if not _is_equal(v, val_gen[k]):
                    return False
            return True

        elif isinstance(val_gt, list) and isinstance(val_gen, list):
            if len(val_gt) != len(val_gen):
                return False
            for item_gt, item_gen in zip(val_gt, val_gen):
                if not _is_equal(item_gt, item_gen):
                    return False
            return True

        elif isinstance(val_gt, (int, float)) and isinstance(val_gen, (int, float)):
            if abs(val_gt) <= abs_tol and abs(val_gen) <= abs_tol:
                return True
            if val_gt == 0 or val_gen == 0:
                return False
            return math.isclose(_normalize(val_gt), _normalize(val_gen),
                                 rel_tol=rel_tol, abs_tol=abs_tol)

        else:
            return val_gt == val_gen

    return 1.0 if _is_equal(gt, gen) else 0.0


def check_interference_detection_json_res(gt, gen, rel_tol=1e-3, abs_tol=1e-12):
    """
    "gt": {
        "components": {
            "count": 2,
            "names": [
                "51862_e5f65013_0010_1:1",
                "51862_e5f65013_0011_2:1"
            ]
        },
        "interference": {
            "count": 0,
            "total_volume": 0.0
        }
    }
    """
    try:
        if 'interference' in gt:
            if (gt["components"]["count"] == gen["components"]["count"] and
                gt["interference"]["count"] == gen["interference"]["count"] and
                math.isclose(gt["interference"]["total_volume"],gen["interference"]["total_volume"], rel_tol=rel_tol, abs_tol=abs_tol)):
                return 1.0
        elif 'hard_interference' in gt:
            if (gt["components"]["count"] == gen["components"]["count"] and
                gt["hard_interference"]["count"] == gen["hard_interference"]["count"] and
                math.isclose(gt["hard_interference"]["total_volume"],gen["hard_interference"]["total_volume"], rel_tol=rel_tol, abs_tol=abs_tol)):
                return 1.0
        return 0.0
    except Exception as e:
        print(e)
        return 0.0