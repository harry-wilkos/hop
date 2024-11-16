from ..util import alembic, place_node
from pathlib import Path
import _alembic_hom_extensions as abc
import math
import numpy as np
from scipy.spatial.transform import Rotation as rot

try:
    import hou
except ModuleNotFoundError:
    from ..util import import_hou

    hou = import_hou()

bindings = [
    "tx",
    "ty",
    "tz",
    "rx",
    "ry",
    "rz",
]

parm_expression = r"""
from hop.shelf_tools import alembic_parm_value
return alembic_parm_value()
"""

xfrom_expression = r"""
from hop.shelf_tools import alembic_transform_value
return alembic_transform_value()
"""


def extract_matrix(matrix):
    matrix4 = np.array(matrix).reshape(4, 4)
    matrix3 = matrix4[:3, :3] 
    scale = np.linalg.norm(matrix3, axis=0).tolist()

    rotation_matrix = matrix3 / scale  # Normalize the rotation matrix
    rotation = rot.from_matrix(rotation_matrix).as_euler("xyz", degrees=True).tolist()

    translate = matrix4[3, :3].tolist()
    return translate + rotation + scale


def alembic_transform_value():
    node = hou.pwd()
    parm_name = hou.expandString("$CH")
    file = node.evalParm("alembic_file")
    alembic_path = node.evalParm("alembic_path")
    alembic_file = Path(hou.text.expandString(file)).resolve().as_posix()

    final_transform = np.identity(4)
    current_path = alembic_path
    while current_path:
        xform = abc.getLocalXform(alembic_file, current_path, hou.frameToTime(hou.frame()))[0] 
        xform_matrix = np.array(xform).reshape((4, 4))
        final_transform = np.dot(final_transform, xform_matrix)
        current_path = "/".join(current_path.split("/")[:-1])

    print(np.array2string(final_transform, formatter={"all": lambda x: f"{x: .4f}"}))

    results = extract_matrix(final_transform)
    return results[bindings.index(parm_name)]


def alembic_parm_value():
    node = hou.pwd()
    parm_name = hou.expandString("$CH")
    file = node.evalParm("alembic_file")
    alembic_file = Path(hou.text.expandString(file)).resolve().as_posix()
    alembic_path = node.evalParm("alembic_path")
    cam_dic = abc.alembicGetCameraDict(
        alembic_file, alembic_path, hou.frameToTime(hou.frame())
    )
    if parm_name in cam_dic:
        value = cam_dic[parm_name]
    else:
        parm = node.parm(parm_name)
        value = parm.parmTemplate().defaultValue()[parm.componentIndex()]
    return value


def obj_alembic_cam(kwargs: dict):
    file = hou.ui.selectFile(
        start_directory=None,
        title="Choose Alembic",
        collapse_sequences=False,
        file_type=hou.fileType.Alembic,
        chooser_mode=hou.fileChooserMode.Read,
    )
    if file:
        path = Path(hou.text.expandString(file)).resolve().as_posix()
        cams = alembic.find_cam_paths(path)
        for cam in cams:
            node = place_node(kwargs, "obj", "cam")
            if node is not None:
                template = node.parmTemplateGroup()
                alembic_file = hou.StringParmTemplate(
                    name="alembic_file",
                    label="Alembic File",
                    num_components=1,
                    string_type=hou.stringParmType.FileReference,
                    file_type=hou.fileType.Geometry,
                )
                alembic_path = hou.StringParmTemplate(
                    name="alembic_path", label="Alembic Path", num_components=1
                )
                template.append(alembic_file)
                template.append(alembic_path)
                node.setParmTemplateGroup(template)
                node.setParms({"alembic_file": file, "alembic_path": cam})
                parms = abc.alembicGetCameraDict(path, cam, 0)
                resx = node.evalParm("resx")
                resy = node.evalParm("resy")
                for xform in bindings:
                    xf_parm = node.parm(xform)
                    xf_parm.setExpression(
                        xfrom_expression, hou.exprLanguage.Python, True
                    )
                for key in parms:
                    parm = node.parm(key)
                    if parm is not None:
                        parm.setExpression(
                            parm_expression, hou.exprLanguage.Python, True
                        )
                    elif key == "filmaspectratio" and not math.isclose(
                        resx / resy, parms[key]
                    ):
                        hou.ui.displayMessage(
                            text=f"{resx} x {resy} is not the same aspect ration as the alembic ({round(parms[key], 2)})",
                            severity=hou.severityType.Warning,
                            title="Alembic camera",
                        )


if __name__ == "__main__":
    alembic_transform_value()
